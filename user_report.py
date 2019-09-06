#! /usr/bin/env python

import argparse
import sys

import user
import slack_formatter
import report_generator

def uid_for(token):
    """
    token is either a username or a UID.  If UID, make sure it's valid
    If username, try to find a match and return the match's uid
    """
    uid = token.upper()
    if u.get(uid):
        return uid

    if token[0] != '@':
        raise RuntimeError("Usernames must start with '@'")

    matches = u.find(token)
    if len(matches) == 0:
        raise RuntimeError("Could not find a user with name '{}'".format(token))
    if len(matches) > 1:
        raise RuntimeError("Found too many matches for user {}: {}".format(token, json.dumps(matches, indent=4)))
    uid = matches[0]['id']
    return uid

parser = argparse.ArgumentParser(description='Run a user-level Slack activity report.')
parser.add_argument("--uid", help="Run the report for this UID")
parser.add_argument("--regen", action="store_true", help="Regenerate stats even if we have them")
parser.add_argument("--name", help="Run the report for this user")
parser.add_argument("--nosend", action="store_true", help="Do not send report")
parser.add_argument("--fake", action="store_true", help="Use bogus user names")
parser.add_argument("--sendto", help="Specify @username or #channel to send report to rather than to the user who owns the report")
args = parser.parse_args()

slack_formatter_obj = slack_formatter.SlackFormatter(fake=args.fake)
rg = report_generator.ReportGenerator()
u = user.User()

if (not args.uid) and (not args.name):
    raise RuntimeError("--uid|--name is required")

if args.uid:
    uid = uid_for(args.uid)
else:
    uid = uid_for(args.name)

print("Will run report for UID {}".format(uid))

latest_week_start = rg.latest_week_start()
days = 7
send = not args.nosend
(report, previous_report) = rg.report(latest_week_start, days, users=[uid], force_generate=args.regen)
slack_formatter_obj.send_report(uid, report, previous_report, send=send)
