#! /usr/bin/env python3

import sys

from slack_sdk import WebClient

import bulk_store
import channel
import config
import slack_token
import slacker
import utils

slack = slacker.Slacker(config.slack_name, slack_token.read_token)
client = WebClient(token=slack_token.post_token)
channel_obj = channel.Channel()
bulk_store_obj = bulk_store.BulkStore()

channel_name = sys.argv[1]
print("Will attempt to unarchive {}".format(channel_name))
channel_info = channel_obj.get(channel_name)
cid = channel_obj.get(channel_name)['slack_cid']
print("This is channel ID {}".format(cid))
members = bulk_store_obj.get(cid)
members = members.split(",")

print("Found {} members".format(len(members)))

slack.unarchive_channel(cid)
slack.join_channel(cid)
# We can't invite ourself.  We'll know who "we" are by seeing who's in the channel now
my_cid = slack.get_users_for_channel(cid)[0]
members = [x for x in members if x != my_cid]
client.chat_postMessage(channel=cid, text="Greetings fellow humans! This channel is being unarchived by the emergency channel unarchiving system! One moment as we re-populate it with the latest list of members we have for it ({} members)!".format(len(members)))
for members_chunk in utils.chunks(members, 900):
    slack.invite(cid, members_chunk)
    print("Adding {}".format(members_chunk))
client.chat_postMessage(channel=cid, text="We've brought all previously-noted members back into the channel.  Have just the most *awesome* day!")
