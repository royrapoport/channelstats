#! /usr/bin/env python

import copy
import json
import time

import user
import utils

class Report(object):
    def __init__(self):
        self._data = {}
        self.user = user.User()

    def message(self, message):
        accum_methods = [x for x in dir(self) if x.find("accum_") == 0]
        for accum_method in accum_methods:
            method = "self.{}(message)".format(accum_method)
            eval(method)

    def create_key(self, keys, default_value):
        cur = self._data
        nk = copy.copy(keys)
        while nk:
            k = nk.pop(0)
            if k not in cur:
                if nk:
                    cur[k] = {}
                else:
                    cur[k] = default_value
                    return
            cur = cur[k]


    def increment(self, keys, message):
        self.create_key(keys, [0,0])
        cur = self._data
        while keys:
            k = keys.pop(0)
            cur = cur[k]
        cur[0] += 1
        cur[1] += message["wordcount"]

    def accum_timestats(self, message):
        timestamp = int(float(message['timestamp']))

        # First, get stats unadjusted and by UTC
        localtime = time.gmtime(timestamp)
        hour = localtime.tm_hour
        wday = localtime.tm_wday
        self.increment(["weekday", wday], message)
        self.increment(["hour", hour], message)

        # Now, adjust stats to the authors' timezone
        user = self.user.get(message['user_id'])
        if not user: # Weird.  We couldn't find this user.  Oh well.
            print("Couldn't find user {}".format(message['user_id']))
            return
        tz_offset = user['tz_offset']
        tz = user.get("tz", "Unknown")
        self.increment(["timezone", tz], message)
        timestamp += tz_offset
        localtime = time.gmtime(timestamp)
        hour = localtime.tm_hour
        wday = localtime.tm_wday
        self.increment(["user_weekday", wday], message)
        self.increment(["user_hour", hour], message)


    def accum_channel(self, message):
        self.increment(["channels", message['slack_cid']], message)

    def accum_user(self, message):
        self.increment(["users", message['user_id']], message)

    def accum_channel_user(self, message):
        cid = message['slack_cid']
        uid = message['user_id']
        self.increment(["channel_user", cid, uid], message)

    def dump(self):
        print(utils.jdump(self._data))
