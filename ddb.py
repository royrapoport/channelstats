
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
            self.dynamodb_resource = boto3.resource(
                'dynamodb', region_name=config.region, endpoint_url="http://localhost:8000")
            self.dynamodb_client = boto3.client(
                'dynamodb',
                region_name=config.region,
                endpoint_url="http://localhost:8000")
        else:
            self.dynamodb_resource = boto3.resource(
                'dynamodb', region_name=config.region)
            self.dynamodb_client = boto3.client(
                'dynamodb', region_name=config.region)
        self.attributes = attributes
        if attributes:
            self.validate_attributes()
        self.table_name = config.prefix + "." + table_name
        self.table = None

    @staticmethod
    def items(table):
        """
        generator function to return the items in the table
        (basically, a wrapper around table.scan()
        """
        done = False
        ExclusiveStartKey = None
        while not done:
            if ExclusiveStartKey:
                response = table.scan(ExclusiveStartKey=ExclusiveStartKey)
            else:
                response = table.scan()
            if "LastEvaluatedKey" in response:
                ExclusiveStartKey = response['LastEvaluatedKey']
            else:
                done = True
            for item in response['Items']:
                yield item

    @staticmethod
    def delete_empty_tables():
        """
        In case we accidentally created some empty tables in this
        namespace, find them and delete them
        """
        table_names = self.list_tables()
        for table_name in table_names:
            d = DDB(table_name)
            prefixed_table_name = d.table_name
            description = d.dynamodb_client.describe_table(TableName=prefixed_table_name)
            count = description['Table']['ItemCount']
            if count == 0:
                d.get_table().delete()

    def list_tables(self):
        done = False
        start_table = None
        tables = []
        while not done:
            if start_table:
                response = self.dynamodb_client.list_tables(ExclusiveStartTableName=start_table)
            else:
                response = self.dynamodb_client.list_tables()
            tables += response['TableNames']
            if 'LastEvaluatedTableName' in response:
                start_table = response['LastEvaluatedTableName']
            else:
                done = True
        pref = config.prefix + "."
        # Only match the tables that start with our prefix
        tables = [x for x in tables if x.find(pref) == 0]
        # Now, remove our prefix
        tables = [x.replace(pref, "") for x in tables]
        return tables

    def batch_hash_get(self, hashlist, hashkeyname=None):
        if not hashkeyname:
            if not self.attributes:
                raise RuntimeError(
                    "Can't avoid specifying hashkeyname if created without explicit attributes")
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
            raise RuntimeError(
                "mini_batch_hash_get must be called with no more than 99 items")

            # print("Given no hashkeyname, defaulted to {}".format(hashkeyname))
        request_items = dict()
        request_items[self.table_name] = {}
        request_items[self.table_name]['Keys'] = []
        for i in hashlist:
            request_items[self.table_name]['Keys'].append({hashkeyname: i})
        response = self.dynamodb_resource.batch_get_item(
            RequestItems=request_items)
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

    def get_table(self, readonly=False):
        """
        return the DDB table for channel configuration
        if readonly and the table does not exist, do not create it; return None instead
        """

        table = None
        if self.table:
            return self.table

        try:
            self.dynamodb_client.describe_table(TableName=self.table_name)
            table = self.dynamodb_resource.Table(self.table_name)
        except BaseException:
            if not self.attributes:
                raise RuntimeError(
                    "Given no attributes, I cannot create a table")
            if not readonly:
                table = self.create_table()
        self.table = table
        return table

    def delete_table(self):
        table = self.get_table()
        table.delete()

    def dump(self, fname):
        items = []
        for item in self.items(self.get_table()):
            items.append(item)
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
        hash_attribute = self.attributes[0]
        hash_name = hash_attribute[0]
        hash_type = hash_attribute[1]
        keyschema.append({'AttributeName': hash_name, 'KeyType': 'HASH'})
        attributedefinitions.append(
            {'AttributeName': hash_name, 'AttributeType': hash_type})
        if len(self.attributes) > 1:
            range_attribute = self.attributes[1]
            range_name = range_attribute[0]
            range_type = range_attribute[1]
            keyschema.append({'AttributeName': range_name, 'KeyType': 'RANGE'})
            attributedefinitions.append(
                {'AttributeName': range_name, 'AttributeType': range_type})

        table = self.dynamodb_resource.create_table(
            TableName=self.table_name,
            KeySchema=keyschema,
            AttributeDefinitions=attributedefinitions,
            BillingMode='PAY_PER_REQUEST'
        )
        self.dynamodb_client.get_waiter(
            'table_exists').wait(TableName=self.table_name)
        return table
