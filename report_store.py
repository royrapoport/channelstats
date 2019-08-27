#! /usr/bin/env python3


import ddb
import utils

class ReportStore(object):

    def __init__(self, max_size=300000):
        self.DDB = ddb.DDB("ReportStore", [("report_id", "S")])
        self.table = self.DDB.get_table()
        self.max_size = max_size

    def set(self, report_id, report):
        """
        Store the report; if necessary, chop it up
        """
        assert type(report) == str
        if len(report) > self.max_size:
            # print("Report size is too large -- chunking it up")
            self.store_chunks(report_id, report)
        else:
            # print("Report is small enough to store as one blob")
            self.store_chunk(report_id, report)

    def store_chunks(self, report_id, report):
        """
        Normally, called here means that we know we're going to have
        multiple chunks
        """
        # But just in case
        if len(report) < self.max_size:
            self.store_chunk(report_id, report)
        counter = 0
        indexes = {}
        for chunk in utils.chunks(report, self.max_size):
            temp_key = "{}-{}".format(report_id, counter)
            # We don't really need to batch-write these, because they're
            # so big that batch writer will do them individually anyway
            self.store_chunk(temp_key, chunk)
            indexes[counter] = temp_key
            counter += 1

        item = {'report_id': report_id}
        for k in indexes:
            item[str(k)] = indexes[k]
        # print("item: {}".format(item))
        self.table.put_item(Item=item)

    def store_chunk(self, report_id, report_string):
        Item = {
            'report_id': report_id,
            'value': report_string
        }
        self.table.put_item(Item=Item)

    def delete(self, report_id):
        """
        delete the report identified as report_id
        """
        # this is slightly more complicated than normally
        # Because if the report is chunked, we want to delete the chunks
        # So first we have to get it
        response = self.table.get_item(Key={'report_id': report_id})
        if 'Item' not in response:
            # Done!
            return
        item = response['Item']
        if 'value' not in item: # Chunk or unchunked report
            for k in item.keys():
                if k != "report_id": # It's an index
                    index_name = item[k]
                    self.delete(index_name)
        # print("Deleting item {}".format(report_id))
        self.table.delete_item(Key={'report_id': report_id})


    def get(self, report_id):
        """
        Query DDB for the report with the given parameters
        """
        response = self.table.get_item(Key={'report_id': report_id})
        if 'Item' not in response:
            return None
        item = response['Item']
        if 'value' in item: # This was an unchunke report
            return item['value']
        # If we got here, then we have a chunked report
        # print("chunked item: {}".format(item))
        chunked_report_ids = []
        chunks = [int(x) for x in item.keys() if x != "report_id"]
        # print("Chunks: {}".format(chunks))
        chunks.sort()
        for kname in chunks:
            chunked_report_ids.append(item[str(kname)])
        report_chunks = self.DDB.batch_hash_get(chunked_report_ids)
        # report chunks are indexed by chunked_report_id.  We need to
        # assemble them in order
        payload = ""
        for chunk in chunks:
            chunk_key = item[str(chunk)]
            chunk_blob = report_chunks[chunk_key]['value']
            payload += chunk_blob
        return payload
