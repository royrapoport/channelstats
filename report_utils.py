#! /usr/bin/env python

import user
import utils
import channel

u = user.User()
c = channel.Channel()

def override(o):
    """
    Assume that o is #channelname or @username
    Return CHANNELID or USERID
    """

    if o[0] == '@':
        token_type = "user"
    elif o[0] == '#':
        token_type = 'channel'
    else:
        raise RuntimeError("Only tokens starting with # or @ make sense to me")

    if token_type == "user":
        match = uid_for(o)
        if match:
            return match
        else:
            raise RuntimeError("Couldn't find a UID for @{}".format(o))
    else:
        o = o[1:]
        match = c.get(o)
        if match:
            return match['slack_cid']
        else:
            raise RuntimeError("Couldn't find a CID for #{}".format(o))

def uid_for(token):
    """
    token is either a username or a UID.  If UID, make sure it's valid
    If username, try to find a match and return the match's uid
    """
    uid = token.upper()
    if u.get(uid):
        return uid

    if token[0] != '@':
        raise RuntimeError("Usernames must start with '@'")

    matches = u.find(token)
    if len(matches) == 0:
        raise RuntimeError("Could not find a user with name '{}'".format(token))
    if len(matches) > 1:
        raise RuntimeError("Found too many matches for user {}: {}".format(token, json.dumps(matches, indent=4)))
    uid = matches[0]['slack_uid']
    return uid

def cid_for(token):
    """
    token is either a username or a UID.  If UID, make sure it's valid
    If username, try to find a match and return the match's cid
    """
    cid = token.upper()
    entry = c.get(cid)
    if entry:
        return entry['slack_cid']

    if token[0] != '#':
        raise RuntimeError("Channel names must start with '#'")

    token = token[1:]
    entry = c.get(token)
    if entry:
        return entry['slack_cid']
    raise RuntimeError("Could not find a channel with name '{}'".format(token))
