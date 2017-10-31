from __future__ import unicode_literals

from kgb.contextmanagers import spy_on
from kgb.spies import FunctionSpy
from kgb.tests.base import MathClass, TestCase


class SpyOnTests(TestCase):
    """Unit tests for spies.contextmanagers.spy_on."""

    def test_spy_on(self):
        """Testing spy_on context manager"""
        obj = MathClass()
        orig_do_math = obj.do_math

        with spy_on(obj.do_math):
            self.assertTrue(isinstance(obj.do_math, FunctionSpy))

            result = obj.do_math()
            self.assertEqual(result, 3)

        self.assertEqual(obj.do_math, orig_do_math)

    def test_expose_spy(self):
        """Testing spy_on exposes `spy` via context manager"""
        obj = MathClass()
        orig_do_math = obj.do_math

        with spy_on(obj.do_math) as spy:
            self.assertTrue(isinstance(spy, FunctionSpy))

            result = obj.do_math()
            self.assertEqual(result, 3)

        self.assertEqual(obj.do_math, orig_do_math)
