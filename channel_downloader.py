#! /usr/bin/env python3

import time

import slack_token
import slacker
import channel


class ChannelDownloader(object):

    def __init__(self, sname, stoken):
        self.channel = channel.Channel()
        self.slack = slacker.Slacker(sname, stoken)

    def download(self):
        channels = self.slack.get_all_channels()
        self.channel.batch_upload(channels)


if __name__ == "__main__":
    channel_downloader = ChannelDownloader(
        "rands-leadership", slack_token.token)
    channel_downloader.download()
