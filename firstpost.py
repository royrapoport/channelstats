

import json

import ddb
import configuration

class FirstPost(object):
    table_name = "FirstPost"

    def __init__(self):
        self.ddb = ddb.DDB(self.table_name, [('key', 'S')])
        self.table = self.ddb.get_table()
        self.users = {}
        self.modified = {}

    def get(self, key):
        if key in self.users:
            return self.users[key]
        response = self.table.get_item(Key={'key':key})
        item = response.get("Item")
        if item:
            item['ts'] = int(item['ts'])
        self.users[key] = item
        return item

    def message(self, message):
        # print("message: {}".format(message))
        uid = message.get('user')
        if not uid:
            return
        ts = int(float(message['ts']))
        mid = message['ts']
        entry = self.get(uid)
        if entry:
            if entry['ts'] > ts:
                # f = "For {} found an earlier entry than {}/{}: {}/{}".format(entry['key'], entry['channel'], entry['ts'], self.channel, ts)
                # print(f)
                entry['ts'] = ts
                entry['channel'] = self.channel
                entry['message_id'] = str(mid)
        else:
            self.users[uid] = {
                "key":uid,
                "channel":self.channel,
                "message_id":str(mid),
                "ts":int(float(ts))
            }
        return message

    def get_channel(self, cid):
        return self.get(cid)

    def save_channel(self, cid):
        row = {
            "key":cid,
            "channel":cid,
            "ts":0
        }
        print("Saving {}".format(row))

        self.table.put_item(Item=row)

    def save(self):
        channels = {}
        print("self.users: {}".format(json.dumps(self.users, indent=4)))
        with self.table.batch_writer() as batch:
            for uid in self.users:
                row = self.users[uid]
                if not row:
                    continue
                channel = row['channel']
                if channel not in channels:
                    channels[channel] = 1
                print("Inserting new {}".format(row))
                batch.put_item(row)
        for channel in channels.keys():
            self.save_channel(channel)
