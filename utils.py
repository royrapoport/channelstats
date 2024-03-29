#! /usr/bin/env python2.7

import collections
import decimal
import json
import re
import time

import config

# Helper class to convert a DynamoDB item to JSON.


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            if abs(o) % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)


def save_json(j, fname):
    s = dumps(j)
    save(s, fname)


def dumps(j, indent=4):
    """
    json.dumps(j), but deal with Decimal encoding
    """
    return json.dumps(j, indent=indent, cls=DecimalEncoder)


def dump(j):
    """
    json.dump(j), but deal with Decimal encoding
    """
    j = dumps(j)
    return json.loads(j)


def prune_empty(row):
    """
    prune attributes whose value is None
    """
    new_row = {}
    for k in row:
        if row[k] or row[k] == 0:
            new_row[k] = row[k]
    return new_row


def chunks(my_list, n):
    n = max(1, n)
    return (my_list[i:i + n] for i in range(0, len(my_list), n))


def make_ordered_dict(d):
    """
    Turn a {k:v} dictionary into an ordered dictionary ordered from largest
    v to smallest
    """
    k = list(d.keys())
    k.sort(key=lambda x: d[x])
    k.reverse()
    nd = collections.OrderedDict()
    for i in k:
        nd[i] = d[i]
    return nd


def find_user_mentions(text):
    """
    Given message text, returns what users are mentioned
    (may be empty list)
    """
    # text is of the form "whatever <@UID> and also ..."
    return [x[2:-1] for x in re.findall("<@U[A-Z0-9]+>", text)]


def rank(n):
    tenremainder = n % 10
    hundredremainder = n % 100
    suffix = "th"
    if (tenremainder == 1 and hundredremainder != 11):
        suffix = "st"
    if (tenremainder == 2 and hundredremainder != 12):
        suffix = "nd"
    if (tenremainder == 3 and hundredremainder != 13):
        suffix = "rd"
    return "{}{}".format(n, suffix)

def rank(n):
    r = {0: 'th', 1: 'st', 2: 'nd', 3: 'rd'}
    if n in r:
        return "{}{}".format(n, r[n])
    return "{}th".format(n)


def valid_cid(cid):
    return re.match("^C[A-Z0-9]+$", cid)


def valid_uid(uid):
    return re.match("^U[A-Z0-9]+$", uid)


def make_day(ts):
    """
    Given a str ts, return yyyy-mm-dd
    """
    lt = time.localtime(int(float(ts)))
    return time.strftime("%Y-%m-%d", lt)


def today():
    lt = time.localtime(time.time())
    return time.strftime("%Y-%m-%d", lt)


def save(blob, fname):
    if type(blob) == str:
        f = open(fname, "w")
    else:
        f = open(fname, "wb")
    f.write(blob)
    f.close()


def make_url(cid, ts, tts=None):
    """
    Return a URL for the message specified
    if tts (thread_ts) is specified, return a URL which includes the thread_ts
    """
    new_ts = ts.replace(".", "")
    url = "https://{}.slack.com/archives/{}/p{}".format(config.slack_name, cid, new_ts)
    if tts:
        url += "?thread_ts={}&cid={}".format(tts, cid)
    return url
