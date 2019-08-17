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

    def download(self):
        cids = self.slack.get_all_channel_ids()
        cid_count = len(cids)
        idx = 1
        for cid in cids:
            print("Getting messages for {}/{} {} - {}".format(idx, cid_count, cid, self.channel.get(cid)))
            gotit = self.fp.get_channel(cid)
            if gotit:
                print("\tSkipping channel -- already got it")
                continue
            idx += 1
            self.fp.channel = cid
            messages = self.slack.get_messages(cid, 0, self.fp.message)
            self.fp.save()

if __name__ == "__main__":
    downloader = Downloader("rands-leadership", slack_token.token)
    downloader.download()
