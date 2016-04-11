import time

from slackclient import SlackClient

import settings


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


def process_message(message):
    # TODO: Process messages with click!!
    print message


def check_stuff():
    pass


def run():
    if sc.rtm_connect():
        while True:
            message = sc.rtm_read()
            process_message(message)
            check_stuff()

            time.sleep(1)
    else:
        raise ValueError('Could not connect')


if __name__ == '__main__':
    run()
