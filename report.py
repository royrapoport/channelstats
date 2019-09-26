#! /usr/bin/env python

import channel
import decimal

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
    never be larger than LIMIT provided.  It will keep the
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
        self.items.sort(key=lambda x: self.method(x))
        self.items.reverse()
        self.items = self.items[0:self.limit]
        self.min = self.method(self.items[-1])

    def dump(self):
        return self.items


class Report(object):

    # Where we keep the 'top X' of messages, what X should we go for?
    top_limit = 10

    def __init__(self):
        self._data = {}
        self._data['enriched_channel'] = {}
        self.user = user.User()
        self.reactions_accumulator = Accumulator(
            self.top_limit, lambda x: x[0])
        self.reply_accumulator = Accumulator(self.top_limit, lambda x: x[0])
        self.channel_reply_accumulators = {}
        self.channel_reaction_accumulators = {}
        self.user_reply_accumulators = {}
        self.user_reaction_accumulators = {}
        self.reactions = {}
        self.reactions_from = {}  # People who react to the people we're tracking
        self.configuration = configuration.Configuration()
        self.accum_methods = [x for x in dir(self) if x.find("accum_") == 0]
        self.track = {}
        self.channel = channel.Channel()
        self.hydrated_channels = {}

    def set_channels(self, channels):
        if channels:
            self.channel_reply_accumulators = {}
            self.channel_reaction_accumulators = {}
            for channel in channels:
                # print("Will keep track of channel {}".format(channel))
                self.create_key(["enriched_channel", channel, 'most_replied'], {})
                self.create_key(["enriched_channel", channel, 'most_reacted'], {})
                self.channel_reply_accumulators[channel] = Accumulator(
                    self.top_limit, lambda x: x[0])
                self.channel_reaction_accumulators[channel] = Accumulator(
                    self.top_limit, lambda x: x[0])

    def set_users(self, users):
        dummyenriched = {}
        for label in "reactions_from reacted_to you_mentioned thread_responders author_thread_responded mentioned_you mentions_combined".split():
            dummyenriched[label] = {}
        for label in "reactions replies".split():
            dummyenriched[label] = []
        dummyenriched['reaction_count'] = 0
        for label in "reaction_popularity reactions_combined threads_combined".split():
            dummyenriched[label] = {}

        dummy_user = {
            "thread_messages": 0,
            "reactions": 0,
            "count": [
                0,
                0
            ],
            "replies": 0,
            "percent_of_messages": 0,
            "cum_percent_of_messages": 100,
            "rank": 999999,
            "percent_of_words": 0,
            "cum_percent_of_words": 0
        }

        self.create_key(["enriched_user"], {})
        if not users:
            return
        for user in users:
            self.user_reply_accumulators[user] = Accumulator(
                self.top_limit, lambda x: x[0])
            self.user_reaction_accumulators[user] = Accumulator(
                self.top_limit, lambda x: x[0])
            self.reactions[user] = {}
            self.track[user] = 1
            self.create_key(["enriched_user", user], copy.deepcopy(dummyenriched))
            self.create_key(["users", user], [0,0])
            self.create_key(["user_stats", user], copy.deepcopy(dummy_user))
            self.create_key(["user_stats", user, "posting_hours"], {})

    def data(self):
        return utils.dump(self._data)

    def set_start_date(self, start_date):
        self._data['start_date'] = start_date

    def set_end_date(self, end_date):
        self._data['end_date'] = end_date

    def message(self, message):
        cid = message.get('slack_cid')
        if cid not in self.hydrated_channels:
            self.hydrated_channels[cid] = self.channel.get(cid)

        if 'subtype' in message:
            return

        self.accum_channel(message)
        self.accum_channel_user(message)
        self.accum_mentions(message)
        self.accum_reaction_count(message)
        self.accum_reactions(message)
        self.accum_reply_count(message)
        self.accum_threads(message)
        self.accum_timestats(message)
        self.accum_user(message)

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
                    cur[k] = collections.defaultdict(int)
                else:
                    cur[k] = default_value
                    return cur[k]
            cur = cur[k]
        return cur

    def increment(self, keys, message):
        """
        given a set of keys,
        e.g. ['foo', 'bar']
        will find self._data['foo']['bar'] which is presumed to be a
        [message_count, word_count] list and
        and increment its message_count by one, word_count by wordcount
        in message
        """
        self.create_key(keys, [0, 0])
        cur = self._data
        while keys:
            k = keys.pop(0)
            cur = cur[k]
        cur[0] += 1
        cur[1] += message.get("word_count", 1)

    def accum_timestats(self, message):
        uid = message['user_id']
        cid = message['slack_cid']
        ts = int(float(message['ts']))
        # First, get stats unadjusted and by UTC
        localtime = time.gmtime(ts)
        hour = localtime.tm_hour
        wday = localtime.tm_wday
        self.increment(["weekday", wday], message)
        self.increment(["hour", hour], message)
        # Now, adjust stats to the authors' timezone
        user = self.user.get(uid)
        if not user:  # Weird.  We couldn't find this user.  Oh well.
            print("Couldn't find user {}".format(message['user_id']))
            return
        if 'tz_offset' not in user or 'tz' not in user:
            return
        tz_offset = user['tz_offset']
        tz = user.get("tz", "Unknown")
        self.increment(["timezone", tz], message)
        ts += tz_offset
        localtime = time.gmtime(ts)
        hour = localtime.tm_hour
        wday = localtime.tm_wday
        self.increment(["user_weekday", wday], message)
        if uid in self.track:
            self.increment(["user_stats", uid, "posting_days", wday], message)
        if cid in self._data['enriched_channel']:
            self.increment(["enriched_channel", cid, "posting_days", wday], message)
        if wday < 5:  # We only look at weekday activity
            self.increment(["user_weekday_hour", hour], message)
            self.increment(["user_weekday_hour_per_user", uid, hour], message)
            if uid in self.track:
                self.increment(["user_stats", uid, "posting_hours", hour], message)
            if cid in self._data['enriched_channel']:
                self.increment(["enriched_channel", cid, "posting_hours", hour], message)


    def finalize(self):
        self._finalize_channels()
        self._finalize_mentions()
        self._finalize_period_activity()
        self._finalize_reaction()
        self._finalize_reaction_popularity()
        self._finalize_reactions()
        self._finalize_reply_popularity()
        self._finalize_stats()
        self._finalize_threads()
        self._finalize_timezones()
        self._finalize_user_stats()

    @staticmethod
    def make_url(mrecord):
        mid = mrecord[1]
        cid = mrecord[2]
        return "https://{}.slack.com/archives/{}/p{}".format(config.slack_name, cid, mid)

    def _finalize_reactions(self):
        for uid in self.reactions:
            enriched = self.create_key(['enriched_user', uid], {})
            reactions = utils.make_ordered_dict(self.reactions[uid])
            count = sum(reactions.values())
            enriched['reaction_popularity'] = reactions
            enriched['reaction_count'] = count
            Report.order_and_combine(
                enriched, 'reacted_to', 'reactions_from', 'reactions_combined')

    @staticmethod
    def order_and_combine(d, k1, k2, label):
        """
        Given k1 and k2, which are keys into d and point into their own {k:v}
        dictionaries,
        first, convert their dictionaries to OrderedDicts going from highest v to lowest
        Then create a combined dictionary of all keys in k1 and k2, with values being
        sum of values
        so
        k1: {1: 2, 2: 3} and k2: {2: 5, 5: 6}
        would be combined into {1:2, 2:8, 5:6}
        combined dictionary is saved under key LABEL in d
        """
        for k in [k1, k2]:
            if k in d:
                d[k] = utils.make_ordered_dict(d[k])
        combined = {}
        for key in list(d.get(k1, {}).keys()) + list(d.get(k2, {}).keys()):
            combined[key] = d.get(k1, {}).get(key, 0) + \
                d.get(k2, {}).get(key, 0)
        d[label] = utils.make_ordered_dict(combined)

    def _finalize_mentions(self):
        for uid in self.track:
            enriched = self._data['enriched_user'][uid]
            Report.order_and_combine(
                enriched,
                'you_mentioned',
                'mentioned_you',
                'mentions_combined')

    def _finalize_threads(self):
        for uid in self.track:
            enriched = self._data['enriched_user'][uid]
            Report.order_and_combine(
                enriched,
                'author_thread_responded',
                'thread_responders',
                'threads_combined')

    def _finalize_reply_popularity(self):
        self._data['reply_count'] = self.reply_accumulator.dump()
        for uid in self.user_reply_accumulators:
            self._data['enriched_user'][uid]['replies'] = self.user_reply_accumulators[uid].dump()
        for cid in self.channel_reply_accumulators:
            self._data['enriched_channel'][cid]['most_replied'] = self.channel_reply_accumulators[cid].dump()

    def _finalize_reaction_popularity(self):
        self._data['reaction_count'] = self.reactions_accumulator.dump()
        for uid in self.user_reaction_accumulators:
            self._data['enriched_user'][uid]['reactions'] = self.user_reaction_accumulators[uid].dump()
        for cid in self.channel_reaction_accumulators:
            self._data['enriched_channel'][cid]['most_reacted'] = self.channel_reaction_accumulators[cid].dump()

    def _finalize_period_activity(self):
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
                total += hourdict[hour][0]
            percdict = {}
            for hour in range(0, 24):
                if hour not in hourdict:
                    percdict[hour] = 0.0
                    continue
                messagecount = hourdict[hour][0]
                perc = messagecount * 100.0 / total
                percdict[hour] = perc
            up[user] = percdict

        # Now, convert the per-user stats to per-hour stats
        hour_stats = {}
        period_stats = {}
        for hour in range(0, 24):
            stats = [up[x][hour] for x in up.keys()]
            total = sum(stats)
            avg = total / (len(stats) * 1.0)
            hour_stats[hour] = avg
            period = int(hour / 8)
            if period not in period_stats:
                period_stats[period] = 0
            period_stats[period] += avg

        # This element is huge and we don't need it anymore
        del(self._data['user_weekday_hour_per_user'])
        self._data['weekday_activity_percentage'] = hour_stats
        self._data['weekday_actity_percentage_periods'] = period_stats

    def accum_reactions(self, message):
        """
        keep track of most popular reacjis
        """
        uid = message['user_id']
        cid = message['slack_cid']
        reactions = message.get("reactions")
        if not reactions:
            return

        # reactions are of the form reaction_name:uid:uid...,reaction_name...
        reaction_list = reactions.split(",")
        for reaction in reaction_list:
            elements = reaction.split(";")
            reaction_name = elements.pop(0)
            reactors = elements
            if cid in self._data.get("enriched_channel", {}):
                self.create_key(['enriched_channel', cid, 'reaction_count'], 0)
                self._data['enriched_channel'][cid]['reaction_count'] += len(reactors)
                self.create_key(['enriched_channel', cid, 'reactions', reaction_name], 0)
                self._data['enriched_channel'][cid]['reactions'][reaction_name] += len(reactors)
            if uid in self.track:
                # The UID of the person who wrote the message is someone
                # we're tracking
                for reactor in reactors:
                    self.create_key(
                        ['enriched_user', uid, 'reactions_from', reactor], 0)
                    self._data['enriched_user'][uid]['reactions_from'][reactor] += 1
            for reactor in reactors:
                if reactor in self.track:
                    self.create_key(
                        ['enriched_user', reactor, 'reacted_to', uid], 0)
                    self._data['enriched_user'][reactor]['reacted_to'][uid] += 1
            count = len(elements)
            if uid in self.track:
                if uid not in self.reactions:
                    self.reactions[uid] = {}
                if reaction_name not in self.reactions[uid]:
                    self.reactions[uid][reaction_name] = 0
                self.reactions[uid][reaction_name] += count
            self.create_key(["reaction", reaction_name], 0)
            self._data['reaction'][reaction_name] += count

    def _finalize_user_stats(self):
        """
        make sure all user_stats structures have all the fields we expect
        """
        Report.fill_in_values(self._data['user_stats'])
        Report.fill_in_values(self._data['enriched_user'])

    @staticmethod
    def fill_in_values(d):
        """
        presuming that d is {k: somedict} iterate through
        all k and find the complete set of keys that might be
        available in somedict, then iterate again, and fill them in
        if missing
        """
        # What fields do we expect?
        expect = {}
        for user in d:
            for k in d[user]:
                if k in expect:
                    continue
                v = d[user][k]
                if type(v) in [int, float, decimal.Decimal]:
                    expect[k] = 0
                elif type(v) in [dict, collections.OrderedDict, collections.defaultdict]:
                    expect[k] = {}
                elif type(v) == list and len(v) == 2:
                    expect[k] = [0,0]
                elif type(v) == list:
                    expect[k] = []
                else:
                    print("I don't know what to do with type {}".format(type(v)))
        for user in d:
            udict = d[user]
            for ek in expect.keys():
                if ek not in udict:
                    udict[ek] = expect[ek]

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

        mid = message['ts']
        cid = message['slack_cid']
        mrecord = (reaction_count, mid, cid, uid)
        self.reactions_accumulator.append(mrecord)
        if uid in self.user_reaction_accumulators:
            self.user_reaction_accumulators[uid].append(mrecord)
        if cid in self.channel_reaction_accumulators:
            self.channel_reaction_accumulators[cid].append(mrecord)

    def accum_mentions(self, message):
        uid = message['user_id']
        mentions = message.get("mentions")
        if not mentions:
            return
        mentions = mentions.split(",")
        # Due to a bug, about 800 messages have a mention that is the
        # message's UID.  We'll fix that later, but for now, filter this out
        mentions = [x for x in mentions if x != uid]

        if uid in self.track:
            for mention in mentions:
                if mention == uid:
                    continue
                self.create_key(
                    ["enriched_user", uid, "you_mentioned", mention], 0)
                self._data['enriched_user'][uid]['you_mentioned'][mention] += 1

        for mention in mentions:
            if mention == uid:
                continue
            if mention in self.track:
                self.create_key(
                    ["enriched_user", mention, "mentioned_you", uid], 0)
                self._data['enriched_user'][mention]['mentioned_you'][uid] += 1

    def accum_threads(self, message):
        ta = message.get("parent_user_id")
        uid = message['user_id']
        if not ta:
            return
        if ta == message['user_id']:
            return
        self.create_key(["user_stats", ta, "thread_messages"], 0)
        self._data['user_stats'][ta]['thread_messages'] += 1

        if uid in self.track:
            self.create_key(
                ["enriched_user", uid, "author_thread_responded", ta], 0)
            self._data['enriched_user'][uid]['author_thread_responded'][ta] += 1

        if ta in self.track:
            self.create_key(["enriched_user", ta, "thread_responders", uid], 0)
            self._data['enriched_user'][ta]['thread_responders'][uid] += 1

    def accum_reply_count(self, message):
        """
        keep track of the longest  threads
        """
        uid = message['user_id']
        mid = message['ts']
        cid = message['slack_cid']
        reply_count = message.get('reply_count', 0)
        if reply_count == 0:
            return

        self.create_key(["user_stats", uid, "replies"], 0)
        self._data["user_stats"][uid]["replies"] += reply_count

        mrecord = (reply_count, mid, cid, uid)
        self.reply_accumulator.append(mrecord)
        if uid in self.user_reaction_accumulators:
            self.user_reply_accumulators[uid].append(mrecord)
        if cid in self.channel_reply_accumulators:
            self.channel_reply_accumulators[cid].append(mrecord)

    def accum_channel(self, message):
        self.increment(["channels", message['slack_cid']], message)

    @staticmethod
    def order_dict(d):
        """
        Given a dict whose values are either (messages, words) or just an int
        turn it into an ordered dict ordered from key with most to least.
        If given something other than a dict, this returns an empty dict
        """
        if type(d) != dict:
            return {}
        dk = list(d.keys())
        first_elem = d[dk[0]]
        if type(first_elem) in [tuple, list]:
            dk.sort(key=lambda k: d[k][1])
        else:
            dk.sort(key=lambda k: d[k])
        dk.reverse()
        nk = collections.OrderedDict()
        for k in dk:
            nk[k] = d[k]
        return nk

    def _finalize_timezones(self):
        """
        Make the timezone dictionary ordered by words
        """
        self._data['timezone'] = Report.order_dict(self._data['timezone'])

    def _finalize_reaction(self):
        self._data['reaction'] = Report.order_dict(self._data['reaction'])
        for cid in self._data.get("enriched_channel", {}):
            if "reactions" in self._data['enriched_channel'][cid]:
                reactions = self._data['enriched_channel'][cid]['reactions']
                self._data['enriched_channel'][cid]['reactions'] = Report.order_dict(reactions)
            else:
                self._data['enriched_channel'][cid]['reactions'] = {}


    def _finalize_channels(self):
        """
        Make the channels dictionary ordered by words
        """
        self._data['channels'] = Report.order_dict(self._data['channels'])
        cs = {}
        count = 0
        total_words = sum([x[1] for x in self._data['channels'].values()])
        for cname in self._data['channels'].keys():
            words = self._data['channels'][cname][1]
            percent = int(words) * 100.0 / int(total_words)
            count += words
            cpercent = int(count) * 100.0 / int(total_words)
            cs[cname] = {'percent': percent, 'cpercent': cpercent}
        self._data['channel_stats'] = cs

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
            user_names.sort(key=lambda x: users[x][elems[elem]])
            user_names.reverse()
            running_total = 0
            rank = 1
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
                self._data['user_stats'][user_name]["percent_of_{}".format(
                    elem)] = percentage
                self._data['user_stats'][user_name]["cum_percent_of_{}".format(
                    elem)] = running_percentage
                self._data['user_stats'][user_name]['rank'] = rank
                rank += 1
            midpoint_user = user_names[int(total_users / 2)]
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
