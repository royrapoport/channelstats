#! /usr/bin/env python

import jinja2
import htmlmin

import config
import user

class Formatter(object):

    def __init__(self):
        self.jinja_environment = jinja2.Environment(loader=jinja2.FileSystemLoader("."))
        self.template = self.jinja_environment.get_template("general_report_template.html")
        self.user = user.User()

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

    def get_users(self, list_of_userids):
        """
        Given a list of userIDs, returns a dictionary indexed by userID
        where the value is another dictionary with
            'label': The actual label to show for the user ID
            'hover': The text to show when hovering over the label
            'url': The URL to link to for more information about the user
        """
        ret = {}
        for uid in list_of_userids:
            entry = self.user.get(uid)
            # print("entry: {}".format(entry))
            user = {}
            user['label'] = '@' + self.pick_name(entry)
            user['hover'] = entry['real_name']
            url = "https://{}.slack.com/team/{}"
            url = url.format(config.slack_name, uid)
            user['url'] = url
            ret[uid] = user
        return ret

    def format(self, report):

        # Get the canonical list of USER ids we might refer to.
        # That is all users who posted in all channels
        channels = report['channel_user'].keys()
        users = {} # We need a list, but this makes deduping easier
        for channel in channels:
            for user in report['channel_user'][channel]:
                users[user] = 1
        users = list(users.keys())
        user_info = self.get_users(users)
        report['user_info'] = user_info

        html_report = self.template.render(payload=report)
        minified_html_report = htmlmin.minify(html_report,
                              remove_comments=True,
                              remove_empty_space=True,
                              remove_all_empty_space=True,
                              reduce_boolean_attributes=True
                              )
        return minified_html_report
