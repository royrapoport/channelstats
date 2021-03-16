#! /usr/bin/env python2.7

import json
import sys
import time

import requests


class Slacker(object):

    CONVERSATIONS_LIST_TYPES = ['public_channel', 'private_channel', 'mpim', 'im']

    def __init__(self, slack, token):

        self.slack = slack
        self.token = token
        self.api_calls = 0
        self.api_wait = 0

    def conditional_set_topic(self, cid, topic, leave=False):
        """
        Set the topic for cid it it's not already the expected topic
        If leave is True, leaves the channel after setting topic
        """
        current_topic = self.get_topic(cid)
        if current_topic != topic:
            self.set_topic(cid, topic, leave=leave)

    def unarchive_channel(self, cid):
        response = self.api_call("conversations.unarchive?channel={}".format(cid), method=requests.post)
        return response

    def leave_channel(self, cid):
        response = self.api_call("conversations.leave?channel={}".format(cid), method=requests.post)
        return response

    def join_channel(self, cid):
        response = self.api_call("conversations.join?channel={}".format(cid), method=requests.post)
        return response

    def get_users_for_channel(self, cid):
        response = self.paginated_lister("conversations.members?channel={}".format(cid))
        return response

    def invite(self, cid, list_of_uids):
        """
        Invites the list of UIDs into the channel
        """
        uid_string = ",".join(list_of_uids)
        j = {'channel': cid, 'users': uid_string}
        ret = self.api_call(api_endpoint="conversations.invite", method=requests.post, json=j, header_for_token=True)
        return ret

    def get_topic(self, cid):
        response = self.api_call("conversations.info?channel={}".format(cid))
        return response.get("channel", {}).get("topic", {}).get("value")

    def set_topic(self, cid, topic, leave=False):
        """
        Sets topic on the channel.  Because we can only do that if we are in the
        channel, automatically joins the channel before doing so.
        If leave is True, leaves channel after setting topic
        """
        self.join_channel(cid)
        j = {'channel': cid, 'topic': topic}
        ret = self.api_call(api_endpoint="conversations.setTopic",
                            method=requests.post, json=j, header_for_token=True)
        if leave:
            self.leave_channel(cid)
        return ret

    def set_purpose(self, cid, topic):
        j = {'channel': cid, 'topic': topic}
        return self.api_call(api_endpoint="conversations.setPurpose",
                             method=requests.post, json=j, header_for_token=True)

    def delete(self, channel, ts):
        api_endpoint = "chat.delete?channel={}&ts={}".format(channel, ts)
        return self.api_call(api_endpoint, method=requests.post)

    def get_users_for_channel(self, cid):
        response = self.paginated_lister("conversations.members?channel={}".format(cid))
        return response

    def get_thread_responses(self, cid, thread_ts):
        messages = self.paginated_lister(
            "conversations.replies?channel={}&ts={}".format(
                cid, thread_ts))
        return messages

    def get_messages(self, cid, ts, callback=None):
        ts = int(float(ts))
        return self.paginated_lister(
            "conversations.history?channel={}&oldest={}".format(
                cid, ts), callback=callback)

    def get_all_users(self):
        return self.paginated_lister("users.list")

    def get_all_channels(self, types=[]):
        if len(types) == 0:
            # Always default to public channels only
            types = ['public_channel']
        elif type(types) is list:
            if any([conversation_type for conversation_type in types
                    if conversation_type not in self.CONVERSATIONS_LIST_TYPES]):
                raise ValueError('Invalid conversation type')
        types_param = ','.join(types)

        channels = self.paginated_lister(
            "conversations.list?types={types}".format(types=types_param))

        channels.sort(key=lambda x: x['id'])
        if 'private_channel' in types:
            channels_to_iterate = channels
            for index, channel in enumerate(channels_to_iterate):
                is_group = channel.get('is_group', False)
                is_private = channel.get('is_private', False)
                if is_group and is_private:
                    endpoint = 'conversations.info?channel={}&include_num_members=true'
                    channels[index] = self.api_call(
                        api_endpoint=endpoint.format(channel.get('id'))
                    ).get('channel', channel)

        return channels

    def get_all_channel_ids(self):
        channels = self.get_all_channels()
        return [x['id'] for x in channels]

    def report(self):
        print(
            "{} API calls performed in {} seconds".format(
                self.api_calls,
                self.api_wait))

    @staticmethod
    def discover_element_name(response):
        """
        Figure out which part of the response from a paginated lister is the list of elements
        the logic is pretty simple -- in the dict response, find the one key that has a list value
        or raise an error if more than one exists
        """
        lists = [k for k in response if isinstance(response[k], list)]
        if len(lists) == 0:
            print("Response was {}".format(json.dumps(response, indent=4)))
            raise RuntimeError("No list of objects found")
        if len(lists) > 1:
            raise RuntimeError(
                "Multiple response objects corresponding to lists found: {}".format(lists))
        return lists[0]

    def paginated_lister(self, api_call, limit=200, callback=None):
        """
        if callback is defined, we'll call that method on each element we retrieve
        and not keep track of the total set of elements we retrieve.  That way, we can
        get an arbitrary large set of elements without running out of memory
        In that case, we'll only return the latest set of results
        """
        element_name = None
        start = time.time()
        done = False
        cursor = None
        results = []
        separator = self.use_separator(api_call)
        api_call = api_call + separator + "limit={}".format(limit)
        while not done:
            interim_api_call = api_call
            if cursor:
                interim_api_call += "&cursor={}".format(cursor)
            interim_results = self.api_call(interim_api_call)
            if not element_name:
                element_name = Slacker.discover_element_name(interim_results)
            if callback:
                for element in interim_results[element_name]:
                    callback(element)
                results = interim_results[element_name]
            else:
                results += interim_results[element_name]
            cursor = interim_results.get(
                "response_metadata", {}).get(
                "next_cursor", "")
            if not cursor:
                done = True
        end = time.time()
        diff = end - start
        # print "Loaded {} {} in {:.1f} seconds".format(len(results),
        # element_name, diff)
        return results

    def use_separator(self, url):
        """
        if url already has '?', use &; otherwise, use '?'
        """
        separator = "?"
        if '?' in url:
            separator = "&"
        return separator

    def retry_api_call(
            self,
            method,
            url,
            json,
            headers,
            delay=1,
            increment=2,
            max_delay=120):
        while True:
            try:
                start = time.time()
                payload = method(url, json=json, headers=headers)
                end = time.time()
                diff = end - start
                self.api_calls += 1
                self.api_wait += diff
                return payload
            except Exception:
                print(
                    "Failed to retrieve {} : {}.  Sleeping {} seconds".format(
                        url, Exception, delay))
                time.sleep(delay)
                if delay < max_delay:
                    delay += increment
                    # print "Incrementing delay to {}".format(delay)

    def api_call(
            self,
            api_endpoint,
            method=requests.get,
            json=None,
            header_for_token=False):
        url = "https://{}.slack.com/api/{}".format(self.slack, api_endpoint)
        headers = {}
        if header_for_token:
            headers['Authorization'] = "Bearer {}".format(self.token)
        else:
            separator = self.use_separator(url)
            url += "{}token={}".format(separator, self.token)
        # print("url: {}".format(url))
        if json:
            headers['Content-Type'] = "application/json"
        # print("url: {}".format(url))
        done = False
        while not done:
            response = self.retry_api_call(
                method, url, json=json, headers=headers)
            # print(response.status_code)
            if response.status_code == 200:
                done = True
            if response.status_code == 429:
                if 'Retry-After' in response:
                    retry_after = int(response['Retry-After']) + 1
                else:
                    retry_after = 5
                time.sleep(retry_after)
            if response.status_code == 403:
                raise Exception('API returning status code 403')
        payload = response.json()
        # print "json: {} headers: {}".format(json, headers)
        # print "status code: {} payload: {}".format(response.status_code,
        # payload)
        return payload
