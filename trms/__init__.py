#!/usr/bin/python2
# -*- coding: utf-8 -*-

# ==============================================================================
#      Frank Matranga's Third-party Regis High School Python Module
# ==============================================================================

import getopt
import json
import os
import sys
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


# CLI ARGUMENTS
if len(sys.argv) > 10:
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

# ---------------------------


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
        if not "My home" in title:
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
        except KeyboardInterrupt:
            print ""
            self.quit()

    def extract(self, mid):
        base_url = "http://moodle.regis.org/user/profile.php?id="
        if self.scrape_type == "course":
            base_url = "http://moodle.regis.org/course/view.php?id="

        # Get the page
        r = self.session.get(base_url + str(mid))  # The url is created by appending the current ID to the base url
        # Parse the html returned so we can find the title
        parsed_body = html.fromstring(r.text)

        # Get the page title
        title = parsed_body.xpath('//title/text()')
        # Check if page is useful
        if len(title) == 0:
            print "Bad title"
            return
        if "Test" in title:
            print "Skipped test entry"
            return

        if ("Error" in title[0].strip()) or ("Notice" in title[0].strip()):
            print "Error or Notice skipped"
            return
        title = parsed_body.xpath('//title/text()')[0]
        parts = title.split(": ")

        page_for = parts[0]

        print mid, title

        if page_for == "Course":
            if "Advisement " in parts[1]:
                self.extract_advisement(parsed_body, parts, mid)
            else:
                self.extract_course(parsed_body, parts, mid)
        else:
            self.extract_person(parsed_body, parts, mid)

    def extract_person(self, body, parts, mid):
        pass

    def extract_advisement(self, body, parts, mid):
        name = parts[1]
        out = {
            "mID": mid,
            "title": name.replace("Advisement ", "")
        }
        print out

    def extract_course(self, body, parts, mid):
        name = parts[1]
        ps = name.split(" ")

        teacher = parts[2] if len(parts) > 2 else "no"

    def quit(self):
        if self.client is not None:
            self.client.close()
        sys.exit(0)


def main():
    TRMS(PATH, DB_URL, DB_NAME, SCRAPE_TYPE, START_AT, END_AT)


if __name__ == "__main__":
    main()
