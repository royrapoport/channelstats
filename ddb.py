
import boto3
import json

import config
import utils

class DDB(object):

    def __init__(self, table_name, attributes=None):
        """
        table_name is self-explanatory
        attributes is a list of one or two (attribute_name, attribute_type); first is HASH, second
        if present is RANGE.  attribute_type is S, N, etc (as per boto/dynamodb)
        local is boolean, whether we're using local dynamodb
        """
        if config.local:
            self.dynamodb_resource = boto3.resource('dynamodb', region_name=config.region, endpoint_url="http://localhost:8000")
            self.dynamodb_client = boto3.client('dynamodb', region_name=config.region, endpoint_url="http://localhost:8000")
        else:
            self.dynamodb_resource = boto3.resource('dynamodb', region_name=config.region)
            self.dynamodb_client = boto3.client('dynamodb', region_name=config.region)
        self.attributes = attributes
        if attributes:
            self.validate_attributes()
        self.table_name = config.prefix + "." + table_name
        self.table = None

    def batch_hash_get(self, hashlist, hashkeyname=None):
        if not hashkeyname:
            if not self.attributes:
                raise RuntimeError("Can't avoid specifying hashkeyname if created without explicit attributes")
            hashkeyname = self.attributes[0][0]
        ret = {}
        for chunk in utils.chunks(hashlist, 99):
            miniret = self.mini_batch_hash_get(chunk, hashkeyname)
            for i in miniret:
                ret[i] = miniret[i]
        return ret

    def mini_batch_hash_get(self, hashlist, hashkeyname):
        """
        given a list of hashkeys, return all matching items from the table using batch operations
        """
        if len(hashlist) > 99:
            raise RuntimeError("mini_batch_hash_get must be called with no more than 99 items")

            # print("Given no hashkeyname, defaulted to {}".format(hashkeyname))
        RequestItems = {}
        RequestItems[self.table_name] = {}
        RequestItems[self.table_name]['Keys'] = []
        for i in hashlist:
            RequestItems[self.table_name]['Keys'].append({hashkeyname: i})
        response = self.dynamodb_resource.batch_get_item(RequestItems=RequestItems)
        items = response['Responses'][self.table_name]
        item_dict = {}
        for i in items:
            k = i[hashkeyname]
            item_dict[k] = i
        return item_dict

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
            if not self.attributes:
                raise RuntimeError("Given no attributes, I cannot create a table")
            table = self.create_table()
        self.table = table
        return table

    def delete_table(self):
        table = self.get_table()
        table.delete()

    def dump(self, fname):
        response = self.get_table().scan()
        items = response['Items']
        f = open(fname, "w")
        f.write(utils.dumps(items))
        f.close()

    def load(self, fname):
        f = open(fname, "r")
        content = f.read()
        items = json.loads(content)
        f.close()
        with self.get_table().batch_writer() as batch:
            for item in items:
                batch.put_item(item)

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

        table = self.dynamodb_resource.create_table(
            TableName=self.table_name,
            KeySchema=keyschema,
            AttributeDefinitions=attributedefinitions,
            BillingMode='PAY_PER_REQUEST'
        )
        self.dynamodb_client.get_waiter('table_exists').wait(TableName=self.table_name)
        return table
