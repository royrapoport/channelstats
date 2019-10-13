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
        self.ddb.dynamodb_client.update_table(TableName=self.table.name,
               AttributeDefinitions=[{'AttributeName': attname, 'AttributeType': 'S'}],
               GlobalSecondaryIndexUpdates=[ {
                 'Create': {
                        'IndexName': idxname,
                        'KeySchema': [{'AttributeName': attname, 'KeyType': 'HASH'}],
                        'Projection': {'ProjectionType': 'ALL'},
                            }
                        }
                    ]
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
                        print("GSI creation incomplete -- Inactive GSIs pending: {}.  Waiting".format([x['IndexName'] for x in nonactive]))
                    else:
                        done = True
                if not done:
                    time.sleep(5)

    def create_global_secondary_index(self):
        if self.table.global_secondary_indexes:
            return
        for attribute in ["date", "slack_cid", "user_id"]:
            self.gsi(attribute, wait=True)

    def messages_for_day(self, day):
        """
        given a yyyy-mm-dd day, returns generator you can use to get
        all the messages we have for that day
        """

        ExclusiveStartKey = None
        run = True
        while run:
            if ExclusiveStartKey:
                resp = self.table.query(IndexName="Date",
                    ExclusiveStartKey=ExclusiveStartKey,
                    KeyConditionExpression=Key('date').eq(day))
            else:
                resp = self.table.query(IndexName="Date",
                    KeyConditionExpression=Key('date').eq(day))
            if 'LastEvaluatedKey' in resp:
                ExclusiveStartKey = resp['LastEvaluatedKey']
            else:
                run = False
            for item in resp['Items']:
                yield item

if __name__ == "__main__":
    # Just create the table and GSIs
    m = Message()

