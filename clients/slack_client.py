import re
import time
import datetime
from subprocess import Popen, PIPE, STDOUT

from slackclient import SlackClient

import settings
from clients.cli import cli
from commands import create_from_storage


sc = SlackClient(settings.SLACK_TOKEN)


def raise_if_not_ok(response):
    if 'ok' in response and response['ok'] is False:
        raise ValueError('Something went wrong {}'.format(response))


def get_user_id_by_email(email):
    users_response = sc.api_call('users.list')
    raise_if_not_ok(users_response)

    users = users_response['members']

    user = filter(lambda user: user['profile']['email'] == email, users)

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
    return re.sub('<mailto:([^|]+)\|[^>]+>', r'\1', message)


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
_LAST_TIME_CHECKED = None
_CHECK_INTERVAL = 30 # minutes


def do_stuff():
    delta = datetime.timedelta(minutes=_CHECK_INTERVAL)
    now = datetime.datetime.now()
    if ((_LAST_TIME_CHECKED is not None and
            now - _LAST_TIME_CHECKED > delta) is False):
        return

    # try:
    #     activities = create_from_storage()
    # except Exception:
    #     sc.api_call(
    #         'chat.postMessage', channel=message['channel'], text=output,
    #         as_user=True)


def message_checks_out(message):
    return bool(
        message and
        message['type'] == 'message' and
        'user' in message and
        message['user'] != _BOT_ID
    )


def run():
    if sc.rtm_connect():
        while True:
            messages = sc.rtm_read()
            # Currently we only take a message
            message = messages[0] if messages else None

            if message_checks_out(message) is False:
                time.sleep(1)
                continue

            process_message(message)
            do_stuff()

    else:
        raise ValueError('Could not connect')


if __name__ == '__main__':
    run()
