import calendar
from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta
from dateutil.rrule import (
    rrule, MONTHLY, WEEKLY, DAILY, HOURLY, MINUTELY
)

from django.utils import formats
from django.utils.translation import ugettext_lazy as _
from django.utils.dates import MONTHS, MONTHS_3, WEEKDAYS, WEEKDAYS_ABBR

from calendartools.periods.proxybase import SimpleProxy
from calendartools import defaults
from calendartools.utils import make_datetime, standardise_first_dow

__all__ = ['Period', 'Hour', 'Day', 'Week', 'Month', 'TripleMonth', 'Year',
           'first_day_of_week']

# Sensible default:
calendar.setfirstweekday(standardise_first_dow(
    formats.get_format('FIRST_DAY_OF_WEEK')
))

def get_weekday_properties():
    dayabbrs = WEEKDAYS_ABBR.values() * 2
    daynames = WEEKDAYS.values() * 2
    weekday_names = []
    weekday_abbrs = []
    first_dow = standardise_first_dow(formats.get_format('FIRST_DAY_OF_WEEK'))

    for i in range(first_dow, first_dow + 7):
        weekday_names.append(daynames[i])
        weekday_abbrs.append(dayabbrs[i])
    return weekday_names, weekday_abbrs

def first_day_of_week(dt):
    first_dow = standardise_first_dow(formats.get_format('FIRST_DAY_OF_WEEK'))
    tzinfo = dt.tzinfo if hasattr(dt, 'tzinfo') else None
    first_date = make_datetime(dt.year, dt.month, dt.day, tzinfo=tzinfo)
    return first_date + relativedelta(weekday=first_dow, days=-6)


class Period(SimpleProxy):
    month_names = MONTHS.values()
    month_names_abbr = MONTHS_3.values()
    format = 'DATETIME_FORMAT'

    def __init__(self, obj, *args, **kwargs):
        self.day_names, self.day_names_abbr = get_weekday_properties()
        self._real_obj = obj
        obj = self.convert(obj)
        occurrences = kwargs.pop('occurrences', [])
        super(Period, self).__init__(obj, *args, **kwargs)
        self.occurrences = self.process_occurrences(occurrences)

    def __unicode__(self):
        return formats.date_format(self, self.format)

    def process_occurrences(self, occurrences, key=None):
        if not key:
            key = lambda o: o.start
        return [o for o in occurrences if key(o) in self]

    def convert(self, dt):
        """ Returns datetime representation of date/datetime in either the local
        dt or the dt's tzinfo, with no microseconds. """
        if isinstance(dt, datetime):
            return make_datetime(dt.year, dt.month, dt.day, dt.hour, dt.minute,
                                 dt.second, tzinfo=dt.tzinfo)
        else:
            return make_datetime(dt.year, dt.month, dt.day)

    def interval(self):
        raise NotImplementedError

    def __contains__(self, item):
        """Note that when comparing datetime.date objects with this class, they
        will automatically be coerced to datetime objects with a default start
        time of 12:00:00 am, which might mean they are included as members."""
        try:
            item = self.convert(item)
        except AttributeError:
            return False

        return self.start <= item <= self.finish

    def __cmp__(self, other):
        try:
            other = self.convert(other)
        except AttributeError:
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
    convert = lambda self, dt: make_datetime(dt.year, dt.month, dt.day, dt.hour,
                                             tzinfo=dt.tzinfo)
    period_name = _('hour')
    period_adverb = _('hourly')
    format = 'TIME_FORMAT'

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
    period_name = _('day')
    period_adverb = _('daily')
    format = 'DATE_FORMAT'

    def __iter__(self):
        return iter(self.hours)

    def convert(self, dt):
        tzinfo = dt.tzinfo if hasattr(dt, 'tzinfo') else None
        return make_datetime(dt.year, dt.month, dt.day, tzinfo=tzinfo)

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
        return [Hour(dt, occurrences=self.occurrences) for dt in
                rrule(HOURLY, dtstart=self.start, until=self.finish)]

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

            def get_day(self):
                return Day(self, occurrences=self.occurrences)

            def get_week(self):
                return Week(self, occurrences=self.occurrences)

            def get_month(self):
                return Month(self, occurrences=self.occurrences)

            def get_year(self):
                return Year(self, occurrences=self.occurrences)

        intervals = []
        start_time = defaults.TIMESLOT_START_TIME
        start = self.start.replace(hour=start_time.hour,
                                   minute=start_time.minute)
        finish = start + defaults.TIMESLOT_END_TIME_DURATION
        while start <= finish:
            intervals.append(DayInterval(start, occurrences=self.occurrences))
            start += defaults.TIMESLOT_INTERVAL
        return intervals


class Week(Period):
    interval = relativedelta(weeks=+1)
    convert = lambda self, dt: first_day_of_week(dt)
    period_name = _('week')
    period_adverb = _('weekly')
    format = 'DATE_FORMAT'

    def __iter__(self):
        return iter(self.days)

    def __contains__(self, item):
        """ Check if ``item`` is in this week's range but instead of coercing
        ``item`` using ``Week.convert``, use ``Period.convert``. This is to
        avoid "incorrect" starts of the week because of timezone
        differences. """
        try:
            item = super(Week, self).convert(item)
        except AttributeError:
            return False

        return self.start <= item <= self.finish

    @property
    def number(self):
        return ((self - make_datetime(self.year, 1, 1)).days / 7) + 1

    @property
    def days(self):
        return [Day(dt, occurrences=self.occurrences) for dt in rrule(DAILY,
            dtstart=self.start, until=self.finish
        )]

    def get_month(self):
        return Month(self, occurrences=self.occurrences)

    def get_year(self):
        return Year(self, occurrences=self.occurrences)

    @property
    def first_day(self):
        return Day(self.start, occurrences=self.occurrences)

    @property
    def last_day(self):
        return Day(self.finish, occurrences=self.occurrences)

    @property
    def calendar_display(self):
        return zip(*[d.intervals for d in self])


class Month(Period):
    interval = relativedelta(months=+1)
    period_name = _('month')
    period_adverb = _('monthly')
    format = 'DATE_FORMAT'

    def __iter__(self):
        return iter(self.weeks)

    def convert(self, dt):
        tzinfo = dt.tzinfo if hasattr(dt, 'tzinfo') else None
        return make_datetime(dt.year, dt.month, 1, tzinfo=tzinfo)

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
        weeks = [Week(dt, occurrences=self.occurrences) for dt in rrule(WEEKLY,
            dtstart=self.start, until=self.finish
        )]
        following_week_start = weeks[-1].finish + timedelta.resolution
        if following_week_start in self:
            weeks.append(Week(following_week_start, occurrences=self.occurrences))
        return weeks
        """
        res = []
        week = Week(self.start, occurrences=self.occurrences)
        while week in self: # first week not in self - fail!
            res.append(week)
            week = Week(week.start + timedelta(7), occurrences=self.occurrences)
        return res
        """

    @property
    def days(self):
        return [Day(dt, occurrences=self.occurrences) for dt in rrule(DAILY,
            dtstart=self.start, until=self.finish
        )]

    @property
    def calendar_display(self):
        cal = calendar.monthcalendar(self.year, self.month)
        return ((Day(make_datetime(self.year, self.month, num),
                     occurrences=self.occurrences) if num else 0
                     for num in lst) for lst in cal)

    def get_year(self):
        return Year(self, occurrences=self.occurrences)


class TripleMonth(Month):
    interval = relativedelta(months=+3)
    period_name = _('triple month')
    period_adverb = _('tri-monthly')

    def __iter__(self):
        return iter(self.months)

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
        return [Month(dt, occurrences=self.occurrences) for dt in
                rrule(MONTHLY, dtstart=self.start, until=self.finish
        )]


class Year(Period):
    interval = relativedelta(years=+1)
    period_name = _('year')
    period_adverb = _('yearly')
    format = 'DATE_FORMAT'

    def __iter__(self):
        return iter(self.months)

    def convert(self, dt):
        tzinfo = dt.tzinfo if hasattr(dt, 'tzinfo') else None
        return make_datetime(dt.year, 1, 1, tzinfo=tzinfo)

    @property
    def number(self):
        return self.year

    @property
    def months(self):
        return [Month(dt, occurrences=self.occurrences) for dt in
                rrule(MONTHLY, dtstart=self.start, until=self.finish
        )]

    @property
    def days(self):
        for month in self.months:
            for dt in rrule(DAILY, dtstart=month.start, until=month.finish):
                yield Day(dt, occurrences=self.occurrences)
