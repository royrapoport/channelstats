#! /usr/bin/env python3


import ddb
import utils


class BulkStore(object):

    def __init__(self, max_size=300000):
        self.DDB = ddb.DDB("BulkStore", [("item_id", "S")])
        self.table = self.DDB.get_table()
        self.max_size = max_size

    def set(self, item_id, content):
        """
        Store the item; if necessary, chop it up
        """
        assert isinstance(content, str)
        if len(content) > self.max_size:
            # print("Item size is too large -- chunking it up")
            self.store_chunks(item_id, content)
        else:
            # print("Report is small enough to store as one blob")
            self.store_chunk(item_id, content)

    def store_chunks(self, item_id, content):
        """
        Normally, called here means that we know we're going to have
        multiple chunks
        """
        # But just in case
        if len(content) < self.max_size:
            self.store_chunk(item_id, content)
        counter = 0
        indexes = {}
        for chunk in utils.chunks(content, self.max_size):
            temp_key = "{}-{}".format(item_id, counter)
            # We don't really need to batch-write these, because they're
            # so big that batch writer will do them individually anyway
            self.store_chunk(temp_key, chunk)
            indexes[counter] = temp_key
            counter += 1

        item = {'item_id': item_id}
        for k in indexes:
            item[str(k)] = indexes[k]
        # print("item: {}".format(item))
        self.table.put_item(Item=item)

    def store_chunk(self, item_id, content):
        Item = {
            'item_id': item_id,
            'value': content
        }
        self.table.put_item(Item=Item)

    def delete(self, item_id):
        """
        delete the item identified as item_id
        """
        # this is slightly more complicated than normally
        # Because if the item is chunked, we want to delete the chunks
        # So first we have to get it
        response = self.table.get_item(Key={'item_id': item_id})
        if 'Item' not in response:
            # Done!
            return
        item = response['Item']
        if 'value' not in item:  # Chunk or unchunked report
            for k in item.keys():
                if k != "item_id":  # It's an index
                    index_name = item[k]
                    self.delete(index_name)
        # print("Deleting item {}".format(report_id))
        self.table.delete_item(Key={'item_id': item_id})

    def get(self, item_id):
        """
        Query DDB for the item with the given parameters
        """
        response = self.table.get_item(Key={'item_id': item_id})
        if 'Item' not in response:
            return None
        item = response['Item']
        if 'value' in item:  # This was an unchunke report
            return item['value']
        # If we got here, then we have a chunked item
        # print("chunked item: {}".format(item))
        chunked_item_ids = []
        chunks = sorted([int(x) for x in item.keys() if x != "item_id"])
        # print("Chunks: {}".format(chunks))
        for kname in chunks:
            chunked_item_ids.append(item[str(kname)])
        item_chunks = self.DDB.batch_hash_get(chunked_item_ids)
        # report chunks are indexed by chunked_item_id.  We need to
        # assemble them in order
        payload = ""
        for chunk in chunks:
            chunk_key = item[str(chunk)]
            chunk_blob = item_chunks[chunk_key]['value']
            payload += chunk_blob
        return payload
