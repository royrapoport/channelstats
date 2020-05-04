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
        self.channel = channel.Channel()
        self.fake_channel = channel.Channel(fake=True)
        if self.fake:
            self.channel = self.fake_channel
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

    def simple_comparison(self, cur_item, prev_item, found_prev=True, print_num=True, is_percent=False):
        if prev_item == 0:
            if cur_item == 0:
                return "0"
            else:
                if is_percent:
                    return "{}% :infinity:".format(cur_item)
                else:
                    return "{} :infinity:".format(cur_item)
        diff = (cur_item * 100.0) / prev_item
        diff = diff - 100
        ds = ""
        emoji = False
        if not found_prev:
            emoji = ":new:"
        if print_num:
            if is_percent:
                ds = "{}%".format(cur_item)
            else:
                ds = "{}".format(cur_item)
        if diff > 0.5 or diff < -0.5:
            if diff > 0:
                emoji = emoji or ":green_arrow_up:"
                ds += " (+{:.0f}%)".format(diff)
            else:
                emoji = emoji or ":red_arrow_down:"
                ds += " ({:.0f}%)".format(diff)
        else:
            emoji = emoji or ""
        ds += emoji
        return ds

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
        return self.simple_comparison(cur_item, prev_item, found_prev, print_num)

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
            label = "msgs"
        elif idx == 1:
            label = "words"
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
            histo = "`{}` ".format('*' * int(new[i][0])) if int(new[i][0]) > 0 else ''
            fields.append("{}{:.1f}% ({} {})".format(histo, new[i][0], new[i][1], label))
        blocks = []
        for fset in self.make_fields(fields):
            block = {'type': 'section', 'fields': fset}
            blocks.append(block)
        return blocks

    def hour_formatter(self, hr):
        hr = int(hr)
        return "{0:02d}00-{0:02d}59".format(hr, hr)

    def day_formatter(self, day):
        days = "Monday Tuesday Wednesday Thursday Friday Saturday Sunday".split()
        return days[int(day)]

    def show_cid(self, cid):
        entry = self.channel.get(cid)
        friendly_name = ""
        if entry:
            friendly_name = entry['friendly_name']
        if not self.fake:
            if friendly_name:
                return "<#{}|{}>".format(cid, friendly_name)
            else:
                return "<#{}>".format(cid)
        if not friendly_name:
            choice = self.rn.name()
        return "#{}".format(choice)

    def show_uid(self, uid):
        if not self.fake:
            return "<@{}>".format(uid)
        entry = self.user.get(uid)
        if not entry:
            choice = self.rn.name()
        elif random.choice(range(2)) == 1:
            choice = entry['user_name']
        else:
            choice = entry['real_name']
        return "@{}".format(choice)

    def make_link_button(self, text, buttontext, url):
        block = {'type':'section', 'text': { 'type': 'mrkdwn', 'text':text} }
        block['accessory'] = { 'type':'button', 'text':{'type':'plain_text', 'text':buttontext }, 'url':url }
        return block

    def get_fake_channel(self, cname):
        """
        given a friendly channel name, return a fake one
        """
        c = self.channel.get(cname)
        cid = c['friendly_name']
        c = self.fake_channel.get(cid)
        cname = c['friendly_name']
        return cname

    def make_fields(self, ftext):
        """
        given a list of field texts, convert to a list of lists of fields,
        where each list of fields is no more than 10 fields, and each field
        is {'type': 'mrkdwn', 'text': text}
        """
        fields = [{'type': 'mrkdwn', 'text': x} for x in ftext]
        return utils.chunks(fields, 10)

    def reactions(self, popularity):
        t = "*Count* *Reactji*\n"
        for rname in list(popularity.keys())[0:10]:
            num = popularity[rname]
            t += "{} :{}:\n".format(str(num), rname)
        block = self.text_block(t)
        return [block]

    def messager(self, message_list, label, show_user=False, show_channel=False):
        blocks = []
        for message in message_list:
            m = "*{}* {}".format(message['count'], label)
            if show_channel:
                m += " in #{}".format(message['channel'])
            if show_user:
                m += " to a message from {}".format(message['user'])
            m += " on {}".format(message['dt'])
            t = "<{}|{}>".format(message['url'], m)
            block = self.make_link_button(m, 'link', message['url'])
            block = self.text_block(t)
            blocks.append(block)
        if not blocks:
            return blocks
        blocks = [self.divider()] + blocks
        blocks = [(self.text_block("*Messages which got the most {}*".format(label)))] + blocks
        return blocks

    def posting_hours(self, d):
        """
        Report on activity per hour of the workday
        """
        blocks = []
        blocks.append(self.text_block("*Weekday posting activity by (local) hour of the day:*"))
        # We'll use messages (idx 0) rather than words (idx 1)
        idx = 0
        blocks += self.histogram(d, self.hour_formatter, idx, "*(Local) Time of Weekday*")
        return blocks

    def posting_days(self, d):
        """
        Report on activity per day of the week
        """
        blocks = []
        blocks.append(self.text_block("*Posting activity by day of the week:*"))
        # We'll use messages (idx 0) rather than words (idx 1)
        idx = 0
        blocks += self.histogram(d, self.day_formatter, idx, "*Day of Week*")
        return blocks

    def pn(self, num, label):
        """
        Output string "*num* label" but if num is > 1, change 'label' to 'labels'
        Also use thousands separator
        So pn(1, "poster") outputs "*1* poster", but pn(2, "poster") outputs "*2* posters"
        """
        f = "*{:,}* {}".format(num, label)
        if num > 1:
            f += "s"
        return f
