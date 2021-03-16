# channelstats data model

channelstats stores its data in DynamoDB tables (either local or in AWS).  Here
is their structure and expected use.

Columns marked with (H) are Hash keys
Columns marked with (R) are Range keys (if present)

Learn more about Hash and Range keys [here](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.CoreComponents.html).


## Channel

| column      | values |
| ----------- | -------- |
| **channel_key** (H) | Slack Channel ID or friendly name of channel |
| **friendly_name**  | Friendly name of the channel |
| **slack_cid**  | Slack Channel ID |
| **members** | int number of members |
| **is_channel** | Boolean, whether channel is a public channel |
| **is_im** | Boolean, whether channel is an IM/DM |
| **is_group** | Boolean, whether channel is a group (AKA private channel) |
| **is_mpim** | Boolean, whether channel is an MPIM/MPDM (DM with multiple people) |
| **created** | int timestamp of channel creation |

Keeps tracks of the channels we have. Of particular note is the fact we end up with two rows per channel -- one is
indexed by the Slack channel ID, and the other is indexed by the friendly name.

Column `members` may be 0 and will be for archived channels.


## ChannelConfiguration

| column      | values |
| ----------- | -------- |
| **slack_cid** (H) | Slack Channel ID |
| **last_message_timestamp**  | The int timestamp of the last message we retrieved from the channel |

Used to keep track of where in channel history we are to know where we need to start grabbing messages (or, if config.refetch is defined, then we go `config.refetch` days back from `last_message_timestamp`)

## Configuration

| column      | values |
| ----------- | -------- |
| **key** (H) | Some key |
| **SOMEVALUE**  | Some Value |

General-purpose configuration table to keep track of bits and pieces we want to remember (e.g. last time we ran).  

Of interest is the `counts` key, whose value is a set of K:V columns for various K
we care about (e.g. `active_users`, `all_users`, etc)

## FirstPost

| column      | values |
| ----------- | -------- |
| **slack_uid** (H) | Slack User ID |
| **slack_cid**  | Channel ID of the message |
| **message_id**  | str Message ID |
| **ts** | int timestamp of the message |

This table stores a pointer to a user's first message on the Slack.  

Some entries in this table only have a channel and a key, both pointing to the same
Channel ID, and a ts which is 0 (so no message_id, and no reference to a user).  
I'm not at this point clear why these entries exist.


## Message

| column      | values |
| ----------- | -------- |
| **cid_ts** (H) | combination of slack_cid and ts of the message |
| **date** | date of message in yyyy-mm-dd |
| **ts** | timestamp of the message |
| **slack_cid**  | Channel ID of the message |
| **word_count** | int number of words in the message |
| **slack_uid** | | Slack UID of the author of the message |
| **mentions** | UID:UID:UID of mentioned users in message text |
| **reactions** | emoji:UID:UID:UID,emoji:UID:UID |
| **reaction_count** | int number of reactions to the message |
| **thread_ts** | If part of a thread, the thread timestamp |
| **parent_user_id** | If part of a thread, the thread's author |
| **replies** | UID:TS,UID:TS,UID:TS |
| **reply_count** | int number of replies to the message |
| **subtype** | If the message has a subtype, this is the subtype |
| **files** | json.dumps() of files structure from message |
| **is_threadhead** | this message starts a thread |
| **is_threaded** | this message is part of a thread |

For `replies`, we keep the replies as pairs of UID:TS (UID of the author of the reply, timestamp of the reply),
joined by a ','.  Replies are guaranteed to be in the same channel (of course), so the combination of this
message's channel and the reply's TS gives a unique message.

A message's `parent_user_id` may by the same as the message's `user_id` (either because this is the
originating message in the thread or because the author of the thread replies in it).
The message is the head of the thread if the `thread_timestamp` is identical to the
`timestamp`.

## ItemStore

| column      | values |
| ----------- | -------- |
| **item_id** (H) | unique ID of the item |
| **value**    | item text |
| **0 [ 1 ... N ]** |  item_id for chunk N|

Used to store (potentially large) items.  Used for reports (so we don't have to re-generate them) and channel membership records.

If the item size is smaller than 300K, we'll just store the item text in `value`.  

If the item size is larger than 300K, we'll chunk it up into 300K chunks.
Each will be given its own unique item_id and stored in its own row.
Then, the item ID for that chunk will be stored as the value of the particular
index of that chunk.

So for example, if the item with item_id `foo` is "whatever" and chunk size is limited to 2, we'll break it into `wh`, `at`, `ev`, and `er`
(chunks 0, 1, 2, 3 in order).  `foo` will have 4 keys in addition to `item_id`: 0, 1, 2, 3.  Each key will have as its value another item_id -- e.g. 0:foo-0, 1:foo-1, etc.
Then item_id foo-0 will have an entry in the table whose `value` is `wh`.

## ReportStore

| column      | values |
| ----------- | -------- |
| **report_id** (H) | unique ID of the report |
| **value**    | report text |
| **0 [ 1 ... N ]** |  report_id for chunk N|

Used to store generated reports so we don't need to re-generate them.

If the report size is smaller than 300K, we'll just store the report text in `value`.  

If the report size is larger than 300K, we'll chunk it up into 300K chunks.
Each will be given its own unique report_id and stored in its own row.
Then, the report ID for that chunk will be stored as the value of the particular
index of that chunk.

So for example, if the report with report_id `foo` is "whatever" and chunk size is limited to 2, we'll break it into `wh`, `at`, `ev`, and `er`
(chunks 0, 1, 2, 3 in order).  `foo` will have 4 keys in addition to `report_id`: 0, 1, 2, 3.  Each key will have as its value another report_id -- e.g. 0:foo-0, 1:foo-1, etc.
Then report_id foo-0 will have an entry in the table whose `value` is `wh`.


## User

| column      | values |
| ----------- | -------- |
| **slack_uid** (H) |  Slack UID|
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
| **user_key** (H) | UID Hash |
| **uids**    | UID UID UID UID ... UID |

The UID Hash is the result of a simplistic hash function (see userhash.UserHash.make_key()) which currently
returns the last character in the UID.  

UIDs are about 10 chars; we store them as
```
 k: UID UID UID
```
item (row) sizes in DDB must not be over 400K, which means no more than 400,000
chars.  At approx 15chars per UID, and not wanting to exceed about 300K, that
gives us about 20,000 UIDs per row Using the last char in the UID turns out to
give us a pretty good distribution -- and with 35 possible values, gives us up
to about 700K users.

This table allows us to quickly ascertain whether we already know about a user before
deciding whether to simply upload the user or modify it.  By using this hash approach,
we can do one DB get() per approximately 20K userIDs (or at most, we'll end up with ~35
DB gets) rather than one per userID.  

**uids** is a text field with UIDs separated by spaces.
