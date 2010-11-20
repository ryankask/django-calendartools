# -*- coding: UTF-8 -*-

from django.template import Template, Context
from django.test import TestCase
from django.utils import translation
from django.utils.translation import ugettext_lazy as _
from nose.tools import *
from calendartools.templatetags.calendartools_tags import (
    get_query_string,
    set_query_string,
    delete_query_string,
    clear_query_string
)


class TestTranslationTags(TestCase):
    def setUp(self):
        translation.activate('ar')

    def tearDown(self):
        translation.deactivate()

    def test_no_trans(self):
        context = Context({
            'january': _('January')
        })
        template = Template("""
            {{ january }}
        """)
        output = template.render(context)
        assert_in(u'يناير', output)
        template = Template("""
            {% load calendartools_tags %}
            {% notrans %}{{ january }}{% endnotrans %}
        """)
        output = template.render(context)
        assert_not_in(u'يناير', output)
        assert_in('January', output)

    def test_no_trans_filter(self):
        context = Context({
            'january': _('January')
        })
        template = Template("""
            {{ january }}
        """)
        output = template.render(context)
        assert_in(u'يناير', output)
        template = Template("""
            {% load calendartools_tags %}
            {{ january|notrans }}
        """)
        output = template.render(context)
        assert_not_in(u'يناير', output)
        assert_in('January', output)


class TestQueryStringManipulation(TestCase):
    def setUp(self):
        self.urls = (
            'http://example.com/foo',
            'http://example.com/foo/',
            'http://example.com/foo/?a=1&b=2',
            'http://example.com/foo/?a=1&a=4&b=2&b=5',
            '/foo',
            '/foo/',
            '/foo/?a=1&b=2',
            '/foo/?a=1&a=4&b=2&b=5',
        )

    def test_clear_query_string(self):
        expected = (
            'http://example.com/foo',
            'http://example.com/foo/',
            'http://example.com/foo/',
            'http://example.com/foo/',
            '/foo',
            '/foo/',
            '/foo/',
            '/foo/',
        )

        for url, expected in zip(self.urls, expected):
            assert_equal(clear_query_string(url), expected)

    def test_set_query_string(self):
        mapping = (
            ('http://example.com/foo',            'a', 1,
             'http://example.com/foo?a=1'),
            ('http://example.com/foo/',           'a', 1,
             'http://example.com/foo/?a=1'),
            ('http://example.com/foo/?a=2',       'a', 1,
             'http://example.com/foo/?a=1'),
            ('http://example.com/foo/?a=2&b=2&b=5', 'a', 1,
             'http://example.com/foo/?a=1&b=2&b=5'),
            ('/foo',            'a', 1,
             '/foo?a=1'),
            ('/foo/',           'a', 1,
             '/foo/?a=1'),
            ('/foo/?a=2',       'a', 1,
             '/foo/?a=1'),
            ('/foo/?a=2&b=2&b=5', 'a', 1,
             '/foo/?a=1&b=2&b=5'),
        )
        for url, key, value, expected in mapping:
            assert_equal(set_query_string(url, key, value), expected)

    def test_get_query_string(self):
        mapping = (
            ('http://example.com/foo',  'a', ''),
            ('http://example.com/foo/', 'a', ''),
            ('http://example.com/foo/?a=2', 'a', ['2'],),
            ('http://example.com/foo/?a=2&a=4&b=2&b=5', 'a', ['2','4']),
            ('/foo',  'a', ''),
            ('/foo/', 'a', ''),
            ('/foo/?a=2', 'a', ['2'],),
            ('/foo/?a=2&a=4&b=2&b=5', 'a', ['2','4']),
        )
        for url, key, expected in mapping:
            assert_equal(get_query_string(url, key), expected)

    def test_delete_query_string(self):
        mapping = (
            ('http://example.com/foo',  'a',
             'http://example.com/foo'),
            ('http://example.com/foo/', 'a',
             'http://example.com/foo/'),
            ('http://example.com/foo/?a=2', 'a',
             'http://example.com/foo/',),
            ('http://example.com/foo/?a=2&a=4&b=2&b=5', 'a',
             'http://example.com/foo/?b=2&b=5'),
            ('/foo',  'a',
             '/foo'),
            ('/foo/', 'a',
             '/foo/'),
            ('/foo/?a=2', 'a',
             '/foo/',),
            ('/foo/?a=2&a=4&b=2&b=5', 'a',
             '/foo/?b=2&b=5'),
        )
        for url, key, expected in mapping:
            assert_equal(delete_query_string(url, key), expected)
