#!/usr/bin/python2
# -*- coding: utf-8 -*-

# ==============================================================================
#      Frank Matranga's Third-party Regis High School Python Module
# ==============================================================================

import getopt
import sys
import json
import os

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

        self.secrets = None

        self.running = True

        print self.path, self.db_url, self.db_name
        print " --- Initializing TRMS Alpha 1 --- \n"
        self.get_credentials()
        self.connect()
        self.run()

    def get_credentials(self):
        if os.path.isdir(self.path):
            if self.path[-1] != "/":
                self.path += "/"
            self.path += "secrets.json"
        else:
            if not os.path.exists(self.path):
                print "'"+self.path+"' does not exist."
                self.quit()
        try:
            self.secrets = json.loads(open(self.path).read())
        except (ValueError, IOError):
            print "'"+self.path+"' is not a valid JSON file."
            self.quit()

        try:
            self.secrets['regis_username']
            self.secrets['regis_password']
        except KeyError:
            print "Missing required credentials in JSON file."
            self.quit()

        print "Using found credentials for "+self.secrets['regis_username']+"."

    def connect(self):
        pass

    def run(self):
        while self.running:
            pass
        self.quit()

    def quit(self):
        sys.exit(0)


def main():
    get_opts()
    TRMS(PATH, DB_URL, DB_NAME)

main()

