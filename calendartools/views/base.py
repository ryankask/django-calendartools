from django.conf import settings
from django.db.models import Max, Min
from django.db.models.loading import get_model
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.generic.base import TemplateResponseMixin
from django.views.generic.list import BaseListView
from django.views.generic.dates import DateMixin, _date_from_string

import pytz

from calendartools import defaults, forms

Calendar = get_model(defaults.CALENDAR_APP_LABEL, 'Calendar')
Occurrence = get_model(defaults.CALENDAR_APP_LABEL, 'Occurrence')


class CalendarViewBase(DateMixin, BaseListView, TemplateResponseMixin):
    filter_names = ['period', 'timezone']
    allow_future = True
    allow_empty  = True
    date_field   = 'start'
    date_attrs   = ['year', 'year_format', 'month', 'month_format', 'day',
                   'day_format']
    context_object_name = 'occurrences'

    def __init__(self, *args, **kwargs):
        super(CalendarViewBase, self).__init__(*args, **kwargs)
        self.timezone = pytz.timezone(settings.TIME_ZONE)
        self.extra_context = getattr(self, 'extra_context', {})
        self.extra_context.update(kwargs.pop('extra_context', {}))

    def get_template_names(self):
        if self.template_name is None:
            return []
        else:
            app_label = defaults.CALENDAR_APP_LABEL
            return [
                self.template_name.replace('calendar',  app_label, 1),
                self.template_name
            ]

    @property
    def queryset(self):
        return Occurrence.objects.visible().select_related(
                    'event', 'calendar').filter(calendar=self.calendar)

    @property
    def calendar(self):
        if not hasattr(self, '_calendar'):
            self._calendar = get_object_or_404(
                Calendar.objects.visible(self.request.user), slug=self.slug
            )
        return self._calendar

    @property
    def calendar_bounds(self):
        return self.calendar.occurrences.visible().aggregate(
            earliest_occurrence=Min('start'),
            latest_occurrence=Max('finish'),
        )

    def _get_kwargs_for_date_from_string(self):
        kwargs = {}
        for attrname in self.date_attrs:
            attr = getattr(self, 'get_%s' % attrname, None)
            if attr:
                kwargs[attrname] = attr()
        return kwargs

    @property
    def date(self):
        kwargs = self._get_kwargs_for_date_from_string()
        return _date_from_string(**kwargs)

    def create_period_object(self, dt, occurrences):
        occurrences = occurrences or []
        return self.period(dt, occurrences=occurrences)

    def parse_filter_params(self):
        filter_params = {}
        for key in self.filter_names:
            value = self.request.REQUEST.get(key)
            if value is not None:
                filter_params[key] = value
        return filter_params

    def apply_filters(self, queryset):
        for key in self.filter_params:
            attr = getattr(self, 'apply_%s_filter' % key)
            if attr and callable(attr):
                queryset = attr(queryset, self.filter_params[key])
        return queryset

    def apply_timezone_filter(self, queryset, timezone):
        try:
            self.timezone = pytz.timezone(timezone)
        except pytz.UnknownTimeZoneError:
            # fall-back to settings.TIME_ZONE
            self.timezone = pytz.timezone(settings.TIME_ZONE)
        return queryset

    def apply_period_filter(self, queryset, period):
        now = timezone.now()
        if period == 'past':
            queryset = queryset.filter(start__lt=now)
        elif period == 'future':
            queryset = queryset.filter(start__gte=now)
        elif period == 'today':
            queryset = queryset.filter(
                start__year=now.year,
                start__month=now.month,
                start__day=now.day
            )
        return queryset

    def allow_future_check(self, queryset):
        allow_future = self.get_allow_future()
        date_field = self.get_date_field()
        if not allow_future:
            queryset = queryset.filter(**{'%s__lte' % date_field: timezone.now()})
        return queryset

    def allow_empty_check(self, queryset):
        allow_empty = self.get_allow_empty()
        if not allow_empty and not queryset:
            raise Http404(u"No %s available" % unicode(
                queryset.model._meta.verbose_name_plural)
            )
        return queryset

    def get_dated_queryset(self, ordering='asc', **lookup):
        qs = self.get_queryset().filter(**lookup)
        date_field = self.get_date_field()
        period = self.period(self.date)
        filter_kwargs = {'%s__range' % date_field: (period.start, period.finish)}
        order = '' if ordering == 'asc' else '-'
        return qs.filter(**filter_kwargs).order_by("%s%s" % (order, date_field))

    def get_context_data(self, **kwargs):
        context = super(CalendarViewBase, self).get_context_data(**kwargs)
        for key, value in self.extra_context.items():
            context[key] = callable(value) and value() or value
        return context

    def get(self, request, *args, **kwargs):
        self.slug = kwargs.pop('slug', None)
        self.filter_params = self.parse_filter_params()
        occurrences = self.get_dated_queryset()
        occurrences = self.apply_filters(occurrences)
        occurrences = self.allow_future_check(occurrences)
        occurrences = self.allow_empty_check(occurrences)

        context = self.get_context_data(**{
            'calendar': self.calendar,
            'object_list': occurrences,
        })
        self.period_object = self.create_period_object(self.date,
                                                       context['object_list'])
        context.update(self.calendar_bounds)
        context[self.period_name] = self.period_object

        if kwargs.get('small'):
            context['size'] = 'small'

        context['timezone_form'] = forms.TimeZoneForm(
            initial={'timezone': self.timezone}
        )

        return self.render_to_response(context)
