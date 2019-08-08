#! /usr/bin/env python

import time

# import botocore
# import botocore.errorfactory.ResourceNotFoundException
import boto3
import ddb


class MessageTableFactory(object):

    def __init__(self):
        self.__day_tables = {}

    def get_existing_tables(self):
        """
        Returns list of existing tables
        """
        return self.dynamodb_client.list_tables()['TableNames']

    def get_message_table_name(self, timestamp):
        """
        given str timestamp, return the name of the Message table we'll store
        a message in
        """
        return "Message-{}".format(self.make_day(timestamp))

    def make_day(self, timestamp):
        """
        Given a str timestamp, return yyyy-mm-dd
        """
        lt = time.localtime(int(float(timestamp)))
        return time.strftime("%Y-%m-%d", lt)

    def get_message_table(self, timestamp):
        """
        Return a pynamodb.models.Model Table for the given UNIX timestamp;
        """

        day = self.make_day(timestamp)
        table_name = self.get_message_table_name(timestamp)
        if table_name not in self.__day_tables:
            DDB = ddb.DDB(table_name, [("timestamp", "S"), ("slack_cid", "S")], (10,10))
            table = DDB.get_table()
            self.__day_tables[table_name] = table
        return self.__day_tables[table_name]
