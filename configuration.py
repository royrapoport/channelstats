
import time

import ddb

class Configuration(object):
    table_name = "Configuration"

    def __init__(self):
        self.ddb = ddb.DDB(self.table_name, [('key', 'S')])
        self.table = self.ddb.get_table()
        self.cache = {}

    def get(self, key):
        if key in self.cache:
            return self.cache[key]
        response = self.table.get_item(Key={'key':key})
        item = response.get("Item")
        self.cache[key] = item
        return item

    def get_last_run(self):
        last_run = self.get("last run")
        if not last_run:
            return 0
        last_run = int(last_run['last run'])
        return last_run

    def set_last_run(self):
        now = int(time.time())
        self.table.put_item(
            Item={
                'key': "last run",
                "last run": now
            }
        )
