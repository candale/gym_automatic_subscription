import datetime
from collections import namedtuple
import re

import click

from scheduler import CrossfitScheduler


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
def create(email, activity, date):
    '''Register for a class'''

    with CrossfitScheduler(email) as scheduler:
        for date_time in date:
            try:
                if scheduler.schedule(
                        activity, date_time.date, date_time.time):
                    click.echo('Scheduled you for {} on {} at {}:{}'.format(
                        activity, date_time.date, *date_time.time))
                else:
                    click.echo(
                        'Could not schedule you for {} on {} at {}:{}'.format(
                            activity, date_time.date, *date_time.time))
            except Exception, e:
                raise click.ClickException('Failed with reason: {}'.format(e))


@gym_schedule.command()
@click.option('--email', type=click.STRING, required=True,
              help='Email address for the registration')
@click.option('--activity', type=ClassParamType(), required=True,
              help='The activity you want to register for')
@click.option('--date', type=DateTimeParamType(), required=True, nargs=10,
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
                raise click.ClickException('Failed with reason: {}'.format(e))
