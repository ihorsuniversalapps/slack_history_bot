#!/usr/bin/env python

import datetime
import os
import time

from pymongo import MongoClient
from slackclient import SlackClient

BOT_NAME = 'historybot'
BOT_ID = '--'

# slack_client = SlackClient(os.environ.get('HISTORY_SLACK_BOT_KEY'))
slack_client = SlackClient('xoxb-70176096084-POycIyI9iEP3WHGwPpc8FKZf')
mongo_client = MongoClient()
db = mongo_client.slack_history_db
history_collection = db.history
channels_collections = db.channels
users_collection = db.users

COMMAND_START = "start"
COMMAND_STOP = "stop"
COMMAND_GET = "get"
COMMAND_SIZE = "size"
COMMAND_HELP = "help"
COMMAND_CLEAR = "clear"


def get_bot_name():
    return "<@" + BOT_ID + ">"


def post_message(channel, response):
    slack_client.api_call("chat.postMessage", channel=channel, text=response, as_user=True)


def handle_command(command, channel):
    print command, channel
    if command.startswith(COMMAND_START):
        channel_obj = {'channel_id': channel}
        channel_id = channels_collections.find_one(channel_obj)
        if channel_id:
            post_message(channel, "The channel is already on listening.")
        else:
            channels_collections.insert_one(channel_obj)
            post_message(channel, "The channel listening has been started.")
    elif command.startswith(COMMAND_STOP):
        channel_obj = {'channel_id': channel}
        channel_id = channels_collections.find_one(channel_obj)
        if channel_id:
            channels_collections.delete_one(channel_obj)
            post_message(channel, "The channel listening has been stopped.")
        else:
            post_message(channel, "The channel is not on listening.")
    elif command.startswith(COMMAND_SIZE):
        history = history_collection.find({'channel': channel})
        if history and history.count() > 0:
            post_message(channel, "I can remember {} messages.".format(history.count()))
        else:
            post_message(channel, "I can't remember anything.")
    elif command.startswith(COMMAND_CLEAR):
        history_collection.delete_many({'channel': channel})
        post_message(channel, "I have forgotten everything.")
    elif command.startswith(COMMAND_GET):
        history = history_collection.find({'channel': channel})
        users_col = users_collection.find()
        messages = ""

        users_normalized = {}
        for usr in users_col:
            users_normalized[usr['id']] = usr

        for record in history:
            print record
            messages += u"{}   {}: {}\n".format(
                datetime.datetime.fromtimestamp(float(record['ts'])),
                users_normalized[record['user']]['profile']['real_name_normalized'],
                record['text']
            )
        try:
            print slack_client.api_call("files.upload", channels=channel, filename='history.txt', file=messages)
        except Exception as e:
            print e
    elif command.startswith(COMMAND_HELP):
        message = """
        I can do next things:
        * help - Show this text
        * start - Start recording history for this channel/private group
        * stop - Stop recording history
        * size - Show amount of stored messages
        * clear - Clear history
        * get - Return all stored messages
        """
        post_message(channel, message)
    else:
        post_message(channel, "Not sure what you mean. Use help.")


def parse_slack_output(slack_rtm_output):
    output_list = slack_rtm_output
    if output_list and len(output_list) > 0:
        for output in output_list:
            if output and 'text' in output and get_bot_name() in output['text']:
                return output['text'].split(get_bot_name())[1].strip().lower(), output['channel']
            elif output and 'text' in output:
                channel_obj = {'channel_id': output['channel']}
                channel_id = channels_collections.find_one(channel_obj)
                if channel_id:
                    if output['user'] != BOT_ID:
                        history_collection.insert_one(output)
                    else:
                        print "Bot message"
    return None, None


if __name__ == "__main__":
    api_call = slack_client.api_call("users.list")
    if api_call.get('ok'):
        users = api_call.get('members')
        for user in users:
            print user
            is_user = users_collection.find_one({'id': user.get('id')})
            if not is_user:
                users_collection.insert_one(user)
            if 'name' in user and user.get('name') == BOT_NAME:
                print("Bot ID for '" + user['name'] + "' is " + user.get('id'))
                BOT_ID = user.get('id')
    else:
        print("could not find bot user with the name " + BOT_NAME)
        exit()

    READ_WEBSOCKET_DELAY = 1

    run = True
    while run:
        try:
            if slack_client.rtm_connect():
                print("HistoryBot connected and running!")
                while True:
                    command, channel = parse_slack_output(slack_client.rtm_read())
                    if command and channel:
                        handle_command(command.lower(), channel)
                    time.sleep(READ_WEBSOCKET_DELAY)
            else:
                print("Connection failed. Invalid Slack token or bot ID?")
        except Exception as e:
            print e.message
        except KeyboardInterrupt:
            run = False
