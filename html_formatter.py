#! /usr/bin/env python

import datetime
import json
import time

import jinja2
import htmlmin

import channel
import config
import user

class HTMLFormatter(object):

    def __init__(self):
        self.jinja_environment = jinja2.Environment(loader=jinja2.FileSystemLoader("."))
        self.general_template = self.jinja_environment.get_template("general_report_template.html")
        self.user_template = self.jinja_environment.get_template("user_report_template.html")
        self.user = user.User()
        self.channel = channel.Channel()

    def pick_name(self, user):
        """
        given a user structure from user.get(), return the name we should
        show people -- this should ideally be the name they see people
        interact as in slack
        """
        dn = user.get('display_name')
        rn = user.get("real_name")
        un = user.get("user_name")
        return dn or rn or un

    def get_channels(self, list_of_cid, report_start_date):
        """
        Given a list of channel IDs and an yyyy-mm-dd str date,
        returns a dictionary indexed by cid
        where the value is another dictionary with
            'name': user-friendly channel name
            'new': True/False based on whether it was created during this period
            'members': Count of members
        """
        (y, m, d) = [int(x) for x in report_start_date.split("-")]
        dt = datetime.datetime(y, m, d, 0, 0, 0)
        report_start_timestamp = dt.timestamp()

        entries = self.channel.batch_get_channel(list_of_cid)
        ret = {}
        for cid in entries:
            entry = entries[cid]
            # print("Entry: {}".format(entry))
            name = entry['name']
            created = int(entry['created'])
            new = created > report_start_timestamp
            members = entry.get("members", 0)
            entry = {'name': name, 'new': new, 'members': members}
            ret[cid] = entry
        return ret

    def get_users(self, list_of_userids):
        """
        Given a list of userIDs, returns a dictionary indexed by userID
        where the value is another dictionary with
            'label': The actual label to show for the user ID
            'hover': The text to show when hovering over the label
            'url': The URL to link to for more information about the user
        """
        ret = {}
        start = time.time()
        entries = self.user.batch_get_user(list_of_userids)
        for uid in list_of_userids:
            entry = entries[uid]
            # print("entry: {}".format(entry))
            user = {}
            user['label'] = '@' + self.pick_name(entry)
            user['hover'] = entry['real_name']
            url = "https://{}.slack.com/team/{}"
            url = url.format(config.slack_name, uid)
            user['url'] = url
            ret[uid] = user
        end = time.time()
        diff = end - start
        # print("Fetching users took {:.1f} seconds".format(diff))
        return ret

    def popular_messages(self, messages, cinfo, uinfo):
        """
        given a list of lists where each list is
        [reaction count, timestamp, cid, uid]
        convert to dict with 'count', 'dt', 'channel', 'user', 'url'
        """
        ret = []
        for message in messages:
            if type(message) != list:
                continue
            (reactions, timestamp, cid, uid) = message
            d = {}
            d['count'] = reactions
            d['dt'] = time.strftime("%m/%d/%Y %H:%M", time.localtime(int(float(timestamp))))
            d['channel'] = cinfo[cid]['name']
            d['user'] = uinfo[uid]['label']
            url = "https://{}.slack.com/archives/{}/p{}"
            d['url'] = url.format(config.slack_name, cid, timestamp)
            ret.append(d)
        return ret

    def enrich(self, report):
        # Get the canonical list of USER ids we might refer to.
        # That is all users who posted in all channels
        channels = report['channel_user'].keys()
        users = {} # We need a list, but this makes deduping easier
        channel_list = []
        for channel in channels:
            channel_list.append(channel)
            for user in report['channel_user'][channel]:
                users[user] = 1
        users = list(users.keys())
        channel_info = self.get_channels(channel_list, report['start_date'])
        user_info = self.get_users(users)
        report['user_info'] = user_info
        report['channel_info'] = channel_info

        reactions = report['reaction']
        reactji = list(reactions.keys())
        report['top_ten_reactions'] = reactji[0:10]

        report['reacted_messages'] = self.popular_messages(report['reaction_count'], channel_info, user_info)
        report['reacted_messages'] = report['reacted_messages'][0:10]

        report['replied_messages'] = self.popular_messages(report['reply_count'], channel_info, user_info)
        report['replied_messages'] = report['replied_messages'][0:10]

    def user_format(self, report, uid):
        print("Running report for {}".format(uid))
        self.enrich(report)
        user = report['user_info'][uid]['label']
        report['uid'] = uid
        report['user'] = user

        channel_list = []
        for cid in report['channel_user']:
            print("Examining cid {}".format(cid))
            channel = report['channel_user'][cid]
            if uid not in channel:
                continue
            users = list(channel.keys())
            users.sort(key = lambda x: channel[x][1])
            users.reverse()
            rank = 1
            for i in users:
                if i == uid:
                    break
                rank += 1
            cname = report['channel_info'][cid]['name']
            channel_messages = report['channels'][cid][0]
            channel_words = report['channels'][cid][1]
            messages = channel[uid][0]
            words = channel[uid][1]
            percent_words = words * 100.0 / channel_words
            percent_messages = messages * 100.0 / channel_messages
            c = {}
            c['name'] = cname
            c['rank'] = rank
            c['words'] = words
            c['messages'] = messages
            c['percent'] = percent_words
            channel_list.append(c)
        channel_list.sort(key = lambda x: x['words'])
        channel_list.reverse()
        report['channels'] = channel_list

        ci = report['channel_info']
        ui = report['user_info']
        for user in report['enriched_user']:
            for t in ['reactions', 'replies']:
                messages = self.popular_messages(report['enriched_user'][user][t], ci, ui)
                report['enriched_user'][user][t] = messages

        html_report = self.user_template.render(payload=report)
        minified_html_report = htmlmin.minify(html_report,
                              remove_comments=True,
                              remove_empty_space=True,
                              remove_all_empty_space=True,
                              reduce_boolean_attributes=True
                              )
        return minified_html_report


    def format(self, report):
        self.enrich(report)
        html_report = self.general_template.render(payload=report, statistics=report['statistics'])
        minified_html_report = htmlmin.minify(html_report,
                              remove_comments=True,
                              remove_empty_space=True,
                              remove_all_empty_space=True,
                              reduce_boolean_attributes=True
                              )
        return minified_html_report
