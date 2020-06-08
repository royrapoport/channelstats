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
import slack_global_report


class SlackBriefGlobalReport(slack_global_report.SlackGlobalReport):

    def __init__(self):
        super(SlackBriefGlobalReport, self).__init__()
        self.top = 10

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
            blocks.append(self.sf.text_block(it))
        blocks.append(self.sf.divider())
        return blocks

    def detailed_format_user(self, t, pt, per, pper, cper, pcper):
        """
        Provides some details for a user's volume line.
        Or would, if this was not a brief report.
        """
        return "\n"

    def make_report(self, ur, pur):
        blocks = []
        blocks += self.make_header(ur, pur)
        blocks += self.top_channels(ur, pur)
        blocks += self.top_users(ur, pur)
        blocks += self.days(ur, pur)
        blocks += self.reacji(ur, pur)
        blocks += self.reacted_messages(ur)
        blocks += self.replied_messages(ur)
        return blocks
