
import ddb

import config


class ChannelConfiguration(object):
    table_name = "ChannelConfiguration"

    def __init__(self):
        self.ddb = ddb.DDB(self.table_name, [('slack_cid', 'S')])
        self.table = self.ddb.get_table()

    def channel_configuration_exists(self, slack_cid):
        response = self.table.get_item(
            Key={
                'slack_cid': slack_cid
            }
        )
        return 'Item' in response

    def update_channel_timestamp(self, slack_cid, last_message_timestamp):
        if not self.channel_configuration_exists(slack_cid):
            self.set_channel_config(slack_cid, last_message_timestamp)
            return

        self.table.update_item(
            Key={
                'slack_cid': slack_cid
            },
            UpdateExpression="set last_message_timestamp=:t",
            ExpressionAttributeValues={
                ":t": int(last_message_timestamp)
            },
            ReturnValues="UPDATED_NEW"
        )

    def set_channel_config(
            self,
            slack_cid,
            last_message_timestamp):
        """
        Sets configuration for the given slack_cid
        """

        self.table.put_item(
            Item={
                'slack_cid': slack_cid,
                'last_message_timestamp': str(last_message_timestamp)
            }
        )

    def get_channel_config(self, cid):
        """
        returns last_message_timestamp for cid
        If we have never gotten cid, last_message_timestamp will be 0
        """
        response = self.table.get_item(
            Key={
                'slack_cid': cid
            }
        )
        if 'Item' not in response:
            return 0
        item = response['Item']
        last_message_timestamp = item['last_message_timestamp']
        ret = last_message_timestamp
        return ret
