#! /usr/bin/env python3

import csv
import datetime
import sys
import time

import user_created

# Reads a CSV created via the export function in the /stats
# page for a Slack.  Make sure to modify columns to include
# user ID and creation date

uc = user_created.UserCreated()
uc.load()


def process(member):
    assert "User ID" in member
    assert "Account created" in member
    slack_uid = member['User ID']
    creation_date = member['Account created']
    print("Processing {}/{}".format(slack_uid, creation_date))
    # creation_date is of the form Nov 3, 2017
    ts = time.mktime(time.strptime(creation_date, "%b %d, %Y"))
    uc.set(slack_uid, ts)


assert len(sys.argv) == 2, "Usage: {} CSVFILE".format(sys.argv[0])
fobj = open(sys.argv[1], newline='')
csvreader = csv.DictReader(fobj)
start = time.time()
ctr = 0
for member in csvreader:
    ctr += 1
    process(member)
end = time.time()
diff = end - start
print("Processed {} members in {:.1f} seconds".format(ctr, diff))
uc.save()
