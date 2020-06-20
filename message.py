#! /usr/bin/env python3

import re
import time

import boto3
from boto3.dynamodb.conditions import Key
import ddb
import utils
import config
import configuration


class Message(object):
    table_name = "Message"

    def __init__(self):
        self.ddb = ddb.DDB(self.table_name, [('cid_ts', 'S')])
        self.table = self.ddb.get_table()
        self.create_global_secondary_index()

    def gsi(self, attname, wait=True):
        """
        Create a GSI for attname, named AttnameIndex; wait until done if wait
        """
        idxname = attname.capitalize()
        AttributeDefinitions = [{'AttributeName': attname, 'AttributeType': 'S'}]
        Projection = {'ProjectionType': 'ALL'}
        KeySchema = [{'AttributeName': attname, 'KeyType': 'HASH'}],
        Create = {'IndexName': idxname, 'KeySchema': KeySchema, 'Projection': Projection}
        GSIUpdates = [{'Create': Create}]
        self.ddb.dynamodb_client.update_table(TableName=self.table.name,
                                              AttributeDefinitions=AttributeDefinitions,
                                              GlobalSecondaryIndexUpdates=GSIUpdates,
                                              )
        if wait:
            done = False
            while not done:
                self.table.reload()
                gsis = self.table.global_secondary_indexes
                if not gsis:
                    print("GSI creation incomplete -- no GSIs created.  Waiting")
                else:
                    nonactive = [x for x in gsis if x['IndexStatus'] != "ACTIVE"]
                    if nonactive:
                        m = "GSI creation incomplete -- Inactive GSIs pending: "
                        m += "{}.  Waiting".format([x['IndexName'] for x in nonactive])
                        print(m)
                    else:
                        done = True
                if not done:
                    time.sleep(5)

    def create_global_secondary_index(self):
        if self.table.global_secondary_indexes:
            return
        for attribute in ["date", "slack_cid", "user_id"]:
            self.gsi(attribute, wait=True)

    def gsi_search(self, field_name, GSIname, field_value):
        """
        Given a field_name, a GSIname, and a field_value
        return generator you can use to get all items that have
        that field_value for that field_name indexed by GSIname
        (GlobalSecondaryIndex)
        """

        ExclusiveStartKey = None
        run = True
        while run:
            if ExclusiveStartKey:
                resp = self.table.query(IndexName=GSIname,
                                        ExclusiveStartKey=ExclusiveStartKey,
                                        KeyConditionExpression=Key(field_name).eq(field_value))
            else:
                resp = self.table.query(IndexName=GSIname,
                                        KeyConditionExpression=Key(field_name).eq(field_value))
            if 'LastEvaluatedKey' in resp:
                ExclusiveStartKey = resp['LastEvaluatedKey']
            else:
                run = False
            for item in resp['Items']:
                yield item

    def messages_for_channel(self, cid):
        """
        given a cid (Channel ID), return generator you can use to get all messages
        we have for that channel
        """

        return self.gsi_search("slack_cid", "Slack_cid", cid)

    def messages_for_user(self, user):
        """
        given a user_id, return generator you can use to get all messages
        we have for that user
        """

        return self.gsi_search("user_id", "User_id", user)

    def messages_for_day(self, day):
        """
        given a yyyy-mm-dd day, returns generator you can use to get
        all the messages we have for that day
        """

        return self.gsi_search("date", "Date", day)


if __name__ == "__main__":
    # Just create the table and GSIs
    m = Message()
