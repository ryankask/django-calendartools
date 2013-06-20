from functools import wraps

from django.core.urlresolvers import reverse, resolve, Resolver404
from django.http import HttpResponseRedirect


def get_occurrence_data_from_session(view):
    @wraps(view)
    def new_view(request, *args, **kwargs):
        try:
            match = resolve(request.path)
        except Resolver404:
            url = '/'
        else:
            if match.namespace:
                url = reverse('{}:event-list'.format(match.namespace))
            else:
                url = reverse('event-list')

        occurrence_info = request.session.get('occurrence_info')
        if not occurrence_info:
            return HttpResponseRedirect(url)

        event               = occurrence_info['event']
        valid_occurrences   = occurrence_info['valid_occurrences']
        invalid_occurrences = occurrence_info['invalid_occurrences']

        return view(request, event, valid_occurrences, invalid_occurrences,
                    *args, **kwargs)
    return new_view
