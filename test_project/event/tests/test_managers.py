from datetime import datetime, timedelta
from django.test import TestCase
from django.contrib.auth.models import User
from nose.tools import *
from event.models import Calendar, Event, Occurrence


class TestCommonManager(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='TestyMcTesterson')
        self.calendar = Calendar.objects.create(name='Basic', slug='basic')

        self.events = []
        for status, label in Event.STATUS_CHOICES:
            self.events.append(Event.objects.create(
                name='Event',
                slug='%s-event' % label.lower(),
                creator=self.user,
                status=status
            ))

        self.start = datetime.now() + timedelta(minutes=30)
        self.finish = self.start + timedelta(hours=2)

        self.occurrences = []
        for status, label in Occurrence.STATUS_CHOICES:
            self.occurrences.append(Occurrence.objects.create(
                event=self.events[-1], start=self.start, finish=self.finish,
                status=status, calendar=self.calendar
            ))
        self.model = Calendar

    def _test_status_properties(self, prop, status):
        assert_equal(
            set(getattr(self.model.objects, prop)),
            set(self.model.objects.filter(status=status))
        )

    def test_inactive_property(self):
        self._test_status_properties('inactive', self.model.INACTIVE)

    def test_hidden_property(self):
        self._test_status_properties('hidden', self.model.HIDDEN)

    def test_cancelled_property(self):
        self._test_status_properties('cancelled', self.model.CANCELLED)

    def test_published_property(self):
        self._test_status_properties('published', self.model.PUBLISHED)

    def test_visible_method(self):
        assert_equal(
            set(self.model.objects.visible()),
            set(self.model.objects.filter(status__gte=self.model.CANCELLED))
        )
        assert_equal(
            set(self.model.objects.visible(user=self.user)),
            set(self.model.objects.filter(status__gte=self.model.CANCELLED))
        )
        self.user.is_staff = True
        self.user.save()
        assert_equal(
            set(self.model.objects.visible(user=self.user)),
            set(self.model.objects.filter(status__gte=self.model.HIDDEN))
        )
        self.user.is_superuser = True
        self.user.is_staff = False
        self.user.save()
        assert_equal(
            set(self.model.objects.visible(user=self.user)),
            set(self.model.objects.filter(status__gte=self.model.HIDDEN))
        )


class TestCalendarManager(TestCommonManager):
    def setUp(self):
        super(TestCalendarManager, self).setUp()


class TestEventManager(TestCommonManager):
    def setUp(self):
        super(TestEventManager, self).setUp()
        self.model = Event


class TestOccurrenceManager(TestCommonManager):
    def setUp(self):
        super(TestOccurrenceManager, self).setUp()
        self.model = Occurrence
        self.event = self.occurrences[0].event

    def test_visible_with_hidden_event(self):
        self.event.status = Event.HIDDEN
        self.event.save()
        assert_equal(
            set(Occurrence.objects.visible()),
            set(Occurrence.objects.none())
        )
        assert_equal(
            set(Occurrence.objects.visible(self.user)),
            set(Occurrence.objects.none())
        )
        self.user.is_staff = True
        self.user.save()
        assert_equal(
            set(Occurrence.objects.visible(self.user)),
            set(Occurrence.objects.filter(status__gte=Occurrence.HIDDEN))
        )
        self.user.is_superuser = True
        self.user.is_staff = False
        self.user.save()
        assert_equal(
            set(Occurrence.objects.visible(self.user)),
            set(Occurrence.objects.filter(status__gte=Occurrence.HIDDEN))
        )

    def test_visible_with_inactive_event(self):
        self.event.status = Event.INACTIVE
        self.event.save()
        assert_equal(
            set(Occurrence.objects.visible()),
            set(Occurrence.objects.none())
        )
        assert_equal(
            set(Occurrence.objects.visible(self.user)),
            set(Occurrence.objects.none())
        )
        self.user.is_staff = True
        self.user.save()
        assert_equal(
            set(Occurrence.objects.visible(self.user)),
            set(Occurrence.objects.none())
        )
        self.user.is_superuser = True
        self.user.is_staff = False
        self.user.save()
        assert_equal(
            set(Occurrence.objects.visible(self.user)),
            set(Occurrence.objects.none())
        )

    def test_visible_with_hidden_calendar(self):
        self.calendar.status = Calendar.HIDDEN
        self.calendar.save()
        assert_equal(
            set(Occurrence.objects.visible()),
            set(Occurrence.objects.none())
        )
        assert_equal(
            set(Occurrence.objects.visible(self.user)),
            set(Occurrence.objects.none())
        )
        self.user.is_staff = True
        self.user.save()
        assert_equal(
            set(Occurrence.objects.visible(self.user)),
            set(Occurrence.objects.filter(status__gte=Occurrence.HIDDEN))
        )
        self.user.is_superuser = True
        self.user.is_staff = False
        self.user.save()
        assert_equal(
            set(Occurrence.objects.visible(self.user)),
            set(Occurrence.objects.filter(status__gte=Occurrence.HIDDEN))
        )

    def test_visible_with_inactive_calendar(self):
        self.calendar.status = Calendar.INACTIVE
        self.calendar.save()
        assert_equal(
            set(Occurrence.objects.visible()),
            set(Occurrence.objects.none())
        )
        assert_equal(
            set(Occurrence.objects.visible(self.user)),
            set(Occurrence.objects.none())
        )
        self.user.is_staff = True
        self.user.save()
        assert_equal(
            set(Occurrence.objects.visible(self.user)),
            set(Occurrence.objects.none())
        )
        self.user.is_superuser = True
        self.user.is_staff = False
        self.user.save()
        assert_equal(
            set(Occurrence.objects.visible(self.user)),
            set(Occurrence.objects.none())
        )