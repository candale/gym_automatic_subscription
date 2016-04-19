import re
import time
import datetime
import traceback
import sys
from subprocess import Popen, PIPE, STDOUT

from slackclient import SlackClient

import settings
from commands import create_from_storage, get_active_schedules


sc = SlackClient(settings.SLACK_TOKEN)


def raise_if_not_ok(response):
    if 'ok' in response and response['ok'] is False:
        raise ValueError('Something went wrong {}'.format(response))


def get_user_id_by_email(email):
    def email_filter(user):
        return 'email' in user['profile'] and user['profile']['email'] == email

    users_response = sc.api_call('users.list')
    raise_if_not_ok(users_response)

    users = users_response['members']

    user = filter(email_filter, users)

    if not user:
        raise ValueError('No user for email {}'.format(email))

    return user[0]['id']


def get_user_id_by_name(name):
    users_response = sc.api_call('users.list')
    raise_if_not_ok(users_response)

    users = users_response['members']

    user = filter(lambda user: user['name'] == name, users)

    if not user:
        raise ValueError('No user for email {}'.format(name))

    return user[0]['id']


def get_email_by_user_id(user_id):
    users_response = sc.api_call('users.list')
    raise_if_not_ok(users_response)

    users = users_response['members']

    user = filter(lambda user: user['id'] == user_id, users)

    if not user:
        raise ValueError('No user for email {}'.format(user_id))

    return user[0]['profile']['email']


def get_chat_with_user(user_id):
    chat_response = sc.api_call('im.open', user=user_id)
    raise_if_not_ok(chat_response)

    return chat_response['channel']['id']


def normalize_message(message):
    # TODO: make this safer
    # The mail is sent in this format
    # "<mailto:email_addres@doamin.com:email_addres@doamin.com>"
    msg = re.sub('<mailto:([^|]+)\|[^>]+>', r'\1', message)

    # A small precaution for chained commands or piped or stuff like that
    msg = msg.replace(';', '')
    msg = msg.replace('|', '')
    msg = msg.replace('&', '')

    return msg


def process_message(message):
    if message['type'] != 'message':
        return

    cmd = 'gym_sub {}'.format(normalize_message(message['text']))

    p = Popen(cmd, shell=True, close_fds=True, stdin=PIPE,
              stdout=PIPE, stderr=STDOUT)
    output = p.stdout.read()
    sc.api_call(
        'chat.postMessage', channel=message['channel'], text=output,
        as_user=True)


_BOT_NAME = 'schedule_keeper'
_BOT_ID = get_user_id_by_name(_BOT_NAME)

_STORAGE_LAST_TIME_CHECKED = None
_SHOW_ACTIVITIES_LAST_TIME_CHECKED = None
# In minutes
_STORAGE_CHECK_INTERVAL = 30
_SHOW_SCHEDULES_AVTIVITIES_INTERVAL = 300


def run_storage():
    global _STORAGE_LAST_TIME_CHECKED

    delta = datetime.timedelta(minutes=_STORAGE_CHECK_INTERVAL)
    now = datetime.datetime.now()
    if (_STORAGE_LAST_TIME_CHECKED is not None and now - _STORAGE_LAST_TIME_CHECKED < delta):
        return

    _STORAGE_LAST_TIME_CHECKED = datetime.datetime.now()

    activities = create_from_storage()

    for activity in activities:
        user_id = get_user_id_by_email(activity['email'])
        channel = get_chat_with_user(user_id)

        if activity.get('error'):
            sc.api_call(
                'chat.postMessage', channel=channel, text=activity['error'],
                as_user=True)
            continue

        text = 'Scheduled you for {} on {} at {}:{}'.format(
            activity['activity'], activity['date'], *activity['time'])
        sc.api_call(
            'chat.postMessage', channel=channel, text=text, as_user=True)


def run_show_schedules_activities():
    global _SHOW_ACTIVITIES_LAST_TIME_CHECKED

    delta = datetime.timedelta(minutes=_SHOW_SCHEDULES_AVTIVITIES_INTERVAL)
    now = datetime.datetime.now()
    if (_SHOW_ACTIVITIES_LAST_TIME_CHECKED is not None and
            now - _SHOW_ACTIVITIES_LAST_TIME_CHECKED < delta):
        return

    _SHOW_ACTIVITIES_LAST_TIME_CHECKED = datetime.datetime.now()

    schedules = get_active_schedules(settings.EMAIL)

    texts = [
        'Active schedule for {} on {} at {}:{}'.format(
            schedule['activity'], schedule['date'], *schedule['time'])
        for schedule in schedules
    ]
    text = '\n'.join(texts)
    text = 'Reminder of active schedules: \n\n' + text

    user_id = get_user_id_by_email(settings.EMAIL)
    channel = get_chat_with_user(user_id)

    sc.api_call(
        'chat.postMessage', channel=channel, text=text, as_user=True)


def do_stuff():
    run_storage()
    run_show_schedules_activities()


def message_checks_out(message):
    return bool(
        message and
        message['type'] == 'message' and
        'user' in message and
        message['user'] != _BOT_ID
    )


def run():
    if sc.rtm_connect() is False:
        raise ValueError('Could not connect')

    while True:
        messages = sc.rtm_read()
        # Currently we only take a single message
        message = messages[0] if messages else None

        if message_checks_out(message):
            process_message(message)

        do_stuff()

        time.sleep(1)


def entry_point():
    try:
        run()
    except Exception, e:
        user_id = get_user_id_by_email(settings.EMAIL)
        channel = get_chat_with_user(user_id)

        exc_type, exc_value, exc_traceback = sys.exc_info()
        sc.api_call(
            'chat.postMessage', channel=channel,
            text='ERROR: You just got an error: {}.\n Traceback:\n{}'.format(
                e, '\n'.join(map(str, traceback.extract_tb(exc_traceback)))),
            as_user=True)
