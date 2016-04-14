import datetime
from collections import namedtuple
import json
import re
import os

import click

from scheduler import CrossfitScheduler


_DEFAULT_STORAGE_DIR = os.path.join(os.getenv('HOME'), '.gym_sub')
_DEFAULT_STORAGE_FILE_NAME = 'subscriptions.json'
_DEFAULT_STORAGE_FILE = os.path.join(
    _DEFAULT_STORAGE_DIR, _DEFAULT_STORAGE_FILE_NAME)


class DateTimeParamType(click.ParamType):
    name = 'date'
    _fail_message = (
        'datetime should be a string of the format DD-MM-YYYY-HH:MM')

    def _get_time(self, time_value):
        def check_bounds(value, lower, upper):
            if not lower <= value <= upper:
                self.fail(self._fail_message)

        if not re.match('\d{1,2}:\d{1,2}', time_value):
            self.fail(self._fail_message)

        hour_str, minute_str = time_value.split(':')
        hour = int(hour_str)
        minute = int(minute_str)

        check_bounds(hour, 0, 60)
        check_bounds(minute, 0, 60)

        return hour, minute

    def convert(self, value, param, ctx):
        DateTimeType = namedtuple('DateTimeType', ['date', 'time'])
        try:
            values = value.split('-')
            time_str = values.pop()
            date_str = '-'.join(values)

            date = datetime.datetime.strptime(date_str, '%d-%m-%Y').date()
            time = self._get_time(time_str)

            return DateTimeType(date, time)
        except ValueError:
            self.fail(self._fail_message)


class ClassParamType(click.ParamType):
    name = 'class'
    _allowed_values = (
        CrossfitScheduler.Activities.CROSSFIT,
        CrossfitScheduler.Activities.FREESTYLE,
        CrossfitScheduler.Activities.METABOLIC,
        CrossfitScheduler.Activities.PILATES,
        CrossfitScheduler.Activities.TRX,
        CrossfitScheduler.Activities.YOGA,
        CrossfitScheduler.Activities.XTREME,
    )

    def convert(self, value, param, ctx):
        if value not in self._allowed_values:
            self.fail('Class must be one of the following: {}'.format(
                ', '.join(self._allowed_values))
            )

        return value


@click.group()
def cli():
    pass


@cli.group()
def gym_schedule():
    '''Manage registrations'''
    pass


@gym_schedule.command()
@click.option('--email', type=click.STRING, required=True,
              help='Email address for the registration')
@click.option('--activity', type=ClassParamType(), required=True,
              help='The activity you want to register for')
@click.option('--date', type=DateTimeParamType(), required=True,
              multiple=True, help='The dates separated by spaces')
@click.option('--store-if-not-active/--no-storage', default=False,
              help=('If any of the dates is not active it will be stored '
                    'for subsequent runs with command create_from_storage'))
@click.option('--storage-file', default=None,
              type=click.Path(writable=True, readable=True),
              help=('File for saving inactive activities. '
                    'Defaults to home directory'))
def create(email, activity, date, store_if_not_active, storage_file):
    '''Register for a class'''

    # TODO: Move all this logic somewhere else. Too many things here
    def save_activity(activity_name, date_time):
        data = []

        # TODO: we should not check for this every time, just when it is used
        if os.path.isdir(_DEFAULT_STORAGE_DIR) is False:
            os.mkdir(_DEFAULT_STORAGE_DIR)

        file_path = storage_file or _DEFAULT_STORAGE_FILE
        file_ = open(file_path, 'r+')

        try:
            data = json.load(file_)
        except ValueError:
            click.echo('The file is badly formatted. Check it at {}'
                       .format(file_path))

        data.append({
            'activity': activity_name,
            'date_time': '{}-{}:{}'.format(
                date_time.date.strftime('%d-%m-%Y'),
                date_time.time[0], date_time.time[1])
        })

        file_.seek(0)
        file_.truncate()
        json.dump(data, file_)
        file_.close()

    with CrossfitScheduler(email) as scheduler:
        for date_time in date:
            try:
                if scheduler.schedule(
                        activity, date_time.date, date_time.time):
                    click.echo('Scheduled you for {} on {} at {}:{}'.format(
                        activity, date_time.date, *date_time.time))
                else:
                    click.echo(
                        'Could not schedule you for {} on {} at {}:{}. '
                        .format(activity, date_time.date, *date_time.time))

                    if store_if_not_active:
                        save_activity(activity, date_time)
                        click.echo(
                            'You can try again later by running command '
                            'run_from_storage')
            except Exception, e:
                raise click.ClickException('Failed with reason: {}'.format(e))


@gym_schedule.command()
@click.option('--email', type=click.STRING, required=True,
              help='Email address for the registration')
@click.option('--activity', type=ClassParamType(), required=True,
              help='The activity you want to register for')
@click.option('--date', type=DateTimeParamType(), required=True,
              multiple=True, help='The date(s) for the registration')
def cancel(email, activity, date):
    '''Cancel a registration'''

    with CrossfitScheduler(email) as scheduler:
        for date_time in date:
            try:
                if scheduler.cancel_schedule(
                        activity, date_time.date, date_time.time):
                    click.echo(
                        'Canceled schedule for {} on {} at {}:{}'.format(
                            activity, date_time.date, *date_time.time))
                else:
                    click.echo(
                        'Could not cancel schedule '
                        'for {} on {} at {}:{}'.format(
                            activity, date_time.date, *date_time.time)
                    )
            except Exception, e:
                raise click.Abort('Failed with reason: {}'.format(e))


@gym_schedule.command()
@click.option('--storage-file', default=None,
              type=click.Path(writable=True, readable=True),
              help=('File for saving inactive activities. '
                    'Defaults to home directory'))
def create_from_storage(storage_file):
    file_path = storage_file or _DEFAULT_STORAGE_FILE

    # If a path was not specified, we do not throw an error if the default
    # file is missing
    if os.path.exists(file_path) is False:
        if file_path != _DEFAULT_STORAGE_FILE:
            raise click.Abort('The given path does not exists')

        click.echo('No stored schedules were found')
        exit(0)

    file_ = open(file_path, 'r+')
    try:
        data = json.load(file_)
    except ValueError:
        raise click.Abort(
            'The file is not a valid JSON. Check at path {}'.format(file_path))

    for entry in data:
        # call for scheduling
        pass
