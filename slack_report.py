#! /usr/bin/env python

import argparse
import os.path
import sys

import report_generator

import slack

import utils
import report_utils

import slack_global_report
import slack_brief_global_report

parser = argparse.ArgumentParser(description='Run a global Slack activity report.')
parser.add_argument("--regen", action="store_true", help="Regenerate stats even if we have them")
parser.add_argument("--nosend", action="store_true", help="Do not send report")
parser.add_argument("--destination", help="Specify @username or #channel to send report to")
help = "Generate brief version of the global Slack activity report, do not send PDF"
parser.add_argument("--brief", action="store_true", help=help)
args = parser.parse_args()

rg = report_generator.ReportGenerator()
if args.brief:
    sgr = slack_brief_global_report.SlackBriefGlobalReport()
else:
    sgr = slack_global_report.SlackGlobalReport()

send = not args.nosend
if send and not args.destination:
    raise RuntimeError("Must specify --destination if did not specify --nosend")
if args.destination and args.nosend:
    raise RuntimeError("You cannot specify both --nosend and a --destination")
if args.destination:
    destination = report_utils.override(args.destination)
    print("Will send report to {}".format(destination))


latest_week_start = rg.latest_week_start()
days = 7

(report, previous_report) = rg.report(latest_week_start, days, force_generate=args.regen)

f = open("report.json", "w")
f.write(utils.dumps(report))
f.close()
f = open("previous_report.json", "w")
f.write(utils.dumps(previous_report))
f.close()

if send:
    sgr.send_report(report, previous_report, send=send, destination=destination)
