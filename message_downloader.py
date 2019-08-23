#! /usr/bin/env python3

import time

import config
import channel
import channel_configuration
import slack_token
import slacker
import message_writer
import firstpost

class Downloader(object):

    def __init__(self, sname, stoken):
        self.cconfig = channel_configuration.ChannelConfiguration()
        self.slack = slacker.Slacker(sname, stoken)
        self.MessageWriter = message_writer.MessageWriter()
        self.channel = channel.Channel()
        self.fp = firstpost.FirstPost()

    def earliest_timestamp(self):
        """
        Given config.max_age, return the minimum timestamp we're willing to refetch
        """
        now = time.time()
        then = now - 86400 * config.max_age
        return then

    def ts_print(self, timestamp):
        return time.asctime(time.localtime(float(timestamp)))

    def filter_messages(self, messages):
        new_messages = [x for x in messages if x.get("subtype") != "bot_message"]
        return new_messages

    def download(self):
        cids = self.slack.get_all_channel_ids()
        cid_count = len(cids)
        idx = 1
        for cid in cids:
            print("Getting messages for {}/{} {} - {}".format(idx, cid_count, cid, self.channel.get(cid)))
            idx += 1
            (last_timestamp, refetch) = self.cconfig.get_channel_config(cid)
            last_timestamp = int(float(last_timestamp))
            timestamp = last_timestamp - refetch
            timestamp = max(timestamp, self.earliest_timestamp())
            timestamp = self.earliest_timestamp()
            lt = str(timestamp)
            messages = self.slack.get_messages(cid, timestamp)
            messages = self.filter_messages(messages)
            print("Got {} messages since {} in {}".format(len(messages), self.ts_print(timestamp), cid))
            if messages:
                max_ts = max([int(float(x['ts'])) for x in messages])
                print("Setting max ts for {} to {}".format(cid, time.asctime(time.localtime(max_ts))))
                self.cconfig.update_channel_timestamp(cid, max_ts)
                print("Got {} messages for CID {}".format(len(messages), cid))
                self.MessageWriter.write(messages, cid)
                self.fp.set_channel(cid)
                for message in messages:
                    self.fp.message(message)
            # WRITE_MESSAGES(messages, cid)
        self.fp.save()

if __name__ == "__main__":
    downloader = Downloader("rands-leadership", slack_token.token)
    downloader.download()
