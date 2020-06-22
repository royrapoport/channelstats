#! /usr/bin/env python

import random_name
import user
import slack_token

import user_downloader


def make_username(name):
    first, last = name.split()
    return "{}{}".format(first[0].lower(), last.lower())


rn = random_name.RandomName()
ud = user_downloader.UserDownloader("rands-leadership", slack_token.token)
users = ud.slack.get_all_users()
# print("I have {} users".format(len(users)))
for u in users:
    name = rn.name()
    uname = make_username(name)
    if u['name'] == uname:
        raise RuntimeError("NAME COLLISION? WHAT THE HECK")
    u['name'] = uname
    u['real_name'] = name
    if 'profile' not in u:
        u['profile'] = {}
    u['profile']['display_name'] = uname
    u['profile']['display_name_normalized'] = uname
    u['profile']['real_name'] = name
    u['profile']['real_name_normalized'] = name

# print("Now I have {} users".format(len(users)))
# roy = "U06NSQT34"
# print("Roy: {}".format([x for x in users if x['id'] == roy]))


fake_user = user.User(fake=True)
fake_user.batch_upload(users)
