#! /usr/bin/env python2.7

# What region do we use DDB in?
region = "us-west-2"
# What's the Slack name? Used for creating URLs
slack_name = "rands-leadership"
# Use DDB in local mode?
local = True
# How far back are we willing to go for old messages
max_age = 60
# What prefix, should we give DDB table names? This makes it easy to
# have multiple channelstats instances using the same DDB environment, each
# with its own namespace
prefix = "channelstats"
# By default, refetch this many days
refetch = 7
# What channels should we upload weekly reports to?
report_channel = "zmeta-statistics"
