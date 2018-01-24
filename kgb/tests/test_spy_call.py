from __future__ import unicode_literals

from kgb.spies import text_type
from kgb.tests.base import MathClass, TestCase


class SpyCallTests(TestCase):
    """Test cases for kgb.spies.SpyCall."""

    def test_called_with(self):
        """Testing SpyCall.called_with"""
        obj = MathClass()
        self.agency.spy_on(obj.do_math_mixed)

        obj.do_math_mixed(1, b=2)
        obj.do_math_mixed(3, b=4)

        call = obj.do_math_mixed.calls[0]
        self.assertTrue(call.called_with(1, b=2))
        self.assertTrue(call.called_with(a=1, b=2))
        self.assertFalse(call.called_with(3, b=4))
        self.assertFalse(call.called_with(1, 2))

    def test_called_with_and_keyword_args(self):
        """Testing SpyCall.called_with and keyword arguments"""
        obj = MathClass()
        self.agency.spy_on(obj.do_math_mixed)

        obj.do_math_mixed(a=1, b=2)
        obj.do_math_mixed(a=3, b=4)

        call = obj.do_math_mixed.calls[0]
        self.assertTrue(call.called_with(1, b=2))
        self.assertTrue(call.called_with(a=1, b=2))
        self.assertFalse(call.called_with(1, 2))
        self.assertFalse(call.called_with(3, b=4))

    def test_called_with_and_partial_args(self):
        """Testing SpyCall.called_with and partial arguments"""
        obj = MathClass()
        self.agency.spy_on(obj.do_math_mixed)

        obj.do_math_mixed(1, 2)
        obj.do_math_mixed(3, 4)

        call = obj.do_math_mixed.calls[0]
        self.assertTrue(call.called_with(1))
        self.assertFalse(call.called_with(1, 2, 3))
        self.assertFalse(call.called_with(3))

    def test_called_with_and_partial_kwargs(self):
        """Testing SpyCall.called_with and partial keyword arguments"""
        obj = MathClass()
        self.agency.spy_on(obj.do_math_mixed)

        obj.do_math_mixed(a=1, b=2)
        obj.do_math_mixed(a=3, b=4)

        call = obj.do_math_mixed.calls[0]
        self.assertTrue(call.called_with(1))
        self.assertTrue(call.called_with(b=2))
        self.assertTrue(call.called_with(a=1))
        self.assertFalse(call.called_with(a=4))
        self.assertFalse(call.called_with(a=1, b=2, c=3))
        self.assertFalse(call.called_with(a=3, b=2))

    def test_returned(self):
        """Testing SpyCall.returned"""
        obj = MathClass()
        self.agency.spy_on(obj.do_math_mixed)

        obj.do_math_mixed(1, 2)
        obj.do_math_mixed(3, 4)

        call = obj.do_math_mixed.calls[0]
        self.assertTrue(call.returned(3))
        self.assertFalse(call.returned(7))
        self.assertFalse(call.returned(None))

    def test_raised(self):
        """Testing SpyCall.raised"""
        obj = MathClass()
        self.agency.spy_on(obj.do_math)

        with self.assertRaises(TypeError):
            obj.do_math(1, 'a')

        call = obj.do_math.calls[0]
        self.assertTrue(call.raised(TypeError))
        self.assertFalse(call.raised(ValueError))
        self.assertFalse(call.raised(None))

    def test_raised_with_message(self):
        """Testing SpyCall.raised_with_message"""
        obj = MathClass()
        self.agency.spy_on(obj.do_math)

        with self.assertRaises(TypeError):
            obj.do_math(1, 'a')

        call = obj.do_math.calls[0]
        self.assertTrue(call.raised_with_message(
            TypeError,
            "unsupported operand type(s) for +: 'int' and '%s'"
            % text_type.__name__))
        self.assertFalse(call.raised_with_message(
            ValueError,
            "unsupported operand type(s) for +: 'int' and '%s'"
            % text_type.__name__))
        self.assertFalse(call.raised_with_message(TypeError, None))
