
import re
import time

import ddb
import utils
import config
import userhash
import configuration

class User(object):
    table_name = "User"
    fake_table_name = "FakeUser"

    def __init__(self, fake=False):
        self.fake = fake
        if fake:
            self.table_name = self.fake_table_name
        self.ddb = ddb.DDB(self.table_name, [('slack_uid', 'S')])
        self.table = self.ddb.get_table()
        self.users = {}
        self.userhash = userhash.UserHash(fake=fake)
        self.configuration = configuration.Configuration(fake=fake)
        self.modified = {}

    def find(self, username):
        """
        Return a list of matches to the given username, case-sensitive
        """
        if username[0] == "@":
            username = username[1:]
        matches = []
        attrs = "user_name display_name real_name".split()
        for item in self.ddb.items(self.table):
            for i in attrs:
                if username == item.get(i):
                    matches.append(item)
                    break
        return matches

    def batch_get_user(self, userids):
        return self.ddb.batch_hash_get(userids)

    def pick_name(self, user):
        """
        given a user structure from user.get(), return the name we should
        show people -- this should ideally be the name they see people
        interact as in slack
        """
        dn = user.get('display_name')
        rn = user.get("real_name")
        un = user.get("user_name")
        return dn or rn or un

    def get_users(self, list_of_userids):
        """
        Given a list of userIDs, returns a dictionary indexed by userID
        where the value is another dictionary with
            'label': The actual label to show for the user ID
            'hover': The text to show when hovering over the label
            'url': The URL to link to for more information about the user
        """

        dummy = {
            'slack_uid': 'USLACKBOT',
            'tz_offset': -25200,
            'insert_timestamp': 1567210676,
            'user_name': 'dummy',
            'tz': 'America/Los_Angeles',
            'real_name': 'Dummy User',
            'display_name': 'Dummy User'}

        ret = {}
        start = time.time()
        entries = self.batch_get_user(list_of_userids)
        for uid in list_of_userids:
            entry = entries.get(uid, dummy)
            ret[uid] = self.make_pretty(entry)
        return ret

    def get_pretty(self, uid):
        entry = self.get(uid)
        return self.make_pretty(entry)

    def make_pretty(self, user_structure):
        url = "https://{}.slack.com/team/{}"
        url = url.format(config.slack_name, user_structure['slack_uid'])
        ret = {
            'label': '@' + self.pick_name(user_structure),
            'hover': user_structure.get("real_name", ""),
            'url': url
        }
        return ret

    def get(self, key):
        if key in self.users:
            return self.users[key]
        response = self.table.get_item(Key={'slack_uid': key})
        item = response.get("Item")
        self.users[key] = item
        return item

    def update_user(self, row):
        values = {
            ":t": row["tz"],
            ":D": row["deleted"],
            ":o": row["tz_offset"]
        }
        expr = "set deleted=:D, tz=:t, tz_offset=:o, "
        if row['real_name']:
            expr += "real_name=:r, "
            values[":r"] = row["real_name"]
        if row["user_name"]:
            expr += "user_name=:n, "
            values[":n"] = row["user_name"]
        if row["display_name"]:
            expr += "display_name=:d, "
            values[":d"] = row["display_name"]
        expr = re.sub(", $", "", expr)
        self.table.update_item(
            Key={
                'slack_uid': row['id']
            },
            UpdateExpression=expr,
            ExpressionAttributeValues=values,
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

        active_users = [x for x in users if x['deleted'] == False]
        self.configuration.set_count("active_users", len(active_users))
        self.configuration.set_count("all_users", len(users))
        insert_users = []
        now = int(time.time())
        last_run = self.configuration.get_last_run()
        for user in users:
            uid = user['id']
            Row = {
                'slack_uid': user['id'],
                'real_name': user.get("real_name"),
                'deleted': user.get("deleted"),
                'user_name': user.get("name"),
                'display_name': user.get('profile', {}).get('display_name'),
                'tz': user.get("tz"),
                'tz_offset': user.get("tz_offset"),
            }
            if not self.userhash.user_exists(uid):
                self.userhash.register_user(uid)
                Row['insert_timestamp'] = now
                Row = utils.prune_empty(Row)
                insert_users.append(Row)
            else:  # user already exists.  Updated?
                updated = user['updated']
                if updated > last_run:
                    self.update_user(Row)

        with self.table.batch_writer() as batch:
            for row in insert_users:
                batch.put_item(row)

        self.userhash.finish_registration()
        self.configuration.set_last_run()

    def f(self, row):
        return "{} ({})".format(row['slack_uid'], row['display_name'])
