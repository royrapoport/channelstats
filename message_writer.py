#! /usr/bin/env python3

import json
import sys

import messagetablefactory
import utils

class MessageWriter(object):

    def __init__(self):
        self.MessageTableFactory = messagetablefactory.MessageTableFactory()
        seen = {}

    def write(self, list_of_messages, cid, thread_author_uid=None):
        """
        Given the list of message JSONs, write them to DynamoDB
        cid is the Slack channel ID
        if thread_author_uid is provided, this is the UID of the originator of the thread
        of which this message is a part
        """
        # Map message table name to actual message table objects
        message_tables = {}
        # Map message table names to list of messages
        messages = {}

        for message in list_of_messages:
            if message.get("type") != "message":
                continue
            timestamp = message['ts']
            table_name = self.MessageTableFactory.get_message_table_name(timestamp)
            if table_name not in message_tables:
                message_tables[table_name] = self.MessageTableFactory.get_message_table(timestamp)
                messages[table_name] = []
            messages[table_name].append(message)

        for table_name in messages:
            # print("Writing to message table {}".format(table_name))
            table = message_tables[table_name]
            with table.batch_writer() as batch:
                for message in messages[table_name]:
                    Row = self.make_row(message, cid, thread_author_uid)
                    if not Row:
                        continue
                    batch.put_item(Row)

    def make_row(self, message, cid, thread_author_uid):
        """
        create a Row dictionary for insertion into DynamoDB
        """
        timestamp = message['ts']
        try:
            user_id = message['user']
        except:
            print("How the hell no user? {}".format(json.dumps(message, indent=4)))
            return None
        wordcount = len(message['text'].split())
        mentions = utils.find_user_mentions(message['text'])
        (reaction_count, reactions) = self.get_reactions(message)
        (reply_count, replies) = self.get_replies(message)
        files = json.dumps(message.get("files", None))
        thread_ts = message.get("thread_ts")
        if files == 'null':
            files = None
        Row = {
            "timestamp": timestamp,
            "thread_timestamp": thread_ts,
            "slack_cid": cid,
            "user_id": user_id,
            "wordcount": wordcount,
            "reaction_count": reaction_count,
            "reactions": reactions,
            "replies": replies,
            "reply_count": reply_count,
            "files": files
        }
        if thread_author_uid:
            Row['thread_author'] = thread_author_uid
        if mentions:
            Row['mentions'] = ":".join(mentions)
        else: # if it's a thread head, we want to capture that
            if message.get("thread_ts") == message.get("ts"):
                Row['thread_author'] = user_id
        Row = utils.prune_empty(Row)
        return Row

    def get_replies(self, message):
        """
        Given a message, return (reply_count, replies)
        where reply_count is the number of replies and
        replies is str of the form "UID:TS,UID:TS"
        If no replies, returns (0,"")
        """
        reply_count = 0
        replies = []
        for reply in message.get("replies", []):
            reply_count += 1
            reply_string = "{}:{}".format(reply['user'], reply['ts'])
            replies.append(reply_string)
        # Fun fact: DynamoDB does not allow empty strings in attributevalues.
        # So if we can't find any replies, we'll insert the string 'none'
        # (This is lame)
        if replies:
            replies = ",".join(replies)
        else:
            replies = None
        return (reply_count, replies)

    def get_reactions(self, message):
        """
        given a message, return (COUNT_OF_REACTIONS, REACTIONS)
        where COUNT_OF_REACTIONS is the total number of reactions and
        REACTIONS is of the form REACTION_TYPE:UID:UID,REACTION_TYPE:UID:UID, etc
        if no reactions, return (0, "")
        """
        count = 0
        reactions = []
        for reaction in message.get("reactions", []):
            reaction_name = reaction['name']
            users = ":".join(reaction['users'])
            count += len(reaction['users'])
            reaction_text = "{}:{}".format(reaction_name, users)
            reactions.append(reaction_text)
        if reactions:
            reactions = ",".join(reactions)
        else:
            reactions = None
        return (count, reactions)
