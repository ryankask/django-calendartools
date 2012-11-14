from datetime import date

from django.contrib.sites.models import Site
from django.utils import timezone

from calendartools.periods import Day

def current_datetime(request):
    data = {
        'now':   timezone.now(),
        'today': Day(date.today()),
    }
    return data


def current_site(request):
    '''
    A context processor to add the "current site" to the current Context
    '''
    try:
        current_site = Site.objects.get_current()
        return {'current_site': current_site}
    except Site.DoesNotExist:
        return {'current_site':''}
