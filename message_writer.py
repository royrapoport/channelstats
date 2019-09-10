#! /usr/bin/env python3

import json
import sys

import messagetablefactory
import utils


class MessageWriter(object):

    def __init__(self):
        self.MessageTableFactory = messagetablefactory.MessageTableFactory()
        seen = {}

    def write(self, list_of_messages, cid, parent_user_id=None):
        """
        Given the list of message JSONs, write them to DynamoDB
        cid is the Slack channel ID
        if parent_user_id is provided, this is the UID of the originator of the thread
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
            table_name = self.MessageTableFactory.get_message_table_name(
                timestamp)
            if table_name not in message_tables:
                message_tables[table_name] = self.MessageTableFactory.get_message_table(
                    timestamp)
                messages[table_name] = []
            messages[table_name].append(message)

        for table_name in messages:
            # print("Writing to message table {}".format(table_name))
            table = message_tables[table_name]
            with table.batch_writer() as batch:
                for message in messages[table_name]:
                    Row = self.make_row(message, cid, parent_user_id)
                    if not Row:
                        continue
                    batch.put_item(Row)

    def make_row(self, message, cid, parent_user_id):
        """
        create a Row dictionary for insertion into DynamoDB
        """
        timestamp = message['ts']
        try:
            user_id = message.get("user") or message.get("bot_id")
        except BaseException:
            print(
                "How the hell no user? {}".format(
                    json.dumps(
                        message,
                        indent=4)))
            return None
        word_count = len(message['text'].split())
        mentions = utils.find_user_mentions(message['text'])
        mentions = [x for x in mentions if x != user_id]
        (reaction_count, reactions) = self.get_reactions(message)
        (reply_count, replies) = self.get_replies(message)
        files = json.dumps(message.get("files", None))
        thread_ts = message.get("thread_ts")
        is_threadhead = thread_ts == timestamp
        is_threaded = 'thread_ts' in message
        if files == 'null':
            files = None
        Row = {
            "is_threaded": is_threaded,
            "is_thread_head": is_threadhead,
            "ts": timestamp,
            "thread_ts": thread_ts,
            "slack_cid": cid,
            "user_id": user_id,
            "word_count": word_count,
            "reaction_count": reaction_count,
            "reactions": reactions,
            "replies": replies,
            "reply_count": reply_count,
            "files": files
        }
        Row['subtype'] = message.get("subtype")
        if parent_user_id:
            Row['parent_user_id'] = parent_user_id
        if mentions:
            Row['mentions'] = ":".join(mentions)
        else:  # if it's a thread head, we want to capture that
            if message.get("thread_ts") == message.get("ts"):
                Row['parent_user_id'] = user_id
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
