#!/usr/bin/python3

import argparse
from api import API

parser = argparse.ArgumentParser(description="Insertion to DB")

parser.add_argument('-a', '--address', help='IP address')
parser.add_argument('-d', '--description', help='modify description')
parser.add_argument('-n', '--name', help='rule name')

parser.add_argument('code', help='rule code to insert')
parser.add_argument('ruleset', nargs='?', help='Rule set content')

args = parser.parse_args()

# Input Validation of the argument parsing
if not args.ruleset:
    ruleset = "CUSTOM"
else:
    ruleset = args.ruleset

if not args.name:
    name = "default name"
else:
    name = args.name

if not args.description:
    description = "default description"
else:
    description = args.description

# EXECUTION
token = API.login()
res = API.insert_rule(token, args.code, ruleset, name, description)
if res.ok:
    print("Successful Insertion")
else:
    print("Insertion failure")

