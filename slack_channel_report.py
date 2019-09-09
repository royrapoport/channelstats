#! /usr/bin/env python

import copy
import json
import random
import time
import sys

import slack

import random_name
import channel
import channel_members_log
import user
import utils
import enricher
import slack_token
import slack_formatter


class SlackChannelReport(object):

    def __init__(self, fake=False):
        self.sf = slack_formatter.SlackFormatter()
        random.seed(time.time())
        self.fake = fake
        self.fake_channel = channel.Channel(fake=True)
        self.channel = channel.Channel(fake=fake)
        self.rn = random_name.RandomName()
        self.user = user.User(fake=fake)
        self.client = slack.WebClient(token=slack_token.token)
        self.enricher = enricher.Enricher(fake=fake)
        self.cml = channel_members_log.ChannelMembersLog()

    def membercount(self, cid, start, end):
        sc = self.cml.earliest_count(cid, start)
        ec = self.cml.latest_count(cid, end)
        text = self.sf.simple_comparison(sc, ec)
        diff = sc - ec
        text = "{} ended this period with {} members, a change of {} members".format(self.sf.show_cid(cid), text, diff)
        return self.sf.text_block(text)

    def messages(self, cid, ur, pur):
        text = ""
        m = "*{}* messages and *{}* words were posted to the channel"
        m = m.format(self.sf.comparison(ur, pur, ['channels', cid, 0]), self.sf.comparison(ur, pur, ['channels', cid, 1]))
        text += m
        curchannelvol = ur['channels'][cid][1]
        curtotal = ur['statistics']["words"]
        prevchannelvol = pur['channels'][cid][1]
        prevtotal = pur['statistics']["words"]
        curper = float("{:.1f}".format(curchannelvol * 100.0 / curtotal))
        prevper = float("{:.1f}".format(prevchannelvol * 100.0 / prevtotal))
        m = "In all, this channel represented *{}* of total traffic"
        m = m.format(self.sf.simple_comparison(curper, prevper, True, True, True))
        text += "\n" + m
        b = self.sf.text_block(text)
        return b

    def users(self, cid, ur, pur):
        blocks = []
        cur_users = ur['channel_user'].get(cid)
        prev_users = pur['channel_user'].get(cid)
        total = sum([x[1] for x in cur_users.values()])
        cur_user_names = list(cur_users.keys())
        cur_user_names.sort(key = lambda x: cur_users[x][1])
        cur_user_names.reverse()
        fields = ["*User*", "*Activity"]
        ctr = 1
        for user in cur_user_names:
            fields.append("{} {}".format(ctr, self.sf.show_uid(user)))
            m = "*{}* m".format(self.sf.comparison(ur, pur, ['channel_user', cid, user, 0]))
            m += " *{}* w".format(self.sf.comparison(ur, pur, ['channel_user', cid, user, 1]))
            fields.append(m)
            ctr += 1
        for fset in self.sf.make_fields(fields):
            block = {'type': 'section', 'fields': fset}
            blocks.append(block)
        return blocks



    def make_header(self, ur, pur, cid):
        blocks = []
        header = "Channel Activity Report for *{}* Between {} and {}"
        header = header.format(self.sf.show_cid(cid), ur['start_date'], ur['end_date'])
        blocks.append(self.sf.text_block(header))
        blocks.append(self.sf.divider())
        blocks.append(self.membercount(cid, ur['start_date'], ur['end_date']))
        blocks.append(self.messages(cid, ur, pur))
        blocks.append(self.sf.divider())
        blocks += self.users(cid, ur, pur)
        #m = m.format(self.sf.comparison(us, pus, ['count', 1]), self.sf.comparison(us, pus, ['count', 0]))
        #m += "\n"
        #m += "That made you the *{}*-ranked poster on the Slack and meant you contributed "
        #m += "*{:.1f}%*{} of this Slack's total public volume"
        #m = m.format(utils.rank(us['rank']), us['percent_of_words'], self.sf.comparison(us, pus, ['percent_of_words'], False))
        #tm = us.get("thread_messages")
        #if tm:
            #t = "In total, {} messages were posted as threaded responses to your messages.\n"
            #t = t.format(self.sf.comparison(us, pus, ['thread_messages']))
            #m += t
        #blocks.append(self.sf.text_block(m))
        return blocks

    def make_report(self, ur, pur, cid):
        blocks = []
        blocks += self.make_header(ur, pur, cid)
        blocks.append(self.sf.divider())
        blocks.append(self.sf.text_block(
                "People sent {} reactions to the channel".format(
                    self.sf.comparison(ur, pur, ['enriched_channel', cid, 'reaction_count']))))
        blocks += self.popular_reactions(ur, cid)
        blocks += self.reacted_messages(ur, cid)
        blocks += self.replied_messages(ur, cid)
        #blocks += self.make_channels(ur, pur)
        #blocks.append(self.sf.divider())
        #blocks += self.posting_hours(ur, pur, uid)
        #blocks += self.posting_days(ur, pur, uid)
        #blocks += self.popular_reactions(ur, uid)
        #blocks += self.topten(ur, pur, uid, 'reactions_from', "The people who most responded to you are")
        #blocks += self.topten(ur, pur, uid, 'reacted_to', "The people you most responded to are")
        #blocks += self.topten(ur, pur, uid, 'reactions_combined', "Reaction Affinity")
        #blocks += self.topten(ur, pur, uid, 'author_thread_responded', "Authors whose threads you responded to the most")
        #blocks += self.topten(ur, pur, uid, 'thread_responders', "Most frequent responders to your threads")
        #blocks += self.topten(ur, pur, uid, 'threads_combined', "Thread Affinity")
        #blocks += self.topten(ur, pur, uid, 'you_mentioned', "The people you mentioned the most")
        #blocks += self.topten(ur, pur, uid, 'mentioned_you', "The people who mentioned you the most")
        #blocks += self.topten(ur, pur, uid, 'mentions_combined', "Mention Affinity")
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

    def reacted_messages(self, ur, cid):
        return self.sf.messager(
            ur['enriched_channel'][cid]['most_reacted'],
            'reactions',
            show_user=True,
            show_channel=False)

    def replied_messages(self, ur, cid):
        return self.sf.messager(
            ur['enriched_channel'][cid]['most_replied'],
            'replies',
            show_user=True,
            show_channel=False)

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

    def popular_reactions(self, ur, cid):
        popularity = ur['enriched_channel'][cid]['reactions']
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
            if self.fake:
                cname = self.sf.get_fake_channel(channel_name)
            f1 = "{} *{}*".format(ctr, cname)
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


    def send_report(self, cid, ur, previous, send=True, override_uid=None):
        enricher.Enricher(fake=self.fake).enrich(ur)
        enricher.Enricher(fake=self.fake).enrich(previous)
        blocks = self.make_report(ur, previous, cid)
        if not send:
            print("Saving report to slack.json")
            f = open("slack.json", "w")
            f.write(json.dumps(blocks, indent=4))
            f.close()
            return
        # If set to true, this message will be sent as the user who owns the token we use
        as_user = False
        if override_uid:
            cid=override_uid
        for blockset in utils.chunks(blocks, 49):
            if send:
                print("Sending report to {}".format(cid))
                try:
                    response = self.client.chat_postMessage(
                        channel=cid,
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
