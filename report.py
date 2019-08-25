#! /usr/bin/env python

import collections
import copy
import json
import time

import config
import configuration
import user
import utils

class Accumulator(object):
    """
    Accumulator accumulates a list of objects, which will
    never ben larger than LIMIT provided.  It will keep the
    top LIMIT objects, where the size of object is determined
    by running METHOD(object)
    """
    def __init__(self, limit, method):
        self.limit = limit
        self.method = method
        self.items = []
        self.min = 0
        self.size = 0

    def append(self, item):
        item_size = self.method(item)
        if item_size < self.min and self.size >= self.limit:
            return
        # If we're here, then this is bigger than the minimum
        # current size, and that means we'll definitely add it
        self.items.append(item)
        self.items.sort(key = lambda x: self.method(x))
        self.items.reverse()
        self.items = self.items[0:self.limit]
        self.min = self.method(self.items[-1])

class Report(object):

    # Where we keep the 'top X' of messages, what X should we go for?
    top_limit = 10

    def __init__(self):
        self._data = {}
        self.user = user.User()
        self.reactions_accumulator = Accumulator(self.top_limit, lambda x: x[0])
        self.reply_accumulator = Accumulator(self.top_limit, lambda x: x[0])
        self.configuration = configuration.Configuration()

    def data(self):
        return utils.dump(self._data)

    def set_start_date(self, start_date):
        self._data['start_date'] = start_date

    def set_end_date(self, end_date):
        self._data['end_date'] = end_date

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
        cur[1] += message.get("wordcount", 0)

    def accum_timestats(self, message):
        # print("accumulating data for {}".format(message))
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
            # print("User has no tz info: {}".format(user))
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
            # print("Incrementing user_weekday_hour because wday is {}".format(wday))
            self.increment(["user_weekday_hour", hour], message)
            self.increment(["user_weekday_hour_per_user", uid, hour], message)

    def finalize(self):
        final_methods = [x for x in dir(self) if x.find("_finalize_") == 0]
        for final_method in final_methods:
            method = "self.{}()".format(final_method)
            eval(method)

    def make_url(self, mrecord):
        mid = mrecord[1]
        cid = mrecord[2]
        return("https://{}.slack.com/archives/{}/p{}".format(config.slack_name, cid,mid))

    def _finalize_reply_popularity(self):
        self._data['reply_count'] = self.reply_accumulator.items
        return
        x = self._data['reply_count'][0]
        print("Most replied message: {}".format(x))
        print(self.make_url(x))
        x = self._data['reply_count'][-1]
        print("Least replied tracked message: {}".format(x))
        print(self.make_url(x))

    def _finalize_reaction_popularity(self):
        self._data['reaction_count'] = self.reactions_accumulator.items
        return
        x = self._data['reaction_count'][0]
        print("Most popular message: {}".format(x))
        x = self._data['reaction_count'][-1]
        print("Least popular tracked message: {}".format(x))

    def _finalize_period_activity(self):
        # Two-step process:
        # First, we'll take the per-hour stats per user in
        # user_weekday_hour_per_user and convert them from message counts
        # to percentage of messages
        up = {}
        print("data keys: {}".format(self._data.keys()))
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
            # print("converting\n{}\nto\n{}".format(hourdict, percdict))
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
        keep track of most reacji'ed messages, keep count of
        reactions per user
        """
        reaction_count = message.get('reaction_count', 0)
        uid = message['user_id']
        # No sense in keeping count of unreacted messages
        if reaction_count == 0:
            return

        self.create_key(["user_stats", uid, "reactions"], 0)
        self._data["user_stats"][uid]["reactions"] += reaction_count

        mid = message['timestamp']
        cid = message['slack_cid']
        mrecord = (reaction_count, mid, cid, uid)
        self.reactions_accumulator.append(mrecord)

    def accum_reply_count(self,  message):
        """
        keep track of the longest  threads
        """
        uid = message['user_id']
        mid = message['timestamp']
        cid = message['slack_cid']
        reply_count = message.get('reply_count', 0)
        if reply_count == 0:
            return

        self.create_key(["user_stats", uid, "replies"], 0)
        self._data["user_stats"][uid]["replies"] += reply_count

        mrecord = (reply_count, mid, cid, uid)
        self.reply_accumulator.append(mrecord)

    def accum_channel(self, message):
        self.increment(["channels", message['slack_cid']], message)

    def order_dict(self, d):
        """
        Given a dict whose values are (messages, words)
        turn it into an ordered dict ordered from key with most
        words to least
        """
        dk = list(d.keys())
        dk.sort(key = lambda k: d[k][1])
        dk.reverse()
        nk = collections.OrderedDict()
        for k in dk:
            nk[k] = d[k]
        return nk

    def _finalize_timezones(self):
        """
        Make the timezone dictionary ordered by words
        """
        self._data['timezone'] = self.order_dict(self._data['timezone'])

    def _finalize_channels(self):
        """
        Make the channels dictionary ordered by words
        """
        self._data['channels'] = self.order_dict(self._data['channels'])

    def _finalize_stats(self):
        stats = {}
        users = self._data['users']
        user_names = list(users.keys())

        total_users = len(user_names)
        stats['posters'] = total_users

        elems = {'messages': 0, 'words': 1}

        for label in ["active_users", "all_users"]:
            stats[label] = self.configuration.get_count(label)

        for elem in ['messages', 'words']:
            report_user_names = []
            include = True
            count_of = float(sum([x[elems[elem]] for x in users.values()]))
            stats[elem] = count_of
            stats["average {}".format(elem)] = count_of / total_users
            user_names.sort(key = lambda x: users[x][elems[elem]])
            user_names.reverse()
            running_total = 0
            for user_name in user_names:
                count = float(users[user_name][elems[elem]])
                percentage = count * 100.0 / count_of
                running_total += count
                running_percentage = running_total * 100.0 / count_of
                if running_percentage <= 50:
                    report_user_names.append(user_name)
                elif include:
                    report_user_names.append(user_name)
                    include = False
                self.create_key(["user_stats", user_name], {})
                self._data['user_stats'][user_name]["percent_of_{}".format(elem)] = percentage
                self._data['user_stats'][user_name]["cum_percent_of_{}".format(elem)] = running_percentage
            midpoint_user = user_names[int(total_users/2)]
            midpoint_number = users[midpoint_user][elems[elem]]
            stats['median {}'.format(elem)] = midpoint_number
            # What percent of messages/words did the top ten users account for?
            top_ten = user_names[0:10]
            count = float(sum([users[x][elems[elem]] for x in top_ten]))
            stats['topten {}'.format(elem)] = (count * 100.0) / count_of
            # How many users account for 50% of the volume?
            idx = 0
            count = 0
            while count < count_of / 2:
                count += users[user_names[idx]][elems[elem]]
                idx += 1
            stats['50percent of {}'.format(elem)] = idx
            stats['50percent users for {}'.format(elem)] = report_user_names
        self._data['statistics'] = stats

    def accum_user(self, message):
        uid = message['user_id']
        self.increment(["users", uid], message)
        self.increment(["user_stats", message['user_id'], "count"], message)

    def accum_channel_user(self, message):
        cid = message['slack_cid']
        uid = message['user_id']
        self.increment(["channel_user", cid, uid], message)

    def dump(self):
        print(utils.jdump(self._data))
