#! /usr/bin/env python

import slack_global_report


class SlackBriefGlobalReport(slack_global_report.SlackGlobalReport):

    def __init__(self):
        super(SlackBriefGlobalReport, self).__init__()
        self.top = 10

    def detailed_format_channel(*args):
        """
        Provides some details for a user's volume line.
        Or would, if this was not a brief report.
        """
        return "\n"

    def detailed_format_user(*args):
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
