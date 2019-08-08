
import ddb

class User(object):
    table_name = "User"

    def __init__(self):
        self.ddb = ddb.DDB(self.table_name, [('slack_uid', 'S')], (10,10))
        self.table = self.ddb.get_table()

    def batch_upload(self, users):
        with self.table.batch_writer() as batch:
            for user in users:
                Row = {
                    'slack_uid': user['id'],
                    'real_name': user.get("real_name"),
                    'name': user.get("name"),
                    'display_name': user.get('profile', {}).get('display_name'),
                    'tz': user.get("tz")
                }
                Row = self.prune_empty(Row)
                batch.put_item(Row)

    def prune_empty(self, row):
        """
        prune attributes whose value is None
        """
        new_row = {}
        for k in row:
            if row[k]:
                new_row[k] = row[k]
        return new_row
