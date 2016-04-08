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
        self._driver = webdriver.Firefox()
        self._driver.get(
            'http://89.137.4.84/site/Extern.php?sectiune=program')
        self._driver.switch_to.frame(
            self._driver.find_element_by_id('changer2'))

        self._activities = self._get_all_activities()

    def _get_all_activities(self):
        activities = []
        logging.info('Getting all schedule-able activities')

        valid_elements = self._driver.find_elements_by_xpath(
            "//td[.//a[contains(@href, 'programari')]]")

        for element in valid_elements:
            logging.info('Getting all schedule links')
            links = element.find_elements_by_xpath(
                ".//a[contains(@href, 'programari')]")

            logging.info('Getting information about activities')
            infos = element.find_elements_by_xpath(
                ".//div[contains(@id, 'info')]")

            logging.info('Getting activities names')
            names = element.find_elements_by_xpath(".//strong")

            logging.info('Aggregating links infos and names')
            activity_raw_data = zip(names, links, infos)

            for data in activity_raw_data:
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
        logging.info('Finishing schedule')

        schedule_button.click()
        self._driver.switch_to.alert.accept()

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

        logging.info(
            'Searching for activity with search params -'
            ' Name: {}, Date: {}, Time: {}:{}'.format(
                activity_name, date, *time)
        )

        activity = filter(activity_matches, self._activities)

        if not activity:
            logging.info('No activity found')
            return False

        if len(activity) > 1:
            logging.error(
                'Weird. There are more than one activities for given search '
                'params. That should not happen. Aborting'
            )
            return False

        return self._schedule(activity[0])


a = CrossfitScheduler('some_email_example@email.com')
a.schedule('Crossfit', datetime.date(2016, 4, 9), (14, 0))
