

import datetime
import json
import sys
import time

import ddb
import configuration
import utils


class UserCreated(object):
    table_name = "UserCreated"

    def __init__(self, fake=False):
        self.ddb = ddb.DDB(self.table_name, [('slack_uid', 'S')])
        self.table = self.ddb.get_table()
        self.users = {}
        self.new = []
        self.fake = fake

    def date(self, ts):
        """
        return yyyy-mm-dd for ts
        """
        localtime = time.localtime(ts)
        return time.strftime("%Y-%m-%d", localtime)

    def days(self, ts):
        """
        return date difference between today and the ts
        """
        then = datetime.datetime.fromtimestamp(ts).date()
        now = datetime.date.today()
        diff = now - then
        return diff.days

    def load(self):
        """
        Loads the entirety of the table into memory; this is both way faster than
        doing per-user gets() and saves us money (since we're using bulk gets)
        """
        start = time.time()
        for item in self.ddb.items(self.table):
            self.users[item['slack_uid']] = item
        end = time.time()
        diff = end - start
        print("Loaded {} table in {:.1f} seconds".format(self.table_name, diff))

    def get(self, key):
        if key in self.users:
            return self.users[key]
        response = self.table.get_item(Key={'slack_uid': key})
        item = response.get("Item")
        if item:
            item['ts'] = int(item['ts'])
            item['days'] = self.days(item['ts'])
            item['date'] = self.date(item['ts'])
        self.users[key] = item
        return item

    def set(self, slack_uid, ts=None):
        if not ts:
            ts = time.time()
        ts = int(ts)
        item = self.get(slack_uid)
        if item:  # We already know about this person -- ignore
            return
        item = {'slack_uid': slack_uid, 'ts': ts}
        self.new.append(item)

    def save(self):
        with self.table.batch_writer() as batch:
            for item in self.new:
                batch.put_item(item)
        self.new = []
