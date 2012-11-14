from django.utils import timezone

from calendartools import defaults
from calendartools.views.calendars import (
    YearView, TriMonthView, MonthView, WeekView, DayView
)


class YearAgenda(YearView):
    template_name = 'calendar/agenda/year.html'
    paginate_by = defaults.MAX_AGENDA_ITEMS_PER_PAGE


class MonthAgenda(MonthView):
    template_name = 'calendar/agenda/month.html'
    paginate_by = defaults.MAX_AGENDA_ITEMS_PER_PAGE


class TriMonthAgenda(TriMonthView):
    template_name = 'calendar/agenda/tri_month.html'
    paginate_by = defaults.MAX_AGENDA_ITEMS_PER_PAGE


class WeekAgenda(WeekView):
    template_name = 'calendar/agenda/week.html'
    paginate_by = defaults.MAX_AGENDA_ITEMS_PER_PAGE


class DayAgenda(DayView):
    template_name = 'calendar/agenda/day.html'
    paginate_by = defaults.MAX_AGENDA_ITEMS_PER_PAGE


def today_agenda(request, slug, *args, **kwargs):
    now = timezone.now()
    view = DayAgenda(request=request, slug=slug, year=str(now.year),
                   month=str(now.strftime('%b').lower()), day=str(now.day), **kwargs)
    return view.get(request, slug=slug, year=now.year, day=now.day)
