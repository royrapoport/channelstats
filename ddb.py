
import boto3

import config

class DDB(object):

    def __init__(self, table_name, attributes, provisioned_throughput):
        """
        table_name is self-explanatory
        attributes is a list of one or two (attribute_name, attribute_type); first is HASH, second
        if present is RANGE.  attribute_type is S, N, etc (as per boto/dynamodb)
        provisioned_throughput is a list of (read_capacity_units, write_capacity_units)
        local is boolean, whether we're using local dynamodb
        """
        if config.local:
            self.dynamodb_resource = boto3.resource('dynamodb', endpoint_url="http://localhost:8000")
            self.dynamodb_client = boto3.client('dynamodb', endpoint_url="http://localhost:8000")
        else:
            self.dynamodb_resource = boto3.resource('dynamodb')
            self.dynamodb_client = boto3.client('dynamodb')
        self.attributes = attributes
        self.provisioned_throughput = provisioned_throughput
        self.validate_attributes()
        self.validate_provisioned_throughput()
        self.table_name = table_name
        self.table = None

    def validate_provisioned_throughput(self):
        pt = self.provisioned_throughput
        assert len(pt) == 2
        assert type(pt[0]) == int
        assert type(pt[1]) == int

    def validate_attributes(self):
        at = self.attributes
        assert len(at) > 0
        assert len(at) < 3
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/customizations/dynamodb.html
        valid_types = "S N B BOOL NULL SS NS BS L M".split()
        for a in at:
            assert len(a) == 2, "Attribute {} is not a 2-item list".format(a)
            assert a[1] in valid_types

    def get_table(self):
        """
        return the DDB table for channel configuration
        """

        if self.table:
            return self.table

        try:
            self.dynamodb_client.describe_table(TableName=self.table_name)
            table = self.dynamodb_resource.Table(self.table_name)
        except:
            table = self.create_table()
        self.table = table
        return table

    def delete_table(self):
        table = self.get_table()
        table.delete()

    def create_table(self):
        """
        creates DynamoDB table.  Returns table
        """
        keyschema = []
        attributedefinitions = []
        hash = self.attributes[0]
        hash_name = hash[0]
        hash_type = hash[1]
        keyschema.append({'AttributeName':hash_name, 'KeyType':'HASH'})
        attributedefinitions.append({'AttributeName':hash_name, 'AttributeType':hash_type})
        if len(self.attributes) > 1:
            range = self.attributes[1]
            range_name = range[0]
            range_type = range[1]
            keyschema.append({'AttributeName':range_name, 'KeyType':'RANGE'})
            attributedefinitions.append({'AttributeName':range_name, 'AttributeType':range_type})

        read_units = self.provisioned_throughput[0]
        write_units = self.provisioned_throughput[1]
        provisioned_throughput = {'ReadCapacityUnits': read_units, 'WriteCapacityUnits':write_units}

        table = self.dynamodb_resource.create_table(
            TableName=self.table_name,
            KeySchema=keyschema,
            AttributeDefinitions=attributedefinitions,
            ProvisionedThroughput=provisioned_throughput
        )
        self.dynamodb_client.get_waiter('table_exists').wait(TableName=self.table_name)
        return table
