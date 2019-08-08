#! /usr/bin/env python3

import time

import slack_token
import slacker
import user

class UserDownloader(object):

    def __init__(self, sname, stoken):
        self.user = user.User()
        self.slack = slacker.Slacker(sname, stoken)

    def download(self):
        users = self.slack.get_all_users()
        self.user.batch_upload(users)

if __name__ == "__main__":
    user_downloader = UserDownloader("rands-leadership", slack_token.token)
    user_downloader.download()
