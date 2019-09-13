
import re
import time

import boto3
from boto3.dynamodb.conditions import Key
import ddb
import utils
import config
import userhash
import configuration

class Message(object):
    table_name = "Message"

    def __init__(self):
        self.ddb = ddb.DDB(self.table_name, [('cid_ts', 'S')])
        self.table = self.ddb.get_table()
        self.create_global_secondary_index()

    def create_global_secondary_index(self):
        if self.table.global_secondary_indexes:
            return
        print("Creating Global Secondary Index")
        self.ddb.dynamodb_client.update_table(TableName=self.table.name,
               AttributeDefinitions=[{'AttributeName': 'date', 'AttributeType': 'S'}],
               GlobalSecondaryIndexUpdates=[ {
                 'Create': {
                        'IndexName': 'DateIndex',
                        'KeySchema': [{'AttributeName': 'date', 'KeyType': 'HASH'}],
                        'Projection': {'ProjectionType': 'ALL'},
                            }
                        }
                    ]
              )

    def messages_for_day(self, day):
        """
        given a yyyy-mm-dd day, returns generator you can use to get
        all the messages we have for that day
        """

        ExclusiveStartKey = None
        run = True
        while run:
            if ExclusiveStartKey:
                resp = self.table.query(IndexName="DateIndex",
                    ExclusiveStartKey=ExclusiveStartKey,
                    KeyConditionExpression=Key('date').eq(day))
            else:
                resp = self.table.query(IndexName="DateIndex",
                    KeyConditionExpression=Key('date').eq(day))
            if 'LastEvaluatedKey' in resp:
                ExclusiveStartKey = resp['LastEvaluatedKey']
            else:
                run = False
            for item in resp['Items']:
                yield item
