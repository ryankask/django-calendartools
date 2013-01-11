from functools import wraps

from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect

def get_occurrence_data_from_session(view):
    @wraps(view)
    def new_view(request, *args, **kwargs):
        occurrence_info = request.session.get('occurrence_info')
        if not occurrence_info:
            return HttpResponseRedirect(reverse('event-list'))

        event               = occurrence_info['event']
        valid_occurrences   = occurrence_info['valid_occurrences']
        invalid_occurrences = occurrence_info['invalid_occurrences']
        next_url            = occurrence_info.get('next_url', '')

        return view(request, event, valid_occurrences, invalid_occurrences,
                    next_url, *args, **kwargs)
    return new_view
