#! /usr/bin/env python

import copy
import json
import random
import time
import sys

import slack

import random_name
import channel
import user
import utils
import enricher
import slack_token
import slack_formatter


class SlackUserReport(object):

    def __init__(self, fake=False):
        self.sf = slack_formatter.SlackFormatter(fake=fake)
        random.seed(time.time())
        self.fake = fake
        self.fake_channel = channel.Channel(fake=True)
        self.channel = channel.Channel()
        self.rn = random_name.RandomName()
        self.user = user.User(fake=fake)
        self.client = slack.WebClient(token=slack_token.token)
        self.enricher = enricher.Enricher(fake=fake)

    def make_header(self, ur, us, pur, pus):
        blocks = []
        header = "Public User Activity Report for *{}* Between {} and {}"
        header = header.format(ur['user'], ur['start_date'], ur['end_date'])
        blocks.append(self.sf.text_block(header))
        blocks.append(self.sf.divider())
        m = "You posted *{}* words in *{}* public messages."
        m = m.format(self.sf.comparison(us, pus, ['count', 1]), self.sf.comparison(us, pus, ['count', 0]))
        m += "\n"
        m += "That made you the *{}*-ranked poster on the Slack and meant you contributed "
        m += "*{:.1f}%*{} of this Slack's total public volume"
        m = m.format(utils.rank(us['rank']), us['percent_of_words'], self.sf.comparison(us, pus, ['percent_of_words'], False))
        tm = us.get("thread_messages")
        if tm:
            t = ".  In total, {} messages were posted as threaded responses to your messages.\n"
            t = t.format(self.sf.comparison(us, pus, ['thread_messages']))
            m += t
        blocks.append(self.sf.text_block(m))
        return blocks

    def make_report(self, ur, us, pur, pus, uid):
        blocks = []
        blocks += self.make_header(ur, us, pur, pus)
        blocks.append(self.sf.divider())
        blocks += self.make_channels(ur, pur)
        blocks.append(self.sf.divider())
        blocks += self.posting_hours(ur, pur, uid)
        blocks += self.posting_days(ur, pur, uid)
        blocks += self.reacted_messages(ur, uid)
        blocks += self.replied_messages(ur, uid)
        blocks.append(self.sf.text_block("You got {} reactions".format(ur['enriched_user'][uid]['reaction_count'])))
        blocks += self.popular_reactions(ur, uid)
        blocks += self.topten(ur, pur, uid, 'reactions_from', "The people who most reacted to you are")
        blocks += self.topten(ur, pur, uid, 'reacted_to', "The people you most reacted to are")
        blocks += self.topten(ur, pur, uid, 'reactions_combined', "Reaction Affinity")
        blocks += self.topten(ur, pur, uid, 'author_thread_responded', "Authors whose threads you responded to the most")
        blocks += self.topten(ur, pur, uid, 'thread_responders', "Most frequent responders to your threads")
        blocks += self.topten(ur, pur, uid, 'threads_combined', "Thread Affinity")
        blocks += self.topten(ur, pur, uid, 'you_mentioned', "The people you mentioned the most")
        blocks += self.topten(ur, pur, uid, 'mentioned_you', "The people who mentioned you the most")
        blocks += self.topten(ur, pur, uid, 'mentions_combined', "Mention Affinity")
        return blocks

    def posting_days(self, ur, pur, uid):
        """
        Report on activity per day of the week
        """
        blocks = []
        blocks.append(self.sf.text_block("*Your posting activity by day of the week:*"))
        # We'll use messages (idx 0) rather than words (idx 1)
        idx = 0
        d = ur['user_stats'][uid]['posting_days']
        blocks += self.sf.histogram(d, self.sf.day_formatter, idx, "*Day of Week*")
        return blocks

    def posting_hours(self, ur, pur, uid):
        """
        Report on activity per hour of the workday
        """
        blocks = []
        blocks.append(self.sf.text_block("*Your weekday posting activity by (local) hour of the day:*"))
        # We'll use messages (idx 0) rather than words (idx 1)
        idx = 0
        d = ur['user_stats'][uid]['posting_hours']
        blocks += self.sf.histogram(d, self.sf.hour_formatter, idx, "*(Local) Time of Weekday*")
        return blocks

    def topten(self, ur, pur, uid, label, header):
        blocks = []
        blocks.append(self.sf.text_block("*{}*".format(header)))
        fields = ["*Person*", "*Count*"]

        d = ur['enriched_user'][uid].get(label, {})
        if not d:
            return []

        pd = pur['enriched_user'][uid].get(label, {})
        t = "*{}* times between you and *{}* unique people"
        total = sum(d.values())
        count = len(list(d.keys()))
        ptotal = sum(pd.values())
        pcount = len(list(pd.keys()))
        cur = {'total': total, 'count': count}
        prev = {'total': ptotal, 'count': pcount}
        total_comp = self.sf.comparison(cur, prev, ['total'])
        count_comp = self.sf.comparison(cur, prev, ['count'])
        t = t.format(total_comp, count_comp)
        blocks.append(self.sf.text_block(t))
        uids = list(d.keys())[0:10]
        for uid in uids:
            # fields.append(ur['user_info'][uid]['label'])
            fields.append(self.sf.show_uid(uid))
            fields.append(str(d[uid]))

        for fset in self.sf.make_fields(fields):
            block = {'type': 'section', 'fields': fset}
            blocks.append(block)
        return blocks

    def reacted_messages(self, ur, uid):
        return self.sf.messager(
            ur['reenriched_user'][uid]['reactions'],
            'reactions',
            show_user=False,
            show_channel=True)

    def replied_messages(self, ur, uid):
        return self.sf.messager(
            ur['reenriched_user'][uid]['replies'],
            'replies',
            show_user=False,
            show_channel=True)

    def popular_reactions(self, ur, uid):
        popularity = ur['enriched_user'][uid]['reaction_popularity']
        return self.sf.reactions(popularity)

    def make_channels(self, ur, pur):
        fields = []
        ctr = 1
        if not ur['enriched_channels']:
            return fields
        fields.append("*Channel*")
        fields.append("*Rank, Messages, Words*")
        for channel_name in ur['enriched_channels']:
            channel = ur['enriched_channels'][channel_name]
            cname = channel['name']
            cid = channel['slack_cid']
            f1 = "{} *{}*".format(ctr, self.sf.show_cid(cid))
            f2 = "*{}* rank, *{}* m, *{}* w"
            messages = self.sf.comparison(ur, pur, ['enriched_channels', channel_name, 'messages'])
            words = self.sf.comparison(ur, pur, ['enriched_channels', channel_name, 'words'])
            f2 = f2.format(channel['rank'], messages, words)
            fields.append(f1)
            fields.append(f2)
            ctr += 1
        blocks = []
        for fset in self.sf.make_fields(fields):
            block = {'type': 'section', 'fields': fset}
            blocks.append(block)
        return blocks

    def send_report(self, uid, ur, previous, send=True, override_uid=None):
        ur = copy.deepcopy(ur)
        previous = copy.deepcopy(previous)
        enricher.Enricher(fake=self.fake).user_enrich(ur, uid)
        enricher.Enricher(fake=self.fake).user_enrich(previous, uid)
        us = ur['user_stats'].get(uid, {})
        pus = previous['user_stats'].get(uid, {})
        blocks = self.make_report(ur, us, previous, pus, uid)
        if not send:
            print("Saving report to slack.json")
            f = open("slack.json", "w")
            f.write(json.dumps(blocks, indent=4))
            f.close()
            return
        # If set to true, this message will be sent as the user who owns the token we use
        as_user = False
        if override_uid:
            uid=override_uid
        for blockset in utils.chunks(blocks, 49):
            if send:
                print("Sending report to {}".format(uid))
                try:
                    response = self.client.chat_postMessage(
                        channel=uid,
                        blocks=blockset,
                        parse='full',
                        as_user=as_user,
                        unfurl_links=True,
                        link_names=True)
                    # print("Response: {}".format(response))
                except Exception:
                    print(Exception)
                    print(json.dumps(blockset, indent=4))
                    sys.exit(0)
