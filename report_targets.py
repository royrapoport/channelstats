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


def channels(debug=False):
    """
    for a cid that we should get activity for, return
    {cid: report_cid} where report_cid is the CID to which we should send the report
    """
    friendly_names = channel_obj.friendly_channel_names(active=True)
    stats_channels = [x for x in friendly_names if re.match(".*-stats$", x)]
    friendly_names = channel_obj.friendly_channel_names()
    if debug:
        print("Stats channels: {}".format(stats_channels))
    # channel_names will be a
    # {channel_name_to_do_report_on: channel_name_to_send_report_to}
    # dict
    channel_names = {}
    for stat_channel in stats_channels:
        rep = re.sub("-stats$", "", stat_channel)
        if rep in friendly_names:
            channel_names[rep] = stat_channel
    channel_ids = {}
    for channel_name in channel_names.keys():
        entry = channel_obj.get(channel_name)
        if entry:
            cid = entry['slack_cid']
            report_cid = channel_obj.get(channel_names[channel_name])['slack_cid']
            channel_ids[cid] = report_cid

    return channel_ids


if __name__ == "__main__":
    print("users: {}".format(users()))
    print("channels: {}".format(channels(debug=True)))
