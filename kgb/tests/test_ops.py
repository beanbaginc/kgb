"""Unit tests for kgb.ops."""

from __future__ import unicode_literals

import re

from kgb.errors import UnexpectedCallError
from kgb.ops import SpyOpMatchAny, SpyOpMatchInOrder, SpyOpRaise, SpyOpReturn
from kgb.tests.base import MathClass, TestCase


class SpyOpMatchAnyTests(TestCase):
    """Unit tests for kgb.ops.SpyOpMatchAny."""

    def test_setup_with_instance(self):
        """Testing SpyOpMatchAny set up with op=SpyOpMatchAny([...])"""
        obj = MathClass()

        self.agency.spy_on(
            obj.do_math,
            op=SpyOpMatchAny([
                {
                    'kwargs': {
                        'a': 1,
                        'b': 2,
                    },
                    'call_fake': lambda a, b: a - b,
                },
            ]))

        self.assertEqual(obj.do_math(a=1, b=2), -1)

    def test_with_function(self):
        """Testing SpyOpMatchAny with function"""
        def do_math(a, b):
            return a + b

        self.agency.spy_on(
            do_math,
            op=SpyOpMatchAny([
                {
                    'args': [5, 3],
                    'call_fake': lambda a, b: a - b
                },
            ]))

        self.assertEqual(do_math(5, 3), 2)

    def test_with_classmethod(self):
        """Testing SpyOpMatchAny with classmethod"""
        self.agency.spy_on(
            MathClass.class_do_math,
            owner=MathClass,
            op=SpyOpMatchAny([
                {
                    'kwargs': {
                        'a': 5,
                        'b': 3,
                    },
                    'call_fake': lambda a, b: a - b
                },
            ]))

        self.assertEqual(MathClass.class_do_math(a=5, b=3), 2)

    def test_with_unbound_method(self):
        """Testing SpyOpMatchAny with unbound method"""
        self.agency.spy_on(
            MathClass.do_math,
            owner=MathClass,
            op=SpyOpMatchAny([
                {
                    'kwargs': {
                        'a': 4,
                        'b': 3,
                    },
                },
            ]))

        obj = MathClass()

        self.assertEqual(obj.do_math(a=4, b=3), 7)

    def test_with_expected_calls(self):
        """Testing SpyOpMatchAny with all expected calls"""
        obj = MathClass()

        self.agency.spy_on(
            obj.do_math,
            op=SpyOpMatchAny([
                {
                    'kwargs': {
                        'a': 4,
                        'b': 7,
                    },
                },
                {
                    'kwargs': {
                        'a': 2,
                        'b': 8,
                    },
                    'call_original': False,
                },
                {
                    'kwargs': {
                        'a': 5,
                        'b': 9,
                    },
                    'call_fake': lambda a, b: a + b + 10,
                },
                {
                    'a': 2,
                    'call_fake': lambda a, b: 1001,
                },
            ]))

        values = [
            obj.do_math(5, b=9),
            obj.do_math(a=2, b=8),
            obj.do_math(a=1, b=1),
            obj.do_math(4, 7),
        ]

        self.assertEqual(values, [24, None, 1001, 11])

    def test_with_unexpected_call(self):
        """Testing SpyOpMatchAny with unexpected call"""
        obj = MathClass()

        self.agency.spy_on(
            obj.do_math,
            op=SpyOpMatchAny([
                {
                    'kwargs': {
                        'a': 4,
                        'b': 7,
                    },
                },
            ]))

        expected_message = re.escape(
            'do_math was not called with any expected arguments.'
        )

        with self.assertRaisesRegexp(AssertionError, expected_message):
            obj.do_math(a=4, b=9)


class SpyOpMatchInOrderTests(TestCase):
    """Unit tests for kgb.ops.SpyOpMatchInOrder."""

    def test_setup_with_instance(self):
        """Testing SpyOpMatchInOrder set up with op=SpyOpMatchInOrder([...])"""
        obj = MathClass()

        self.agency.spy_on(
            obj.do_math,
            op=SpyOpMatchInOrder([
                {
                    'kwargs': {
                        'a': 1,
                        'b': 2,
                    },
                },
            ]))

        self.assertEqual(obj.do_math(a=1, b=2), 3)

    def test_with_function(self):
        """Testing SpyOpMatchInOrder with function"""
        def do_math(a, b):
            return a + b

        self.agency.spy_on(
            do_math,
            op=SpyOpMatchInOrder([
                {
                    'args': [5, 3],
                    'call_fake': lambda a, b: a - b
                },
            ]))

        self.assertEqual(do_math(5, 3), 2)

    def test_with_classmethod(self):
        """Testing SpyOpMatchInOrder with classmethod"""
        self.agency.spy_on(
            MathClass.class_do_math,
            owner=MathClass,
            op=SpyOpMatchInOrder([
                {
                    'kwargs': {
                        'a': 5,
                        'b': 3,
                    },
                    'call_fake': lambda a, b: a - b
                },
            ]))

        self.assertEqual(MathClass.class_do_math(a=5, b=3), 2)

    def test_with_unbound_method(self):
        """Testing SpyOpMatchInOrder with unbound method"""
        self.agency.spy_on(
            MathClass.do_math,
            owner=MathClass,
            op=SpyOpMatchInOrder([
                {
                    'kwargs': {
                        'a': 4,
                        'b': 3,
                    },
                },
            ]))

        obj = MathClass()

        self.assertEqual(obj.do_math(a=4, b=3), 7)

    def test_with_expected_calls(self):
        """Testing SpyOpMatchInOrder with all expected calls"""
        obj = MathClass()

        self.agency.spy_on(
            obj.do_math,
            op=SpyOpMatchInOrder([
                {
                    'kwargs': {
                        'a': 4,
                        'b': 7,
                    },
                },
                {
                    'kwargs': {
                        'a': 2,
                        'b': 8,
                    },
                    'call_original': False,
                },
                {
                    'kwargs': {
                        'a': 5,
                        'b': 9,
                    },
                    'call_fake': lambda a, b: a + b + 10,
                },
                {
                    'call_fake': lambda a, b: 1001,
                },
            ]))

        values = [
            obj.do_math(4, 7),
            obj.do_math(a=2, b=8),
            obj.do_math(5, b=9),
            obj.do_math(a=1, b=1),
        ]

        self.assertEqual(values, [11, None, 24, 1001])

    def test_with_unexpected_call(self):
        """Testing SpyOpMatchInOrder with unexpected call"""
        obj = MathClass()

        self.agency.spy_on(
            obj.do_math,
            op=SpyOpMatchInOrder([
                {
                    'kwargs': {
                        'a': 4,
                        'b': 7,
                    },
                },
            ]))

        expected_message = re.escape(
            "This call to do_math was not passed args=(), "
            "kwargs={'a': 4, 'b': 7}.\n"
            "\n"
            "It was called with:\n"
            "\n"
            "args=()\n"
            "kwargs={'a': 4, 'b': 9}"
        )

        with self.assertRaisesRegexp(AssertionError, expected_message):
            obj.do_math(a=4, b=9)

    def test_with_extra_call(self):
        """Testing SpyOpMatchInOrder with extra unexpected call"""
        obj = MathClass()

        self.agency.spy_on(
            obj.do_math,
            op=SpyOpMatchInOrder([
                {
                    'kwargs': {
                        'a': 4,
                        'b': 7,
                    },
                },
            ]))

        self.assertEqual(obj.do_math(a=4, b=7), 11)

        expected_message = re.escape(
            'do_math was called 2 time(s), but only 1 call(s) were expected.'
        )

        with self.assertRaisesRegexp(UnexpectedCallError, expected_message):
            obj.do_math(a=4, b=9)


class SpyOpRaiseTests(TestCase):
    """Unit tests for kgb.ops.SpyOpRaise."""

    def test_with_function(self):
        """Testing SpyOpRaise with function"""
        def do_math(a, b):
            return a + b

        self.agency.spy_on(
            do_math,
            op=SpyOpRaise(ValueError('foo')))

        with self.assertRaisesRegexp(ValueError, 'foo'):
            do_math(5, 3)

    def test_with_classmethod(self):
        """Testing SpyOpRaise with classmethod"""
        self.agency.spy_on(
            MathClass.class_do_math,
            owner=MathClass,
            op=SpyOpRaise(ValueError('foo')))

        with self.assertRaisesRegexp(ValueError, 'foo'):
            MathClass.class_do_math(5, 3)

    def test_with_unbound_method(self):
        """Testing SpyOpRaise with unbound method"""
        self.agency.spy_on(
            MathClass.do_math,
            owner=MathClass,
            op=SpyOpRaise(ValueError('foo')))

        obj = MathClass()

        with self.assertRaisesRegexp(ValueError, 'foo'):
            obj.do_math(a=4, b=3)


class SpyOpReturnTests(TestCase):
    """Unit tests for kgb.ops.SpyOpReturn."""

    def test_with_function(self):
        """Testing SpyOpReturn with function"""
        def do_math(a, b):
            return a + b

        self.agency.spy_on(
            do_math,
            op=SpyOpReturn('abc123'))

        self.assertEqual(do_math(5, 3), 'abc123')

    def test_with_classmethod(self):
        """Testing SpyOpReturn with classmethod"""
        self.agency.spy_on(
            MathClass.class_do_math,
            owner=MathClass,
            op=SpyOpReturn('abc123'))

        self.assertEqual(MathClass.class_do_math(5, 3), 'abc123')

    def test_with_unbound_method(self):
        """Testing SpyOpReturn with unbound method"""
        self.agency.spy_on(
            MathClass.do_math,
            owner=MathClass,
            op=SpyOpReturn('abc123'))

        obj = MathClass()

        self.assertEqual(obj.do_math(a=4, b=3), 'abc123')
