#! /usr/bin/env python

import argparse

import slack_formatter
import report_generator

parser = argparse.ArgumentParser(description='Run a user-level Slack activity report.')
parser.add_argument("--uid", help="Run the report for this UID")
parser.add_argument("--fake", action="store_true", help="Use fake usernames")
parser.add_argument("--regen", action="store_true", help="Regenerate stats even if we have them")
args = parser.parse_args()

slack_formatter_obj = slack_formatter.SlackFormatter(fake=args.fake)
print("args.fake is {}".format(args.fake))
rg = report_generator.ReportGenerator(fake=args.fake)
latest_week_start = rg.latest_week_start()
days = 7
(report, previous_report) = rg.report(latest_week_start, days, users=[args.uid], force_generate=args.regen)
slack_formatter_obj.send_report(args.uid, report, previous_report)
