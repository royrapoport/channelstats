#! /usr/bin/env python

import json

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

    def make_header(self, ur, us):
        blocks = []
        header = "Public User Activity Report for *{}* Between {} and {}"
        header = header.format(ur['user'], ur['start_date'], ur['end_date'])
        blocks.append(self.text_block(header))
        blocks.append(self.divider())
        m = "You posted *{:,}* words in *{:,}* public messages."
        m = m.format(us['count'][1], us['count'][0])
        m += "\n"
        tm = us.get("thread_messages")
        if tm:
            m += "You started public threads that added *{}* messages by other people to total volume\n".format(tm)
        m += "That made the *{}*-ranked poster on the Slack and meant you contributed "
        m += "*{:.1f}%* of this Slack's total public volume"
        m = m.format(us['rank'], us['percent_of_words'])
        blocks.append(self.text_block(m))
        return blocks

    def make_report(self, ur, us, uid):
        blocks = []
        blocks += self.make_header(ur, us)
        blocks.append(self.divider())
        blocks += self.make_channels(ur)
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
        print("I have {} blocks".format(len(blocks)))
        # print(json.dumps(blocks, indent=4))
        return blocks

    def topten(self, ur, uid, label, header):
        blocks = []
        blocks.append(self.text_block("*{}*".format(header)))
        fields = ["*Person*", "*Count*"]

        d = ur['enriched_user'][uid][label]
        uids = list(d.keys())[0:10]
        for uid in uids:
            fields.append(ur['user_info'][uid]['label'])
            fields.append(str(d[uid]))

        for fset in self.make_fields(fields):
            block = {'type': 'section', 'fields': fset}
            blocks.append(block)
        return blocks

    def reacted_messages(self, ur, uid):
        return self.messager(ur, uid, "reactions")

    def replied_messages(self, ur, uid):
        return self.messager(ur, uid, "replies")

    def messager(self, ur, uid, label):
        text = ""
        for message in ur['reenriched_user'][uid][label]:
            m = "*{}* {} to {} in #{} on {}\n"
            m = m.format(message['count'], label, message['url'], message['channel'], message['dt'])
            text += m
        blocks = []
        blocks.append(self.divider())
        blocks.append(self.text_block(text))
        return blocks

    def popular_reactions(self, ur, uid):
        popularity = ur['enriched_user'][uid]['reaction_popularity']
        fields = []
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

    def make_channels(self, ur):
        fields = []
        ctr = 1
        fields.append("*Channel*")
        fields.append("*Rank, Messages, Words*")
        for channel in ur['enriched_channels']:
            f1 = "{} *{}*".format(ctr, channel['name'])
            f2 = "*{}* rank, *{}* m, *{}* w"
            f2 = f2.format(channel['rank'], channel['messages'], channel['words'])
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

    def send_report(self, uid, ur):
        self.enricher.user_enrich(ur, uid)
        us = ur['user_stats'][uid]
        blocks = self.make_report(ur, us, uid)
        for blockset in utils.chunks(blocks, 49):
            self.client.chat_postMessage(channel=uid, blocks=blockset)
