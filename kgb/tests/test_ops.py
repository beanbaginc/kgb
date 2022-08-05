"""Unit tests for kgb.ops."""

from __future__ import unicode_literals

import re

from kgb.errors import UnexpectedCallError
from kgb.ops import (SpyOpMatchAny,
                     SpyOpMatchInOrder,
                     SpyOpRaise,
                     SpyOpRaiseInOrder,
                     SpyOpReturn,
                     SpyOpReturnInOrder)
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

    def test_setup_with_instance_and_op(self):
        """Testing SpyOpMatchAny set up with op=SpyOpMatchAny([...]) and op"""
        obj = MathClass()

        self.agency.spy_on(
            obj.do_math,
            op=SpyOpMatchAny([
                {
                    'kwargs': {
                        'a': 1,
                        'b': 2,
                    },
                    'op': SpyOpMatchInOrder([
                        {
                            'kwargs': {
                                'a': 1,
                                'b': 2,
                                'x': 1,
                            },
                            'op': SpyOpReturn(123),
                        },
                        {
                            'kwargs': {
                                'a': 1,
                                'b': 2,
                                'x': 2,
                            },
                            'op': SpyOpReturn(456),
                        },
                    ]),
                },
            ]))

        self.assertEqual(obj.do_math(a=1, b=2, x=1), 123)
        self.assertEqual(obj.do_math(a=1, b=2, x=2), 456)

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

    def test_with_function_and_op(self):
        """Testing SpyOpMatchAny with function and op"""
        def do_math(a, b, x=0):
            return a + b

        self.agency.spy_on(
            do_math,
            op=SpyOpMatchAny([
                {
                    'args': [5, 3],
                    'op': SpyOpMatchInOrder([
                        {
                            'args': [5, 3],
                            'kwargs': {
                                'x': 1,
                            },
                            'op': SpyOpReturn(123),
                        },
                        {
                            'args': [5, 3],
                            'kwargs': {
                                'x': 2,
                            },
                            'op': SpyOpReturn(456),
                        },
                    ]),
                },
            ]))

        self.assertEqual(do_math(a=5, b=3, x=1), 123)
        self.assertEqual(do_math(a=5, b=3, x=2), 456)

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

    def test_with_classmethod_and_op(self):
        """Testing SpyOpMatchAny with classmethod and op"""
        self.agency.spy_on(
            MathClass.class_do_math,
            owner=MathClass,
            op=SpyOpMatchAny([
                {
                    'kwargs': {
                        'a': 5,
                        'b': 3,
                    },
                    'op': SpyOpMatchInOrder([
                        {
                            'kwargs': {
                                'a': 5,
                                'b': 3,
                                'x': 1,
                            },
                            'op': SpyOpReturn(123),
                        },
                        {
                            'kwargs': {
                                'a': 5,
                                'b': 3,
                                'x': 2,
                            },
                            'op': SpyOpReturn(456),
                        },
                    ]),
                },
            ]))

        self.assertEqual(MathClass.class_do_math(a=5, b=3, x=1), 123)
        self.assertEqual(MathClass.class_do_math(a=5, b=3, x=2), 456)

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

    def test_with_unbound_method_and_op(self):
        """Testing SpyOpMatchAny with unbound method and op"""
        self.agency.spy_on(
            MathClass.do_math,
            owner=MathClass,
            op=SpyOpMatchAny([
                {
                    'kwargs': {
                        'a': 4,
                        'b': 3,
                    },
                    'op': SpyOpMatchInOrder([
                        {
                            'kwargs': {
                                'a': 4,
                                'b': 3,
                                'x': 1,
                            },
                            'op': SpyOpReturn(123),
                        },
                        {
                            'kwargs': {
                                'a': 4,
                                'b': 3,
                                'x': 2,
                            },
                            'op': SpyOpReturn(456),
                        },
                    ]),
                },
            ]))

        obj = MathClass()
        self.assertEqual(obj.do_math(a=4, b=3, x=1), 123)
        self.assertEqual(obj.do_math(a=4, b=3, x=2), 456)

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
                        'a': 100,
                        'b': 200,
                    },
                    'op': SpyOpMatchInOrder([
                        {
                            'kwargs': {
                                'a': 100,
                                'b': 200,
                                'x': 1,
                            },
                            'op': SpyOpReturn(123),
                        },
                        {
                            'kwargs': {
                                'a': 100,
                                'b': 200,
                                'x': 2,
                            },
                            'op': SpyOpReturn(456),
                        },
                    ]),
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
            obj.do_math(a=100, b=200, x=1),
            obj.do_math(a=100, b=200, x=2),
            obj.do_math(a=1, b=1),
            obj.do_math(4, 7),
        ]

        self.assertEqual(values, [24, None, 123, 456, 1001, 11])

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

        with self.assertRaisesRegex(AssertionError, expected_message):
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

    def test_setup_with_instance_and_op(self):
        """Testing SpyOpMatchInOrder set up with op=SpyOpMatchInOrder([...])
        and op
        """
        obj = MathClass()

        self.agency.spy_on(
            obj.do_math,
            op=SpyOpMatchInOrder([
                {
                    'kwargs': {
                        'a': 1,
                        'b': 2,
                    },
                    'op': SpyOpReturn(123),
                },
            ]))

        self.assertEqual(obj.do_math(a=1, b=2), 123)

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

    def test_with_function_and_op(self):
        """Testing SpyOpMatchInOrder with function and op"""
        def do_math(a, b):
            return a + b

        self.agency.spy_on(
            do_math,
            op=SpyOpMatchInOrder([
                {
                    'args': [5, 3],
                    'op': SpyOpReturn(123),
                },
            ]))

        self.assertEqual(do_math(5, 3), 123)

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

    def test_with_classmethod_and_op(self):
        """Testing SpyOpMatchInOrder with classmethod and op"""
        self.agency.spy_on(
            MathClass.class_do_math,
            owner=MathClass,
            op=SpyOpMatchInOrder([
                {
                    'kwargs': {
                        'a': 5,
                        'b': 3,
                    },
                    'op': SpyOpReturn(123),
                },
            ]))

        self.assertEqual(MathClass.class_do_math(a=5, b=3), 123)

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

    def test_with_unbound_method_and_op(self):
        """Testing SpyOpMatchInOrder with unbound method and op"""
        self.agency.spy_on(
            MathClass.do_math,
            owner=MathClass,
            op=SpyOpMatchInOrder([
                {
                    'kwargs': {
                        'a': 4,
                        'b': 3,
                    },
                    'op': SpyOpReturn(123),
                },
            ]))

        obj = MathClass()

        self.assertEqual(obj.do_math(a=4, b=3), 123)

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
                        'a': 100,
                        'b': 200,
                    },
                    'op': SpyOpReturn(123),
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
            obj.do_math(a=100, b=200),
            obj.do_math(5, b=9),
            obj.do_math(a=1, b=1),
        ]

        self.assertEqual(values, [11, None, 123, 24, 1001])

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

        with self.assertRaisesRegex(AssertionError, expected_message):
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
            "do_math was called 2 time(s), but only 1 call(s) were expected. "
            "Latest call: <SpyCall(args=(), kwargs={'a': 4, 'b': 9}, "
            "returned=None, raised=None)>"
        )

        with self.assertRaisesRegex(UnexpectedCallError, expected_message):
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

        with self.assertRaisesRegex(ValueError, 'foo'):
            do_math(5, 3)

    def test_with_classmethod(self):
        """Testing SpyOpRaise with classmethod"""
        self.agency.spy_on(
            MathClass.class_do_math,
            owner=MathClass,
            op=SpyOpRaise(ValueError('foo')))

        with self.assertRaisesRegex(ValueError, 'foo'):
            MathClass.class_do_math(5, 3)

    def test_with_unbound_method(self):
        """Testing SpyOpRaise with unbound method"""
        self.agency.spy_on(
            MathClass.do_math,
            owner=MathClass,
            op=SpyOpRaise(ValueError('foo')))

        obj = MathClass()

        with self.assertRaisesRegex(ValueError, 'foo'):
            obj.do_math(a=4, b=3)


class SpyOpRaiseInOrderTests(TestCase):
    """Unit tests for kgb.ops.SpyOpRaiseInOrder."""

    def test_with_function(self):
        """Testing SpyOpRaiseInOrder with function"""
        def do_math(a, b):
            return a + b

        self.agency.spy_on(
            do_math,
            op=SpyOpRaiseInOrder([
                ValueError('foo'),
                KeyError('bar'),
                AttributeError('foobar'),
            ]))

        with self.assertRaisesRegex(ValueError, 'foo'):
            do_math(5, 3)

        with self.assertRaisesRegex(KeyError, 'bar'):
            do_math(5, 3)

        with self.assertRaisesRegex(AttributeError, 'foobar'):
            do_math(5, 3)

        message = re.escape(
            "do_math was called 4 time(s), but only 3 call(s) were expected. "
            "Latest call: <SpyCall(args=(5, 3), kwargs={}, returned=None, "
            "raised=None)>"
        )

        with self.assertRaisesRegex(UnexpectedCallError, message):
            do_math(5, 3)

    def test_with_classmethod(self):
        """Testing SpyOpRaiseInOrder with classmethod"""
        self.agency.spy_on(
            MathClass.class_do_math,
            owner=MathClass,
            op=SpyOpRaiseInOrder([
                ValueError('foo'),
                KeyError('bar'),
                AttributeError('foobar'),
            ]))

        with self.assertRaisesRegex(ValueError, 'foo'):
            MathClass.class_do_math(5, 3)

        with self.assertRaisesRegex(KeyError, 'bar'):
            MathClass.class_do_math(5, 3)

        with self.assertRaisesRegex(AttributeError, 'foobar'):
            MathClass.class_do_math(5, 3)

        message = re.escape(
            "class_do_math was called 4 time(s), but only 3 call(s) were "
            "expected. Latest call: <SpyCall(args=(), kwargs={'a': 5, "
            "'b': 3}, returned=None, raised=None)>"
        )

        with self.assertRaisesRegex(UnexpectedCallError, message):
            MathClass.class_do_math(5, 3)

    def test_with_unbound_method(self):
        """Testing SpyOpRaiseInOrder with unbound method"""
        self.agency.spy_on(
            MathClass.do_math,
            owner=MathClass,
            op=SpyOpRaiseInOrder([
                ValueError('foo'),
                KeyError('bar'),
                AttributeError('foobar'),
            ]))

        obj = MathClass()

        with self.assertRaisesRegex(ValueError, 'foo'):
            obj.do_math(a=4, b=3)

        with self.assertRaisesRegex(KeyError, 'bar'):
            obj.do_math(a=4, b=3)

        with self.assertRaisesRegex(AttributeError, 'foobar'):
            obj.do_math(a=4, b=3)

        message = re.escape(
            "do_math was called 4 time(s), but only 3 call(s) were expected. "
            "Latest call: <SpyCall(args=(), kwargs={'a': 5, 'b': 3}, "
            "returned=None, raised=None)>"
        )

        with self.assertRaisesRegex(UnexpectedCallError, message):
            obj.do_math(5, 3)


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


class SpyOpReturnInOrderTests(TestCase):
    """Unit tests for kgb.ops.SpyOpReturnInOrder."""

    def test_with_function(self):
        """Testing SpyOpReturnInOrder with function"""
        def do_math(a, b):
            return a + b

        self.agency.spy_on(
            do_math,
            op=SpyOpReturnInOrder([
                'abc123',
                'def456',
                'ghi789',
            ]))

        self.assertEqual(do_math(5, 3), 'abc123')
        self.assertEqual(do_math(5, 3), 'def456')
        self.assertEqual(do_math(5, 3), 'ghi789')

        message = re.escape(
            "do_math was called 4 time(s), but only 3 call(s) were expected. "
            "Latest call: <SpyCall(args=(5, 3), kwargs={}, returned=None, "
            "raised=None)>"
        )

        with self.assertRaisesRegex(UnexpectedCallError, message):
            do_math(5, 3)

    def test_with_classmethod(self):
        """Testing SpyOpReturnInOrder with classmethod"""
        self.agency.spy_on(
            MathClass.class_do_math,
            owner=MathClass,
            op=SpyOpReturnInOrder([
                'abc123',
                'def456',
                'ghi789',
            ]))

        self.assertEqual(MathClass.class_do_math(5, 3), 'abc123')
        self.assertEqual(MathClass.class_do_math(5, 3), 'def456')
        self.assertEqual(MathClass.class_do_math(5, 3), 'ghi789')

        message = re.escape(
            "class_do_math was called 4 time(s), but only 3 call(s) were "
            "expected. Latest call: <SpyCall(args=(), kwargs={'a': 5, "
            "'b': 3}, returned=None, raised=None)>"
        )

        with self.assertRaisesRegex(UnexpectedCallError, message):
            MathClass.class_do_math(5, 3)

    def test_with_unbound_method(self):
        """Testing SpyOpReturnInOrder with unbound method"""
        self.agency.spy_on(
            MathClass.do_math,
            owner=MathClass,
            op=SpyOpReturnInOrder([
                'abc123',
                'def456',
                'ghi789',
            ]))

        obj = MathClass()

        self.assertEqual(obj.do_math(a=4, b=3), 'abc123')
        self.assertEqual(obj.do_math(a=4, b=3), 'def456')
        self.assertEqual(obj.do_math(a=4, b=3), 'ghi789')

        message = re.escape(
            "do_math was called 4 time(s), but only 3 call(s) were "
            "expected. Latest call: <SpyCall(args=(), kwargs={'a': 4, "
            "'b': 3}, returned=None, raised=None)>"
        )

        with self.assertRaisesRegex(UnexpectedCallError, message):
            obj.do_math(a=4, b=3)
