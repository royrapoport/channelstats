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

    def set_topic(self, cid, topic):
        j = {'channel': cid, 'topic': topic}
        return self.api_call(api_endpoint="conversations.setTopic", method=requests.post, json=j, header_for_token=True)

    def set_purpose(self, cid, topic):
        j = {'channel': cid, 'topic': topic}
        return self.api_call(api_endpoint="conversations.setPurpose", method=requests.post, json=j, header_for_token=True)

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
        # print("Getting messages from {} starting {}".format(cid, time.asctime(time.localtime(int(ts)))))
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

        channels.sort(key = lambda x: x['id'])
        if 'private_channel' in types:
            channels_to_iterate = channels
            for index, channel in enumerate(channels_to_iterate):
                is_group = channel.get('is_group', False)
                is_private = channel.get('is_private', False)
                if is_group and is_private:
                    channels[index] = self.api_call(
                        api_endpoint='conversations.info?channel={}&include_num_members=true'.format(
                            channel.get('id'))
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
