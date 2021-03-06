import calendar
from datetime import date
import time

from dateutil.relativedelta import relativedelta
from django.db.models.loading import get_model
from django.http import Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.utils import formats, timezone
from django.views.generic import ListView
from django.views.generic.dates import YearMixin, MonthMixin, WeekMixin, DayMixin

from calendartools import defaults
from calendartools.periods import Year, TripleMonth, Month, Week, Day
from calendartools.views.base import CalendarViewBase
from calendartools.utils import standardise_first_dow

Calendar = get_model(defaults.CALENDAR_APP_LABEL, 'Calendar')
Occurrence = get_model(defaults.CALENDAR_APP_LABEL, 'Occurrence')

def calendar_list(request, *args, **kwargs):
    info = {
        'queryset': Calendar.objects.visible(request.user),
        'template_name': 'calendar/calendar_list.html'
    }
    return ListView.as_view(**info)(request, *args, **kwargs)

def calendar_detail(request, slug, *args, **kwargs):
    calendar = get_object_or_404(Calendar.objects.visible(request.user), slug=slug)
    data = {'calendar': calendar}
    return render_to_response('calendar/calendar_detail.html', data,
                            context_instance=RequestContext(request))


class YearView(CalendarViewBase, YearMixin):
    period_name = 'year'
    period = Year
    template_name = "calendar/calendar/year.html"
    extra_context = {'size': 'small'}

    @property
    def date(self):
        return date(int(self.get_year()), 1, 1)


class MonthView(CalendarViewBase, YearMixin, MonthMixin):
    period_name = 'month'
    period = Month
    template_name = "calendar/calendar/month.html"


class TriMonthView(MonthView):
    period_name = 'tri_month'
    period = TripleMonth
    template_name = "calendar/calendar/tri_month.html"
    extra_context = {'size': 'small'}

    @property
    def date(self):
        return super(TriMonthView, self).date - relativedelta(months=+1)


class WeekView(CalendarViewBase, YearMixin, WeekMixin):
    period_name = 'week'
    period = Week
    template_name = "calendar/calendar/week.html"

    @property
    def week_format(self):
        first_dow = standardise_first_dow(formats.get_format('FIRST_DAY_OF_WEEK'))
        return '%W' if first_dow == calendar.MONDAY else '%U'

    @property
    def date(self):
        year = self.get_year()
        week = self.get_week()
        week_format = self.get_week_format()
        try:
            tt = time.strptime('%s-%s-1' % (year, week), '%%Y-%s-%%w' % (week_format))
            return date(*tt[:3])
        except ValueError:
            raise Http404


class DayView(CalendarViewBase, YearMixin, MonthMixin, DayMixin):
    period_name = 'day'
    period = Day
    template_name = "calendar/calendar/day.html"


def today_view(request, slug, *args, **kwargs):
    now = timezone.now()
    view = DayView(request=request, slug=slug, year=str(now.year),
                   month=str(now.strftime('%b').lower()), day=str(now.day), **kwargs)
    return view.get(request, slug=slug, year=now.year, day=now.day)
