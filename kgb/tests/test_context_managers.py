from __future__ import unicode_literals

from kgb.contextmanagers import spy_on
from kgb.tests.base import MathClass, TestCase


class SpyOnTests(TestCase):
    """Unit tests for spies.contextmanagers.spy_on."""

    def test_spy_on(self):
        """Testing spy_on context manager"""
        obj = MathClass()

        with spy_on(obj.do_math):
            self.assertTrue(hasattr(obj.do_math, 'spy'))

            result = obj.do_math()
            self.assertEqual(result, 3)

        self.assertFalse(hasattr(obj.do_math, 'spy'))

    def test_expose_spy(self):
        """Testing spy_on exposes `spy` via context manager"""
        obj = MathClass()

        with spy_on(obj.do_math) as spy:
            self.assertTrue(hasattr(obj.do_math, 'spy'))
            self.assertIs(obj.do_math.spy, spy)

            result = obj.do_math()
            self.assertEqual(result, 3)

        self.assertFalse(hasattr(obj.do_math, 'spy'))
