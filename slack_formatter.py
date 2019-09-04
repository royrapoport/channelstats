#! /usr/bin/env python

import copy
import json
import sys

import slack

import utils
import enricher
import slack_token


class SlackFormatter(object):

    def __init__(self):
        self.client = slack.WebClient(token=slack_token.token)
        self.enricher = enricher.Enricher()

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
        tm = us.get("thread_messages")
        if tm:
            t = "In total, {} messages were posted as threaded responses to your messages.\n"
            t = t.format(self.comparison(us, pus, ['thread_messages']))
            m += t
        m += "That made you the *{}*-ranked poster on the Slack and meant you contributed "
        m += "*{:.1f}%*{} of this Slack's total public volume"
        m = m.format(utils.rank(us['rank']), us['percent_of_words'], self.comparison(us, pus, ['percent_of_words'], False))
        blocks.append(self.text_block(m))
        return blocks

    def make_report(self, ur, us, pur, pus, uid):
        blocks = []
        blocks += self.make_header(ur, us, pur, pus)
        blocks.append(self.divider())
        blocks += self.make_channels(ur, pur)
        blocks += self.reacted_messages(ur, uid)
        blocks += self.replied_messages(ur, uid)
        blocks.append(self.text_block("You got {} reactions".format(ur['enriched_user'][uid]['reaction_count'])))
        blocks += self.popular_reactions(ur, uid)
        blocks += self.topten(ur, uid, 'reactions_from', "The people who most responded to you are")
        blocks += self.topten(ur, uid, 'reacted_to', "The people you most responded to are")
        blocks += self.topten(ur, uid, 'reactions_combined', "Reaction Affinity")
        blocks += self.topten(ur, uid, 'author_thread_responded', "Authors whose threads you responded to the most")
        blocks += self.topten(ur, uid, 'thread_responders', "Most frequent responders to your threads")
        blocks += self.topten(ur, uid, 'threads_combined', "Thread Affinity")
        blocks += self.topten(ur, uid, 'you_mentioned', "The people you mentioned the most")
        blocks += self.topten(ur, uid, 'mentioned_you', "The people who mentioned you the most")
        blocks += self.topten(ur, uid, 'mentions_combined', "Mention Affinity")
        return blocks

    def topten(self, ur, uid, label, header):
        blocks = []
        blocks.append(self.text_block("*{}*".format(header)))
        fields = ["*Person*", "*Count*"]

        d = ur['enriched_user'][uid].get(label)
        if not d:
            return []
        t = "*{}* times between you and *{}* unique people"
        total = sum(d.values())
        count = len(list(d.keys()))
        t = t.format(total, count)
        blocks.append(self.text_block(t))
        uids = list(d.keys())[0:10]
        for uid in uids:
            # fields.append(ur['user_info'][uid]['label'])
            fields.append("<@{}>".format(uid))
            fields.append(str(d[uid]))

        for fset in self.make_fields(fields):
            block = {'type': 'section', 'fields': fset}
            blocks.append(block)
        return blocks

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
            m = "*{}* {} in #{} on {}"
            m = m.format(message['count'], label, message['channel'], message['dt'])
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

    def make_channels(self, ur, pur):
        fields = []
        ctr = 1
        if not ur['enriched_channels']:
            return fields
        fields.append("*Channel*")
        fields.append("*Rank, Messages, Words*")
        for channel_name in ur['enriched_channels']:
            channel = ur['enriched_channels'][channel_name]
            f1 = "{} *{}*".format(ctr, channel['name'])
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
        enricher.Enricher().user_enrich(ur, uid)
        enricher.Enricher().user_enrich(previous, uid)
        us = ur['user_stats'].get(uid, {})
        pus = previous['user_stats'].get(uid, {})
        blocks = self.make_report(ur, us, previous, pus, uid)
        # If set to true, this message will be sent as the user who owns the token we use
        as_user = False
        for blockset in utils.chunks(blocks, 49):
            if send:
                print("Sending report to {}".format(uid))
                if override_uid:
                    uid=override_uid
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
