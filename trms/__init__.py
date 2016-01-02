#!/usr/bin/python2
# -*- coding: utf-8 -*-

# ==============================================================================
#      Frank Matranga's Third-party Regis High School Moodle Scraper
# ==============================================================================

import getopt
import json
import os
import sys
import traceback
from time import sleep

import requests
from lxml import html
from pymongo import MongoClient

SKIP_LOGINS_AND_CONNECTION = False

PATH = "./secrets.json"
DB_URL = "localhost:27017"
DB_NAME = "regis"
SCRAPE_TYPE = None
START_AT = None
END_AT = None


def usage():
    """
    Prints the usage for the command line.
    """
    print "usage: trms [--help] [-p <json_path>] [-u <db_url>] [-n <db_name>] [-t <scrape_type>] [-s <start_mID>] [-e <end_mID>]"


# ----------- CLI ARGUMENTS -----------
if len(sys.argv) > 14:
    print('Too many arguments.')
    usage()
    sys.exit(2)

try:
    opts, args = getopt.getopt(sys.argv[1:], 'p:u:n:t:s:e:h',
                               ['path=', 'dburl=', 'dbname=', 'scrapetype=', 'startmid=', 'endmid=', 'help'])
except getopt.GetoptError:
    usage()
    sys.exit(2)

for opt, arg in opts:
    if opt in ('-h', '--help'):
        usage()
        sys.exit(2)
    elif opt in ('-p', '--path'):
        PATH = arg
    elif opt in ('-u', '--dburl'):
        DB_URL = arg
    elif opt in ('-n', '--dbname'):
        DB_NAME = arg
    elif opt in ('-t', '--scrapetype'):
        if arg in ['course', 'person']:
            SCRAPE_TYPE = arg
        else:
            print "Invalid scrape type. Try 'person' or 'course'."
            sys.exit()
    elif opt in ('-s', '--startmid'):
        try:
            START_AT = int(arg)
        except ValueError:
            print "Please user integers for -s and -e."
            sys.exit(2)
    elif opt in ('-e', '--endmid'):
        try:
            END_AT = int(arg)
        except ValueError:
            print "Please user integers for -s and -e."
            sys.exit(2)
    else:
        usage()
        sys.exit(2)

if None == END_AT and None == START_AT:
    START_AT = 1
    if SCRAPE_TYPE == "course":
        END_AT = 600
    else:
        END_AT = 2500

if None == START_AT:
    START_AT = 1

if None == END_AT:
    END_AT = START_AT

if START_AT > END_AT:
    print "Starting Moodle ID (-s) must be less than ending Moodle ID (-e)."
    sys.exit(2)

if None == SCRAPE_TYPE:
    print "No scrape type (-t) specified."
    sys.exit(2)


# ----------------------------------------


class TRMS:
    def __init__(self, path, db_url, db_name, scrape_type, start_mid, end_mid):
        self.path = path
        self.db_url = db_url
        self.db_name = db_name
        self.scrape_type = scrape_type
        self.start_mid = start_mid
        self.end_mid = end_mid

        # MongoDB
        self.client = None
        self.db = None

        self.secrets = None  # Intranet username/password from JSON file
        self.session = None  # Requests session for persistent login
        self.running = True

        # print self.path, self.db_url, self.db_name
        print " --- Initializing TRMS Alpha 1 --- "
        if not SKIP_LOGINS_AND_CONNECTION:
            self.get_credentials()
            self.login()
            self.connect()
        print ""
        self.run()

    def get_credentials(self):
        """
        Validates passed path to JSON file and then tries to parse it for username/password
        """
        if os.path.isdir(self.path):  # Is it a directory?
            if self.path[-1] != "/":  # If a dir, add a ending / if it doesn't already.
                self.path += "/"
            self.path += "secrets.json"
            if not os.path.exists(self.path):  # Does the file not exist?
                print "'" + self.path + "' does not exist."
                self.quit()

        # Try to open the file and parse it for JSON
        try:
            self.secrets = json.loads(open(self.path).read())
        except (ValueError, IOError):
            print "'" + self.path + "' is not a valid JSON file."
            self.quit()

        # Make sure it contains the two needed keys
        try:
            self.secrets['regis_username']
            self.secrets['regis_password']
        except KeyError:
            print "Missing required credentials in JSON file."
            self.quit()

        print "Using found credentials for " + self.secrets['regis_username'] + "."

    def login(self):
        """
        Attempts to login to Moodle and then the Intranet with the passed credentials
        and keep a persistent session for later.
        """
        creds = {'username': self.secrets['regis_username'], 'password': self.secrets['regis_password']}

        url = "https://moodle.regis.org/login/index.php"
        session = requests.Session()
        r = session.post(url, data=creds)
        parsed_body = html.fromstring(r.text)
        title = parsed_body.xpath('//title/text()')[0]

        # Check whether login was successful or not
        if not "Dashboard" in title:
            print "Failed to login to Moodle, check your credentials in '" + self.path + "'."
            self.quit()
        print "Successfully logged into Moodle."

        url = "https://intranet.regis.org/login/submit.cfm"
        values = creds
        r = session.post(url, data=values)
        parsed_body = html.fromstring(r.text)

        # When logged in to the Intranet the page title is 'Regis Intranet' so we can use this to
        # check for a successful login.
        try:
            title = parsed_body.xpath('//title/text()')[0]
            if not "Intranet" in title:
                print "Failed to login to the Intranet, check your credentials in '" + self.path + "'."
                self.quit()
        except Exception:
            print "Failed to login to the Intranet, check your credentials in '" + self.path + "'."
            self.quit()

        print "Successfully logged in to the Intranet."
        self.session = session  # Store this in a persistent session so the logins are saved

    def connect(self):
        """
        Attempts to connect to MongoDB using the URI (or URL?) passed, and attempts to authenicate if possible.
        """
        uri = "mongodb://" + self.db_url
        try:
            self.client = MongoClient(uri)
            self.db = self.client[self.db_name]
            try:
                self.db.authenticate('ontrac', 'ontrac')  # TODO: add support for this in JSON file
            except Exception:
                pass
            self.db.students.count()
        except Exception as e:
            print "Failed to connect to '" + uri + "'"
            self.quit()

        sleep(1)  # nasty hack to make it seems like something actually happens since the connection is so fast
        print "Successfully connected to Database."

    def run(self):
        try:
            print "[ scrape", self.scrape_type, "with Moodle ID's", self.start_mid, "to", self.end_mid, "]"
            for mid in range(self.start_mid, self.end_mid + 1):
                self.extract(mid)
            self.quit()
        except Exception as e:
            print e
            traceback.print_exc()
            self.quit()

    def extract(self, mid):
        base_url = "http://moodle.regis.org/user/profile.php?id="
        if self.scrape_type == "course":
            base_url = "http://moodle.regis.org/course/view.php?id="
            if mid == 1:  # Moodle Course 1 is your homepage
                return

        # Get the page
        r = self.session.get(base_url + str(mid)+"&showallcourses=1")  # The url is created by appending the current ID to the base url
        # Parse the html returned so we can find the title
        parsed_body = html.fromstring(r.text)

        # Get the page title
        title = parsed_body.xpath('//title/text()')
        # Check if page is useful

        # --- POSSIBLE TITLES ---
        # Matranga, Frank: Public profile
        # Course: Computer Technology I: Croce
        # Course: Advisement 2B-1: Bonagura
        # Notice
        # Error
        # (Empty)

        if len(title) == 0:  # Check if page title exists
            self.remove(mid, [])
            print "Bad title"
            return

        title = parsed_body.xpath('//title/text()')[0]
        parts = title.split(": ")

        # Make sure its a valid page on some item
        if "Test" in title:
            self.remove(mid, parts)
            print "Skipped test entry"
            return
        if ("Error" in title.strip()) or ("Notice" in title.strip()):
            self.remove(mid, parts)
            print "Error or Notice skipped"
            return
        try:
            name = parts[1]
        except:
            name = parts[0]
            # traceback.print_exc()

        # print mid, title

        if self.scrape_type == "course":
            if "Advisement " in name:
                self.extract_advisement(parsed_body, parts, mid)
            else:
                self.extract_course(parsed_body, parts, mid)
        else:
            self.extract_person(parsed_body, parts, mid)

    def extract_person(self, body, parts, mid):
        out = {}

        name_parts = body.xpath('//title/text()')[0].split(":")[0].split(" ")[::-1] if \
            len(body.xpath('//title/text()')) > 0 else ['Unknown']
        #department = body.xpath('//dl/dd[1]/text()')

        # Advisement (for students) or Department (for staff)
        department = body.xpath('//dd[../dt = "Department"]/text()')
        if len(department) == 0:
            return
        else:
            department = department[0]

        # Class list on profile with links to each
        class_as = body.xpath('//dd[../dt = "Courses"]//a')
        classes = []
        for a in class_as:
            #print a.get("href")
            classes.append(int(a.get("href").split("?id=")[1].replace("&showallcourses=1", "")))

        #print "CLASSES: ", classes
        # Test department to get user type
        f = department[0]
        try:
            int(f)  # This would work if it was a student since department would be like '1C-2' so f would be '1'
            userType = "student"
        except ValueError:
            userType = "teacher"

        if department.startswith("REACH"):
            userType = "other"

        # Place holder profile image
        picsrc = "/images/person-placeholder.jpg"

        # Get Intranet profile picture
        for img in body.xpath('//img[@class="userpicture"]'):
            picsrc = img.get("src")

        collect = self.db.courses
        courses = []  # This will store the _id's of a user's courses

        intranet = self.session.get(
            "http://intranet.regis.org/infocenter/default.cfm?FuseAction=basicsearch&searchtype=namewildcard&criteria=" +
            name_parts[0] + "%2C+" + name_parts[1] + "&[whatever]=Search")
        intrabody = html.fromstring(intranet.text)

        schedule = "<h2>Not Found</h2>"

        if userType == "student":
            style = "float:left;width:200px;"
        else:
            style = "float:left; width:200px;"

        # Get student Advisement
        if userType == "student":
            if classes:
                adv = self.db.advisements.find_one({"mID": classes[0]})
                if adv:
                    department = adv['title']

        # Get the list of search results (hopefully just one)
        search_results = intrabody.xpath('//div[@style="' + style + '"]/span[1]/text()')
        # print search_results
        if len(search_results) == 0:
            print str(mid) + ": Found on Moodle but not the Intranet. Disregarding."
            return  # should people found only on Moodle be included?

        # print "Intranet found "+str(len(search_results))+" search results for", name_parts

        # Go through Intrant search results for user until the correct one is found
        for result in search_results:
            index = search_results.index(result)
            name_p = result.encode('utf-8').split(", ")
            intranet_dep = name_p[1].split(" ")[1].replace("(", "").replace(")", "")

            first_name = name_p[1].split(" ")[0]
            last_name = name_p[0]
            # print "Attempting to match "+ str([name_parts[0], name_parts[1], department])+" with " + str([last_name, first_name, intranet_dep])
            if [last_name, first_name] == name_parts:
                if userType == "student":
                    if intranet_dep == department:
                        # print "Yup!"
                        break
                else:
                    # print "Yup!"
                    break
                    # print "Nope"

        # Get user email from correct search result
        email = intrabody.xpath('//div[@style="' + style + '"]/span[2]/a/text()')[index]
        # print email

        # Get username from email
        username = str(email).replace("@regis.org", "").lower()

        pic_elm = intrabody.xpath('//div[@style="' + style + '"]/a')[index]
        # Get user Student ID# from profile picture
        code = pic_elm.get("href").split("/")[-1].replace(".jpg", "")

        # Student schedule HTML table and teacher HTML table uses very slightly differing style attributes
        if userType == "student":
            style = "float:left;width:200px;"
            scheduleurl = "http://intranet.regis.org/infocenter?StudentCode=" + code
        else:
            style = "float:left; width:200px;"
            scheduleurl = "http://intranet.regis.org/infocenter/default.cfm?StaffCode=" + code
        # THIS CAN BREAK AT ANY TIME ^^^

        # Request url for user's profile to get the schedule
        htmlschedulereq = self.session.get(scheduleurl)
        htmls = html.fromstring(htmlschedulereq.text)
        if len(htmls.xpath('//div[@id="main"]/table[4]')) > 0:
            schedule = html.tostring(htmls.xpath('//div[@id="main"]/table[4]')[0])

        if userType == "student":
            out = {
                "mID": mid,
                "firstName": name_parts[1],
                "lastName": name_parts[0],
                "username": username,
                "code": code,
                "mpicture": picsrc,
                "ipicture": pic_elm.get("href"),
                "schedule": schedule,
                "email": username + "@regis.org",
                "advisement": department,
                "sclasses": classes,
            }

            # Check if this student already exists
            existing = self.db.students.find_one({'mID': mid})

            newID = None
            if existing is not None:
                if self.db.students.update_one({'mID': mid}, {'$set': out}).modified_count > 0:
                    print "Updated student."
                newID = existing['_id']
            else:
                newID = self.db.students.insert_one(out).inserted_id
                print "Added new student."

            print str(
                mid) + ": Student " + username + " in Advisement " + department + " with Student ID " + code + " in " + str(
                len(classes)) + " courses"
            if classes:
                total = len(classes) # Total number of courses
                matched = [] # List of mID's of courses Successfully matched

                # Add student's _id to his advisement
                if newID not in self.db.advisements.find_one({"mID": classes[0]})['students']:
                    self.db.advisements.update_one({"mID": classes[0]}, {"$push": {"students": newID}})
                matched.append(classes[0]) # Advisement

                for c in classes:  # C IS A MOODLE ID FOR A COURSE
                    course = collect.find_one({"mID": c})
                    if course:
                        #print "FOUND "+course['title']
                        cID = course['_id']
                        courses.append(cID)
                        matched.append(c)
                        # Add student to advisement (IF HE IS NOT ALREADY)
                        if newID not in self.db.courses.find_one({"mID": c})['students']:
                            collect.update_one({"mID": c}, {"$push": {"students": newID}})

                for mID in classes:
                    if mID not in matched:
                        print "FAILED TO MATCH COURSE " +str(mID)

                # print courses
                self.db.students.update_one({"_id": newID}, {"$set": {"courses": courses}})
        else:
            print str(
                mid) + ": Staff Member " + username + " of the " + department + " Department with Staff ID " + code + " in " + str(
                len(classes)) + " courses"
            out = {
                "mID": mid,
                "userType": userType,
                "image": picsrc,
                "code": code,
                "ipicture": pic_elm.get("href"),
                "department": department,
                "firstName": name_parts[1],
                "lastName": name_parts[0],
                "schedule": schedule,
                "username": username,
                "email": email,
                "sclasses": classes,
                "courses": courses
            }
            existing = self.db.teachers.find_one({"mID": mid})

            newID = None
            if existing is not None:
                newID = existing['_id']
                self.db.teachers.update_one({"mID": mid}, {"$set": out})
            else:
                out['courses'] = []
                newID = self.db.teachers.insert_one(out).inserted_id

            # print "Teacher " + str(mid) + ": " + str(newID)
            for c in classes:
                print c
                course = collect.find_one({"mID": c})
                if course:
                    print "FOUND"
                    if name_parts[0] in course["full"]:
                        collect.update_one({'mID': c}, {'$set': {'teacher': newID}})
                    if course['_id'] not in self.db.teachers.find_one({"_id": newID})['courses']:
                        self.db.teachers.update_one({"_id": newID}, {"$push": {"courses": course['_id']}})
                adv = self.db.advisements.find_one({"mID": c})
                if adv:
                    self.db.advisements.update_one({
                        'mID': c
                    }, {
                        '$set': {
                            'teacher': newID
                        }
                    })
                    # print out

    def extract_advisement(self, body, parts, mid):
        name = parts[1]
        out = {
            "mID": mid,
            "title": name.replace("Advisement ", "")
        }
        existing = self.db.advisements.find_one({"mID": mid})
        newID = None
        if existing:
            newID = existing['_id']
            self.db.advisements.update_one({"mID": mid}, {"$set": out})
        else:
            out['students'] = []
            newID = self.db.advisements.insert_one(out).inserted_id

        print str(mid) + ": Advisement " + out['title'] + " " + str(newID)

    def extract_course(self, body, parts, mid):
        # print "REACHED HERE"
        try:
            name = parts[1]
        except IndexError:
            name = parts[0]
        ps = name.split(" ")

        teacher = parts[2] if len(parts) > 2 else "no"
        grade = 13
        for pa in ps:
            for index, g in enumerate(["I", "II", "III", "IV"]):
                if g == pa:
                    grade = 9 + index
            try:
                grade = int(pa)
            except ValueError:
                pass
        courseType = "class"
        if "Club" in name or "Society" in name:
            courseType = "club"

        if "REACH" in name or "Reach" in name:
            courseType = "reach"

        out = {
            "mID": mid,
            "full": ": ".join(parts),
            "courseType": courseType,
            "title": name,
            "grade": grade
        }
        existing = self.db.courses.find_one({"mID": mid})
        newID = None
        if existing:
            newID = existing['_id']
            self.db.courses.update_one({"mID": mid}, {"$set": out})
        else:
            out['students'] = []
            newID = self.db.courses.insert_one(out).inserted_id

        print str(mid) + ": Course " + str(newID)

    def remove(self, mid, parts):
        try:
            if self.scrape_type == "course":
                self.db.courses.delete_one({'mID': mid})
                self.db.advisements.delete_one({'mID': mid})
            else:
                self.db.students.delete_one({'mID': mid})
                self.db.teachers.delete_one({'mID': mid})
        except:
            pass

    def quit(self):
        if self.client is not None:
            self.client.close()
        sys.exit(0)


def main():
    TRMS(PATH, DB_URL, DB_NAME, SCRAPE_TYPE, START_AT, END_AT)


if __name__ == "__main__":
    main()
