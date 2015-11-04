#!/usr/bin/python2
# -*- coding: utf-8 -*-

# ==============================================================================
#      Frank Matranga's Third-party Regis High School Python Module
# ==============================================================================

import getopt
import sys
import json
import os
import requests
from lxml import html
from pymongo import MongoClient

PATH = "./secrets.json"
DB_URL = "localhost:27017"
DB_NAME = "regis"


def usage():
    print "usage: trms [--help] [-p <json_path>] [-u <db_url>] [-n <db_name>]"


def get_opts():
    if len(sys.argv) > 10:
        print('Too many arguments.')
        usage()
        sys.exit(2)

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'p:u:n:h', ['path=', 'dburl=', 'dbname=', 'help'])
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
        else:
            usage()
            sys.exit(2)


class TRMS:
    def __init__(self, PATH, DB_URL, DB_NAME):
        self.path = PATH
        self.db_url = DB_URL
        self.db_name = DB_NAME

        # MongoDB
        self.client = None
        self.db = None

        self.secrets = None
        self.session = None
        self.running = True

        print self.path, self.db_url, self.db_name
        print " --- Initializing TRMS Alpha 1 --- \n"
        self.get_credentials()
        self.login()
        self.connect()
        print " --- DONE --- \n"
        self.run()

    def get_credentials(self):
        if os.path.isdir(self.path):
            if self.path[-1] != "/":
                self.path += "/"
            self.path += "secrets.json"
        else:
            if not os.path.exists(self.path):
                print "'" + self.path + "' does not exist."
                self.quit()
        try:
            self.secrets = json.loads(open(self.path).read())
        except (ValueError, IOError):
            print "'" + self.path + "' is not a valid JSON file."
            self.quit()

        try:
            self.secrets['regis_username']
            self.secrets['regis_password']
        except KeyError:
            print "Missing required credentials in JSON file."
            self.quit()

        print "Using found credentials for " + self.secrets['regis_username'] + "."

    def login(self):
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
        try:
            title = parsed_body.xpath('//title/text()')[0]
            if not "Intranet" in title:
                print "Failed to login to the Intranet, check your credentials in '" + self.path + "'."
                self.quit()
        except:
            print "Failed to login to the Intranet, check your credentials in '" + self.path + "'."
            self.quit()

        print "Successfully logged in to the Intranet."
        self.session = session

    def connect(self):
        uri = "mongodb://" + self.db_url
        try:
            self.client = MongoClient(uri)
            self.db = self.client[self.db_name]
            try:
                self.db.authenticate('ontrac', 'ontrac')
            except Exception:
                pass
            self.db.students.count()
        except Exception as e:
            print "Failed to connect to '" + uri + "'"
            self.quit()
        print "Successfully connected to Database at '" + self.uri + "/" + self.db_name + "'"

    def run(self):
        while self.running:
            pass
        self.quit()

    def quit(self):
        if self.client is not None:
            self.client.close()
        sys.exit(0)


def main():
    get_opts()
    TRMS(PATH, DB_URL, DB_NAME)

main()
