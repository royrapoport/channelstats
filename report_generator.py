#! /usr/bin/env python3

import datetime
import json

import channel
import messagetablefactory
import report
import user
import utils

class ReportGenerator(object):

    def __init__(self):
        self.mtf = messagetablefactory.MessageTableFactory()
        self.report = report.Report()

    def generate_report(self, start_day, days, user=None):
        """
        Generate a channel stats report starting on start_day, which is
        formatted as yyyy-mm-dd, and for the period of DAYS duration
        """
        dates = self.generate_dates(start_day, days)
        # print("For the report of {} days starting {} we have dates {}".format(days, start_day, dates))
        tables = [self.mtf.get_message_table(date) for date in dates]
        # print("Message table names: {}".format(tables))
        for table in tables:
            messages = table.scan()["Items"]
            for message in messages:
                if user is None:
                    self.report.message(message)
                elif message['user_id'] == user:
                    self.report.message(message)
        self.report.finalize()
        # self.report.dump()
        # self.reaction_summary(40)
        # return
        # print("gm activity by hour:")
        # for x in range(0,24):
        #    print("{}: {}".format(x, self.report._data['hour'].get(x)))
        report = self.report.data()
        print("Report is {} chars".format(len(json.dumps(report))))
        print("user activity by hour:")
        for x in range(0,24):
            print("{}: {}".format(x, self.report._data['user_weekday_hour'].get(x)))

        print("user activity by timezone:")
        tzs = list(self.report._data['timezone'].keys())
        tzs.sort(key = lambda x: self.report._data['timezone'][x])
        tzs.reverse()
        for tz in tzs:
            print("{}: {}".format(tz, self.report._data['timezone'][tz]))

    def reaction_summary(self, top=10):
        rdict = self.report._data['reaction']
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
    noemi = "UHWD9BHPD"
    roy = "U06NSQT34"
    jenna =  "U8MEPG4Q7"
    rg = ReportGenerator()
    rg.generate_report("2019-07-28", 7)
    # rg.generate_report("2019-07-28", 7, roy)
    # rg.generate_report("2019-07-28", 7, jenna)
    # rg.generate_report("2019-07-28", 7, noemi)
