#! /usr/bin/env python

import collections
import datetime
import time

import channel
import config
import user
import utils


class Enricher(object):

    def __init__(self, fake=False):
        self.fake = fake
        self.user = user.User(fake=self.fake)
        self.channel = channel.Channel()

    def get_channels(self, list_of_cid, report_start_date):
        """
        Given a list of channel IDs and an yyyy-mm-dd str date,
        returns a dictionary indexed by cid
        where the value is another dictionary with
            'name': user-friendly channel name
            'new': True/False based on whether it was created during this period
            'members': Count of members
        """
        (y, m, d) = [int(x) for x in report_start_date.split("-")]
        dt = datetime.datetime(y, m, d, 0, 0, 0)
        report_start_ts = dt.timestamp()

        entries = self.channel.batch_get_channel(list_of_cid)
        ret = {}
        for cid in entries:
            entry = entries[cid]
            name = entry['friendly_name']
            created = int(entry['created'])
            new = created > report_start_ts
            members = entry.get("members", 0)
            ret[cid] = {'name': name, 'new': new, 'members': members}
        return ret

    @staticmethod
    def popular_messages(messages, cinfo, uinfo):
        """
        given a list of lists where each list is
        [reaction count, ts, cid, uid]
        convert to dict with 'count', 'dt', 'channel', 'cid', 'uid', 'user', 'url'
        """
        ret = []
        for message in messages:
            if not isinstance(message, list):
                continue
            (reactions, ts, cid, uid) = message
            ret.append({
                'count': reactions,
                'dt': time.strftime("%m/%d/%Y %H:%M", time.localtime(int(float(ts)))),
                'channel': cinfo[cid]['name'],
                'user': uinfo[uid]['label'],
                'uid': uid,
                'cid': cid,
                'url': utils.make_url(cid, ts)
            })
        return ret

    def enrich(self, report):
        # Get the canonical list of USER ids we might refer to.
        # That is all users who posted in all channels
        channels = report['channel_user'].keys()
        users = {}  # We need a list, but this makes deduping easier
        channel_list = []
        # Collect list of userIDs we might refer to
        for channel in channels:
            channel_list.append(channel)
            for user in report['channel_user'][channel]:
                users[user] = 1
        for uid in report['enriched_user']:
            enriched = report['enriched_user'][uid]
            for elem in ['reacted_to', 'reactions_from']:
                reactors = enriched.get(elem, {}).keys()
                for user in reactors:
                    users[user] = 1

        users = list(users.keys())
        channel_info = self.get_channels(channel_list, report['start_date'])
        user_info = self.user.get_users(users)
        report['user_info'] = user_info
        report['channel_info'] = channel_info

        reactions = report['reaction']
        reactji = list(reactions.keys())
        report['top_ten_reactions'] = reactji[0:10]

        report['reacted_messages'] = Enricher.popular_messages(
            report['reaction_count'], channel_info, user_info)
        report['reacted_messages'] = report['reacted_messages'][0:10]

        report['replied_messages'] = Enricher.popular_messages(
            report['reply_count'], channel_info, user_info)
        report['replied_messages'] = report['replied_messages'][0:10]

        for cid in report.get('enriched_channel', {}):
            for k in ['most_replied', 'most_reacted']:
                report['enriched_channel'][cid][k] = Enricher.popular_messages(
                    report['enriched_channel'][cid][k], channel_info, user_info)

    def user_enrich(self, report, uid):
        self.enrich(report)
        if uid not in report['user_info']:
            report['user_info'][uid] = self.user.get_pretty(uid)
        user = report['user_info'][uid]['label']
        report['uid'] = uid
        report['user'] = user

        channel_list = []
        for cid in report['channel_user']:
            # print("Examining cid {}".format(cid))
            channel = report['channel_user'][cid]
            if uid not in channel:
                continue
            users = list(channel.keys())
            users.sort(key=lambda x: channel[x][1])
            users.reverse()
            rank = 1
            for i in users:
                if i == uid:
                    break
                rank += 1
            cname = report['channel_info'][cid]['name']
            channel_messages = report['channels'][cid][0]
            channel_words = report['channels'][cid][1]
            messages = channel[uid][0]
            words = channel[uid][1]
            percent_words = words * 100.0 / channel_words
            percent_messages = messages * 100.0 / channel_messages
            c = {
                'slack_cid': cid,
                'name': cname,
                'rank': rank,
                'words': words,
                'messages': messages,
                'percent': percent_words
            }
            channel_list.append(c)
        channel_list.sort(key=lambda x: x['words'])
        channel_list.reverse()
        d = collections.OrderedDict()
        for channel in channel_list:
            name = channel['name']
            d[name] = channel
        report['enriched_channels'] = d

        ci = report['channel_info']
        ui = report['user_info']
        report['reenriched_user'] = {}
        for user in report['enriched_user']:
            report['reenriched_user'][user] = {}
            for t in ['reactions', 'replies']:
                messages = Enricher.popular_messages(
                    report['enriched_user'][user][t], ci, ui)
                report['reenriched_user'][user][t] = messages
