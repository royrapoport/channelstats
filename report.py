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
        uid = message['user_id']
        timestamp = int(float(message['timestamp']))
        # First, get stats unadjusted and by UTC
        localtime = time.gmtime(timestamp)
        hour = localtime.tm_hour
        wday = localtime.tm_wday
        self.increment(["weekday", wday], message)
        self.increment(["hour", hour], message)
        # Now, adjust stats to the authors' timezone
        user = self.user.get(uid)
        if not user: # Weird.  We couldn't find this user.  Oh well.
            print("Couldn't find user {}".format(message['user_id']))
            return
        if 'tz_offset' not in user or 'tz' not in user:
            print("User has no tz info: {}".format(user))
            return
        tz_offset = user['tz_offset']
        tz = user.get("tz", "Unknown")
        self.increment(["timezone", tz], message)
        timestamp += tz_offset
        localtime = time.gmtime(timestamp)
        hour = localtime.tm_hour
        wday = localtime.tm_wday
        self.increment(["user_weekday", wday], message)
        if wday < 5: # We only look at weekday activity
            self.increment(["user_weekday_hour", hour], message)
            self.increment(["user_weekday_hour_per_user", uid, hour], message)

    def finalize(self):
        # Two-step process:
        # First, we'll take the per-hour stats per user in
        # user_weekday_hour_per_user and convert them from message counts
        # to percentage of messages
        up = {}
        users = self._data['user_weekday_hour_per_user'].keys()
        for user in users:
            hourdict = self._data['user_weekday_hour_per_user'][user]
            total = 0
            for hour in hourdict.keys():
                messagecount = hourdict[hour][0]
                total += hourdict[hour][0]
            percdict = {}
            for hour in range(0,24):
                if hour not in hourdict:
                    percdict[hour] = 0.0
                    continue
                messagecount = hourdict[hour][0]
                perc = messagecount * 100.0 / total
                percdict[hour] = perc
            print("converting\n{}\nto\n{}".format(hourdict, percdict))
            up[user] = percdict

        # Now, convert the per-user stats to per-hour stats
        hour_stats = {}
        # print("Average of messages sent by users per hour of the day:")
        period_stats = {}
        for hour in range(0,24):
            stats = [up[x][hour] for x in up.keys()]
            total = sum(stats)
            avg = total / (len(stats) * 1.0)
            hour_stats[hour] = avg
            period = int(hour / 8)
            if period not in period_stats:
                period_stats[period] = 0
            period_stats[period] += avg
            # print("{:.1f}% of messages on hour {}".format(avg, hour))
        # This element is huge and we don't need it anymore
        del(self._data['user_weekday_hour_per_user'])
        self._data['weekday_activity_percentage'] = hour_stats
        self._data['weekday_actity_percentage_periods'] = period_stats
        # print("Period Stats:")
        # print("Period 1 (0000-0800): {:.1f}%".format(period_stats[0]))
        # print("Period 2 (0800-1600): {:.1f}%".format(period_stats[1]))
        # print("Period 3 (1700-0000): {:.1f}%".format(period_stats[2]))

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
