#! /usr/bin/env python

import time

import boto3


class MessageTableFactory(object):

    def __init__(self, local=False):
        self.__day_tables = {}
        self.local = local
        if local:
            self.dynamodb_resource = boto3.resource('dynamodb', endpoint_url="http://localhost:8000")
            self.dynamodb_client = boto3.client('dynamodb', endpoint_url="http://localhost:8000")
        else:
            self.dynamodb_resource = boto3.resource('dynamodb')
            self.dynamodb_client = boto3.client('dynamodb')

    def get_existing_tables(self):
        """
        Returns list of existing tables
        """
        return self.dynamodb_client.list_tables()['TableNames']

    def get_message_table_name(self, timestamp):
        """
        given str timestamp, return the name of the Message table we'll store
        a message in
        """
        return "Message-{}".format(self.make_day(timestamp))

    def make_day(self, timestamp):
        """
        Given a str timestamp, return yyyy-mm-dd
        """
        lt = time.localtime(int(float(timestamp)))
        return time.strftime("%Y-%m-%d", lt)

    def get_message_table(self, timestamp):
        """
        Return a pynamodb.models.Model Table for the given UNIX timestamp;
        if local, use a local endpoint for DynamoDB
        """

        day = self.make_day(timestamp)
        if day not in self.__day_tables:
            table_name = self.get_message_table_name(timestamp)
            try:
                self.dynamodb_client.describe_table(TableName=table_name)
                table = self.dynamodb_resource.Table(table_name)
            except botocore.errorfactory.ResourceNotFoundException:
                table = self.create_table(table_name)
            self.__day_tables[day] = table
        return self.__day_tables[day]

    def create_table(self, table_name):
        """
        creates DynamoDB table with this name; waits until table is created;
        returns table
        """
        table = self.dynamodb_resource.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': "timestamp",
                    'KeyType': 'HASH'
                },
                {
                    'AttributeName': "slack_cid",
                    'KeyType': 'RANGE'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': "timestamp",
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': "slack_cid",
                    'AttributeType': 'S'
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 10,
                'WriteCapacityUnits': 10
            }
        )
        self.dynamodb_client.get_waiter('table_exists').wait(TableName=table_name)
        return table
