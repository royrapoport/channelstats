#! /usr/bin/env python3

import datetime

import ddb
import messagetablefactory
import user
import channel
import report

class ReportGenerator(object):

    def __init__(self):
        self.mtf = messagetablefactory.MessageTableFactory()
        self.report = report.Report()

    def generate_report(self, start_day, days):
        """
        Generate a channel stats report starting on start_day, which is
        formatted as yyyy-mm-dd, and for the period of DAYS duration
        """
        dates = self.generate_dates(start_day, days)
        print("For the report of {} days starting {} we have dates {}".format(days, start_day, dates))
        tables = [self.mtf.get_message_table(date) for date in dates]
        print("Message table names: {}".format(tables))
        for table in tables:
            messages = table.scan()["Items"]
            for message in messages:
                if message['user_id'] == "U06NSQT34":
                    self.report.message(message)
        # self.report.dump()
        print("gm activity by hour:")
        for x in range(0,24):
            print("{}: {}".format(x, self.report._data['hour'].get(x)))

        print("user activity by hour:")
        for x in range(0,24):
            print("{}: {}".format(x, self.report._data['user_hour'].get(x)))


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
    rg = ReportGenerator()
    rg.generate_report("2019-07-21", 7)
    rg.generate_report("2019-07-28", 7)
