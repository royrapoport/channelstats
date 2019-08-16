
import time

import ddb
import utils
import userhash
import configuration

class User(object):
    table_name = "User"

    def __init__(self):
        self.ddb = ddb.DDB(self.table_name, [('id', 'S')])
        self.table = self.ddb.get_table()
        self.users = {}
        self.userhash = userhash.UserHash()
        self.configuration = configuration.Configuration()
        self.modified = {}

    def get(self, key):
        if key in self.users:
            return self.users[key]
        response = self.table.get_item(Key={'id':key})
        item = response.get("Item")
        self.users[key] = item
        return item

    def update_user(self, row):
        expr="set real_name=:r, name=:n, display_name=:d, tz=:t, tz_offset=:o"
        self.table.update_item(
            Key={
                'id':row['id']
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
        now = int(time.time())
        last_run = self.configuration.get_last_run()
        for user in users:
            uid = user['id']
            Row = {
                'id': user['id'],
                'real_name': user.get("real_name"),
                'name': user.get("name"),
                'display_name': user.get('profile', {}).get('display_name'),
                'tz': user.get("tz"),
                'tz_offset': user.get("tz_offset"),
            }
            if not self.userhash.user_exists(uid):
                self.userhash.register_user(uid)
                Row['insert_timestamp'] = now
                Row = utils.prune_empty(Row)
                insert_users.append(Row)
            else: # user already exists.  Updated?
                updated = user['updated']
                if updated > last_run:
                    print("Updating {}".format(Row))
                    self.update_user(Row)

        with self.table.batch_writer() as batch:
            for row in insert_users:
                print("Inserting new {}".format(row))
                batch.put_item(row)

        self.userhash.finish_registration()
        self.configuration.set_last_run()

    def f(self, row):
        return "{} ({})".format(row['id'], row['display_name'])
