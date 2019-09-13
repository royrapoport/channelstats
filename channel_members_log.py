import collections
import datetime
import time
import ddb
import utils

class ChannelMembersLog(object):
    table_name = "ChannelMembersLog"

    def __init__(self, fake=False):
        self.fake = fake
        if self.fake:
            self.table_name = "Fake" + self.table_name
        self.ddb = ddb.DDB(self.table_name, [('slack_cid', 'S')])
        self.table = self.ddb.get_table()

    def token(self, ts):
        return "ts_{}".format(ts)

    def is_token(self, column):
        return column.find("ts_") == 0

    def detoken(self, column):
        assert self.is_token(column)
        column = column.replace("ts_", "")
        return int(column)

    def update(self, cid, ts, count):
        nows = self.token(int(ts))
        self.table.update_item(
            Key = {'slack_cid': cid},
            UpdateExpression='set {} = :m'.format(nows),
            ExpressionAttributeValues={':m': count},
            ReturnValues='UPDATED_NEW'
        )

    def batch_upload(self, channels):
        now = str(int(time.time()))
        nows = self.token(now)
        new_rows = []
        update_rows = []
        for channel in channels:
            cid = channel['id']
            members = 0
            if 'num_members' in channel:
                members = channel['num_members']
            row = {'slack_cid': cid, nows: members}
            item = self.get(cid)
            if item:
                update_rows.append(row)
            else:
                new_rows.append(row)
        with self.table.batch_writer() as batch:
            for row in new_rows:
                batch.put_item(row)
        for row in update_rows:
            cid = row['slack_cid']
            ts = now
            count = row[nows]
            self.update(cid, ts, count)

    def get(self, key):
        response = self.table.get_item(Key={'slack_cid': key})
        return response.get('Item')

    def make_ts(self, date):
        """
        Given yyyy-mm-dd return timestamp
        """
        y, m, d = [int(x) for x in date.split("-")]
        dt = datetime.datetime(y, m, d, 0, 0, 0, 0)
        return dt.timestamp()

    def dump(self, cid):
        entry = self.get(cid)
        if not entry:
            return 0
        mcounts = self.get_mcounts(entry)
        ret = collections.OrderedDict()
        mckeys = list(mcounts.keys())
        mckeys.sort()
        for i in mckeys:
            t = time.asctime(time.localtime(int(i)))
            ret[t] = mcounts[i]
        return ret

    def get_mcounts(self, entry):
        mcounts = {}
        for c in entry:
            if self.is_token(c):
                mcounts[self.detoken(c)] = int(entry[c])
        return mcounts

    def get_count(self, cid, date, comparator, reducer):
        """
        Given a yyyy-mm-dd date, return the latest count before 0000 on this date
        """
        ts = self.make_ts(date)
        entry = self.get(cid)
        if not entry:
            return 0
        mcounts = self.get_mcounts(entry)
        timestamps = list(mcounts.keys())
        filtered_timestamps = [x for x in timestamps if comparator(x, ts)]
        if filtered_timestamps:
            ts = reducer(filtered_timestamps)
            return mcounts[ts]
        return 0

    def latest_count(self, cid, date):
        """
        Given a yyyy-mm-dd date, return the latest count before 0000 on this date
        """
        def f(a, b):
            return a < b
        return self.get_count(cid, date, f, max)

    def earliest_count(self, cid, date):
        """
        Given a yyyy-mm-dd date, return the earliest count after 0000 on this date
        """
        def f(a, b):
            return a >= b
        return self.get_count(cid, date, f, min)
