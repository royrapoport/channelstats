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

| column      | values |
| ----------- | -------- |
| **report_id** (H) | unique ID of the report |
| **value**    | report text |
| **0 [ 1 ... N ]** |  report_id for chunk N|

Used to store generated reports so we don't need to re-generate them.

If the report size is smaller than 300K, we'll just store the report text in `value`.  

If the report size is larger than 300K, we'll chunk it up into 300K chunks.  Each will be given its own unique report_id and stored in its own row.  Then, the report ID for that chunk will be stored as the value of the particular index of that chunk.

So for example, if the report with report_id `foo` is "whatever" and chunk size is limited to 2, we'll break it into `wh`, `at`, `ev`, and `er`
(chunks 0, 1, 2, 3 in order).  `foo` will have 4 keys in addition to `report_id`: 0, 1, 2, 3.  Each key will have as its value another report_id -- e.g. 0:foo-0, 1:foo-1, etc.
Then report_id foo-0 will have an entry in the table whose `value` is `wh`


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
