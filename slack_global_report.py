#! /usr/bin/env python

import copy
import json
import random
import time
import sys

import slack

import config
import channel
import utils
import enricher
import slack_token
import slack_formatter


class SlackGlobalReport(object):

    def __init__(self):
        self.sf = slack_formatter.SlackFormatter()
        self.channel = channel.Channel()
        self.client = slack.WebClient(token=slack_token.token)
        self.enricher = enricher.Enricher()
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
        text = "*{:,}/{:,}* (or *{:.1f}%* of) users posted messages\n".format(posters, active_users, percent)
        text += "Median message count was *{}*\n".format(stats['median messages'])
        text += "The top *10* posters contributed *{:.1f}%* of all messages (lower is better)\n".format(stats['topten messages'])
        text += "The top *{}* posters (higher is better) accounted for about 50% of total volume\n".format(stats['50percent of words'])
        blocks.append(self.sf.text_block(text))
        w = int(stats['words'])
        m = int(stats['messages'])
        pages = int(w/500)
        # it = interim text
        # We approximate 500 words to a page
        it = "People posted {} in {} (approximately {}), ".format(self.sf.pn(w, "word"), self.sf.pn(m, "message"), self.sf.pn(pages, "page"))
        it += "or about *{:.1f}* words per message, *{:.1f}* words per poster, ".format(w/m, w/posters)
        it += "or *{:.1f}* messages per poster\n".format(m/posters)
        it += "(We estimate number of pages using the figure of 500 words per page)"
        text = it
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
            it += "{}, ".format(self.sf.pn(ci['members'], "member"))

            m = channels[channel][0]
            w = channels[channel][1]
            p = len(cu)
            it += "{}, {}, {}, ".format(self.sf.pn(p, "poster"), self.sf.pn(w, "word"), self.sf.pn(m, "message"))
            it += "*{:.1f}* words/poster, ".format(w/p)
            it += "*{:.1f}%* of total traffic, ".format(cs['percent'])
            it += "*{:.1f}%* cumulative of total ".format(cs['cpercent'])
            blocks.append(self.sf.text_block(it))
        blocks.append(self.sf.divider())
        return blocks

    def top_users(self, ur, pur):
        blocks = []
        top = 20
        header = "*Top {} Users*\n".format(top)
        header += "(rphw = Reactions Per Hundred Messages)"
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
            it += "{}, {}, *{:.1f}* w/m, ".format(self.sf.pn(w, "word"), self.sf.pn(m, "message"), w_per_m)
            it += "*{:.1f}* rphw, {} in threads, ".format(rphw, self.sf.pn(t, "message"))
            it += "*{:.1f}%*, *{:.1f}%* cumulative of total\n".format(per, cper)
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
            it += " {} wrote {} in {}\n".format(self.sf.pn(posters, "poster"), self.sf.pn(timezones[tz][1], "word"), self.sf.pn(timezones[tz][0], "message"))
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
            it = "*{}* {} in {}\n".format(day, self.sf.pn(w, "word"), self.sf.pn(m, "message"))
            text += it
        blocks.append(self.sf.text_block(text))
        blocks.append(self.sf.divider())
        return blocks

    def hours(self, ur, pur):
        blocks = []
        header = "*Activity Per Hour (on Weekdays)*"
        blocks.append(self.sf.text_block(header))
        # Grr, the way we keep things is in percentages, but we need total numbers.  Convert
        hours = ur['weekday_activity_percentage']
        words = ur['statistics']['words']
        new_hours = {}
        for idx in hours:
            new_hours[idx] = [int(hours[idx] * words / 100)]
        blocks += self.sf.histogram(new_hours, self.sf.hour_formatter, 0, "*(Local) Time of Weekday*", label="words")
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
            show_channel=True)

    def send_report(self, ur, previous, send=True, destination=None, summary=False):
        enricher.Enricher().enrich(ur)
        enricher.Enricher().enrich(previous)
        blocks = self.make_report(ur, previous)
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
