#! /usr/bin/env python

import argparse
import sys

import user
import utils
import channel
import slack_user_report
import report_generator

import report_utils

parser = argparse.ArgumentParser(description='Run a user-level Slack activity report.')
parser.add_argument("--uid", help="Run the report for this UID")
parser.add_argument("--regen", action="store_true", help="Regenerate stats even if we have them")
parser.add_argument("--name", help="Run the report for this user")
parser.add_argument("--nosend", action="store_true", help="Do not send report")
parser.add_argument("--fake", action="store_true", help="Use bogus user names")
parser.add_argument("--override", help="Specify @username or #channel to send report to rather than to the user who owns the report")
args = parser.parse_args()

slack_formatter_obj = slack_user_report.SlackUserReport(fake=args.fake)
rg = report_generator.ReportGenerator()
u = user.User()
c = channel.Channel()

if (not args.uid) and (not args.name):
    raise RuntimeError("--uid|--name is required")

if args.uid:
    uid = report_utils.uid_for(args.uid)
else:
    uid = report_utils.uid_for(args.name)

if args.override:
    destination = report_utils.override(args.override)
else:
    destination = uid
print("Will send report to {}".format(destination))
print("Will run report for UID {}".format(uid))

latest_week_start = rg.latest_week_start()
days = 7
send = not args.nosend
(report, previous_report) = rg.report(latest_week_start, days, users=[uid], force_generate=args.regen)
slack_formatter_obj.send_report(uid, report, previous_report, send=send, override_uid=destination)
