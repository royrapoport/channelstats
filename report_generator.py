#! /usr/bin/env python3

import copy
import datetime
import json
import sys
import time

import channel
import html_formatter
import pdf_formatter
import messagetablefactory
import report
import report_store
import user
import utils


class ReportGenerator(object):

    def __init__(self, fake=False):
        self.fake = fake
        self.mtf = messagetablefactory.MessageTableFactory()
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

    def previous_report(self, start_day, days, users=None, force_generate=False):
        """
        Given a start day and days, get the PREVIOUS period's report with the same
        parameters as report() takes.
        In other words, if start_day is 2019-08-10 and days is 3, then
        this will get the report for 2019-08-07 for 3 days
        """
        y, m, d = [int(x) for x in start_day.split('-')]
        dt = datetime.date(y, m, d)
        delta = datetime.timedelta(days=days)
        dt -= delta
        new_start_day = dt.strftime("%Y-%m-%d")
        return self.get_report(new_start_day, days, users, force_generate)

    def report(self, start_day, days, users=None, force_generate=False):
        """
        Returns (current_report, previous_report)
        """
        current_report = self.get_report(start_day, days, users, force_generate)
        previous_report = self.previous_report(start_day, days, users, force_generate)
        return (current_report, previous_report)

    def get_report(self, start_day, days, users=None, force_generate=False):
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
                    user_report = self.query_report(start_day, days, user)
                    if not user_report:
                        emptyReport = True
                    reports[user] = user_report
            general_report = self.query_report(start_day, days)
            if general_report and not emptyReport:
                print("Found all parts of the report in storage!")
                general_report['enriched_user'] = reports
                return general_report
        general_report = self.generate_report(start_day, days, users)
        enriched_users = general_report['enriched_user']
        if enriched_users:
            for user in enriched_users:
                self.store_report(
                    start_day, days, enriched_users[user], user=user)
        ret = copy.deepcopy(general_report)
        del(general_report['enriched_user'])
        self.store_report(start_day, days, general_report, user=None)
        return ret

    def generate_report(self, start_day, days, users=[]):
        """
        Generate a channel stats report starting on start_day, which is
        formatted as yyyy-mm-dd, and for the period of DAYS duration
        """
        # print("Generating report for {}/{}/{}".format(start_day, days, user))
        report_creator = report.Report()
        report_creator.set_users(users)
        dates = self.generate_dates(start_day, days)
        report_creator.set_start_date(dates[0])
        report_creator.set_end_date(dates[-1])
        print("For the report of {} days starting {} we have dates {}".format(days, start_day, dates))
        tables = [self.mtf.get_message_table(date) for date in dates]
        print("Message table names: {}".format(tables))
        for table in tables:
            messages = table.scan()["Items"]
            for message in messages:
                report_creator.message(message)
        report_creator.finalize()
        current_report = report_creator.data()
        return current_report

    def generate_dates(self, start_day, days):
        dates = []
        yyyy, mm, dd = [int(x) for x in start_day.split("-")]
        current_day = datetime.date(yyyy, mm, dd)
        while days:
            dates.append(current_day.strftime("%Y-%m-%d"))
            days -= 1
            current_day += datetime.timedelta(days=1)
        return dates
