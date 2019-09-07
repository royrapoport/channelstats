import time
import ddb
import utils


class ChannelMembersLog(object):
    table_name = "ChannelMembersLog"

    def __init__(self, fake=False):
        self.fake = fake
        if self.fake:
            self.table_name = "Fake" + self.table_name
        self.ddb = ddb.DDB(self.table_name, [('channel_id', 'S')])
        self.table = self.ddb.get_table()

    def batch_upload(self, channels):
        now = str(time.time())
        new_rows = []
        update_rows = []
        for channel in channels:
            cid = channel['id']
            members = 0
            if 'num_members' in channel:
                members = channel['num_members']
            row = {'channel_id': cid, now: members}
            item = self.get(cid)
            if item:
                update_rows.append(row)
            else:
                new_rows.append(row)
        with self.table.batch_writer() as batch:
            for row in new_rows:
                batch.put_item(row)
        for row in update_rows:
            self.table.update_item(
                Key = {'channel_id': row['channel_id']},
                UpdateExpression='set {} = :m'.format(now),
                ExpressionAttributeValues={':m': row[now]},
                ReturnValue='UPDATED_NEW'
            )

    def get(self, key):
        response = self.table.get_item(Key={'channel_id': key})
        return response.get('Item')
