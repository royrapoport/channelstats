#! /usr/bin/env python3

import json

import message_writer

mw = message_writer.MessageWriter(local=True)

cid = "GL3A0K8HE"

messages = json.loads(open("quandary.json", "r").read())
print("I have {} messages".format(len(messages)))
mw.write(messages, cid)
