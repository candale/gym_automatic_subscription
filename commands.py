import os
import json

from scheduler import CrossfitScheduler
from helpers import parse_date_time_string


_DEFAULT_STORAGE_DIR = os.path.join(os.getenv('HOME'), '.gym_sub')
_DEFAULT_STORAGE_FILE_NAME = 'subscriptions.json'
_DEFAULT_STORAGE_FILE = os.path.join(
    _DEFAULT_STORAGE_DIR, _DEFAULT_STORAGE_FILE_NAME)


def save_activity(email, activity_name, date, time, storage_file=None):
    data = []

    # TODO: we should not check for this every time, just when it is used
    if os.path.isdir(_DEFAULT_STORAGE_DIR) is False:
        os.mkdir(_DEFAULT_STORAGE_DIR)

    file_path = storage_file or _DEFAULT_STORAGE_FILE
    file_ = open(file_path, 'r+')

    try:
        data = json.load(file_)
    except ValueError:
        raise ValueError('The file is badly formatted. Check it at {}'
                         .format(file_path))

    entry = {
        'email': email,
        'activity': activity_name,
        'date_time': '{}-{}:{}'.format(
            date.strftime('%d-%m-%Y'), time[0], time[1])
    }

    if entry in data:
        file_.close()
        return

    data.append(entry)

    file_.seek(0)
    file_.truncate()
    json.dump(data, file_)
    file_.close()


def create_from_storage(storage_path=None):
    file_path = storage_path or _DEFAULT_STORAGE_FILE

    # If a path was not specified, we do not throw an error if the default
    # file is missing
    if os.path.exists(file_path) is False:
        if file_path != _DEFAULT_STORAGE_FILE:
            raise ValueError('The given path does not exist')

        return []

    file_ = open(file_path, 'r+')
    try:
        data = json.load(file_)
    except ValueError:
        raise ValueError(
            'The file is not a valid JSON. Check at path {}'.format(file_path))

    scheduled_activities = []
    scheduled_activities_indexes = []
    for counter in range(len(data)):
        entry = data[counter]
        date_time = parse_date_time_string(entry['date_time'])
        error_message = None
        was_scheduled = False

        try:
            was_scheduled = schedule_activity(
                entry['email'], entry['activity'],
                date_time.date, date_time.time)
        except Exception, e:
            error_message = str(e)

        activity = {
            'email': entry['email'],
            'activity': entry['activity'],
            'date': date_time.date,
            'time': date_time.time,
            'error': error_message
        }

        if was_scheduled or error_message:
            scheduled_activities_indexes.append(counter)
            scheduled_activities.append(activity)

    for index in scheduled_activities_indexes:
        data.pop(index)

    file_.seek(0)
    file_.truncate()
    json.dump(data, file_)
    file_.close()

    return scheduled_activities


def get_active_schedules(email):
    with CrossfitScheduler(email) as scheduler:
        return scheduler.get_active_schedules()


def schedule_activity(email, activity, date, time):
    with CrossfitScheduler(email) as scheduler:
        return scheduler.schedule(activity, date, time)


def cancel_schedule(email, activity, date, time):
    with CrossfitScheduler(email) as scheduler:
        return scheduler.cancel_schedule(activity, date, time)
