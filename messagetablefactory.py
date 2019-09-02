#! /usr/bin/env python

import re
import time

# import botocore
# import botocore.errorfactory.ResourceNotFoundException
import ddb


class MessageTableFactory(object):

    prefix = "Message-"

    def __init__(self, readonly=False):
        self.__day_tables = {}
        self.readonly = readonly

    def latest_date(self):
        """
        return the latest date for which we have messages in yyyy-mm-dd format
        """
        dates = self.get_dates()
        if dates:
            return dates[-1]
        return None

    def get_dates(self):
        d = ddb.DDB("bogus")
        tables = d.list_tables()
        message_tables = [x for x in tables if x.find(self.prefix) == 0]
        dates = [x.replace(self.prefix, "") for x in message_tables]
        dates.sort()
        return dates

    def earliest_date(self):
        """
        return the earliest date for which we have messages in yyyy-mm-dd format
        """
        dates = self.get_dates()
        if dates:
            return dates[0]
        return None

    def get_message_table_name(self, timestamp_or_dt):
        """
        given str timestamp or yyyy-mm-dd, return the name of the Message table we'll store
        a message in
        """
        try:
            int(float(timestamp_or_dt))
            date = self.make_day(timestamp_or_dt)
        except BaseException:
            if not re.match(r"\d\d\d\d-\d\d-\d\d", timestamp_or_dt):
                raise RuntimeError(
                    "timestamp_or_dt needs to be a timestamp or dt")
            date = timestamp_or_dt
        return "{}{}".format(self.prefix, date)

    def make_day(self, timestamp):
        """
        Given a str timestamp, return yyyy-mm-dd
        """
        lt = time.localtime(int(float(timestamp)))
        return time.strftime("%Y-%m-%d", lt)

    def get_message_table(self, timestamp_or_dt):
        """
        Return a pynamodb.models.Model Table for the given UNIX timestamp;
        """

        table_name = self.get_message_table_name(timestamp_or_dt)
        if table_name not in self.__day_tables:
            DDB = ddb.DDB(table_name, [("timestamp", "S"), ("slack_cid", "S")])
            table = DDB.get_table(readonly=self.readonly)
            self.__day_tables[table_name] = table
        return self.__day_tables[table_name]
