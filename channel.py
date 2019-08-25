
import ddb
import utils

class Channel(object):
    table_name = "Channel"

    def __init__(self):
        self.ddb = ddb.DDB(self.table_name, [('key', 'S')])
        self.table = self.ddb.get_table()

    def batch_upload(self, channels):
        with self.table.batch_writer() as batch:
            for channel in channels:
                cid = channel['id']
                cname = channel.get("name")
                created = channel['created']
                Row = {'key': cid, 'name': cname, 'created': created}
                Row = utils.prune_empty(Row)
                batch.put_item(Row)
                Row = {'key': cname, 'name': cid, 'created': created}
                Row = utils.prune_empty(Row)
                batch.put_item(Row)

    def get(self, key):
        response = self.table.get_item(Key={'key': key})
        if 'Item' not in response:
            return None
        item = response['Item']
        return item
