from datetime import datetime, timedelta
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from calendartools.models import Event, Occurrence
from nose.tools import *


class TestEvent(TestCase):
    def setUp(self):
        self.creator = User.objects.create(username='TestyMcTesterson')
        self.event = Event.objects.create(
            name='Event', slug='event', creator=self.creator
        )
        self.start = datetime.now() + timedelta(minutes=30)
        self.finish = self.start + timedelta(hours=2)

    def test_add_occurrences_basic(self):
        self.event.add_occurrences(self.start, self.finish)
        assert_equal(self.event.occurrences.count(), 1)
        assert_equal(
            self.event.occurrences.latest().start.replace(microsecond=0),
            self.start.replace(microsecond=0)
        )
        assert_equal(
            self.event.occurrences.latest().finish.replace(microsecond=0),
            self.finish.replace(microsecond=0)
        )

    def test_add_occurrences_with_count(self):
        self.event.add_occurrences(self.start, self.finish, count=3)
        assert_equal(self.event.occurrences.count(), 3)
        expected = [
            self.start,
            self.start + timedelta(1),
            self.start + timedelta(2)
        ]
        expected = set([dt.replace(microsecond=0) for dt in expected])
        actual = set(self.event.occurrences.values_list('start', flat=True))
        assert_equal(expected, actual)

    def test_add_occurrences_with_until(self):
        until = self.start + timedelta(5)
        self.event.add_occurrences(self.start, self.finish, until=until)
        assert_equal(self.event.occurrences.count(), 6)

    def test_is_cancelled_property(self):
        assert not self.event.is_cancelled
        occurrence = Occurrence.objects.create(
            event=self.event,
            start=self.start,
            finish=self.start + timedelta(microseconds=1)
        )
        occurrence.status = occurrence.CANCELLED
        occurrence.save()
        assert not self.event.is_cancelled
        self.event.status = self.event.CANCELLED
        self.event.save()
        self.event = Event.objects.get(pk=self.event.pk)
        assert self.event.is_cancelled


class TestOccurrence(TestCase):
    def setUp(self):
        self.creator = User.objects.create(username='TestyMcTesterson')
        self.event = Event.objects.create(
            name='Event', slug='event', creator=self.creator
        )
        self.start = datetime.now() + timedelta(minutes=30)

    def test_finish_must_be_greater_than_start(self):
        for finish in [self.start, self.start - timedelta(microseconds=1)]:
            assert_raises(
                ValidationError,
                Occurrence.objects.create,
                event=self.event, start=self.start, finish=finish
            )
        Occurrence.objects.create(
            event=self.event,
            start=self.start,
            finish=self.start + timedelta(microseconds=1)
        )

    def test_created_occurrences_must_occur_in_future(self):
        start = datetime.now()
        finish = start + timedelta(hours=2)
        assert_raises(
            ValidationError,
            Occurrence.objects.create,
            event=self.event, start=start - timedelta.resolution, finish=finish
        )

    def test_updated_occurrences_need_not_occur_in_future(self):
        occurrence = Occurrence.objects.create(
            event=self.event,
            start=self.start,
            finish=self.start + timedelta(hours=2)
        )
        occurrence.start = datetime.now() - timedelta.resolution
        occurrence.finish = occurrence.start + timedelta(hours=2)
        try:
            occurrence.save()
        except ValidationError, e:
            self.fail(
                'Editing Occurrence triggers must-occur-in-future validation:'
                '\n%s' % e
            )

    def test_is_cancelled_property(self):
        occurrence = Occurrence.objects.create(
            event=self.event,
            start=self.start,
            finish=self.start + timedelta(microseconds=1)
        )
        assert not occurrence.is_cancelled
        occurrence.status = occurrence.CANCELLED
        occurrence.save()
        occurrence = Occurrence.objects.get(pk=occurrence.pk)
        assert occurrence.is_cancelled
        occurrence.status = occurrence.PUBLISHED
        occurrence.save()
        assert not occurrence.is_cancelled
        self.event.status = self.event.CANCELLED
        self.event.save()
        occurrence = Occurrence.objects.get(pk=occurrence.pk)
        assert occurrence.is_cancelled
