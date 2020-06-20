#! /usr/bin/env python

import sys
import urllib.parse

import config
import channel
import slack_token
import slacker

if len(sys.argv) < 2:
    print("Usage: {} CHANNELNAME [CHANNELNAME...]".format(sys.argv[0]))
    sys.exit(0)

cobj = channel.Channel()
friendlies = cobj.friendly_channel_names()
channels = sys.argv[1:]
creates = []
for c in channels:
    if c not in friendlies:
        print("Skipping {}: not a real channel".format(c))
    else:
        creates.append(c)

print("Will create stats channels for {}".format(creates))
slack = slacker.Slacker(config.slack_name, slack_token.token)

for c in creates:
    cs = "{}-stats".format(c)
    u = "channels.create?name={}".format(cs)
    ret = slack.api_call(u)
    if ret['ok'] is True:
        print("Oh oh: {}".format(ret))
        continue
    cid = ret['channel']['id']
    purpose = "A place to post (and, perhaps, discuss) posting stats to the #{} channel".format(c)
    purpose = urllib.parse.quote(purpose)
    u = "channels.setPurpose?channel={}&purpose={}".format(cid, purpose)
    print("setPurpose: {}".format(u))
    ret = slack.api_call(u)
    print("ret: {}".format(ret))
