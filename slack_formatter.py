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


class SlackFormatter(object):

    def __init__(self, fake=False):
        random.seed(time.time())
        self.fake = fake
        self.fake_channel = channel.Channel(fake=True)
        self.channel = channel.Channel()
        self.rn = random_name.RandomName()
        self.user = user.User(fake=fake)
        self.client = slack.WebClient(token=slack_token.token)
        self.enricher = enricher.Enricher(fake=fake)

    def text_block(self, text, markdown=True):
        if markdown:
            t = 'mrkdwn'
        else:
            t = "plan_text"
        block = {'type': 'section', 'text': {'text': text, 'type': t}}
        return block

    def divider(self):
        return { "type": "divider" }

    def comparison(self, cur, prev, idx, print_num=True):
        """
        cur and prev are dicts with identical structures
        idx is a list of keys to delve into each dict into
        returns a difference between the items pointed to by idx
        """
        found_prev = True
        cur_item = cur
        for i in idx:
            cur_item = cur_item[i]
        prev_item = prev
        for i in idx:
            # TODO: Figure out a better answer to "what if there is
            # no number from last time? the answer should be 0, but
            # then we divide by 0 and bad things happen
            try:
                prev_item = prev_item[i]
            except:
                prev_item = cur_item
                found_prev = False
        diff = (cur_item * 100.0) / prev_item
        diff = diff - 100
        ds = ""
        emoji = False
        if not found_prev:
            emoji = ":new:"
        if print_num:
            ds = "{}".format(cur_item)
        if diff > 0.5 or diff < -0.5:
            if diff > 0:
                emoji = emoji or ":green_arrow_up:"
                ds += " (+{:.0f}%)".format(diff)
            else:
                emoji = emoji or ":red_arrow_down:"
                ds += " ({:.0f}%)".format(diff)
        else:
            emoji = emoji or ":same:"
        ds += emoji
        return ds

    def make_header(self, ur, us, pur, pus):
        blocks = []
        header = "Public User Activity Report for *{}* Between {} and {}"
        header = header.format(ur['user'], ur['start_date'], ur['end_date'])
        blocks.append(self.text_block(header))
        blocks.append(self.divider())
        m = "You posted *{}* words in *{}* public messages."
        m = m.format(self.comparison(us, pus, ['count', 1]), self.comparison(us, pus, ['count', 0]))
        m += "\n"
        m += "That made you the *{}*-ranked poster on the Slack and meant you contributed "
        m += "*{:.1f}%*{} of this Slack's total public volume"
        m = m.format(utils.rank(us['rank']), us['percent_of_words'], self.comparison(us, pus, ['percent_of_words'], False))
        tm = us.get("thread_messages")
        if tm:
            t = "In total, {} messages were posted as threaded responses to your messages.\n"
            t = t.format(self.comparison(us, pus, ['thread_messages']))
            m += t
        blocks.append(self.text_block(m))
        return blocks

    def make_report(self, ur, us, pur, pus, uid):
        blocks = []
        blocks += self.make_header(ur, us, pur, pus)
        blocks.append(self.divider())
        blocks += self.make_channels(ur, pur)
        blocks.append(self.divider())
        blocks += self.posting_hours(ur, pur, uid)
        blocks += self.reacted_messages(ur, uid)
        blocks += self.replied_messages(ur, uid)
        blocks.append(self.text_block("You got {} reactions".format(ur['enriched_user'][uid]['reaction_count'])))
        blocks += self.popular_reactions(ur, uid)
        blocks += self.topten(ur, pur, uid, 'reactions_from', "The people who most responded to you are")
        blocks += self.topten(ur, pur, uid, 'reacted_to', "The people you most responded to are")
        blocks += self.topten(ur, pur, uid, 'reactions_combined', "Reaction Affinity")
        blocks += self.topten(ur, pur, uid, 'author_thread_responded', "Authors whose threads you responded to the most")
        blocks += self.topten(ur, pur, uid, 'thread_responders', "Most frequent responders to your threads")
        blocks += self.topten(ur, pur, uid, 'threads_combined', "Thread Affinity")
        blocks += self.topten(ur, pur, uid, 'you_mentioned', "The people you mentioned the most")
        blocks += self.topten(ur, pur, uid, 'mentioned_you', "The people who mentioned you the most")
        blocks += self.topten(ur, pur, uid, 'mentions_combined', "Mention Affinity")
        return blocks

    def histogram(self, d, m, idx, header):
        """
        With d as a dict with {k:v} where v are (messages, words)
        output a histogram with percent of total activity for each k
        m is a method to call with each key of the dictionary which will
        return the formatted version of that key
        idx is 0 if you want to go by messages, 1 if words
        returns a list of blocks
        """
        if idx == 0:
            label = "m"
        elif idx == 1:
            label = "w"
        else:
            raise RuntimeError("idx has to be 0 or 1")
        total = sum([x[idx] for x in d.values()])
        new = {}
        for i in d:
            value = d[i][idx]
            percent = (value * 100.0 / total)
            new[i] = (percent, value)
        k = list(d.keys())
        k.sort(key = lambda x: int(x))
        fields = [header, "*Percent of Activity*"]
        for i in k:
            fields.append("{}".format(m(i)))
            fields.append("`{}` {:.1f}% ({} {})".format('*' * int(new[i][0]), new[i][0], new[i][1], label))
        blocks = []
        for fset in self.make_fields(fields):
            block = {'type': 'section', 'fields': fset}
            blocks.append(block)
        return blocks

    def hour_formatter(self, hr):
        hr = int(hr)
        return "{0:02d}00-{0:02d}59".format(hr, hr)

    def posting_hours(self, ur, pur, uid):
        """
        Report on activity per hour of the workday
        """
        blocks = []
        blocks.append(self.text_block("*Your weekday posting activity by (local) hour of the day:*"))
        # We'll use messages (idx 0) rather than words (idx 1)
        idx = 0
        d = ur['user_stats'][uid]['posting_hours']
        blocks += self.histogram(d, self.hour_formatter, idx, "*(Local) Time of Weekday*")
        return blocks

    def topten(self, ur, pur, uid, label, header):
        blocks = []
        blocks.append(self.text_block("*{}*".format(header)))
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
        total_comp = self.comparison(cur, prev, ['total'])
        count_comp = self.comparison(cur, prev, ['count'])
        t = t.format(total_comp, count_comp)
        blocks.append(self.text_block(t))
        uids = list(d.keys())[0:10]
        for uid in uids:
            # fields.append(ur['user_info'][uid]['label'])
            fields.append(self.show_uid(uid))
            fields.append(str(d[uid]))

        for fset in self.make_fields(fields):
            block = {'type': 'section', 'fields': fset}
            blocks.append(block)
        return blocks

    def show_uid(self, uid):
        if not self.fake:
            return "<@{}>".format(uid)
        entry = self.user.get(uid)
        if not entry:
            choice = rn.name()
        elif random.choice(range(2)) == 1:
            choice = entry['user_name']
        else:
            choice = entry['real_name']
        return "@{}".format(choice)

    def reacted_messages(self, ur, uid):
        return self.messager(ur, uid, "reactions")

    def replied_messages(self, ur, uid):
        return self.messager(ur, uid, "replies")

    def make_link_button(self, text, buttontext, url):
        block = {'type':'section', 'text': { 'type': 'mrkdwn', 'text':text} }
        block['accessory'] = { 'type':'button', 'text':{'type':'plain_text', 'text':buttontext }, 'url':url }
        return block

    def messager(self, ur, uid, label):
        blocks = []
        for message in ur['reenriched_user'][uid][label]:
            cname = message['channel']
            if self.fake:
                cname = self.get_fake_channel(cname)
            m = "*{}* {} in #{} on {}"
            m = m.format(message['count'], label, cname, message['dt'])
            block = self.make_link_button(m, 'link', message['url'])
            blocks.append(block)
        if not blocks:
            return blocks
        blocks = [self.divider()] + blocks
        blocks = [(self.text_block("*Your messages which got the most {}*".format(label)))] + blocks
        return blocks

    def popular_reactions(self, ur, uid):
        popularity = ur['enriched_user'][uid]['reaction_popularity']
        fields = []
        if not popularity:
            return fields
        fields.append("*Reactji*")
        fields.append("*Count*")
        for rname in list(popularity.keys())[0:10]:
            num = popularity[rname]
            fields.append(":{}:".format(rname))
            fields.append(str(num))
        blocks = []
        for fset in self.make_fields(fields):
            block = {'type': 'section', 'fields': fset}
            blocks.append(block)
        return blocks

    def get_fake_channel(self, cname):
        """
        given a friendly channel name, return a fake one
        """
        c = self.channel.get(cname)
        cid = c['channel_name']
        c = self.fake_channel.get(cid)
        cname = c['channel_name']
        return cname

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
                cname = self.get_fake_channel(channel_name)
            f1 = "{} *{}*".format(ctr, cname)
            f2 = "*{}* rank, *{}* m, *{}* w"
            messages = self.comparison(ur, pur, ['enriched_channels', channel_name, 'messages'])
            words = self.comparison(ur, pur, ['enriched_channels', channel_name, 'words'])
            f2 = f2.format(channel['rank'], messages, words)
            fields.append(f1)
            fields.append(f2)
            ctr += 1
        blocks = []
        for fset in self.make_fields(fields):
            block = {'type': 'section', 'fields': fset}
            blocks.append(block)
        return blocks

    def make_fields(self, ftext):
        """
        given a list of field texts, convert to a list of lists of fields,
        where each list of fields is no more than 10 fields, and each field
        is {'type': 'mrkdwn', 'text': text}
        """
        fields = [{'type': 'mrkdwn', 'text': x} for x in ftext]
        return utils.chunks(fields, 10)

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
