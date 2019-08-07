#! /usr/bin/env python3

import time

import channel_configuration
import slack_token
import slacker
import message_writer

class Downloader(object):

    # Maximum age in days of messages
    max_age = 2

    def __init__(self, sname, stoken, local=False):
        self.cconfig = channel_configuration.ChannelConfiguration(local=local)
        self.slack = slacker.Slacker(sname, stoken)
        self.MessageWriter = message_writer.MessageWriter(local=local)

    def earliest_timestamp(self):
        """
        Given self.max_age, return the minimum timestamp we're willing to refetch
        """
        now = time.time()
        then = now - 86400 * self.max_age
        return then

    def ts_print(self, timestamp):
        return time.asctime(time.localtime(float(timestamp)))

    def filter_messages(self, messages):
        new_messages = [x for x in messages if x.get("subtype") != "bot_message"]
        return new_messages

    def download(self):
        for cid in self.slack.get_all_channel_ids():
            print("Getting messages for {}".format(cid))
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
                self.cconfig.set_channel_config(cid, max_ts, 0)
                print("Got {} messages for CID {}".format(len(messages), cid))
                self.MessageWriter.write(messages, cid)
            # WRITE_MESSAGES(messages, cid)

if __name__ == "__main__":
    downloader = Downloader("rands-leadership", slack_token.token, local=True)
    downloader.download()
