#!/usr/bin/python2
# -*- coding: utf-8 -*-

# ==============================================================================
#      Frank Matranga's Third-party Regis High School Python Module
# ==============================================================================

import getopt
import sys

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
        print self.path, self.db_url, self.db_name


def main():
    get_opts()
    TRMS(PATH, DB_URL, DB_NAME)

if __name__ == "__main__":
    main()
