import click

from commands import (
    schedule_activity, save_activity, cancel_schedule,
    create_from_storage as create_from_store, get_active_schedules)
from scheduler import CrossfitScheduler
from helpers import parse_date_time_string


class DateTimeParamType(click.ParamType):
    name = 'date'
    _fail_message = (
        'datetime should be a string of the format DD-MM-YYYY-HH:MM')

    def convert(self, value, param, ctx):
        try:
            return parse_date_time_string(value)
        except:
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
        CrossfitScheduler.Activities.INSANITY,
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
    for date_time in date:
        try:
            was_scheduled = schedule_activity(
                email, activity, date_time.date, date_time.time)
        except Exception, e:
            click.echo('Failed with reason: {}'.format(e), err=True)
            raise click.Abort()

        if was_scheduled:
            click.echo('Scheduled you for {} on {} at {}:{}'.format(
                activity, date_time.date, *date_time.time))
            exit(0)
        else:
            click.echo(
                'Could not schedule you for {} on {} at {}:{}. '
                .format(activity, date_time.date, *date_time.time))

            if store_if_not_active:
                save_activity(email, activity, date_time.date, date_time.time)
                click.echo(
                    'The activity details were saved. You can try again '
                    'later by running command run_from_storage')


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
                was_cancelled = scheduler.cancel_schedule(
                        activity, date_time.date, date_time.time)
            except Exception, e:
                click.echo('Failed with reason: {}'.format(e), err=True)
                raise click.Abort()

            if was_cancelled:
                click.echo('Canceled schedule for {} on {} at {}:{}'.format(
                    activity, date_time.date, *date_time.time))
            else:
                click.echo(
                    'Could not cancel schedule for {} on {} at {}:{}'.format(
                        activity, date_time.date, *date_time.time))


@gym_schedule.command()
@click.option('--storage-file', default=None,
              type=click.Path(writable=True, readable=True),
              help=('File for saving inactive activities. '
                    'Defaults to home directory'))
def create_from_storage(storage_file):
    '''Try and schedule all saved activities'''
    try:
        scheduled = create_from_store(storage_path=storage_file)
    except Exception, e:
        click.echo('Failed with reason: {}'.format(e), err=True)
        raise click.Abort()

    for schedule in scheduled:
        click.echo('Scheduled {} for {} on {} at {}:{}'.format(
            schedule['email'], schedule['activity'], schedule['date'],
            *schedule['time'])
        )


@gym_schedule.command()
@click.option('--email', type=click.STRING, required=True,
              help='Email address for the registration')
def list_active(email):
    '''List active schedules'''

    try:
        schedules = get_active_schedules(email)
    except Exception, e:
        click.echo('Failed with reason: {}'.format(e), err=True)
        raise click.Abort()

    for schedule in schedules:
        click.echo('Active schedule for {} on {} at {}:{}'.format(
            schedule['activity'], schedule['date'], *schedule['time']))
