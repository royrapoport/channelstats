#! /usr/bin/env python

import argparse
import sys

import user
import utils
import channel
import slack_channel_report
import report_generator
import report_utils

parser = argparse.ArgumentParser(description='Run a user-level Slack activity report.')
parser.add_argument("--cid", help="Run the report for this CID")
parser.add_argument("--regen", action="store_true", help="Regenerate stats even if we have them")
parser.add_argument("--name", help="Run the report for this channel")
parser.add_argument("--nosend", action="store_true", help="Do not send report")
parser.add_argument("--fake", action="store_true", help="Use bogus user names")
help = "Specify @username or #channel to send report to rather than to the user who owns the report"
parser.add_argument("--override", help=help)
args = parser.parse_args()

slack_formatter_obj = slack_channel_report.SlackChannelReport(fake=args.fake)
rg = report_generator.ReportGenerator()
u = user.User()
c = channel.Channel()

if (not args.cid) and (not args.name):
    raise RuntimeError("--cid|--name is required")

if args.cid:
    cid = report_utils.cid_for(args.cid)
else:
    cid = report_utils.cid_for(args.name)

if args.override:
    destination = report_utils.override(args.override)
else:
    destination = cid
print("Will send report to {}".format(destination))
print("Will run report for CID {}".format(cid))

latest_week_start = rg.latest_week_start()
days = 7
send = not args.nosend
(report, previous_report) = rg.report(latest_week_start, days, channels=[cid],
                                      force_generate=args.regen)
slack_formatter_obj.send_report(cid, report, previous_report, send=send, override_cid=destination)
