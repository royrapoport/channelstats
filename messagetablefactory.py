#! /usr/bin/env python

import time

import pynamodb.models
import pynamodb.attributes

class MessageTableFactory(object):

    def __init__(self, local=False):
        self.__day_tables = {}
        self.local = local

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
        if local, use a local endpoint for DynamoDB
        """

        day = self.make_day(timestamp)
        if day in self.__day_tables:
            return self.__day_tables[day]

        class MessageTable(pynamodb.models.Model):
            class Meta:
                read_capacity_units = 10
                write_capacity_units = 20
                table_name = self.get_message_table_name(timestamp)
                if self.local:
                    host = "http://localhost:8000"
            timestamp = pynamodb.attributes.UnicodeAttribute(hash_key=True)
            slack_cid = pynamodb.attributes.UnicodeAttribute(range_key=True)
            user_id= pynamodb.attributes.UnicodeAttribute()
            wordcount = pynamodb.attributes.NumberAttribute()
            files = pynamodb.attributes.UnicodeAttribute()
            reactions = pynamodb.attributes.UnicodeAttribute()
            reaction_count = pynamodb.attributes.NumberAttribute()
            replies = pynamodb.attributes.UnicodeAttribute()
            reply_count = pynamodb.attributes.NumberAttribute()
        self.__day_tables[day] = MessageTable
        MessageTable.create_table(wait=True)
        return MessageTable
