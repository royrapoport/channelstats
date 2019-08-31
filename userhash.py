
import time

import ddb
import utils


class UserHash(object):
    table_name = "UserHash"

    def __init__(self):
        self.ddb = ddb.DDB(self.table_name, [('key', 'S')])
        self.table = self.ddb.get_table()
        self.modified = {}
        self.cache = {}

    def get(self, key):
        if key in self.cache:
            return self.cache[key]
        response = self.table.get_item(Key={'key': key})
        item = response.get("Item")
        self.cache[key] = item
        return item

    def make_key(self, uid):
        """
        We need to store efficiently (so we can fetch more than one at a time)
        To do that, we need to store multiple UIDs against the same key.
        This method will map a UID to a key.  UIDs should reliably always
        map to the same key (but a key cannot be reliably mapped to a given
        UID -- it's a one-way function)
        """
        # UIDs are about 10 chars; we intend to store them as
        # k: UID UID UID
        # item sizes in DDB are not to be over 400K, which means no more
        # than 400,000 chars.  At approx 15chars per UID, and not wanting
        # to exceed about 300K, that gives us about 20,000 UIDs per row
        # Using the last char in the UID turns out to give us a pretty good
        # distribution -- and with 35 possible values, gives us up to about
        # 700K users.
        return uid[-1]

    def register_user(self, uid):
        k = self.make_key(uid)
        row = self.get(k)
        if not row:
            row = {'key': k, 'uids': ""}
        else:
            row["uids"] += " {}".format(uid)
        self.cache[k] = row
        self.modified[k] = True

    def finish_registration(self):
        with self.table.batch_writer() as batch:
            for k in self.modified:
                # print("Saving hash key {}".format(k))
                Row = self.cache[k]
                batch.put_item(Row)

    def user_exists(self, uid):
        """
        Returns True/False based on our belief about whether or not
        the user exists
        """
        k = self.make_key(uid)
        row = self.get(k)
        if not row:
            return False
        if row["uids"].find(uid) == -1:
            return False
        return True
