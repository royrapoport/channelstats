#! /usr/bin/env python3

import sys
import time

import slack_token
import slacker
import channel
import channel_members_log
import bulk_store


class ChannelDownloader(object):

    def __init__(self, sname, stoken):
        self.channel = channel.Channel()
        self.channel_members_log = channel_members_log.ChannelMembersLog()
        self.slack = slacker.Slacker(sname, stoken)
        self.bulk_store = bulk_store.BulkStore()

    def download(self, include_private=False):
        start_time = time.time()
        channel_types = ['public_channel']
        if include_private:
            channel_types.append('private_channel')
        channels = self.slack.get_all_channels(types=channel_types)
        channels = [x for x in channels if x['is_archived'] == False]
        channels.sort(key = lambda x: x['name'])
        # channels = [x for x in channels if x['name'].find("ztest") == 0]
        print("Getting channel memberships now ... ")
        total = len(channels)
        idx = 0
        for channel in channels:
            idx += 1
            m = "{}/{} Downloading members for {} ... ".format(idx, total, channel['name'])
            sys.stdout.write(m)
            cid = channel['id']
            try:
                members = self.slack.get_users_for_channel(cid)
            except:
                sys.stdout.write("F\n")
                sys.stdout.flush()
                continue
            # When a channel is archived its membership is purged
            # We don't want to store empty memberships because we want to
            # basically always have the last membership before the channel
            # was archived
            count = len(members)
            sys.stdout.write(str(count) + "\n")
            sys.stdout.flush()
            if count == 0:
                continue
            members_string = ",".join(members)
            self.bulk_store.set(cid, members_string)
        self.channel.batch_upload(channels)
        self.channel_members_log.batch_upload(channels)
        end_time = time.time()
        diff_time = int(end_time - start_time)
        print("Downloaded channel information in {} seconds".format(diff_time)) 



if __name__ == "__main__":
    channel_downloader = ChannelDownloader(
        "rands-leadership", slack_token.token)
    channel_downloader.download()
