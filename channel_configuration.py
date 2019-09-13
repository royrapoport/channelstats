
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

    def update_channel_ts(self, slack_cid, last_message_ts):
        if not self.channel_configuration_exists(slack_cid):
            self.set_channel_config(slack_cid, last_message_ts)
            return

        self.table.update_item(
            Key={
                'slack_cid': slack_cid
            },
            UpdateExpression="set last_message_ts=:t",
            ExpressionAttributeValues={
                ":t": int(last_message_ts)
            },
            ReturnValues="UPDATED_NEW"
        )

    def set_channel_config(
            self,
            slack_cid,
            last_message_ts):
        """
        Sets configuration for the given slack_cid
        """

        self.table.put_item(
            Item={
                'slack_cid': slack_cid,
                'last_message_ts': str(last_message_ts)
            }
        )

    def get_channel_config(self, cid):
        """
        returns last_message_ts for cid
        If we have never gotten cid, last_message_ts will be 0
        """
        response = self.table.get_item(
            Key={
                'slack_cid': cid
            }
        )
        if 'Item' not in response:
            return 0
        item = response['Item']
        last_message_ts = item['last_message_ts']
        ret = last_message_ts
        return ret
