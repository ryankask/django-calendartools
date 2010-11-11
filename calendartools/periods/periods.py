import calendar
from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta
from dateutil.rrule import (
    rrule, YEARLY, MONTHLY, WEEKLY, DAILY, HOURLY, MINUTELY
)

from django.utils.dates import MONTHS, MONTHS_3, WEEKDAYS, WEEKDAYS_ABBR

from calendartools.periods.proxybase import SimpleProxy
from calendartools import defaults

__all__ = ['Period', 'Hour', 'Day', 'Week', 'Month', 'TripleMonth', 'Year']


class Period(SimpleProxy):
    day_names = WEEKDAYS.values()
    day_names_abbr = WEEKDAYS_ABBR.values()
    month_names = MONTHS.values()
    month_names_abbr = MONTHS_3.values()

    def __init__(self, obj, *args, **kwargs):
        self._real_obj = obj
        obj = self.convert(obj)
        occurrences = kwargs.pop('occurrences', [])
        super(Period, self).__init__(obj, *args, **kwargs)
        self.occurrences = self.process_occurrences(occurrences)

    def process_occurrences(self, occurrences, key=None):
        if not key:
            key = lambda o: o.start
        return [i for i in occurrences if key(i) in self]

    def convert(self, dt):
        """Returns naive datetime representation of date/datetime, with no
        microseconds."""
        for attr in ('hour', 'minute', 'second'):
            if not hasattr(dt, attr):
                return datetime(dt.year, dt.month, dt.day)
        return datetime(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)

    def interval(self):
        raise NotImplementedError

    def _coerce_to_datetime(self, dt):
        try:
            return self.convert(dt)
        except (AttributeError, ValueError, TypeError):
            return

    def __contains__(self, item):
        """Note that when comparing datetime.date objects with this class, they
        will automatically be coerced to datetime objects with a default start
        time of 12:00:00 am, which might mean they are included as members."""
        item = self._coerce_to_datetime(item)
        if not item:
            return False
        return self.start <= item <= self.finish

    def __cmp__(self, other):
        other = self._coerce_to_datetime(other)
        if not other:
            return -1
        return cmp(self.start, other)

    def previous(self):
        return self.__class__(self._obj - self.interval)

    def next(self):
        return self.__class__(self._obj + self.interval)

    @property
    def start(self):
        return self._obj

    @property
    def finish(self):
        return (self.start + self.interval) - timedelta.resolution


class Hour(Period):
    interval = relativedelta(hours=+1)
    convert = lambda self, dt: datetime(dt.year, dt.month, dt.day, dt.hour)

    def __iter__(self):
        return (dt for dt in rrule(
            MINUTELY, dtstart=self.start, until=self.finish)
        )

    @property
    def number(self):
        return self.hour

    def get_day(self):
        return Day(self, occurrences=self.occurrences)

    def get_week(self):
        return Week(self, occurrences=self.occurrences)

    def get_month(self):
        return Month(self, occurrences=self.occurrences)

    def get_year(self):
        return Year(self, occurrences=self.occurrences)


class Day(Period):
    interval = relativedelta(days=+1)
    convert = lambda self, dt: datetime(dt.year, dt.month, dt.day)

    def __iter__(self):
        return self.hours

    @property
    def name(self):
        return WEEKDAYS[self.weekday()]

    @property
    def abbr(self):
        return WEEKDAYS_ABBR[self.weekday()]

    @property
    def number(self):
        return self.day

    @property
    def hours(self):
        return (Hour(dt, occurrences=self.occurrences) for dt in
                rrule(HOURLY, dtstart=self.start, until=self.finish))

    def get_week(self):
        return Week(self, occurrences=self.occurrences)

    def get_month(self):
        return Month(self, occurrences=self.occurrences)

    def get_year(self):
        return Year(self, occurrences=self.occurrences)


    @property
    def intervals(self):
        class DayInterval(Period):
            interval = defaults.TIMESLOT_INTERVAL

        intervals = []
        start = datetime.combine(self.start.date(), defaults.TIMESLOT_START_TIME)
        finish = start + defaults.TIMESLOT_END_TIME_DURATION
        while start <= finish:
            intervals.append(DayInterval(start, occurrences=self.occurrences))
            start += defaults.TIMESLOT_INTERVAL
        return intervals


class Week(Period):
    interval = relativedelta(weeks=+1)
    convert = lambda self, dt: (datetime(dt.year, dt.month, dt.day) +
                          relativedelta(weekday=calendar.MONDAY, days=-6))

    def __iter__(self):
        return self.days

    @property
    def number(self):
        return ((self - datetime(self.year, 1, 1)).days / 7) + 1

    @property
    def days(self):
        return (Day(dt, occurrences=self.occurrences) for dt in rrule(DAILY,
            dtstart=self.start, until=self.finish
        ))

    def get_month(self):
        return Month(self, occurrences=self.occurrences)

    def get_year(self):
        return Year(self, occurrences=self.occurrences)


class Month(Period):
    interval = relativedelta(months=+1)
    convert = lambda self, dt: datetime(dt.year, dt.month, 1)

    def __iter__(self):
        return self.weeks

    @property
    def name(self):
        return MONTHS[self.month]

    @property
    def abbr(self):
        return MONTHS_3[self.month]

    @property
    def number(self):
        return self.month

    @property
    def weeks(self):
        return (Week(dt, occurrences=self.occurrences) for dt in rrule(WEEKLY,
            dtstart=self.start, until=self.finish
        ))

    @property
    def days(self):
        return (Day(dt, occurrences=self.occurrences) for dt in rrule(DAILY,
            dtstart=self.start, until=self.finish
        ))

    @property
    def calendar_display(self):
        cal = calendar.monthcalendar(self.year, self.month)
        return ((Day(datetime(self.year, self.month, num),
                     occurrences=self.occurrences) if num else 0
                     for num in lst) for lst in cal)

    def get_year(self):
        return Year(self, occurrences=self.occurrences)


class TripleMonth(Month):
    interval = relativedelta(months=+3)

    def __iter__(self):
        return self.months

    @property
    def first_month(self):
        return Month(self.start, occurrences=self.occurrences)

    @property
    def second_month(self):
        return Month(self.start + relativedelta(months=+1),
                     occurrences=self.occurrences)

    @property
    def third_month(self):
        return Month(self.start + relativedelta(months=+2),
                     occurrences=self.occurrences)

    @property
    def months(self):
        return (Month(dt, occurrences=self.occurrences) for dt in
                rrule(MONTHLY, dtstart=self.start, until=self.finish
        ))


class Year(Period):
    interval = relativedelta(years=+1)
    convert = lambda self, dt: datetime(dt.year, 1, 1)

    def __iter__(self):
        return self.months

    @property
    def number(self):
        return self.year

    @property
    def months(self):
        return (Month(dt, occurrences=self.occurrences) for dt in
                rrule(MONTHLY, dtstart=self.start, until=self.finish
        ))

    @property
    def days(self):
        for month in self.months:
            for dt in rrule(DAILY, dtstart=month.start, until=month.finish):
                yield Day(dt, occurrences=self.occurrences)


# Unused:
# -------

class Calendar(object):
    day_names = WEEKDAYS.values()
    day_names_abbr = WEEKDAYS_ABBR.values()
    month_names = MONTHS.values()
    month_names_abbr = MONTHS_3.values()

    def __init__(self, start, finish, occurrences=None, *args, **kwargs):
        self.start  = start
        self.finish = finish
        self.occurrences = occurrences or []
        super(Calendar, self).__init__(*args, **kwargs)

    def __iter__(self):
        return self.years

    @property
    def years(self):
        start = datetime(self.start.year, 1, 1)
        if not hasattr(self, '_years'):
            self._years = rrule(YEARLY, dtstart=start, until=self.finish, cache=True)
        return (Year(dt) for dt in self._years)

    @property
    def months(self):
        start = datetime(self.start.year, self.start.month, 1)
        if not hasattr(self, '_months'):
            self._months = rrule(MONTHLY, dtstart=start, until=self.finish, cache=True)
        return (Month(dt) for dt in self._months)

    @property
    def days(self):
        start = datetime(self.start.year, self.start.month, self.start.day)
        if not hasattr(self, '_days'):
            self._days = rrule(DAILY, dtstart=start, until=self.finish, cache=True)
        return self._days
        return (Day(dt) for dt in self._days)