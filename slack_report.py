#! /usr/bin/env python

import argparse
import os.path
import sys

import report_generator
import html_formatter
import pdf_formatter

import slack_token
import slack

import utils
import report_utils

parser = argparse.ArgumentParser(description='Run a user-level Slack activity report.')
parser.add_argument("--regen", action="store_true", help="Regenerate stats even if we have them")
parser.add_argument("--nosend", action="store_true", help="Do not send report")
parser.add_argument("--destination", help="Specify @username or #channel to send report to")
args = parser.parse_args()

rg = report_generator.ReportGenerator()
html = html_formatter.HTMLFormatter()
pdf = pdf_formatter.PDFFormatter()

send = not args.nosend
if not args.destination:
    raise RuntimeError("Must specify --destination")
destination = report_utils.override(args.destination)
print("Will send report to {}".format(destination))


latest_week_start = rg.latest_week_start()
days = 7

pdf_fname = "reports/{}-{}-report.pdf".format(latest_week_start, days)
html_fname = "reports/{}-{}-report.html".format(latest_week_start, days)
print("Will find, or create, {}".format(pdf_fname))

if args.regen or not os.path.exists(pdf_fname):
    print("Generating report")
    (report, previous_report) = rg.report(latest_week_start, days, force_generate=args.regen)
    report_html = html.format(report)
    report_pdf = pdf.convert(report_html)
    utils.save(report_html, html_fname)
    utils.save(report_pdf, pdf_fname)
else:
    print("Report {} already exists".format(pdf_fname))

client = slack.WebClient(token=slack_token.token)
comment="Slack activity report for the {} days starting {}".format(days, latest_week_start)
response = client.files_upload(
    channels=destination, 
    channel=destination, 
    file=pdf_fname,
    filename=pdf_fname,
    comment=comment,
    title=comment
    )
print(response)
