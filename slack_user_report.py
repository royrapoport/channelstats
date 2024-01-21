#! /usr/bin/env python

import copy
import json
import random
import time
import sys

from slack_sdk import WebClient

import channel
import enricher
import firstpost
import random_name
import slack_formatter
import slack_token
import user
import user_created
import utils


class SlackUserReport(object):

    def __init__(self, fake=False):
        self.sf = slack_formatter.SlackFormatter(fake=fake)
        random.seed(time.time())
        self.fake = fake
        self.fake_channel = channel.Channel(fake=True)
        self.fp = firstpost.FirstPost()
        self.channel = channel.Channel()
        self.rn = random_name.RandomName()
        self.user = user.User(fake=fake)
        self.client = WebClient(token=slack_token.token)
        self.enricher = enricher.Enricher(fake=fake)
        self.uc = user_created.UserCreated()

    def make_header(self, ur, us, pur, pus, uid):
        blocks = []
        header = "*Public User Activity Report for <@{}>*"
        # header = header.format(ur['user'])
        header = header.format(uid)
        blocks.append(self.sf.text_block(header))

        uc_entry = self.uc.get(uid)
        fp_entry = self.fp.get(uid)
        if uc_entry:
            user_created = "Your account was created on {}, {:,} days ago."
            user_created = user_created.format(uc_entry['date'], uc_entry['days'])
            blocks.append(self.sf.text_block(user_created))
        if fp_entry:
            first_message = "Your first public message was posted on {}".format(fp_entry['date'])
            first_message += ", {:,} days ago. {}".format(fp_entry['days'], fp_entry['url'])
            blocks.append(self.sf.text_block(first_message))

        blocks.append(self.sf.divider())

        tmp_text = "*Last Week (between {} and {})*".format(ur['start_date'], ur['end_date'])
        blocks.append(self.sf.text_block(tmp_text))

        m = "You posted {} words in {} public messages."
        word_comparison = self.sf.comparison(us, pus, ['count', 1])
        msg_comparison = self.sf.comparison(us, pus, ['count', 0])
        m = m.format(word_comparison, msg_comparison)
        m += "\n"
        m += "That made you the *{}*-ranked poster on the Slack and meant you contributed "
        m += "*{:.1f}%*{} of this Slack's total public volume"
        pow_comparison = self.sf.comparison(us, pus, ['percent_of_words'], False)
        m = m.format(utils.rank(us['rank']), us['percent_of_words'], pow_comparison)
        tm = us.get("thread_messages")
        if tm:
            t = ".  In total, {} messages were posted as threaded responses to your messages.\n"
            t = t.format(self.sf.comparison(us, pus, ['thread_messages']))
            m += t
        blocks.append(self.sf.text_block(m))
        return blocks

    def make_report(self, ur, us, pur, pus, uid):
        blocks = []
        blocks += self.make_header(ur, us, pur, pus, uid)
        blocks.append(self.sf.divider())
        blocks += self.make_channels(ur, pur)
        blocks.append(self.sf.divider())
        blocks += self.posting_hours(ur, pur, uid)
        blocks += self.posting_days(ur, pur, uid)
        blocks += self.reacted_messages(ur, uid)
        blocks += self.replied_messages(ur, uid)
        reaction_count_text = "You got {} reactions"
        reaction_count_text = reaction_count_text.format(ur['enriched_user'][uid]['reaction_count'])
        blocks.append(self.sf.text_block(reaction_count_text))
        blocks += self.popular_reactions(ur, uid, count=us['count'][1])
        blocks += self.topten(ur, pur, uid, 'reactions_from',
                              "The people who most reacted to you are")
        blocks += self.topten(ur, pur, uid,
                              'reacted_to', "The people you most reacted to are")
        blocks += self.topten(ur, pur, uid, 'reactions_combined', "Reaction Affinity")
        blocks += self.topten(ur, pur, uid, 'author_thread_responded',
                              "In-thread responses per original author (top ten authors)")
        blocks += self.topten(ur, pur, uid, 'thread_responders',
                              "In-thread responses to your threads (top ten authors)")
        blocks += self.topten(ur, pur, uid, 'threads_combined', "Thread Affinity")
        blocks += self.topten(ur, pur, uid, 'you_mentioned', "The people you mentioned the most")
        blocks += self.topten(ur, pur, uid, 'mentioned_you',
                              "The people who mentioned you the most")
        blocks += self.topten(ur, pur, uid, 'mentions_combined', "Mention Affinity")
        blocks += self.unsubscribe()
        return blocks

    def created(self, uid):
        blocks = []
        entry = self.uc.get(uid)
        if not entry:
            return blocks
        m = "Your account was created on {}, {:,} days ago"
        m = m.format(entry['date'], entry['days'])
        blocks.append(self.sf.text_block(m))
        return blocks

    def unsubscribe(self):
        explanatory = """
        You are receiving this because you are a member of #zmeta-per-user-report-optin.
        Feedback is welcome over in #rls-statistics-tech
        """
        unsub_block = self.sf.text_block(explanatory)
        return [unsub_block]

    def firstpost(self, uid):
        blocks = []
        entry = self.fp.get(uid)
        if not entry:
            return blocks
        m = "By the way, your first-ever message (to the best of our knowledge) was {}, "
        m += "on {}, {:,} days ago"
        m = m.format(entry['url'], entry['date'], entry['days'])
        blocks.append(self.sf.text_block(m))
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
        header = "*Your weekday posting activity by (local) hour of the day:*"
        blocks.append(self.sf.text_block(header))
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
        t = "{} times between you and {} unique people"
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

    def popular_reactions(self, ur, uid, count=None):
        popularity = ur['enriched_user'][uid]['reaction_popularity']
        return self.sf.reactions(popularity, count=count)

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
            f2 = "*{}* rank, {} m, {} w"
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
            utils.save_json(blocks, "slack.json")
            utils.save_json(ur, "enriched_current_report.json")
            utils.save_json(previous, "enriched_previous_report.json")
            return
        # If set to true, this message will be sent as the user who owns the token we use
        as_user = False
        if override_uid:
            uid = override_uid
        for blockset in utils.chunks(blocks, 49):
            if send:
                print("Sending report to {}".format(uid))
                try:
                    response = self.client.chat_postMessage(
                        text="Your Weekly Activity Report",
                        channel=uid,
                        blocks=blockset,
                        parse='full',
                        as_user=as_user,
                        unfurl_links=False,
                        link_names=True)
                    # print("Response: {}".format(response))
                except Exception:
                    print(Exception)
                    print(json.dumps(blockset, indent=4))
                    sys.exit(0)
