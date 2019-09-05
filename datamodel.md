# channelstats data model

channelstats stores its data in DynamoDB tables (either local or in AWS).  Here
is their structure. and expected use.

Columns marked with (H) are Hash keys
Columns marked with (R) are Range keys (if present)

## Channel

## ChannelConfiguration

## Configuration

## FirstPost

## Message-yyyy-mm-dd

## ReportStore

## User

| column      | values |
| ----------- | -------- |
| **id** (H) |  Slack UID|
| **tz_offset** | TZ offset in seconds (e.g. `-14400`)
| **insert_timestamp** | timestamp when we inserted user for the first time |
| **user_name**  | 'name' field from Slack user structure |
| **tz**  |  Name of user's timezone |
| **real_name**  |  `real_name` field from Slack user structure |
| **display_name**  | `display_name` field from `profile` of Slack user structure |
| **deleted** | true/false |

We store both tz and
tz_offset because tz_offset is useful for calculations of when a message was
posted, and tz is useful for categorizing messages by timezone and having a nice
label.  If we were concerned about space more than reads, we could normalize
this information.

`insert_timestamp` should never be updated, and should always reflect the first
time we inserted the user.  Ideally, at some point we'll move insert_timestamp
to a different table.

## UserHash

| column      | values |
| ----------- | -------- |
| **key** (H) | UID Hash |
| **uids**    | UID UID UID UID ... UID |

The UID Hash is the result of a simplistic hash function (see userhash.UserHash.make_key()) which currently simply returns the last character in the UID.  

UIDs are about 10 chars; we store them as
```
 k: UID UID UID
```
item (row) sizes in DDB must not be over 400K, which means no more than 400,000
chars.  At approx 15chars per UID, and not wanting to exceed about 300K, that
gives us about 20,000 UIDs per row Using the last char in the UID turns out to
give us a pretty good distribution -- and with 35 possible values, gives us up
to about 700K users.

This table allows us to quickly ascertain whether we already know about a user before deciding whether to simply upload the user or modify it.  By using this hash approach, we can do one DB get() per approximately 20K userIDs (or at most, we'll end up with ~35 DB gets) rather than one per userID.  

**uids** is a text field with UIDs separated by spaces.
