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

    def earliest_ts(self):
        """
        Given config.max_age, return the minimum ts we're willing to refetch
        """
        now = time.time()
        then = now - 86400 * config.max_age
        return then

    def ts_print(self, ts):
        return time.asctime(time.localtime(float(ts)))

    def filter_messages(self, messages):
        new_messages = [x for x in messages if x.get(
            "subtype") != "bot_message"]
        return new_messages

    def dt(self, ts):
        tl = time.localtime(ts)
        s = time.strftime("%Y-%m-%d %H:%M", tl)
        return s

    def download(self, start_at = None):
        cids = self.slack.get_all_channel_ids()
        # cids = [self.channel.get("devops")["name"]]
        #cids = cids[17:]
        if start_at:
            cids = cids[start_at:]
        cid_count = len(cids)
        idx = 1
        for cid in cids:
            centry = self.channel.get(cid)
            friendly_name = "unknown"
            if centry:
                friendly_name = centry['friendly_name']
            sys.stdout.write("{}/{} {} - {} ".format(idx, cid_count, cid, friendly_name))
            sys.stdout.flush()
            idx += 1
            last_ts = self.cconfig.get_channel_config(cid)
            refetch = (config.refetch * 86400)
            last_ts = int(float(last_ts))
            # print("\t Last ts is {}".format(self.dt(last_ts)))
            ts = last_ts - refetch
            # print("\t After reducing by {}, ts is {}".format(refetch, self.dt(ts)))
            ts = max(ts, self.earliest_ts())
            # print("\t After looking at max, ts is {}".format(self.dt(ts)))
            messages = self.slack.get_messages(cid, ts)
            # messages = self.filter_messages(messages)
            # print("Got {} messages since {} in {}".format(
            #   len(messages), self.ts_print(ts), cid))
            threads = 0
            message_count = 0
            if messages:
                max_ts = max([int(float(x['ts'])) for x in messages])
                # print(
                #    "Setting max ts for {} to {}".format(
                #        cid, time.asctime(
                #            time.localtime(max_ts))))
                self.cconfig.update_channel_ts(cid, max_ts)
                # print("Got {} messages for CID {}".format(len(messages), cid))
                self.fp.set_channel(cid)
                for message in messages:
                    message_count += 1
                    self.fp.message(message)
                    if message.get("thread_ts") == message.get(
                            "ts"):  # thread head
                        threads += 1
                        if 'user' in message:
                            parent_user_id = message['user']
                        elif 'bot_id' in message:
                            parent_user_id = message['bot_id']
                        else:
                            raise RuntimeError("Could not deduce message author: {}".format(message))
                        thread_messages = self.slack.get_thread_responses(
                            cid, message['thread_ts'])
                        thread_messages = [
                            x for x in thread_messages if x['thread_ts'] != x['ts']]
                        message['replies'] = thread_messages
                        self.MessageWriter.write(
                            thread_messages, cid, parent_user_id)
                self.MessageWriter.write(messages, cid)
            # WRITE_MESSAGES(messages, cid)
            m = "Downloaded {} messages and {} threads\n".format(
                    message_count, threads)
            if message_count == 0 and threads == 0:
                m = "\n"
            sys.stdout.write(m)
            sys.stdout.flush()
        self.fp.save()


if __name__ == "__main__":
    downloader = Downloader("rands-leadership", slack_token.token)
    start_at = None
    if len(sys.argv) > 1:
        start_at = int(sys.argv[1])
    downloader.download(start_at)
