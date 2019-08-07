
import ddb

class Channel(object):
    table_name = "Channel"

    def __init__(self, local=False):
        self.local = local
        self.ddb = ddb.DDB(self.table_name, [('key', 'S')], (10,10), local=local)
        self.table = self.ddb.get_table()

    def batch_upload(self, channels):
        with self.table.batch_writer() as batch:
            for channel in channels:
                cid = channel['id']
                cname = channel.get("name")
                Row = {'key': cid, 'value': cname}
                Row = self.prune_empty(Row)
                batch.put_item(Row)
                Row = {'key': cname, 'value': cid}
                Row = self.prune_empty(Row)
                batch.put_item(Row)

    def get(self, key):
        response = self.table.get_item(Key={'key': key})
        if 'Item' not in response:
            return None
        item = response['Item']
        return item['value']

    def prune_empty(self, row):
        """
        prune attributes whose value is None
        """
        new_row = {}
        for k in row:
            if row[k]:
                new_row[k] = row[k]
        return new_row
