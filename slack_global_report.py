#! /usr/bin/env python

import copy
import json
import random
import time
import sys

import slack

import random_name
import config
import channel
import channel_members_log
import user
import utils
import enricher
import slack_token
import slack_formatter


class SlackGlobalReport(object):

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
        self.report_channel  = self.channel.get(config.report_channel)['slack_cid']

    def make_header(self, ur, pur):
        blocks = []
        header = "*Slack Activity Report for the Week Between {} and {}*"
        header = header.format(ur['start_date'], ur['end_date'])
        blocks.append(self.sf.text_block(header))
        stats = ur['statistics']
        posters = int(stats['posters'])
        active_users = stats['active_users']
        percent = (posters * 100.0) / active_users
        text = "*{:,}/{:,}* (or *{:.1f}%*) users posted messages\n".format(posters, active_users, percent)
        text += "Median message count was *{}*\n".format(stats['median messages'])
        text += "The top ten posters contributed *{:.1f}%* of all messages (lower is better)\n".format(stats['topten messages'])
        text += "The top *{}* posters (higher is better) accounted for about 50% of total volume\n".format(stats['50percent of words'])
        blocks.append(self.sf.text_block(text))
        w = stats['words']
        m = stats['messages']
        # it = interim text
        it = "People posted *{:,}* words in *{:,}* messages (approximately *{:,}* pages), "
        it += "or about *{:.1f}* words per message, *{:.1f}* words per poster, "
        it += "or *{:.1f}* messages per poster"
        text = it.format(int(w), int(m), int(w / 500), w/m, w/posters, m/posters)
        blocks.append(self.sf.text_block(text))
        blocks.append(self.sf.divider())
        return blocks

    def top_channels(self, ur, pur):
        blocks = []
        top = 20
        header = "*Top {} Channels*".format(top)
        blocks.append(self.sf.text_block(header))
        channels = ur['channels']
        cids = list(channels.keys())[:top]
        cinfo = ur['channel_info']
        cstats = ur['channel_stats']
        cusers = ur['channel_user']
        for idx, channel in enumerate(cids):
            it = "{}. {} ".format(idx + 1, self.sf.show_cid(channel))
            ci = cinfo[channel]
            cs = cstats[channel]
            cu = cusers[channel]
            if ci['new']:
                it += " (new)"
            it += "{:,} members ".format(ci['members'])

            m = channels[channel][0]
            w = channels[channel][1]
            p = len(cu)
            it += "*{:,}* posters *{:,}* words *{:,}* messages ".format(p, w, m)
            it += "*{:.1f}* words/poster ".format(w/p)
            it += "*{:.1f}%* of total traffic, ".format(cs['percent'])
            it += "*{:.1f}%* cumulative of total ".format(cs['cpercent'])
            blocks.append(self.sf.text_block(it))
        blocks.append(self.sf.divider())
        return blocks

    def top_users(self, ur, pur):
        blocks = []
        top = 20
        header = "*Top {} Users*".format(top)
        blocks.append(self.sf.text_block(header))
        stats = ur['statistics']
        us = ur['user_stats']
        uids = stats['50percent users for words'][:top]
        for idx, uid in enumerate(uids):
            usu = us[uid]
            m = usu['count'][0]
            w = usu['count'][1]
            per = usu['percent_of_words']
            cper = usu['cum_percent_of_words']
            rphw = usu['reactions'] * 100.0 / w
            w_per_m = w / m
            t = usu['thread_messages']
            it = "{}. *{}* ".format(idx + 1, self.sf.show_uid(uid))
            it += "*{:,}* words *{:,}* messages *{:.1f}* w/m ".format(w, m, w_per_m)
            it += "*{:.1f}* rphw ".format(rphw)
            it += "*{:.1f}%* *{:.1f}%* cumulative\n".format(per, cper)
            blocks.append(self.sf.text_block(it))
        blocks.append(self.sf.divider())
        return blocks

    def timezones(self, ur, pur):
        blocks = []
        header = "*Activity Per Author Timezone*\n"
        header += "Counts are based on the poster's profile-based timezone"
        blocks.append(self.sf.text_block(header))
        timezones = ur['timezone']
        text = ""
        for idx, tz in enumerate(timezones):
            it = "{}. *{}* ".format(idx + 1, tz)
            posters = len(ur['posters_per_timezone'][tz].keys())
            it += " {:,} posters wrote {:,} words in {:,} messages\n".format(posters, timezones[tz][1], timezones[tz][0])
            text += it
        blocks.append(self.sf.text_block(text))
        blocks.append(self.sf.divider())
        return blocks

    def days(self, ur, pur):
        blocks = []
        header = "*Activity Per Day*"
        blocks.append(self.sf.text_block(header))
        uwd = ur['user_weekday']
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        text = ""
        for idx, day in enumerate(days):
            match = uwd.get(str(idx), [0,0])
            m = match[0]
            w = match[1]
            it = "*{}* *{:,}* words in *{:,}* messages\n".format(day, w, m)
            text += it
        blocks.append(self.sf.text_block(text))
        blocks.append(self.sf.divider())
        return blocks

    def hours(self, ur, pur):
        blocks = []
        header = "*Activity Per Hour (on Weeekdays)*"
        blocks.append(self.sf.text_block(header))
        hours = ur['weekday_activity_percentage']
        text = ""
        for hour in hours:
            it = "*{}* *{:.2f}%*\n".format(hour, hours[hour])
            text += it
        blocks.append(self.sf.text_block(text))
        blocks.append(self.sf.divider())
        return blocks

    def reacji(self, ur, pur):
        blocks = []
        header = "*Top Ten Reacji*"
        blocks.append(self.sf.text_block(header))
        reacjis = ur['top_ten_reactions']
        text = ""
        for reacji in reacjis:
            it = ":{}: *{:,}*\n".format(reacji, ur['reaction'][reacji])
            text += it
        blocks.append(self.sf.text_block(text))
        blocks.append(self.sf.divider())
        return blocks

    def make_report(self, ur, pur):
        blocks = []
        blocks += self.make_header(ur, pur)
        blocks += self.top_channels(ur, pur)
        blocks += self.top_users(ur, pur)
        blocks += self.timezones(ur, pur)
        blocks += self.days(ur, pur)
        blocks += self.hours(ur, pur)
        blocks += self.reacji(ur, pur)
        blocks += self.reacted_messages(ur)
        blocks += self.replied_messages(ur)
        return blocks

    def reacted_messages(self, ur):
        return self.sf.messager(
            ur['reacted_messages'],
            'reactions',
            show_user=True,
            show_channel=True)

    def replied_messages(self, ur):
        return self.sf.messager(
            ur['replied_messages'],
            'replies',
            show_user=True,
            show_channel=False)

    def send_report(self, ur, previous, send=True, destination=None, summary=False):
        enricher.Enricher(fake=self.fake).enrich(ur)
        enricher.Enricher(fake=self.fake).enrich(previous)
        blocks = self.make_report(ur, previous)
        if not send:
            print("Saving report to slack.json")
            f = open("slack.json", "w")
            f.write(json.dumps(blocks, indent=4))
            f.close()
        # If set to true, this message will be sent as the user who owns the token we use
        as_user = False
        urls = []
        destination = destination or self.report_channel
        for blockset in utils.chunks(blocks, 49):
            if send:
                try:
                    response = self.client.chat_postMessage(
                        channel=destination,
                        blocks=blockset,
                        parse='full',
                        as_user=as_user,
                        unfurl_links=True,
                        link_names=True)
                    # print("Response: {}".format(response))
                    urls.append(utils.make_url(response['channel'], response['ts']))
                except Exception as e:
                    print(e)
                    # print(json.dumps(blockset, indent=4))
                    sys.exit(0)
        if summary and urls:
            cid = self.channel.get(config.channel_stats)['slack_cid']
            self.client.chat_postMessage(
                channel = cid,
                parse='full',
                as_user=as_user,
                unfurl_links=True,
                link_names=True,
                text=urls[0]
            )
