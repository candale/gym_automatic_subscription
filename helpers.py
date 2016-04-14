from collections import namedtuple
import datetime
import re


# TODO: do not use this anymore. have it all be a datetime object


def _get_time(time_value):
    def check_bounds(value, lower, upper):
        if not lower <= value <= upper:
            raise ValueError('Invalid time value')

    if not re.match('\d{1,2}:\d{1,2}', time_value):
        raise ValueError('Invalid time value')

    hour_str, minute_str = time_value.split(':')
    hour = int(hour_str)
    minute = int(minute_str)

    check_bounds(hour, 0, 60)
    check_bounds(minute, 0, 60)

    return hour, minute


def parse_date_time_string(value):
    DateTimeType = namedtuple('DateTimeType', ['date', 'time'])
    values = value.split('-')
    time_str = values.pop()
    date_str = '-'.join(values)

    date = datetime.datetime.strptime(date_str, '%d-%m-%Y').date()
    time = _get_time(time_str)

    return DateTimeType(date, time)
