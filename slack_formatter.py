#! /usr/bin/env python

import copy
import decimal
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

    emoji_infinity = ":infinity:"
    emoji_new = ":new:"
    emoji_down = ":red_arrow_down:"
    emoji_up = ":green_arrow_up:"
    # How small of a difference will we actually show in WoW stats? Expressed as percentage
    # so 0.5 means 0.5% (or 0.005)
    diff_threshold = 0.5

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

    def adjust_values(self, cur, prev, label):
        """
        helper method for simple_comparison
        for both cur and prev, if it's a decimal.Decimal, convert to float
        for cur, if it's a whole number, convert to int
        for label, if cur is not 1, add an 's' (pluralize)
        returns new values for the three as (new_cur, new_prev, new_label)
        """
        if type(cur) == decimal.Decimal:
            cur = float(cur)
        if type(prev) == decimal.Decimal:
            prev = float(prev)
        if int(cur) == cur:
            cur = int(cur)
        if cur != 1 and label:
            label += "s"

        return(cur, prev, label)


    def format_percent(self, n):
        """
        returns string print of n using our preferred formatting
        """
        return "*{:.1f}%*".format(n)

    def format_num(self, n):
        """
        returns string print of n using our preferred formatting
        """
        if int(n) == n:
            return "*{:,}*".format(n)
        else:
            return "*{:,.1f}*".format(n)

    def simple_comparison(self, cur_item, prev_item, found_prev=True, print_num=True, is_percent=False, label=None):
        """
        Returns a string with an emoji indicating difference between
        cur_item and prev_item (which should be numbers or decimal.Decimals).
        if not found_prev, this is a new metric, and we'll use the :new: emoji
        if not print_num, we'll just show the percent difference and emoji
        if is_percent, we'll print the number as a single-decimal percentage (x.y%)
        otherwise we'll print ints with {:,} format, and floats with {:,.1f}
        format.
        if label is provided, we'll add that at the end of the string, and pluralize
        the label if we have more than one cur_item
        """

        cur_item, prev_item, label = self.adjust_values(cur_item, prev_item, label)

        if prev_item == 0:
            if cur_item == 0:
                ret = self.format_num(0)
            else:
                if is_percent:
                    ret = self.format_percent(cur_item)
                else:
                    ret = self.format_num(cur_item)
                ret += " " + self.emoji_infinity
            if label:
                ret += " " + label
            return ret
        diff = (cur_item * 100.0) / prev_item
        diff = diff - 100
        ds = ""
        emoji = None
        if not found_prev:
            emoji = self.emoji_new
        if print_num:
            if is_percent:
                ds = self.format_percent(cur_item)
            else:
                ds = self.format_num(cur_item)
        # If the difference is minor enough, we'll just ignore it
        if abs(diff) < self.diff_threshold:
            diff = 0
        if diff > 0:
            emoji = emoji or self.emoji_up
            sign = "+"
        elif diff < 0:
            emoji = emoji or self.emoji_down
            sign = ""
        if diff: # Don't print change if there's no difference
            ds += " ({}{:.0f}%)".format(sign, diff)
        else:
            emoji = emoji or ""
        ds += emoji
        if label:
            ds += " " + label
        return ds

    def comparison(self, cur, prev, idx, print_num=True, is_percent=False, label=None):
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
        return self.simple_comparison(cur_item, prev_item, found_prev, print_num, is_percent, label)

    def histogram(self, d, m, idx, header, label = None):
        """
        With d as a dict with {k:v} where v are (messages, words)
        output a histogram with percent of total activity for each k
        m is a method to call with each key of the dictionary which will
        return the formatted version of that key
        idx is 0 if you want to go by messages, 1 if words
        returns a list of blocks
        """
        if not label:
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
            fields.append("{}{:.1f}% ({:,} {})".format(histo, new[i][0], new[i][1], label))
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
            link_text = "*{}* {}".format(message['count'], label)
            description = ""
            if show_channel:
                description += " in {}".format(self.show_cid(message['cid']))
            if show_user:
                description += " to a message from {}".format(message['user'])
            description += " on {}".format(message['dt'])
            t = "<{}|{}> {}".format(message['url'], link_text, description)
            # block = self.make_link_button(m, 'link', message['url'])
            block = self.text_block(t)
            blocks.append(block)
        if not blocks:
            return blocks
        blocks = [(self.text_block("*Messages which got the most {}*".format(label)))] + blocks
        blocks.append(self.divider())
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
