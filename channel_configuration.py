
import boto3
import ddb

class ChannelConfiguration(object):
    table_name = "ChannelConfiguration"

    def __init__(self, local=False):
        self.local = local
        self.ddb = ddb.DDB(self.table_name, [('slack_cid', 'S')], (10,10), local=local)
        self.table = self.ddb.get_table()

    def set_channel_config(self, slack_cid, last_message_timestamp, refetch_interval):
        """
        Sets configuration for the given slack_cid
        """

        self.table.put_item(
            Item={
                'slack_cid':slack_cid,
                'last_message_timestamp':str(last_message_timestamp),
                'refetch':refetch_interval
            }
        )

    def get_channel_config(self, cid):
        """
        returns (last_message_timestamp, refetch_interval) for cid
        If we have never gotten cid, last_message_timestamp will be 0
        if we don't have a defined refetch_interval, refetch_interval will be 0
        """
        response = self.table.get_item(
            Key={
                'slack_cid': cid
            }
        )
        if 'Item' not in response:
            return (0,0)
        item = response['Item']
        last_message_timestamp = item['last_message_timestamp']
        refetch = int(item['refetch'])
        ret = (last_message_timestamp, refetch)
        # print("Configuration for {} is {}".format(cid, ret))
        return ret
