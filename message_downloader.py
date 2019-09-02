#! /usr/bin/env python3

import sys
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
        new_messages = [x for x in messages if x.get(
            "subtype") != "bot_message"]
        return new_messages

    def dt(self, timestamp):
        tl = time.localtime(timestamp)
        s = time.strftime("%Y-%m-%d %H:%M", tl)
        return s

    def download(self):
        if len(sys.argv) > 1:
            cids = [self.channel.get(sys.argv[1])['name']]
        else:
            cids = self.slack.get_all_channel_ids()
        # cids = [self.channel.get("devops")["name"]]
        #cids = cids[17:]
        cid_count = len(cids)
        idx = 1
        for cid in cids:
            channel_name = self.channel.get(cid)['name']
            sys.stdout.write("{}/{} {} - {} ".format(idx, cid_count, cid, channel_name))
            idx += 1
            (last_timestamp, refetch) = self.cconfig.get_channel_config(cid)
            refetch = (config.refetch * 86400)
            last_timestamp = int(float(last_timestamp))
            # print("\t Last timestamp is {}".format(self.dt(last_timestamp)))
            timestamp = last_timestamp - refetch
            # print("\t After reducing by {}, timestamp is {}".format(refetch, self.dt(timestamp)))
            timestamp = max(timestamp, self.earliest_timestamp())
            # print("\t After looking at max, timestamp is {}".format(self.dt(timestamp)))
            messages = self.slack.get_messages(cid, timestamp)
            # messages = self.filter_messages(messages)
            # print("Got {} messages since {} in {}".format(
            #   len(messages), self.ts_print(timestamp), cid))
            threads = 0
            message_count = 0
            if messages:
                max_ts = max([int(float(x['ts'])) for x in messages])
                # print(
                #    "Setting max ts for {} to {}".format(
                #        cid, time.asctime(
                #            time.localtime(max_ts))))
                self.cconfig.update_channel_timestamp(cid, max_ts)
                # print("Got {} messages for CID {}".format(len(messages), cid))
                self.MessageWriter.write(messages, cid)
                self.fp.set_channel(cid)
                for message in messages:
                    message_count += 1
                    self.fp.message(message)
                    if message.get("thread_ts") == message.get(
                            "ts"):  # thread head
                        threads += 1
                        thread_author = message['user']
                        thread_messages = self.slack.get_thread_responses(
                            cid, message['thread_ts'])
                        thread_messages = [
                            x for x in thread_messages if x['thread_ts'] != x['ts']]
                        self.MessageWriter.write(
                            thread_messages, cid, thread_author)
            # WRITE_MESSAGES(messages, cid)
            sys.stdout.write(
                "Downloaded {} messages and {} threads\n".format(
                    message_count, threads))
            sys.stdout.flush()
        self.fp.save()


if __name__ == "__main__":
    downloader = Downloader("rands-leadership", slack_token.token)
    downloader.download()
