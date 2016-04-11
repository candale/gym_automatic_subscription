import datetime
import urlparse
import logging
import re

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException


logging.basicConfig(filename='gym.log', level=logging.INFO)


class CrossfitScheduler(object):
    class Activities:
        CROSSFIT = 'Crossfit'

    def __init__(self, email, *args, **kwargs):
        self._email = email

    def _init_driver(self):
        self._driver = webdriver.Firefox()

    def _dispose_of_driver(self):
        self._driver.close()
        self._driver.quit()

    def _get_all_activities(self):
        '''
        Return a list of dictionaries that represents all the active
        activities.

        If an activity can be scheduled, there should be the
        following in the DOM structure
        <strong> ... </strong>              -> name
        <a> ... </a>                        -> schedule link
        <div id="info_<number>"> ... </div> -> activity info
        '''
        def get_active_activities_from_cell(cell):
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

        logging.info('Getting all schedule-able activities')
        activities = []
        valid_table_cells = self._driver.find_elements_by_xpath(
            "//td[.//a[contains(@href, 'programari')]]")

        for cell in valid_table_cells:
            raw_data = get_active_activities_from_cell(cell)

            for data in raw_data:
                logging.info('Making activity with data {}'.format(data))
                activities.append(self._make_activity(data))

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
            'name': data[0].text.strip(),
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
            return False

        self._finish_scheduling(schedule_button)

        logging.info(
            'Successfully scheduled for activity {}'.format(activity))

        return True

    def _go_to_schedule_page(self):
        self._driver.get(
            'http://89.137.4.84/site/Extern.php?sectiune=program')
        self._driver.switch_to.frame(
            self._driver.find_element_by_id('changer2'))

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

        active_schedules = []
        table = self._driver.find_element_by_xpath(
            "//table[@id='gradient-style']/tbody")
        all_schedules = table.find_elements_by_xpath(".//tr")

        for schedule in all_schedules:
            elements = schedule.find_elements_by_xpath('.//td')

            if len(elements) != EXPECTED_NUMBER_OF_COLUMNS:
                logging.error('There should be 8 columns')
                return False

            last_element = elements[EXPECTED_NUMBER_OF_COLUMNS - 1]
            if 'Activa' not in last_element.text:
                continue

            hour, minute = elements[4].text.split(':')
            cancel_but = last_element.find_element_by_xpath('.//a')
            active_schedules.append({
                'name': elements[0].text,
                'date': datetime.datetime.strptime(
                    elements[3].text, '%Y-%m-%d').date(),
                'time': (int(hour), int(minute)),
                'cancel_but': cancel_but
            })

        return active_schedules

    def _finish_cancelling(self, schedule):
        # Hackish so that every confirm is true so we don't have to
        # deal with pressing OK
        self._driver.execute_script(
            "window.confirm = function(){ return true; }")

        schedule['cancel_but'].click()

        logging.info('Canceled schedule {}'.format(schedule))

    def schedule(self, activity_name, date, time):
        '''
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
                activity['name'] == activity_name,
                activity['time'] == time,
                activity['date'] == date,
            ])

        self._init_driver()

        logging.info(
            'Searching for activity with search params -'
            ' Name: {}, Date: {}, Time: {}:{}'.format(
                activity_name, date, *time)
        )

        self._go_to_schedule_page()
        activities = self._get_all_activities()
        activity = filter(activity_matches, activities)

        if not activity:
            logging.info('No activity found')
            return False

        if len(activity) > 1:
            logging.error(
                'Weird. There are more than one activities for given search '
                'params. That should not happen. Aborting'
            )
            return False

        succeessful = self._schedule(activity[0])
        self._dispose_of_driver()

        return succeessful

    def cancel_schedule(self, activity_name, date, time):
        def schedule_matches(schedule):
            return all([
                schedule['name'] == activity_name,
                schedule['time'] == time,
                schedule['date'] == date,
            ])

        self._init_driver()

        logging.info(
            'Trying to cancel schedule with '
            'Name: {}, Date: {}, Time: {}:{}'.format(
                activity_name, date, *time)
        )

        self._go_to_created_schedules_page()
        active_schedules = self._get_active_created_schedules()
        schedule = filter(schedule_matches, active_schedules)

        if not schedule:
            return False

        if len(schedule) > 1:
            logging.error(
                'Weird. There are more than one schedules for given search '
                'params. That should not happen. Aborting'
            )
            return False

        self._finish_cancelling(schedule[0])

        self._dispose_of_driver()

        return True


a = CrossfitScheduler('')
a.schedule('Crossfit', datetime.date(2016, 4, 12), (7, 0))
a.cancel_schedule('Crossfit', datetime.date(2016, 4, 12), (7, 0))
