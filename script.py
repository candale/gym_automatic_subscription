import datetime
import time
import re
from copy import copy

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException


class CrossfitTimeTableBuilder(list):
    day_regex = re.compile('(?P<day_name>[^\s]+)\s\((?P<day_number>\d+)\)')

    def __init__(self, *args, **kwargs):
        super(CrossfitTimeTableBuilder, self).__init__(*args, **kwargs)

        self.driver = webdriver.Firefox()
        self.driver.get('http://89.137.4.84/site/Extern.php?sectiune=program')
        self.driver.switch_to.frame(self.driver.find_element_by_id('changer2'))
        self._build_time_table()

    def _build_time_table(self):
        table_rows = self.driver.find_elements_by_tag_name('tr')
        header = table_rows[0].find_elements_by_tag_name('th')
        activities_rows = [
            table_row.find_elements_by_tag_name('td')
            for table_row in table_rows[1:]
        ]

        header_dates = self._get_header_dates_starting_with_today(header)
        self._build_activities(activities_rows, header_dates)

    def _get_activity_name_and_schedule_link_from_element(self, activity):
        activity_name = schedule_element = None

        try:
            activity_name = (
                activity.find_element_by_tag_name('strong').text)
            schedule_element = activity.find_elements_by_tag_name('a')
        except NoSuchElementException:
            pass

        return activity_name, schedule_element

    def _build_activities(self, activities_rows, header_dates):
        now = datetime.datetime.now()
        weekday = now.weekday()

        for activity_row in activities_rows:
            activity_row = copy(activity_row)
            hour_str = activity_row.pop(0).text

            if not hour_str:
                continue

            hour = int(hour_str.split(':')[0])

            # get only activities from today onward
            counter = weekday
            while counter < 7:
                activity = activity_row[counter]
                date = header_dates[counter]

                activity_name, schedule_element = (
                    self._get_activity_name_and_schedule_link_from_element(
                        activity
                    )
                )

                if schedule_element and activity_name:
                    self.append({
                        'name': activity_name,
                        'date': datetime.datetime(
                            date.year, date.month, date.day, hour)
                    })

                counter += 1

    def _get_header_dates_starting_with_today(self, header_list):
        now = datetime.datetime.now()
        weekday = now.weekday()
        dates = [None] * weekday

        for i in range(7 - weekday):
            dates.append(
                datetime.date(now.year, now.month, now.day + i))

        return dates



a = CrossfitTimeTableBuilder()
