import datetime
import re

import click

from scheduler import CrossfitScheduler


class DateParamType(click.ParamType):
    name = 'date'

    def convert(self, value, param, ctx):
        try:
            date = datetime.datetime.strptime(value, '%d-%m-%Y').date()
            return date
        except ValueError:
            self.fail('Date should be a string of the format DD-MM-YYYY')


class TimeParamType(click.ParamType):
    name = 'time'
    _fail_message = 'Time should look like this HH:MM with 24 hour format'

    def convert(self, value, param, ctx):
        def check_bounds(value, lower, upper):
            if not lower <= value <= upper:
                self.fail(self._fail_message)

        if not re.match('\d{1,2}:\d{1,2}', value):
            self.fail(self._fail_message)

        hour_str, minute_str = value.split(':')
        hour = int(hour_str)
        minute = int(minute_str)

        check_bounds(hour, 0, 60)
        check_bounds(minute, 0, 60)

        return hour, minute


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


@cli.command()
@click.option('--email', type=click.STRING, required=True,
              help='Email address for the registration')
@click.option('--activity', type=ClassParamType(), required=True,
              help='The activity you want to register for')
@click.option('--date', type=DateParamType(), required=True,
              help='The date for the registration')
@click.option('--time', type=TimeParamType(), required=True,
              help='The time of the registration')
def schedule(email, activity, date, time):
    '''Register for a class'''
    scheduler = CrossfitScheduler(email)

    try:
        if scheduler.schedule(activity, date, time):
            click.echo('Scheduled you for {} on {} at {}:{}'.format(
                activity, date, *time))
        else:
            click.echo('Could not schedule you for {} on {} at {}:{}'.format(
                activity, date, *time))
    except Exception, e:
        raise click.ClickException('Failed with reason: {}'.format(e))


@cli.command()
@click.option('--email', type=click.STRING, required=True,
              help='Email address for the registration')
@click.option('--activity', type=ClassParamType(), required=True,
              help='The activity you want to register for')
@click.option('--date', type=DateParamType(), required=True,
              help='The date for the registration')
@click.option('--time', type=TimeParamType(), required=True,
              help='The time of the registration')
def cancel_schedule(email, activity, date, time):
    '''Cancel a registration'''
    scheduler = CrossfitScheduler(email)

    try:
        if scheduler.cancel_schedule(activity, date, time):
            click.echo('Canceled schedule for {} on {} at {}:{}'.format(
                activity, date, *time))
        else:
            click.echo(
                'Could not cancel schedule for {} on {} at {}:{}'.format(
                    activity, date, *time))
    except Exception, e:
        raise click.ClickException('Failed with reason: {}'.format(e))


if __name__ == '__main__':
    cli()
