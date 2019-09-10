#! /usr/bin/env python

import re
import sys

import utils
import random_channel
import channel
import slack_token

import user_downloader

rc = random_channel.RandomChannel()

realc = channel.Channel()
fakec = channel.Channel(fake=True)

rtable = realc.table
ftable = fakec.table
items = []
for item in realc.ddb.items(rtable):
    item['friendly_name'] = rc.name()
    items.append(item)

with ftable.batch_writer() as batch:
    for item in items:
        batch.put_item(item)
