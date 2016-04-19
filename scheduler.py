import datetime
import urlparse
import logging
import re

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException


logging.basicConfig(filename='gym.log', level=logging.INFO)


class CrossfitScheduler(object):

    MAX_HOURS_BEFORE_NOTICE = 18

    class Activities:
        CROSSFIT = 'Crossfit'
        TRX = 'Trx'
        FREESTYLE = 'Freestyle'
        METABOLIC = 'Metabolic'
        PILATES = 'Pilates'
        YOGA = 'Yoga'
        XTREME = 'Xtreme'
        INSANITY = 'Insanity'

    def __init__(self, email, *args, **kwargs):
        self._email = email

    def __enter__(self):
        self._init_driver()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._dispose_of_driver()

    def _init_driver(self):
        self._driver = webdriver.Firefox()

    def _dispose_of_driver(self):
        self._driver.close()
        self._driver.quit()

    def start_driver(self):
        self._init_driver()

    def close_driver(self):
        self._dispose_of_driver()

    def _get_active_activities_from_cell(self, cell):
        '''
        If an activity can be scheduled, there should be the
        following in the DOM structure
        <strong> ... </strong>              -> name
        <a> ... </a>                        -> schedule link
        <div id="info_<number>"> ... </div> -> activity info
        '''
        def is_active_activity(elements):
            if len(elements) != 3:
                return False

            a_href = elements[1].get_attribute('href') or ''
            div_id = elements[2].get_attribute('id') or ''
            return all((
                elements[0].tag_name == 'strong',
                elements[1].tag_name == 'a',
                elements[2].tag_name == 'div',
                'info' in div_id,
                'sectiune=programari' in a_href,
            ))

        active = []
        elements = cell.find_elements_by_xpath('child::*')

        counter = 0
        while counter < len(elements) - 2:
            sample = elements[counter: counter + 3]

            if is_active_activity(sample):
                # name, link, info
                active.append(tuple(sample))
                counter += 4
            else:
                counter += 1

        return active

    def _get_all_activities(self):
        '''
        Return a list of dictionaries that represents all the active
        activities.
        '''
        def get_from_from_table():
            activities = []
            valid_table_cells = self._driver.find_elements_by_xpath(
                "//td[.//a[contains(@href, 'programari')]]")

            for cell in valid_table_cells:
                raw_data = self._get_active_activities_from_cell(cell)

                for data in raw_data:
                    logging.info('Making activity with data {}'.format(data))
                    activities.append(self._make_activity(data))

            return activities

        logging.info('Getting all schedule-able activities')
        activities = []

        # Next week button
        next_week_but = self._driver.find_element_by_link_text('Umatoare')

        # We have to switch to the iframe so we can access the table
        self._driver.switch_to.frame(
            self._driver.find_element_by_id('changer2'))
        activities.extend(get_from_from_table())

        # Go to next week
        self._driver.switch_to.default_content()
        next_week_but.click()

        # Switch back to the frame
        self._driver.switch_to.frame(
            self._driver.find_element_by_id('changer2'))
        activities.extend(get_from_from_table())

        return activities

    def _get_date_from_url_element(self, url_element):
        '''
        Url example:
        http://89.137.4.84/site/Extern.php?sectiune=programari2&ID_CL=85.0&wData=08-04-2016
        '''
        logging.info('Extracting url from url element')
        url = url_element.get_attribute('href')

        logging.info('Extracted url {}'.format(url))
        parsed_url = urlparse.urlparse(url)
        args = urlparse.parse_qs(parsed_url.query)

        logging.info('Got following args from url {}'.format(args))

        assert 'wData' in args and len(args['wData']) == 1,\
               'There should be a date'

        return datetime.datetime.strptime(args['wData'][0], '%d-%m-%Y').date()

    def _get_start_hour_from_info_element(self, info_element):
        info_text = info_element.get_attribute('textContent')
        logging.info('Extracting start time from info "{}"'.format(info_text))

        # We're looking for something like this: "bla bla 07:00-08:00"
        time = re.match(
            '.*(?P<start>\d\d:\d\d)-(?P<end>\d\d:\d\d)$', info_text)

        start = time.group('start')
        hour, minute = start.split(':')
        logging.info('Got start hour {} and minute {}'.format(hour, minute))

        return int(hour), int(minute)

    def _make_activity(self, data):
        activity = {
            'activity': data[0].text.strip(),
            'url': data[1].get_attribute('href'),
            'date': self._get_date_from_url_element(data[1]),
            'time': self._get_start_hour_from_info_element(data[2]),
        }
        logging.info('Created activity {}'.format(activity))

        return activity

    def _login(self):
        logging.info('Starting login')
        form = self._driver.find_element_by_xpath('//form')
        email_input = form.find_element_by_xpath(
            ".//input[contains(@name, 'email')]")
        submit_but = form.find_element_by_xpath(".//img")

        email_input.send_keys(self._email)
        submit_but.submit()

        # Try and see if the login was successful
        try:
            self._driver.find_element_by_link_text('Incearca din nou')
            raise ValueError('Could not login')
        except NoSuchElementException:
            pass

    def _get_schedule_button(self):
        logging.info('Retrieving the schedule button')
        table = self._driver.find_element_by_xpath("//table[@id='hor-zebra1']")
        try:
            return table.find_element_by_xpath('.//a')
        except NoSuchElementException:
            return None

    def _finish_scheduling(self, schedule_button):
        # Hackish so that every confirm is true so we don't have to
        # deal with pressing OK
        self._driver.execute_script(
            "window.confirm = function(){ return true; }")
        logging.info('Finishing schedule')

        schedule_button.click()

    def _schedule(self, activity):
        logging.info('Trying to schedule for activity {}'.format(activity))

        self._driver.get(activity['url'])
        self._login()
        schedule_button = self._get_schedule_button()

        if schedule_button is None:
            logging.info('NO POSITIONS LEFT')
            raise ValueError('There is no open positions for selected options')

        self._finish_scheduling(schedule_button)

        logging.info(
            'Successfully scheduled for activity {}'.format(activity))

        return True

    def _go_to_schedule_page(self):
        self._driver.get(
            'http://89.137.4.84/site/Extern.php?sectiune=program')

    def _go_to_created_schedules_page(self):
        logging.info('Going to active schedules page')

        self._driver.get('http://89.137.4.84/')
        self._login()

        schedules_link = self._driver.find_element_by_xpath(
            "//a[contains(@href, 'sectiune=programari')]")
        schedules_link.click()

    def _get_active_created_schedules(self):
        EXPECTED_NUMBER_OF_COLUMNS = 8

        logging.info('Getting a list of active schedules')

        self._go_to_created_schedules_page()

        active_schedules = []
        table = self._driver.find_element_by_xpath(
            "//table[@id='gradient-style']/tbody")
        all_schedules = table.find_elements_by_xpath(".//tr")

        for schedule in all_schedules:
            elements = schedule.find_elements_by_xpath('.//td')

            if len(elements) != EXPECTED_NUMBER_OF_COLUMNS:
                logging.error('There should be 8 columns')
                raise ValueError(
                    'There should be 8 columns. Somehting is wrong')

            last_element = elements[EXPECTED_NUMBER_OF_COLUMNS - 1]
            if 'Activa' not in last_element.text:
                continue

            hour, minute = elements[4].text.split(':')
            cancel_but = last_element.find_element_by_xpath('.//a')
            active_schedules.append({
                'activity': elements[0].text,
                'date': datetime.datetime.strptime(
                    elements[3].text, '%Y-%m-%d').date(),
                'time': (int(hour), int(minute)),
                'cancel_but': cancel_but
            })

        return active_schedules

    def get_active_schedules(self):
        schedules = self._get_active_created_schedules()

        for schedule in schedules:
            schedule.pop('cancel_but')

        return schedules

    def _finish_cancelling(self, schedule):
        # Hackish so that every confirm is true so we don't have to
        # deal with pressing OK
        self._driver.execute_script(
            "window.confirm = function(){ return true; }")

        schedule['cancel_but'].click()

        logging.info('Canceled schedule {}'.format(schedule))

    def _raise_if_should_be_visible(self, activity_name, date, time):
        max_time = datetime.timedelta(hours=self.MAX_HOURS_BEFORE_NOTICE)
        activity_date_time = datetime.datetime(
            date.year, date.month, date.day, time[0], time[1])

        if activity_date_time - datetime.datetime.now() < max_time:
            raise ValueError(
                'No activity in the next 24 hours with details: '
                'Name: {} Date: {} Hour: {}:{}'.format(
                    activity_name, date, *time)
            )

    def schedule(self, activity_name, date, time):
        '''
        Return true if activity is programmable and false otherwise
        (i.e. it does not find an activity that is programmable but it may find
        it in the future, so it does not raise an error but returns False).

        Raises ValueError for anything else:
            - activity active but no open positions
            - login failed
            - activity is within MAX_HOURS_BEFORE_NOTICE time but it cannot
              find an activity matching the given details

        ** activity
            The name of the activity you want to make a schedule to
        ** time
            A tuple with two values, the first one being the hour (in 24 hour
            format) and the second the minute
        ** date
            A date which has specified only year, month and date
        '''
        def activity_matches(activity):
            return all([
                activity['activity'].lower() == activity_name.lower(),
                activity['time'] == time,
                activity['date'] == date,
            ])

        logging.info(
            'Searching for activity with search params -'
            ' Name: {}, Date: {}, Time: {}:{}'.format(
                activity_name, date, *time)
        )

        self._go_to_schedule_page()
        activities = self._get_all_activities()
        activity = filter(activity_matches, activities)

        if not activity:
            self._raise_if_should_be_visible(activity_name, date, time)
            logging.info('No activity found')
            return False

        if len(activity) > 1:
            logging.error(
                'Weird. There are more than one activities for given search '
                'params. That should not happen. Aborting. '
                'Details: {}'.format(activity)
            )
            raise ValueError(
                'There should not be more activities for single search')

        succeessful = self._schedule(activity[0])

        return succeessful

    def cancel_schedule(self, activity_name, date, time):
        def schedule_matches(schedule):
            return all([
                schedule['activity'].lower() == activity_name.lower(),
                schedule['time'] == time,
                schedule['date'] == date,
            ])

        logging.info(
            'Trying to cancel schedule with '
            'Name: {}, Date: {}, Time: {}:{}'.format(
                activity_name, date, *time)
        )

        active_schedules = self._get_active_created_schedules()
        schedule = filter(schedule_matches, active_schedules)

        if not schedule:
            raise ValueError('No schedules found for given options')

        if len(schedule) > 1:
            logging.error(
                'Weird. There are more than one schedules for given search '
                'params. That should not happen. Aborting'
                'Details: {}'.format(schedule)
            )
            raise ValueError(
                'There should not be more than one schedule for a search')

        self._finish_cancelling(schedule[0])

        return True
