

import json
import sys
import time

import ddb
import configuration


class FirstPost(object):
    table_name = "FirstPost"

    def __init__(self, fake=False):
        self.ddb = ddb.DDB(self.table_name, [('slack_uid', 'S')])
        self.table = self.ddb.get_table()
        self.users = {}
        self.modified = {}
        self.saved = {}
        self.count = None
        self.channel = None
        self.fake = fake

    def get(self, key):
        if key in self.users:
            return self.users[key]
        response = self.table.get_item(Key={'slack_uid': key})
        item = response.get("Item")
        if item:
            item['ts'] = int(item['ts'])
        self.users[key] = item
        return item

    def set_channel(self, cid):
        self.count = 0
        self.channel = cid

    def print_progress(self, ts):
        s = None
        if self.count % 10000 == 0:
            f = time.localtime(ts)
            s = time.strftime("%Y-%m-%d", f)
        elif self.count % 2000 == 0:
            s = str(self.count)
        elif self.count % 200 == 0:
            s = "."
        if s:
            sys.stdout.write(s)
            sys.stdout.flush()

    def message(self, message):
        # print("message: {}".format(message))
        uid = message.get('user_id')
        if not uid:
            return
        ts = int(float(message['ts']))
        mid = message['ts']
        entry = self.get(uid)

        self.count += 1
        self.print_progress(ts)

        if entry:
            if entry['ts'] > ts:
                entry['ts'] = ts
                entry['slack_cid'] = self.channel
                entry['message_id'] = str(mid)
        else:
            self.users[uid] = {
                "slack_uid": uid,
                "slack_cid": self.channel,
                "message_id": str(mid),
                "ts": int(float(ts))
            }
        return message

    def get_channel(self, cid):
        return self.get(cid)

    def save(self):
        channels = {}
        # print("self.users: {}".format(json.dumps(self.users, indent=4)))
        with self.table.batch_writer() as batch:
            for uid in self.users:
                row = self.users[uid]
                if not row:
                    continue
                channel = row['slack_cid']
                if channel not in channels:
                    channels[channel] = 1
                if uid in self.saved:
                    continue
                # print("Inserting new {}".format(row))
                batch.put_item(row)
                self.saved[uid] = 1
