#! /usr/bin/env python3

import re

import config
import slacker
import channel
import slack_token

fake = False
slack = slacker.Slacker(config.slack_name, slack_token.token)
channel_obj = channel.Channel()

def users():
    """
    return list of users who should get user reports
    """
    optchan = config.optin_channel
    optchan_id = channel_obj.get(optchan)['slack_cid']
    users = slack.get_users_for_channel(optchan_id)
    return users

def channels():
    friendly_names = channel_obj.friendly_channel_names()
    stats_channels = [x for x in friendly_names if re.match(".*-stats$", x)]
    report_channel_names = []
    for stat_channel in stats_channels:
        rep = re.sub("-stats$", "", stat_channel)
        if rep in friendly_names:
            report_channel_names.append(rep)
    report_channel_ids = []
    for report_channel_name in report_channel_names:
        entry = channel_obj.get(report_channel_name)
        if entry:
            report_channel_ids.append(entry['slack_cid'])
    return report_channel_ids

if __name__ == "__main__":
    print("users: {}".format(users()))
    print("channels: {}".format(channels()))
    channels()

