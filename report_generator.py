#! /usr/bin/env python3

import copy
import datetime
import json
import sys
import time
import traceback

import message
import channel
import ddb
import report
import report_store
import user
import utils


class ReportGenerator(object):

    def __init__(self, fake=False):
        self.fake = fake
        self.report_store = report_store.ReportStore()
        self.Message = message.Message()

    def make_report_id(self, start_day, days):
        return "{}-{}".format(start_day, days)

    def query_report(self, start_day, days):
        """
        Query DDB for the report with the given parameters
        """
        rid = self.make_report_id(start_day, days)
        report_string = self.report_store.get(rid)
        if not report_string:
            return None
        # print("Found a stored report for {}".format(rid))
        return json.loads(report_string)

    def store_report(self, start_day, days, report):
        print("Storing report for {}/{}".format(start_day, days))
        rid = self.make_report_id(start_day, days)
        self.report_store.set(rid, json.dumps(report))

    def previous_report(self, start_day, days, users=None, force_generate=False, channels=None):
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
        return self.get_report(new_start_day, days, users, force_generate, channels)

    def latest_week_start(self):
        """
        return yyyy-mm-dd of the latest week for which we have a whole week's data
        """
        latest = utils.today()
        y, m, d = [int(x) for x in latest.split('-')]
        dt = datetime.date(y, m, d)
        weekday = dt.weekday()
        if weekday == 6:
            proposed = dt - datetime.timedelta(days=(weekday + 1))
        else:
            proposed = dt - datetime.timedelta(days=(weekday + 1 + 7))
        proposed_s = proposed.strftime("%Y-%m-%d")
        return proposed_s

    def report(self, start_day, days, users=None, force_generate=False, channels=None):
        """
        Returns (current_report, previous_report)
        """
        current_report = self.get_report(start_day, days, users, force_generate, channels)
        print("Got current report")
        try:
            previous_report = self.previous_report(start_day, days, users, force_generate, channels)
        except Exception as e:
            traceback.print_exc()
            print("Exception: {}".format(e))
            previous_report = None
        return current_report, previous_report

    def get_report(self, start_day, days, users=[], force_generate=False, channels=[]):
        """
        Generate a channel stats report starting on start_day, which is
        formatted as yyyy-mm-dd, and for the period of DAYS duration
        If user is specified, limit to messages from the user
        """
        existing_report = None
        if not force_generate:
            complete = True
            existing_report = self.query_report(start_day, days)
            if existing_report:
                if users:
                    for user in users:
                        if user not in existing_report.get("enriched_user", {}):
                            complete = False
                if channels:
                    for channel in channels:
                        if channel not in existing_report.get("enriched_channel", {}):
                            complete = False
                if complete:
                    return existing_report
        general_report = self.generate_report(start_day, days, users, channels)
        if not force_generate:
            if existing_report:
                for token in ['enriched_user', 'enriched_channel']:
                    if token in existing_report:
                        if token not in general_report:
                            general_report[token] = {}
                        for item in existing_report[token]:
                            if item not in general_report[token]:
                                general_report[token][item] = existing_report[token][item]
        self.store_report(start_day, days, general_report)
        return general_report

    def generate_report(self, start_day, days, users=[], channels=[]):
        """
        Generate a channel stats report starting on start_day, which is
        formatted as yyyy-mm-dd, and for the period of DAYS duration
        """
        print("Generating report for {}/{}".format(start_day, days))
        report_creator = report.Report()
        report_creator.set_users(users)
        report_creator.set_channels(channels)
        dates = self.generate_dates(start_day, days)
        report_creator.set_start_date(dates[0])
        report_creator.set_end_date(dates[-1])
        report_creator.set_days(days)
        for date in dates:
            for message in self.Message.messages_for_day(date):
                report_creator.message(message)
        report_creator.finalize()
        current_report = report_creator.data()
        f = open("reports/{}-{}days-report.json".format(start_day, days), "w")
        f.write(json.dumps(current_report, indent=4))
        f.close()
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
