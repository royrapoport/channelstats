#! /usr/bin/env python

import re
import sys

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
    # {'channel_name': 'C471F3NLB', 'created': Decimal('1487352987'), 'is_channel': True, 'channel_key': 'office-pets'}
    if re.match("^C[A-Z0-9]+$", item['channel_name']):
        item['channel_key'] = rc.name()
    else:
        item['channel_name'] = rc.name()
    items.append(item)

with ftable.batch_writer() as batch:
    for item in items:
        batch.put_item(item)
