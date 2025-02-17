#! /usr/bin/env python

import copy
import json
import random
import time
import sys

from slack_sdk import WebClient

import random_name
import config
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
        self.client = WebClient(token=slack_token.token)
        self.enricher = enricher.Enricher(fake=fake)
        self.cml = channel_members_log.ChannelMembersLog()

    def membercount(self, cid, start, end):
        sc = self.cml.earliest_count(cid, start)
        ec = self.cml.latest_count(cid, end)
        text = self.sf.simple_comparison(ec, sc)
        diff = ec - sc
        text = "{} ended this period with {} members".format(self.sf.show_cid(cid), text)
        if diff:
            text += ", a change of {} members".format(diff)
        return self.sf.text_block(text)

    def messages(self, cid, ur, pur):
        text = ""
        m = "{} messages and {} words were posted to the channel"
        msg_comp = self.sf.comparison(ur, pur, ['channels', cid, 0])
        word_comp = self.sf.comparison(ur, pur, ['channels', cid, 1])
        m = m.format(msg_comp, word_comp)
        text += m
        cur_user_count = len(ur['channel_user'].get(cid, []))
        prev_user_count = len(pur['channel_user'].get(cid, []))
        user_comp = self.sf.simple_comparison(cur_user_count, prev_user_count)
        text += " from {} unique users".format(user_comp)
        curchannelvol = ur['channels'][cid][1]
        curtotal = ur['statistics']["words"]
        prevchannelvol = pur['channels'][cid][1]
        prevtotal = pur['statistics']["words"]
        curper = float("{:.1f}".format(curchannelvol * 100.0 / curtotal))
        prevper = float("{:.1f}".format(prevchannelvol * 100.0 / prevtotal))
        m = "In all, this channel represented {} of total traffic"
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
        cur_user_names.sort(key=lambda x: cur_users[x][1])
        cur_user_names.reverse()
        fields = ["*User*", "*Activity"]
        ctr = 1
        for user in cur_user_names:
            fields.append("{} {}".format(ctr, self.sf.show_uid(user)))
            m = "{} m".format(self.sf.comparison(ur, pur, ['channel_user', cid, user, 0]))
            m += " {} w".format(self.sf.comparison(ur, pur, ['channel_user', cid, user, 1]))
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
        return blocks

    def make_report(self, ur, pur, cid):
        blocks = []
        blocks += self.make_header(ur, pur, cid)
        if cid not in ur['channel_stats']:
            text = "There was no activity in this channel for this time period"
            blocks.append(self.sf.text_block(text))
            return blocks
        if cid not in pur['channel_stats']:
            text = "*Note:* No data exists for the previous (penultimate) week"
            blocks.append(self.sf.text_block(text))
        blocks.append(self.membercount(cid, ur['start_date'], ur['end_date']))
        blocks.append(self.messages(cid, ur, pur))
        blocks.append(self.sf.divider())
        blocks += self.users(cid, ur, pur)
        blocks.append(self.sf.divider())
        blocks.append(self.sf.text_block(
                "People sent {} reactions to the channel".format(
                    self.sf.comparison(ur, pur, ['enriched_channel', cid, 'reaction_count']))))
        blocks += self.popular_reactions(ur, cid)
        blocks += self.reacted_messages(ur, cid)
        blocks += self.replied_messages(ur, cid)
        blocks += self.posting_hours(ur, cid)
        blocks += self.posting_days(ur, cid)
        return blocks

    def posting_days(self, ur, cid):
        """
        Report on activity per day of the week
        """
        d = ur['enriched_channel'][cid]['posting_days']
        return self.sf.posting_days(d)

    def posting_hours(self, ur, cid):
        """
        Report on activity per hour of the workday
        """
        # Why might we not have posting hours? One possibility is
        # that posting hours are just for weekdays, so if the only Activity
        # was during the weekend, we won't see posting hours stats
        d = ur['enriched_channel'][cid].get("posting_hours")
        if not d:
            text = "*Note*: No weekday posting hours statistics are available, "
            text += "possibly because all activity during this time period was "
            text += "during the weekend"
            block = self.sf.text_block(text)
            return [block]
        return self.sf.posting_hours(d)

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
        words = ur['channels'][cid][1]
        return self.sf.reactions(popularity, count=words)

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

    def send_report(self, cid, ur, previous, send=True, override_cid=None,
                    summary=False):
        """
        Send report for channel `cid`
        ur is current period report; previous is the previous report
        will not send if `send` is False
        override_cid will send the report to the provided cid instead of to the channel
        if summary, will send summary of report to config.channel_stats channel
        """
        if override_cid == cid:
            m = "You may not specify an override_cid that is the same as the "
            m += "report cid"
            raise RuntimeError(m)

        enricher.Enricher(fake=self.fake).enrich(ur)
        enricher.Enricher(fake=self.fake).enrich(previous)
        utils.save_json(ur, "ur.json")
        utils.save_json(previous, "previous.json")
        blocks = self.make_report(ur, previous, cid)
        if not send:
            print("Saving report to slack.json")
            f = open("slack.json", "w")
            f.write(json.dumps(blocks, indent=4))
            f.close()
            return
        if override_cid:
            cid = override_cid
        urls = []
        for blockset in utils.chunks(blocks, 49):
            if send:
                print("Sending report to {}".format(cid))
                try:
                    response = self.client.chat_postMessage(
                        text="Weekly Channel Activity Report",
                        channel=cid,
                        blocks=blockset,
                        parse='full',
                        unfurl_links=True,
                        link_names=True)
                    # print("Response: {}".format(response))
                    urls.append(utils.make_url(response['channel'], response['ts']))
                except Exception:
                    print(Exception)
                    print(json.dumps(blockset, indent=4))
                    sys.exit(0)
        if summary and urls:
            cid = self.channel.get(config.channel_stats)['slack_cid']
            self.client.chat_postMessage(
                channel=cid,
                parse='full',
                unfurl_links=True,
                link_names=True,
                text=urls[0]
            )
