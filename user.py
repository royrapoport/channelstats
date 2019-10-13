
import re
import time

import ddb
import user_created
import utils
import config
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
        self.configuration = configuration.Configuration(fake=fake)
        self.modified = {}
        self.uc = user_created.UserCreated()

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
            'insert_ts': 1567210676,
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

    def batch_upload(self, users):

        self.uc.load()
        active_users = [x for x in users if x['deleted'] == False]
        self.configuration.set_count("active_users", len(active_users))
        self.configuration.set_count("all_users", len(users))
        insert_users = []
        now = int(time.time())
        for user in users:
            uid = user['id']
            self.uc.set(uid)
            Row = {
                'slack_uid': user['id'],
                'real_name': user.get("real_name"),
                'deleted': user.get("deleted"),
                'user_name': user.get("name"),
                'display_name': user.get('profile', {}).get('display_name'),
                'tz': user.get("tz"),
                'tz_offset': user.get("tz_offset"),
            }
            Row = utils.prune_empty(Row)
            insert_users.append(Row)

        with self.table.batch_writer() as batch:
            for row in insert_users:
                batch.put_item(row)

        self.uc.save()

    def f(self, row):
        return "{} ({})".format(row['slack_uid'], row['display_name'])
