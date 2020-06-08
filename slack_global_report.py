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
import firstpost
import slack_token
import slack_formatter


class SlackGlobalReport(object):

    def __init__(self):
        self.sf = slack_formatter.SlackFormatter()
        self.channel = channel.Channel()
        self.client = slack.WebClient(token=slack_token.token)
        self.firstpost = firstpost.FirstPost()
        self.enricher = enricher.Enricher()
        self.report_channel  = self.channel.get(config.report_channel)['slack_cid']
        self.top = 20

    def firstposters(self, ur):
        """
        return the number of people who had first posts during this period
        """
        start_date = ur['start_date']
        days = ur['days']
        return self.firstpost.firstpost_count(start_date, days)

    def make_header(self, ur, pur):
        blocks = []
        header = "*Slack Activity Report for the Week Between {} and {}*"
        header = header.format(ur['start_date'], ur['end_date'])
        blocks.append(self.sf.text_block(header))
        s = ur['statistics']
        ps = pur['statistics']
        posters = int(s['posters'])
        pposters = int(ps['posters'])
        active_users = s['active_users']
        cur_new_users = self.firstposters(ur)
        prev_new_users = self.firstposters(pur)
        percent = (posters * 100.0) / active_users
        text = "{}/".format (self.sf.comparison(s, ps, ['posters']))
        text += "{} ".format (self.sf.comparison(s, ps, ['active_users']))
        text += " (or *{:.1f}%* of) users posted messages\n".format(percent)
        text += "Median message count was *{}*\n".format(s['median messages'])
        text += "The top *10* posters contributed "
        text += "{} ".format(self.sf.comparison(s, ps, ['topten messages'], is_percent=True))
        text += "of all messages (lower is better)\n"
        text += "The top {} ".format(self.sf.comparison(s, ps, ['50percent of words']))
        text += "posters (higher is better) accounted for about 50% of total volume\n"
        text += "{} people posted for the first time in this Slack!\n".format(self.sf.simple_comparison(cur_new_users, prev_new_users))
        blocks.append(self.sf.text_block(text))
        w = int(s['words'])
        m = int(s['messages'])
        pw = int(ps['words'])
        pm = int(ps['messages'])
        pages = int(s['words']/500)
        ppages = int(ps['words']/500)
        # it = interim text
        # We approximate 500 words to a page
        it = "People posted {} in ".format(self.sf.comparison(s, ps, ['words'], label='word'))
        it += "{} ".format(self.sf.comparison(s, ps, ['messages'], label='message'))
        it += "(approximately {})\n".format(self.sf.simple_comparison(pages, ppages, label="page"))
        it += "That's about {} per message, ".format(self.sf.simple_comparison(w/m, pw/pm, label="word"))
        it += "{} per poster, ".format(self.sf.simple_comparison(w/posters, pw/pposters, label="word"))
        it += "or {} per poster.\n".format(self.sf.simple_comparison(m/posters, pm/pposters, label="message"))
        it += "(We estimate number of pages using the figure of 500 words per page)"
        text = it
        blocks.append(self.sf.text_block(text))
        blocks.append(self.sf.divider())
        return blocks

    def top_channels(self, ur, pur):
        blocks = []
        header = "*Top {} Channels* (w = words, m = messages)".format(self.top)
        blocks.append(self.sf.text_block(header))
        channels = ur['channels']
        pchannels = pur['channels']
        cids = list(channels.keys())[:self.top]
        cinfo = ur['channel_info']
        cstats = ur['channel_stats']
        cusers = ur['channel_user']
        pcinfo = pur['channel_info']
        pcstats = pur['channel_stats']
        pcusers = pur['channel_user']
        for idx, channel in enumerate(cids):
            it = "{}. {} ".format(idx + 1, self.sf.show_cid(channel))
            ci = cinfo[channel]
            cs = cstats[channel]
            cu = cusers[channel]
            pci = pcinfo.get(channel, {})
            pcs = pcstats.get(channel, {})
            pcu = pcusers.get(channel, [])
            if ci['new']:
                it += " (new)"
            members = self.sf.simple_comparison(ci['members'], pci.get('members', 0))
            m = channels[channel][0]
            w = channels[channel][1]
            p = len(cu)
            pm = pchannels.get(channel, [0,0])[0]
            pw = pchannels.get(channel, [0,0])[1]
            pp = len(pcu)
            posters = self.sf.simple_comparison(p, pp, label='')
            it += "{}/{} posters, ".format(posters, members)
            it += self.sf.simple_comparison(w, pw) + "w, "
            it += self.sf.simple_comparison(m, pm) + "m,"
            # wp = words per poster.  Make sure we don't divide by 0
            if p:
                wp = w/p
            else:
                wp = 0
            if pp:
                pwp = pw/pp
            else:
                pwp = 0
            it += self.sf.simple_comparison(wp, pwp, label='word') + "/poster, "
            it += self.sf.simple_comparison(cs['percent'], pcs.get('percent', 0), is_percent=True) + " of total traffic, "
            it += self.sf.simple_comparison(cs['cpercent'], pcs.get('cpercent', 0), is_percent=True) + " cumulative of total."
            blocks.append(self.sf.text_block(it))
        blocks.append(self.sf.divider())
        return blocks

    def top_users(self, ur, pur):
        blocks = []
        header = "*Top {} Users*\n".format(self.top)
        header += "(rphw = Reactions Per Hundred Messages)"
        blocks.append(self.sf.text_block(header))
        stats = ur['statistics']
        us = ur['user_stats']
        pus = pur['user_stats']
        uids = stats['50percent users for words'][:self.top]
        for idx, uid in enumerate(uids):
            # current stats
            usu = us[uid]
            m = usu['count'][0]
            w = usu['count'][1]
            per = usu['percent_of_words']
            cper = usu['cum_percent_of_words']
            rphw = usu['reactions'] * 100.0 / w
            w_per_m = w / m
            t = usu['thread_messages']
            # previous period stats
            if uid in pus:
                pusu = pus[uid]
                pm = pusu['count'][0]
                pw = pusu['count'][1]
                pper = pusu['percent_of_words']
                pcper = pusu['cum_percent_of_words']
                prphw = pusu['reactions'] * 100.0 / pw
                pw_per_m = pw / pm
                pt = pusu['thread_messages']
            else:
                pm = 0
                pw = 0
                pper = 0
                pcper = 0
                prphw = 0
                pw_per_m = 0
                pt = 0

            it = self.format_user(idx, uid, w, pw, m, pm, rphw, prphw, t, pt, per, pper, cper, pcper)
            blocks.append(self.sf.text_block(it))
        blocks.append(self.sf.divider())
        return blocks

    def format_user(self, idx, uid, w, pw, m, pm, rphw, prphw, t, pt, per, pper, cper, pcper):
        """
        Formats a user's volume line.  For all variables, the variable that starts with 'p' is the previous
        week's number
        idx = the index of the user (in the top x list, starting with 0)
        uid = User's UID
        w = words
        m = messages
        rphw = reactions per hundred words
        t = messages in threads
        per = percent of total traffic
        cper = cumulative percent of total traffic
        """
        it = "{}. *{}* ".format(idx + 1, self.sf.show_uid(uid))
        it += self.sf.simple_comparison(w, pw, label='word') + ", "
        it += self.sf.simple_comparison(m, pm, label='message') + ", "
        it += self.sf.simple_comparison(rphw, prphw) + "rphw"
        it += self.detailed_format_user(t, pt, per, pper, cper, pcper)
        return it

    def detailed_format_user(self, t, pt, per, pper, cper, pcper):
        """
        Provides some details for a user's volume line.
        For all variables, the variable that starts with 'p' is the previous week's number
        t = messages in threads
        per = percent of total traffic
        cper = cumulative percent of total traffic
        """

        it = " " + self.sf.simple_comparison(t, pt, label="message") + " in threads, "
        it += self.sf.simple_comparison(per, pper, is_percent=True) + " of total traffic, "
        it += self.sf.simple_comparison(cper, pcper, is_percent=True) + " cumulative of total.\n"
        return it
    

    def timezones(self, ur, pur):
        blocks = []
        header = "*Activity Per Author Timezone*\n"
        header += "Counts are based on the poster's profile-based timezone"
        blocks.append(self.sf.text_block(header))
        timezones = ur['timezone']
        ptimezones = pur['timezone']
        for idx, tz in enumerate(timezones):
            it = "{}. *{}* ".format(idx + 1, tz)
            posters = len(ur['posters_per_timezone'][tz].keys())
            pposters = len(pur['posters_per_timezone'].get(tz, {}).keys())
            w = timezones[tz][1]
            m = timezones[tz][0]
            pw = ptimezones.get(tz, [0,0])[1]
            pm = ptimezones.get(tz, [0,0])[0]
            it += self.sf.simple_comparison(posters, pposters, label="poster") + " wrote "
            it += self.sf.simple_comparison(w, pw, label="word") + " in "
            it += self.sf.simple_comparison(m, pm, label="message") + "\n"
            blocks.append(self.sf.text_block(it))
        blocks.append(self.sf.divider())
        return blocks

    def days(self, ur, pur):
        blocks = []
        header = "*Activity Per Day*"
        blocks.append(self.sf.text_block(header))
        uwd = ur['user_weekday']
        puwd = pur['user_weekday']
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        text = ""
        for idx, day in enumerate(days):
            match = uwd.get(str(idx), [0,0])
            prev_match = puwd.get(str(idx), [0,0])
            m = match[0]
            w = match[1]
            pm = prev_match[0]
            pw = prev_match[1]
            it = "*{}* ".format(day)
            it += "{} in ".format(self.sf.simple_comparison(w, pw, label="word"))
            it += "{}\n".format(self.sf.simple_comparison(m, pm, label="message"))
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
        blocks.append(self.sf.divider())
        return blocks

    def reacji(self, ur, pur):
        blocks = []
        header = "*Top Ten Reacji*"
        blocks.append(self.sf.text_block(header))
        rd = {}
        words = int(ur['statistics']['words'])
        reacjis = ur['top_ten_reactions']
        for reacji in reacjis:
            rd[reacji] = ur['reaction'][reacji]
        blocks += self.sf.reactions(rd, count=words)
        blocks.append(self.sf.divider())
        return blocks

    def make_report(self, ur, pur):
        blocks = []
        blocks += self.make_header(ur, pur)
        blocks += self.top_channels(ur, pur)
        blocks += self.top_users(ur, pur)
        blocks += self.days(ur, pur)
        blocks += self.timezones(ur, pur)
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

    def send_report(self, ur, previous, send=True, destination=None):
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
