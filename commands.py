import os
import json
import copy

from scheduler import CrossfitScheduler
from helpers import parse_date_time_string


_DEFAULT_STORAGE_DIR = os.path.join(os.getenv('HOME'), '.gym_sub')
_DEFAULT_STORAGE_FILE_NAME = 'subscriptions.json'
_DEFAULT_STORAGE_FILE = os.path.join(
    _DEFAULT_STORAGE_DIR, _DEFAULT_STORAGE_FILE_NAME)


def _get_formated_activities_from_storage(file_path):
    # If a path was not specified, we do not throw an error if the default
    # file is missing
    if os.path.exists(file_path) is False:
        if file_path != _DEFAULT_STORAGE_FILE:
            raise ValueError('The given path does not exist')

        return []

    with open(file_path, 'r') as file_:
        try:
            data = json.load(file_)
        except ValueError:
            raise ValueError(
                'The file is not a valid JSON. Check at path {}'
                .format(file_path)
            )

    for entry in data:
        date_time = parse_date_time_string(entry.pop('date_time'))
        entry['date'], entry['time'] = date_time

    return data


def _write_activities_to_storage(data, file_path):
    for entry in data:
        entry['date_time'] = '{}-{}:{}'.format(
            entry.pop('date').strftime('%d-%m-%Y'), *entry.pop('time'))

    if os.path.exists(_DEFAULT_STORAGE_FILE) is False:
        os.mkdir(_DEFAULT_STORAGE_DIR)
        with open(_DEFAULT_STORAGE_FILE, 'w') as file_:
            json.dump([], file_)

    with open(file_path, 'w') as file_:
        json.dump(data, file_)


def save_activity(email, activity_name, date, time, storage_file=None):
    file_path = storage_file or _DEFAULT_STORAGE_FILE
    entries = _get_formated_activities_from_storage(file_path)
    entries.append({
        'email': email,
        'activity': activity_name,
        'date': date,
        'time': time
    })

    _write_activities_to_storage(entries, file_path)


def create_from_storage(storage_path=None):
    file_path = storage_path or _DEFAULT_STORAGE_FILE

    data = _get_formated_activities_from_storage(file_path)

    scheduled_activities = []
    scheduled_activities_indexes = []
    for counter in range(len(data)):
        entry = data[counter]
        error_message = None
        was_scheduled = False

        try:
            was_scheduled = schedule_activity(
                entry['email'], entry['activity'],
                entry['date'], entry['time'])
        except Exception, e:
            error_message = str(e)

        activity = copy.copy(entry)
        activity['error'] = error_message

        if was_scheduled or error_message:
            scheduled_activities_indexes.append(counter)
            scheduled_activities.append(activity)

    for index in scheduled_activities_indexes:
        data.pop(index)

    _write_activities_to_storage(data, file_path)

    return scheduled_activities


def get_pending_activities(email, storage_path=None):
    file_path = storage_path or _DEFAULT_STORAGE_FILE
    activities = _get_formated_activities_from_storage(file_path)

    return filter(lambda activity: activity['email'] == email, activities)


def get_active_schedules(email):
    with CrossfitScheduler(email) as scheduler:
        return scheduler.get_active_schedules()


def schedule_activity(email, activity, date, time):
    with CrossfitScheduler(email) as scheduler:
        return scheduler.schedule(activity, date, time)


def cancel_schedule(email, activity, date, time):
    with CrossfitScheduler(email) as scheduler:
        return scheduler.cancel_schedule(activity, date, time)
