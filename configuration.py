import time

import ddb


class Configuration(object):
    table_name = "Configuration"
    fake_table_name = "FakeConfiguration"

    def __init__(self, fake=False):
        self.fake = fake
        if fake:
            self.table_name = self.fake_table_name
        self.ddb = ddb.DDB(self.table_name, [('item_key', 'S')])
        self.table = self.ddb.get_table()
        self.cache = {}

    def get(self, key):
        if key in self.cache:
            return self.cache[key]
        response = self.table.get_item(Key={'item_key': key})
        item = response.get("Item")
        self.cache[key] = item
        return item

    def set_count(self, count_label, value):
        self.table.update_item(
            Key={
                'item_key': 'counts'
            },
            UpdateExpression="set {}=:v".format(count_label),
            ExpressionAttributeValues={
                ":v": int(value)
            },
            ReturnValues="UPDATED_NEW"
        )

    def get_count(self, count_label):
        counts = self.get("counts")
        if not counts:
            return 0
        return counts.get(count_label, 0)

    def get_last_run(self):
        last_run = self.get("last run")
        if not last_run:
            return 0
        last_run = int(last_run['last run'])
        return last_run

    def set(self, key, valuedict):
        """
        sets valuedict {k:v} as the value in DDB for row identified by key
        """
        item = {'item_key': key}
        for k in valuedict:
            item[k] = valuedict[k]
        self.table.put_item(Item=item)

    def set_last_run(self):
        now = int(time.time())
        self.set('last_run', {'last_run': now})
