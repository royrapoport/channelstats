#! /usr/bin/env python3

import copy
import datetime
import json
import sys
import time

from boto3.dynamodb.conditions import Key, Attr

import channel
import html_formatter
import pdf_formatter
import messagetablefactory
import report
import report_store
import user
import utils

class ReportGenerator(object):

    def __init__(self):
        self.mtf = messagetablefactory.MessageTableFactory()
        self.report_creator = report.Report()
        self.report_store = report_store.ReportStore()

    def make_report_id(self, start_day, days, user):
        if user is None:
            return "{}-{}".format(start_day, days)
        return "{}-{}-{}".format(start_day, days, user)

    def query_report(self, start_day, days, user=None):
        """
        Query DDB for the report with the given parameters
        """
        rid = self.make_report_id(start_day, days, user)
        report_string = self.report_store.get(rid)
        if not report_string:
            return None
        # print("Found a stored report for {}".format(rid))
        return json.loads(report_string)

    def store_report(self, start_day, days, report, user=None):
        print("Storing report for {}/{}/{}".format(start_day, days, user))
        rid = self.make_report_id(start_day, days, user)
        self.report_store.set(rid, json.dumps(report))

    def report(self, start_day, days, users=None, force_generate=False):
        """
        Generate a channel stats report starting on start_day, which is
        formatted as yyyy-mm-dd, and for the period of DAYS duration
        If user is specified, limit to messages from the user
        """
        if not force_generate:
            # print("Querying for {}/{}/{}".format(start_day, days, user))
            reports = {}
            emptyReport = False
            if users:
                for user in users:
                    report = self.query_report(start_day, days, user)
                    if not report:
                        emptyReport = True
                    reports[user] = report
            report = self.query_report(start_day, days)
            if report and not emptyReport:
                print("Found all parts of the report in storage!")
                report['enriched_user'] = reports
                return report
        report = self.generate_report(start_day, days, users)
        enriched_users = report['enriched_user']
        if enriched_users:
            for user in enriched_users:
                self.store_report(start_day, days, enriched_users[user], user=user)
        self.store_report(start_day, days, report, user=None)
        return report

    def generate_report(self, start_day, days, users=[]):
        """
        Generate a channel stats report starting on start_day, which is
        formatted as yyyy-mm-dd, and for the period of DAYS duration
        """
        # print("Generating report for {}/{}/{}".format(start_day, days, user))
        self.report_creator.set_users(users)
        dates = self.generate_dates(start_day, days)
        self.report_creator.set_start_date(dates[0])
        self.report_creator.set_end_date(dates[-1])
        # print("For the report of {} days starting {} we have dates {}".format(days, start_day, dates))
        tables = [self.mtf.get_message_table(date) for date in dates]
        # print("Message table names: {}".format(tables))
        for table in tables:
            messages = table.scan()["Items"]
            for message in messages:
                self.report_creator.message(message)
        self.report_creator.finalize()
        report = self.report_creator.data()
        return report

    def summarize_report(self, report):
        # self.report_creator.dump()
        # self.reaction_summary(40)
        # return
        # print("gm activity by hour:")
        # for x in range(0,24):
        #    print("{}: {}".format(x, self.report_creator._data['hour'].get(x)))
        # report = self.report_creator.data()
        print("Report is {} chars".format(len(json.dumps(report))))
        print("Elements of report:")
        for item in report.keys():
            print("\t{}".format(item))
            # print(utils.dumps(report[item]))
            # print("")
        print("user activity by hour:")
        for x in range(0,24):
            print("{}: {}".format(x, report['user_weekday_hour'].get(str(x))))

        print("user activity by timezone:")
        tzs = list(report['timezone'].keys())
        tzs.sort(key = lambda x: report['timezone'][x])
        tzs.reverse()
        for tz in tzs:
            print("{}: {}".format(tz, report['timezone'][tz]))

        print("Report statistics:")
        stats = report['statistics']
        for k in stats:
            print("\t{} : {}".format(k, stats[k]))

        print("Statistics for Roy:")
        stats = report['user_stats']['U06NSQT34']
        print(json.dumps(stats, indent=4))

    def reaction_summary(self, top=10):
        rdict = report['reaction']
        reactions = list(rdict.keys())
        reactions.sort(key = lambda x: rdict[x])
        reactions.reverse()
        reactions = reactions[0:top]
        for reaction in reactions:
            print(":{}: `:{}:` :{}".format(reaction, reaction, rdict[reaction]))

    def generate_dates(self, start_day, days):

        dates = []
        yyyy, mm, dd = [int(x) for x in start_day.split("-")]
        current_day = datetime.date(yyyy, mm, dd)
        while days:
            dates.append(current_day.strftime("%Y-%m-%d"))
            days -= 1
            current_day += datetime.timedelta(days=1)
        return dates

if __name__ == "__main__":
    html_formatter_obj = html_formatter.HTMLFormatter()
    pdf_formatter_obj = pdf_formatter.PDFFormatter()
    users = {}
    users['noemi'] = "UHWD9BHPD"
    users['roy'] = "U06NSQT34"
    users['jenna'] =  "U8MEPG4Q7"
    users['jude'] = "UCR03V5BP"
    users['moj_hoss'] = "UD9M2GA2J"
    date = "2019-07-02"
    days = 55
    # date = "2019-08-01"
    # days = 21
    force_regen = False
    if len(sys.argv) > 1 and sys.argv[1] == "regen":
        force_regen = True
    # for x in [None, roy, jenna, noemi]:
    rg = ReportGenerator()
    print("users: {}".format(users))
    print("Generating report for {}/{}".format(date,days))
    report = rg.report(date, days, users=users.values(), force_generate=force_regen)
    # rg.summarize_report(report)
    f = open("report.json", "w")
    f.write(json.dumps(report, indent=4))
    f.close()
    print("")
    mhtml = html_formatter_obj.format(report)
    f = open("report.html", "w")
    f.write(mhtml)
    f.close()
    for u in users.keys():
        uid = users[u]
        print("Running user report for {}/{}".format(u, uid))
        u_html = html_formatter_obj.user_format(report, uid)
        f = open("{}_report.html".format(u), "w")
        f.write(u_html)
        f.close()
    if False:
        s = time.time()
        pdf = pdf_formatter_obj.convert(mhtml)
        e = time.time()
        d = e - s
        print("PDF conversion took {:.1f} seconds".format(d))
        f = open("report.pdf", "wb")
        f.write(pdf)
        f.close()
