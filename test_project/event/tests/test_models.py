from datetime import timedelta
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from event.models import (
    Calendar, Event, Occurrence, Attendance, Cancellation
)
from calendartools.exceptions import MaxOccurrenceCreationsExceeded
from calendartools import defaults
from calendartools.signals import collect_validators
from calendartools.validators import BaseValidator
from calendartools.validators.defaults.attendance import (
    CannotAttendFutureEventsValidator
)
from nose.tools import *


class TestStatusBase(TestCase):
    def setUp(self):
        self.creator = User.objects.create(username='TestyMcTesterson')
        self.calendar = Calendar.objects.create(name='Basic', slug='basic')
        self.event = Event.objects.create(
            name='Event', slug='event', creator=self.creator
        )
        self.start = timezone.now() + timedelta(minutes=30)
        self.finish = self.start + timedelta(hours=2)
        self.occurrence = self.event.add_occurrences(
            self.calendar, self.start, self.finish)[0]

    def test_status_slug(self):
        states = ['inactive', 'hidden', 'cancelled', 'published']
        for state in states:
            self.calendar.status = state
            self.event.status = state
            self.occurrence.status = state
            assert_equal(self.calendar.status_slug, state)
            assert_equal(self.event.status_slug, state)
            assert_equal(self.occurrence.status_slug, state)


class TestEvent(TestCase):
    def setUp(self):
        self.creator = User.objects.create(username='TestyMcTesterson')
        self.calendar = Calendar.objects.create(name='Basic', slug='basic')
        self.event = Event.objects.create(
            name='Event', slug='event', creator=self.creator
        )
        self.start = timezone.now() + timedelta(minutes=30)
        self.finish = self.start + timedelta(hours=2)

    def test_add_occurrences_basic(self):
        self.event.add_occurrences(self.calendar, self.start, self.finish)
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
        self.event.add_occurrences(self.calendar, self.start, self.finish, count=3)
        assert_equal(self.event.occurrences.count(), 3)
        expected = [
            self.start,
            self.start + timedelta(1),
            self.start + timedelta(2)
        ]
        expected = set([dt.replace(microsecond=0) for dt in expected])
        actual = set(self.event.occurrences.values_list('start', flat=True))
        assert_equal(expected, actual)
        assert_equal(
            set(Occurrence.objects.filter(calendar=self.calendar)),
            set(Occurrence.objects.all()),
        )

    def test_add_occurrences_with_until(self):
        until = self.start + timedelta(5)
        self.event.add_occurrences(self.calendar, self.start, self.finish, until=until)
        assert_equal(self.event.occurrences.count(), 6)

    def test_add_occurrences_with_commit_false(self):
        occurrences = self.event.add_occurrences(
            self.calendar, self.start, self.finish, commit=False
        )
        assert_equal(self.event.occurrences.count(), 0)
        assert_equal(len(occurrences), 1)
        assert not occurrences[0].pk

        occurrences = self.event.add_occurrences(
            self.calendar, self.start, self.finish, count=3, commit=False
        )
        assert_equal(self.event.occurrences.count(), 0)
        assert_equal(len(occurrences), 3)
        assert_equal(
            [o.pk for o in occurrences],
            [None, None, None]
        )

    def test_add_occurrences_maximum_creation_count_exceeded(self):
        assert_raises(MaxOccurrenceCreationsExceeded,
            self.event.add_occurrences,
            self.calendar, self.start, self.finish, commit=False,
            count=defaults.MAX_OCCURRENCE_CREATION_COUNT + 1
        )

    def test_is_cancelled_property(self):
        assert not self.event.is_cancelled
        occurrence = Occurrence.objects.create(
            calendar=self.calendar,
            event=self.event,
            start=self.start,
            finish=self.start + timedelta(microseconds=1)
        )
        occurrence.status = occurrence.STATUS.cancelled
        occurrence.save()
        assert not self.event.is_cancelled
        self.event.status = self.event.STATUS.cancelled
        self.event.save()
        self.event = Event.objects.get(pk=self.event.pk)
        assert self.event.is_cancelled


class TestOccurrence(TestCase):
    def setUp(self):
        self.creator = User.objects.create(username='TestyMcTesterson')
        self.calendar = Calendar.objects.create(name='Basic', slug='basic')
        self.event = Event.objects.create(
            name='Event', slug='event', creator=self.creator
        )
        self.start = timezone.now() + timedelta(minutes=30)
        self.occurrence = Occurrence.objects.create(
            calendar=self.calendar,
            event=self.event,
            start=self.start,
            finish=self.start + timedelta(microseconds=1)
        )

    def test_finish_must_be_greater_than_start(self):
        for finish in [self.start, self.start - timedelta(microseconds=1)]:
            assert_raises(
                ValidationError,
                Occurrence.objects.create,
                calendar=self.calendar, event=self.event,
                start=self.start, finish=finish
            )

    def test_created_occurrences_must_occur_in_future(self):
        start = timezone.now()
        finish = start + timedelta(hours=2)
        assert_raises(
            ValidationError,
            Occurrence.objects.create,
            event=self.event, start=start - timedelta.resolution, finish=finish
        )

    def test_validation_with_missing_start(self):
        occurrence = Occurrence(
            calendar=self.calendar, event=self.event, finish=self.start
        )
        assert_raises(ValidationError, occurrence.save)

    def test_updated_occurrences_need_not_occur_in_future(self):
        self.occurrence.start = timezone.now() - timedelta.resolution
        self.occurrence.finish = self.occurrence.start + timedelta(hours=2)
        try:
            self.occurrence.save()
        except ValidationError, e:
            self.fail(
                'Editing Occurrence triggers must-occur-in-future validation:'
                '\n%s' % e
            )

    def test_pluggable_validators_priority(self):
        class AngryValidator(BaseValidator):
            priority = 9000
            error_message = "Angry Validator is Angry."

            def validate(self):
                raise ValidationError(self.error_message)

        occurrence = Occurrence(
            calendar=self.calendar,
            event=self.event,
            start=self.start,
            finish=self.start # also fails finish > start check.
        )
        try:
            collect_validators.connect(AngryValidator, sender=Occurrence)
            occurrence.save()
            self.fail('ValidationError not triggered')
        except ValidationError, e:
            assert_equal(e.messages[0], AngryValidator.error_message)
            AngryValidator.priority = -1
            try:
                occurrence.save()
                self.fail('ValidationError not triggered')
            except ValidationError, e:
                assert_not_equal(e.messages[0], AngryValidator.error_message)
        finally:
            collect_validators.disconnect(AngryValidator, sender=Occurrence)

    def test_is_cancelled_property(self):
        assert not self.occurrence.is_cancelled
        self.occurrence.status = self.occurrence.STATUS.cancelled
        self.occurrence.save()
        self.occurrence = Occurrence.objects.get(pk=self.occurrence.pk)
        assert self.occurrence.is_cancelled
        self.occurrence.status = self.occurrence.STATUS.published
        self.occurrence.save()
        assert not self.occurrence.is_cancelled
        self.event.status = self.event.STATUS.cancelled
        self.event.save()
        self.occurrence = Occurrence.objects.get(pk=self.occurrence.pk)
        assert self.occurrence.is_cancelled
        self.event.status = self.event.STATUS.published
        self.event.save()
        self.calendar.status = Calendar.STATUS.cancelled
        self.calendar.save()
        self.occurrence = Occurrence.objects.get(pk=self.occurrence.pk)
        assert self.occurrence.is_cancelled


class TestOccurrenceDuration(TestCase):
    def setUp(self):
        self.creator = User.objects.create(username='TestyMcTesterson')
        self.calendar = Calendar.objects.create(name='Basic', slug='basic')
        self.event = Event.objects.create(
            name='Event', slug='event', creator=self.creator
        )
        self.start = timezone.now() + timedelta(minutes=30)
        defaults.MAX_OCCURRENCE_DURATION = timedelta(hours=2)
        defaults.MIN_OCCURRENCE_DURATION = timedelta(minutes=15)

    def test_default_finish(self):
        o = Occurrence.objects.create(
            calendar=self.calendar,
            event=self.event,
            start=self.start,
        )
        assert_equal(o.finish, o.start + defaults.DEFAULT_OCCURRENCE_DURATION)

    def test_max_occurrence_length(self):
        occurrence = Occurrence.objects.create(
            calendar=self.calendar,
            event=self.event,
            start=self.start,
            finish=self.start + defaults.MAX_OCCURRENCE_DURATION
        )
        assert_raises(
            ValidationError, Occurrence.objects.create,
            calendar=self.calendar,
            event=self.event,
            start=self.start,
            finish=self.start + defaults.MAX_OCCURRENCE_DURATION + timedelta.resolution
        )

    def test_min_occurrence_duration(self):
        occurrence = Occurrence.objects.create(
            calendar=self.calendar,
            event=self.event,
            start=self.start,
            finish=self.start + defaults.MIN_OCCURRENCE_DURATION
        )
        assert_raises(
            ValidationError, Occurrence.objects.create,
            calendar=self.calendar,
            event=self.event,
            start=self.start,
            finish=self.start + defaults.MIN_OCCURRENCE_DURATION - timedelta.resolution
        )


class TestAttendance(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='TestyMcTesterson')
        self.calendar = Calendar.objects.create(name='Basic', slug='basic')
        self.event = Event.objects.create(
            name='Event', slug='event', creator=self.user
        )
        self.start = timezone.now() + timedelta(minutes=30)
        self.finish = self.start + timedelta(minutes=30)
        self.occurrence = self.event.add_occurrences(
            self.calendar, self.start, self.finish)[0]

    def test_create_attendance(self):
        att = Attendance.objects.create(
            user=self.user, occurrence=self.occurrence
        )
        assert_equal(att.status, Attendance.STATUS.booked)

    def test_cannot_book_finished_occurrences(self):
        self.occurrence.start = self.occurrence.start - timedelta(1)
        self.occurrence.finish = self.occurrence.finish - timedelta(1)
        self.occurrence.save()
        self.assertRaises(ValidationError, Attendance.objects.create,
            user=self.user, occurrence=self.occurrence
        )

    def test_cannot_have_attended_future_occurrences(self):
        self.assertRaises(
            ValidationError,
            Attendance.objects.create,
            user=self.user,
            occurrence=self.occurrence,
            status=Attendance.STATUS.attended
        )

    def test_only_one_active_attendance_record_for_user_occurrence(self):
        try:
            collect_validators.disconnect(
                CannotAttendFutureEventsValidator, sender=Attendance
            )
            att = Attendance(user=self.user, occurrence=self.occurrence)
            for status in [Attendance.STATUS.booked, Attendance.STATUS.attended]:
                att.status = att.STATUS.attended
                att.save()
                self.assertRaises(ValidationError, Attendance.objects.create,
                    user=self.user, occurrence=self.occurrence
                )
            for status in [Attendance.STATUS.inactive, Attendance.STATUS.cancelled]:
                att.status = status
                att.save()
                att2 = Attendance.objects.create(
                    user=self.user, occurrence=self.occurrence
                )
                att2.delete()
        finally:
            collect_validators.connect(
                CannotAttendFutureEventsValidator, sender=Attendance
            )


class TestAttendanceCancellation(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='TestyMcTesterson')
        self.calendar = Calendar.objects.create(name='Basic', slug='basic')
        self.event = Event.objects.create(
            name='Event', slug='event', creator=self.user
        )
        self.start = timezone.now() + timedelta(minutes=30)
        self.finish = self.start + timedelta(minutes=30)
        self.occurrence = self.event.add_occurrences(
            self.calendar, self.start, self.finish)[0]

    def test_is_cancelled_property(self):
        att = Attendance.objects.create(
            user=self.user,
            occurrence=self.occurrence,
        )
        assert not att.is_cancelled
        att.status = att.STATUS.cancelled
        att.save()
        assert att.is_cancelled

    def test_cancellation_creates_attendance_cancelled_record(self):
        assert_equal(Cancellation.objects.count(), 0)
        att = Attendance.objects.create(
            user=self.user,
            occurrence=self.occurrence,
            status=Attendance.STATUS.cancelled
        )
        assert_equal(Cancellation.objects.count(), 1)
        assert_equal(att.cancellation, Cancellation.objects.get())
        assert_equal(att.created.date(), att.cancellation.created.date())

    def test_attendance_record_cannot_be_uncancelled(self):
        att = Attendance.objects.create(
            user=self.user,
            occurrence=self.occurrence,
            status=Attendance.STATUS.cancelled
        )
        status_choices = [i[0] for i in Attendance.STATUS if
                          i[0] != Attendance.STATUS.cancelled]
        for status in status_choices:
            att.status = status
            assert_raises(ValidationError, att.save)

    def test_creation_of_attendance_cancellation_record_cancels_attendance(self):
        att = Attendance.objects.create(
            user=self.user,
            occurrence=self.occurrence,
        )
        assert_equal(att.status, att.STATUS.booked)
        cancellation = Cancellation.objects.create(attendance=att)
        assert_equal(att.status, att.STATUS.cancelled)

    def test_attended_attendance_records_cannot_be_cancelled(self):
        try:
            collect_validators.disconnect(
                CannotAttendFutureEventsValidator, sender=Attendance
            )
            att = Attendance.objects.create(
                user=self.user,
                occurrence=self.occurrence,
                status=Attendance.STATUS.attended
            )
            att.status = att.STATUS.cancelled
            assert_raises(ValidationError, att.save)
        finally:
            collect_validators.connect(
                CannotAttendFutureEventsValidator, sender=Attendance
            )
