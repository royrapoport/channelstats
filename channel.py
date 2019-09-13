import copy
import ddb
import utils


class Channel(object):
    table_name = "Channel"

    def __init__(self, fake=False):
        self.fake = fake
        if self.fake:
            self.table_name = "Fake" + self.table_name
        self.ddb = ddb.DDB(self.table_name, [('channel_key', 'S')])
        self.table = self.ddb.get_table()

    def batch_get_channel(self, cids):
        return self.ddb.batch_hash_get(cids)

    def batch_upload(self, channels):
        previouslies = {}
        friendly_names = {}
        with self.table.batch_writer() as batch:
            for channel in channels:
                cid = channel['id']
                cname = channel.get('name')
                friendly_names[cname] = 1
                values = {
                    'friendly_name': cname,
                    'slack_cid': cid,
                    'created': channel.get('created'),
                    'members': channel.get('num_members'),
                    'is_channel': channel.get('is_channel', None),
                    'is_im': channel.get('is_im', None),
                    'is_group': channel.get('is_group', None),
                    'is_private': channel.get('is_private', None),
                    'is_mpim': channel.get('is_mpim', None)
                }
                channel_keys = [cid, cname]
                if 'previous_names' in channel:
                    for previous_name in channel['previous_names']:
                        previouslies[previous_name] = copy.deepcopy(values)
                idx = 0
                for k in channel_keys:
                    idx += 1
                    row = {
                        'channel_key': k,
                    }
                    for i in values:
                        row[i] = values[i]
                    row = utils.prune_empty(row)
                    batch.put_item(row)
        # Why are we doing this?
        # Imagine a situation where channel FOO used to be known as BAR
        # normally, we'd create a new entry pointing BAR at FOO
        # But maybe it used to be known as BAR, but also BAR now exists as a new
        # channel.  In that case, we'll prioritize BAR to mean the new channel
        # and not includea  pointer from BAR to the old channel
        for n in friendly_names:
            if n in previouslies:
                del(previouslies[n])
        with self.table.batch_writer() as batch:
            for n in previouslies:
                entry = previouslies[n]
                entry['channel_key'] = n
                batch.put_item(entry)

    def get(self, key):
        response = self.table.get_item(Key={'channel_key': key})
        if 'Item' not in response:
            return None
        result = response['Item']
        result['name'] = result.get('friendly_name')
        return result
