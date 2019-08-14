
import time

import ddb
import utils

class User(object):
    table_name = "User"

    def __init__(self):
        self.ddb = ddb.DDB(self.table_name, [('key', 'S')], (10,10))
        self.table = self.ddb.get_table()
        self.users = {}
        self.modified = {}

    def get(self, key):
        if key in self.users:
            return self.users[key]
        response = self.table.get_item(Key={'key':uid})
        item = response.get("Item")
        self.users[key] = item
        return item

    def make_key(uid):
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
            row = "{}".format(uid)
        else:
            row["uids"] += " {}".format(uid)
        self.users[k] = row
        self.modified[k] = True

    def finish_registration(self):
        with self.table.batch_writer() as batch:
            for k in self.modified:
                Row = {
                    'key': k,
                    'uids': self.users[k]
                }
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

    def get_last_run(self):
        last_run = self.get("last run")
        if not last_run:
            return 0
        last_run = int(last_run['last run'])
        return last_run

    def set_last_run(self):
        now = time.time()
        self.table.put_item(
            Item={
                'key': "last run",
                "last run": now
            }
        )

    def update_user(self, row):
        expr="set real_name=:r, name=:n, display_name=:d, tz=:t, tz_offset=:o"
        self.table.update_item(
            Key={
                'key':row['id']
            },
            UpdateExpression=expr,
            ExpressionAttributeValues={
                ":r" : row['real_name'],
                ":n": row["name"],
                ":d": row["display_name"],
                ":t": row["tz"],
                ":o": row["tz_offset"]
            },
            ReturnValues="UPDATED_NEW"
        )

    def batch_upload(self, users):
        # How should this work?
        # Download all users from Slack
        # For each user
        #   If they do not exist
        #        insert them, with insert_date set to today
        #        mark that they exist
        #    If they do exist
        #        If the slack user.update is later than the last time we ran
        #            update the user (but don't change insert_date)
        # Mark last run time

        insert_users = []
        now = time.time()
        last_run = self.get_last_run()
        for user in users:
            uid = user['id']
            Row = {
                'key': user['id'],
                'real_name': user.get("real_name"),
                'name': user.get("name"),
                'display_name': user.get('profile', {}).get('display_name'),
                'tz': user.get("tz"),
                'tz_offset': user.get("tz_offset"),
            }
            if not self.user_exists(uid):
                self.register_user(uid)
                Row['insert_timestamp'] = now
                Row = utils.prune_empty(Row)
                insert_users.append(Row)
            else: # user already exists.  Updated?
                updated = user['updated']
                if updated > last_run:
                    print("Updating {}".format(self.f(Row)))
                    self.update_user(Row)

        with self.table.batch_writer() as batch:
            for row in insert_users:
                print("Inserting new {}".format(self.f(Row)))
                batch.put_item(row)

        self.finish_registration()
        self.set_last_run()

    def f(self, row):
        return "{} ({})".format(row['id'], row['display_name'])
