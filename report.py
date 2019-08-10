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
        """
        Given a list of keys, create a recursive dict with final
        key being set to default_value
        e.g.
        ['foo','bar'], 3
        will make it so
        self._data['foo']['bar'] is created and set to 3
        (But will not mess with any existing keys)
        """
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
        """
        given a set of keys,
        e.g. ['foo', 'bar']
        will find self._data['foo']['bar'] which is presumed to be a
        [message_count, word_count] list and
        and increment its message_count by one, word_count by wordcount
        in message
        """
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

    def accum_reactions(self, message):
        """
        keep track of most popular reacjis
        """
        reactions = message.get("reactions")
        if not reactions:
            return
        # print("reactions: {}".format(reactions))
        # reactions are of the form reaction_name:uid:uid...,reaction_name...
        reaction_list = reactions.split(",")
        for reaction in reaction_list:
            elements = reaction.split(":")
            reaction_name = elements.pop(0)
            count = len(elements)
            self.create_key(["reaction", reaction_name], 0)
            self._data['reaction'][reaction_name] += count

    def accum_reaction_count(self, message):
        """
        keep track of most reacji'ed messages
        """
        reaction_count = message['reaction_count']
        mid = message['timestamp']
        cid = message['slack_cid']
        uid = message['user_id']
        # No sense in keeping count of unreacted messages
        if reaction_count == 0:
            return
        self.create_key(["reaction_count", reaction_count], [])
        mrecord = (mid, cid, uid)
        self._data['reaction_count'][reaction_count].append(mid)
        self.create_key(["reactions_per_user", uid], 0)
        self._data['reactions_per_user'][uid] += reaction_count

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
