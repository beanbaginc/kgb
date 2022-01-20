"""Unit tests for kgb.agency.SpyAgency."""

from __future__ import unicode_literals

from contextlib import contextmanager

import kgb.asserts
from kgb.agency import SpyAgency
from kgb.signature import FunctionSig
from kgb.tests.base import MathClass, TestCase


class SpyAgencyTests(TestCase):
    """Unit tests for kgb.agency.SpyAgency."""

    def test_spy_on(self):
        """Testing SpyAgency.spy_on"""
        obj = MathClass()

        spy = self.agency.spy_on(obj.do_math)
        self.assertEqual(self.agency.spies, set([spy]))

    def test_spy_for(self):
        """Testing SpyAgency.spy_for"""
        obj = MathClass()

        @self.agency.spy_for(obj.do_math, owner=obj)
        def my_func(_self, a=None, b=None, *args, **kwargs):
            """Some docs."""
            return 123

        self.assertEqual(obj.do_math(), 123)
        self.assertEqual(my_func(obj), 123)
        self.assertIs(obj.do_math.spy.func, my_func)

        # Make sure we decorated correctly.
        sig = FunctionSig(my_func)
        self.assertEqual(sig.func_name, 'my_func')
        self.assertEqual(sig.func_type, FunctionSig.TYPE_FUNCTION)
        self.assertEqual(my_func.__doc__, 'Some docs.')

    def test_unspy(self):
        """Testing SpyAgency.unspy"""
        obj = MathClass()
        orig_do_math = obj.do_math

        spy = self.agency.spy_on(obj.do_math)
        self.assertEqual(self.agency.spies, set([spy]))
        self.assertTrue(hasattr(obj.do_math, 'spy'))

        self.agency.unspy(obj.do_math)
        self.assertEqual(self.agency.spies, set())
        self.assertFalse(hasattr(obj.do_math, 'spy'))

        self.assertEqual(obj.do_math, orig_do_math)

    def test_unspy_all(self):
        """Testing SpyAgency.unspy_all"""
        obj = MathClass()
        orig_do_math = obj.do_math

        spy1 = self.agency.spy_on(obj.do_math)
        spy2 = self.agency.spy_on(MathClass.class_do_math)

        self.assertEqual(self.agency.spies, set([spy1, spy2]))
        self.assertTrue(hasattr(obj.do_math, 'spy'))
        self.assertTrue(hasattr(MathClass.class_do_math, 'spy'))

        self.agency.unspy_all()
        self.assertEqual(self.agency.spies, set())

        self.assertEqual(obj.do_math, orig_do_math)
        self.assertEqual(MathClass.class_do_math, self.orig_class_do_math)
        self.assertFalse(hasattr(obj.do_math, 'spy'))
        self.assertFalse(hasattr(MathClass.class_do_math, 'spy'))


class TestCaseMixinTests(SpyAgency, TestCase):
    """Unit tests for SpyAgency as a TestCase mixin."""

    def test_spy_on(self):
        """Testing SpyAgency mixed in with spy_on"""
        obj = MathClass()

        self.spy_on(obj.do_math)
        self.assertTrue(hasattr(obj.do_math, 'spy'))

        result = obj.do_math()
        self.assertEqual(result, 3)

    def test_spy_for(self):
        """Testing SpyAgency mixed in with spy_for"""
        obj = MathClass()

        @self.spy_for(obj.do_math)
        def my_func(_self, a=None, b=None, *args, **kwargs):
            """Some docs."""
            return 123

        self.assertEqual(obj.do_math(), 123)
        self.assertEqual(my_func(obj), 123)
        self.assertIs(obj.do_math.spy.func, my_func)

        # Make sure we decorated correctly.
        sig = FunctionSig(my_func)
        self.assertEqual(sig.func_name, 'my_func')
        self.assertEqual(sig.func_type, FunctionSig.TYPE_FUNCTION)
        self.assertEqual(my_func.__doc__, 'Some docs.')

    def test_tear_down(self):
        """Testing SpyAgency mixed in with tearDown"""
        obj = MathClass()
        orig_do_math = obj.do_math
        func_dict = obj.do_math.__dict__.copy()

        self.spy_on(obj.do_math)
        self.assertTrue(hasattr(obj.do_math, 'spy'))
        self.assertNotEqual(func_dict, obj.do_math.__dict__)

        self.tearDown()

        self.assertEqual(obj.do_math, orig_do_math)
        self.assertFalse(hasattr(obj.do_math, 'spy'))
        self.assertEqual(func_dict, obj.do_math.__dict__)

    def test_assertHasSpy_with_spy(self):
        """Testing SpyAgency.assertHasSpy with spy"""
        self.spy_on(MathClass.do_math,
                    owner=MathClass)

        # These should not fail.
        self.assertHasSpy(MathClass.do_math)
        self.assertHasSpy(MathClass.do_math.spy)

        # Check the aliases.
        self.assert_has_spy(MathClass.do_math)
        kgb.asserts.assert_has_spy(MathClass.do_math)

    def test_assertHasSpy_without_spy(self):
        """Testing SpyAgency.assertHasSpy without spy"""
        with self._check_assertion('do_math has not been spied on.'):
            self.assertHasSpy(MathClass.do_math)

    def test_assertSpyCalled_with_called(self):
        """Testing SpyAgency.assertSpyCalled with spy called"""
        obj = MathClass()
        self.spy_on(obj.do_math)

        obj.do_math()

        # These should not fail.
        self.assertSpyCalled(obj.do_math)
        self.assertSpyCalled(obj.do_math.spy)

        # Check the aliases.
        self.assert_spy_called(obj.do_math)
        kgb.asserts.assert_spy_called(obj.do_math)

    def test_assertSpyCalled_without_called(self):
        """Testing SpyAgency.assertSpyCalled without spy called"""
        obj = MathClass()
        self.spy_on(obj.do_math)

        msg = 'do_math was not called.'

        with self._check_assertion(msg):
            self.assertSpyCalled(obj.do_math)

        with self._check_assertion(msg):
            self.assertSpyCalled(obj.do_math.spy)

    def test_assertSpyNotCalled_without_called(self):
        """Testing SpyAgency.assertSpyNotCalled without spy called"""
        obj = MathClass()
        self.spy_on(obj.do_math)

        # These should not fail.
        self.assertSpyNotCalled(obj.do_math)
        self.assertSpyNotCalled(obj.do_math.spy)

        # Check the aliases.
        self.assert_spy_not_called(obj.do_math)
        kgb.asserts.assert_spy_not_called(obj.do_math)

    def test_assertSpyNotCalled_with_called(self):
        """Testing SpyAgency.assertSpyNotCalled with spy called"""
        obj = MathClass()
        self.spy_on(obj.do_math)

        obj.do_math(3, b=4)
        obj.do_math(2, b=9)

        msg = (
            "do_math was called 2 times:\n"
            "\n"
            "Call 0:\n"
            "  args=()\n"
            "  kwargs={'a': 3, 'b': 4}\n"
            "\n"
            "Call 1:\n"
            "  args=()\n"
            "  kwargs={'a': 2, 'b': 9}"
        )

        with self._check_assertion(msg):
            self.assertSpyNotCalled(obj.do_math)

        with self._check_assertion(msg):
            self.assertSpyNotCalled(obj.do_math.spy)

    def test_assertSpyCallCount_with_expected_count(self):
        """Testing SpyAgency.assertSpyCallCount with expected call count"""
        obj = MathClass()
        self.spy_on(obj.do_math)

        obj.do_math()
        obj.do_math()

        # These should not fail.
        self.assertSpyCallCount(obj.do_math, 2)
        self.assertSpyCallCount(obj.do_math.spy, 2)

        # Check the aliases.
        self.assert_spy_call_count(obj.do_math, 2)
        kgb.asserts.assert_spy_call_count(obj.do_math, 2)

    def test_assertSpyCallCount_without_expected_count(self):
        """Testing SpyAgency.assertSpyCallCount without expected call count"""
        obj = MathClass()
        self.spy_on(obj.do_math)

        obj.do_math()

        with self._check_assertion('do_math was called 1 time, not 2.'):
            self.assertSpyCallCount(obj.do_math, 2)

        # Let's bump and test a plural result.
        obj.do_math()

        with self._check_assertion('do_math was called 2 times, not 3.'):
            self.assertSpyCallCount(obj.do_math.spy, 3)

    def test_assertSpyCalledWith_with_expected_arguments(self):
        """Testing SpyAgency.assertSpyCalledWith with expected arguments"""
        obj = MathClass()
        self.spy_on(obj.do_math)

        obj.do_math(1, b=4)
        obj.do_math(2, b=9)

        # These should not fail.
        self.assertSpyCalledWith(obj.do_math, a=1, b=4)
        self.assertSpyCalledWith(obj.do_math.calls[0], a=1, b=4)
        self.assertSpyCalledWith(obj.do_math.spy, a=2, b=9)
        self.assertSpyCalledWith(obj.do_math.spy.calls[1], a=2, b=9)

        # Check the aliases.
        self.assert_spy_called_with(obj.do_math, a=1, b=4)
        kgb.asserts.assert_spy_called_with(obj.do_math, a=1, b=4)

    def test_assertSpyCalledWith_without_expected_arguments(self):
        """Testing SpyAgency.assertSpyCalledWith without expected arguments"""
        obj = MathClass()
        self.spy_on(obj.do_math)

        obj.do_math(1, b=4)
        obj.do_math(2, b=9)

        msg = (
            "No call to do_math was passed args=(), kwargs={'x': 4, 'z': 1}.\n"
            "\n"
            "The following calls were recorded:\n"
            "\n"
            "Call 0:\n"
            "  args=()\n"
            "  kwargs={'a': 1, 'b': 4}\n"
            "\n"
            "Call 1:\n"
            "  args=()\n"
            "  kwargs={'a': 2, 'b': 9}"
        )

        with self._check_assertion(msg):
            self.assertSpyCalledWith(obj.do_math, x=4, z=1)

        with self._check_assertion(msg):
            self.assertSpyCalledWith(obj.do_math.spy, x=4, z=1)

        msg = (
            "This call to do_math was not passed args=(),"
            " kwargs={'x': 4, 'z': 1}.\n"
            "\n"
            "It was called with:\n"
            "\n"
            "args=()\n"
            "kwargs={'a': 1, 'b': 4}"
        )

        with self._check_assertion(msg):
            self.assertSpyCalledWith(obj.do_math.spy.calls[0], x=4, z=1)

    def test_assertSpyNotCalledWith_with_unexpected_arguments(self):
        """Testing SpyAgency.assertSpyNotCalledWith with unexpected arguments
        """
        obj = MathClass()
        self.spy_on(obj.do_math)

        obj.do_math(1, b=4)
        obj.do_math(2, b=9)

        # These should not fail.
        self.assertSpyNotCalledWith(obj.do_math, a=1, b=3)
        self.assertSpyNotCalledWith(obj.do_math.calls[0], a=1, b=3)
        self.assertSpyNotCalledWith(obj.do_math.spy, a=1, b=9)
        self.assertSpyNotCalledWith(obj.do_math.spy.calls[1], a=1, b=9)

        # Check the aliases.
        self.assert_spy_not_called_with(obj.do_math, a=1, b=3)
        kgb.asserts.assert_spy_not_called_with(obj.do_math, a=1, b=3)

    def test_assertSpyNotCalledWith_without_unexpected_arguments(self):
        """Testing SpyAgency.assertSpyNotCalledWith without unexpected
        arguments
        """
        obj = MathClass()
        self.spy_on(obj.do_math)

        obj.do_math(1, b=4)
        obj.do_math(2, b=9)

        msg = (
            "A call to do_math was unexpectedly passed args=(), "
            "kwargs={'a': 1, 'b': 4}.\n"
            "\n"
            "The following calls were recorded:\n"
            "\n"
            "Call 0:\n"
            "  args=()\n"
            "  kwargs={'a': 1, 'b': 4}\n"
            "\n"
            "Call 1:\n"
            "  args=()\n"
            "  kwargs={'a': 2, 'b': 9}"
        )

        with self._check_assertion(msg):
            self.assertSpyNotCalledWith(obj.do_math, a=1, b=4)

        with self._check_assertion(msg):
            self.assertSpyNotCalledWith(obj.do_math.spy, a=1, b=4)

        msg = (
            "This call to do_math was unexpectedly passed args=(),"
            " kwargs={'a': 2, 'b': 9}."
        )

        with self._check_assertion(msg):
            self.assertSpyNotCalledWith(obj.do_math.spy.calls[1], a=2, b=9)

    def test_assertSpyLastCalledWith_with_expected_arguments(self):
        """Testing SpyAgency.assertSpyLastCalledWith with expected arguments"""
        obj = MathClass()
        self.spy_on(obj.do_math)

        obj.do_math(1, b=4)
        obj.do_math(2, b=9)

        # These should not fail.
        self.assertSpyLastCalledWith(obj.do_math, a=2, b=9)
        self.assertSpyLastCalledWith(obj.do_math.spy, a=2, b=9)

        # Check the aliases.
        self.assert_spy_last_called_with(obj.do_math, a=2, b=9)
        kgb.asserts.assert_spy_last_called_with(obj.do_math, a=2, b=9)

    def test_assertSpyLastCalledWith_without_expected_arguments(self):
        """Testing SpyAgency.assertSpyLastCalledWith without expected
        arguments
        """
        obj = MathClass()
        self.spy_on(obj.do_math)

        obj.do_math(1, b=4)
        obj.do_math(2, b=9)

        msg = (
            "The last call to do_math was not passed args=(),"
            " kwargs={'a': 1, 'b': 4}.\n"
            "\n"
            "It was last called with:\n"
            "\n"
            "args=()\n"
            "kwargs={'a': 2, 'b': 9}"
        )

        with self._check_assertion(msg):
            self.assertSpyLastCalledWith(obj.do_math, a=1, b=4)

        with self._check_assertion(msg):
            self.assertSpyLastCalledWith(obj.do_math.spy, a=1, b=4)

    def test_assertSpyReturned_with_expected_return(self):
        """Testing SpyAgency.assertSpyReturned with expected return value"""
        obj = MathClass()
        self.spy_on(obj.do_math)

        obj.do_math(1, b=4)
        obj.do_math(2, b=9)

        # These should not fail.
        self.assertSpyReturned(obj.do_math, 5)
        self.assertSpyReturned(obj.do_math.calls[0], 5)
        self.assertSpyReturned(obj.do_math.spy, 11)
        self.assertSpyReturned(obj.do_math.spy.calls[1], 11)

        # Check the aliases.
        self.assert_spy_returned(obj.do_math, 5)
        kgb.asserts.assert_spy_returned(obj.do_math, 5)

    def test_assertSpyReturned_without_expected_return(self):
        """Testing SpyAgency.assertSpyReturned without expected return value"""
        obj = MathClass()
        self.spy_on(obj.do_math)

        obj.do_math(1, b=4)
        obj.do_math(2, b=9)

        msg = (
            'No call to do_math returned 100.\n'
            '\n'
            'The following values have been returned:\n'
            '\n'
            'Call 0:\n'
            '  5\n'
            '\n'
            'Call 1:\n'
            '  11'
        )

        with self._check_assertion(msg):
            self.assertSpyReturned(obj.do_math, 100)

        with self._check_assertion(msg):
            self.assertSpyReturned(obj.do_math.spy, 100)

        msg = (
            'This call to do_math did not return 100.\n'
            '\n'
            'It returned:\n'
            '\n'
            '5'
        )

        with self._check_assertion(msg):
            self.assertSpyReturned(obj.do_math.calls[0], 100)

    def test_assertSpyLastReturned_with_expected_return(self):
        """Testing SpyAgency.assertSpyLastReturned with expected return value
        """
        obj = MathClass()
        self.spy_on(obj.do_math)

        obj.do_math(1, b=4)
        obj.do_math(2, b=9)

        # These should not fail.
        self.assertSpyLastReturned(obj.do_math, 11)
        self.assertSpyLastReturned(obj.do_math.spy, 11)

        # Check the aliases.
        self.assert_spy_last_returned(obj.do_math, 11)
        kgb.asserts.assert_spy_last_returned(obj.do_math, 11)

    def test_assertSpyLastReturned_without_expected_return(self):
        """Testing SpyAgency.assertSpyLastReturned without expected return
        value
        """
        obj = MathClass()
        self.spy_on(obj.do_math)

        obj.do_math(1, b=4)
        obj.do_math(2, b=9)

        msg = (
            'The last call to do_math did not return 5.\n'
            '\n'
            'It last returned:\n'
            '\n'
            '11'
        )

        with self._check_assertion(msg):
            self.assertSpyLastReturned(obj.do_math, 5)

        with self._check_assertion(msg):
            self.assertSpyLastReturned(obj.do_math.spy, 5)

    def test_assertSpyRaised_with_expected_exception(self):
        """Testing SpyAgency.assertSpyRaised with expected exception raised"""
        def _do_math(_self, a, *args, **kwargs):
            if a == 1:
                raise KeyError
            elif a == 2:
                raise ValueError

        obj = MathClass()
        self.spy_on(obj.do_math, call_fake=_do_math)

        try:
            obj.do_math(1)
        except KeyError:
            pass

        try:
            obj.do_math(2)
        except ValueError:
            pass

        # These should not fail.
        self.assertSpyRaised(obj.do_math, KeyError)
        self.assertSpyRaised(obj.do_math.calls[0], KeyError)
        self.assertSpyRaised(obj.do_math.spy, ValueError)
        self.assertSpyRaised(obj.do_math.spy.calls[1], ValueError)

        # Check the aliases.
        self.assert_spy_raised(obj.do_math, KeyError)
        kgb.asserts.assert_spy_raised(obj.do_math, KeyError)

    def test_assertSpyRaised_with_expected_no_exception(self):
        """Testing SpyAgency.assertSpyRaised with expected completions without
        exceptions
        """
        obj = MathClass()
        self.spy_on(obj.do_math)

        obj.do_math(1)
        obj.do_math(2)

        # These should not fail.
        self.assertSpyRaised(obj.do_math, None)
        self.assertSpyRaised(obj.do_math.calls[0], None)
        self.assertSpyRaised(obj.do_math.spy, None)
        self.assertSpyRaised(obj.do_math.spy.calls[1], None)

    def test_assertSpyRaised_without_expected_exception(self):
        """Testing SpyAgency.assertSpyRaised without expected exception raised
        """
        def _do_math(_self, a, *args, **kwargs):
            if a == 1:
                raise KeyError
            elif a == 2:
                raise ValueError

        obj = MathClass()
        self.spy_on(obj.do_math, call_fake=_do_math)

        # First test without any exceptions raised
        try:
            obj.do_math(1)
        except KeyError:
            pass

        try:
            obj.do_math(2)
        except ValueError:
            pass

        msg = (
            'No call to do_math raised AttributeError.\n'
            '\n'
            'The following exceptions have been raised:\n'
            '\n'
            'Call 0:\n'
            '  KeyError\n'
            '\n'
            'Call 1:\n'
            '  ValueError'
        )

        with self._check_assertion(msg):
            self.assertSpyRaised(obj.do_math, AttributeError)

        with self._check_assertion(msg):
            self.assertSpyRaised(obj.do_math.spy, AttributeError)

        msg = (
            'This call to do_math did not raise AttributeError. It raised '
            'KeyError.'
        )

        with self._check_assertion(msg):
            self.assertSpyRaised(obj.do_math.calls[0], AttributeError)

    def test_assertSpyRaised_without_raised(self):
        """Testing SpyAgency.assertSpyRaised without any exceptions raised"""
        obj = MathClass()
        self.spy_on(obj.do_math)

        # First test without any exceptions raised
        obj.do_math(1)
        obj.do_math(2)

        msg = 'No call to do_math raised an exception.'

        with self._check_assertion(msg):
            self.assertSpyRaised(obj.do_math, AttributeError)

        with self._check_assertion(msg):
            self.assertSpyRaised(obj.do_math.spy, AttributeError)

        msg = 'This call to do_math did not raise an exception.'

        with self._check_assertion(msg):
            self.assertSpyRaised(obj.do_math.spy.calls[0], AttributeError)

    def test_assertSpyLastRaised_with_expected_exception(self):
        """Testing SpyAgency.assertSpyLastRaised with expected exception
        raised
        """
        def _do_math(_self, a, *args, **kwargs):
            if a == 1:
                raise KeyError
            elif a == 2:
                raise ValueError

        obj = MathClass()
        self.spy_on(obj.do_math, call_fake=_do_math)

        try:
            obj.do_math(1)
        except KeyError:
            pass

        try:
            obj.do_math(2)
        except ValueError:
            pass

        # These should not fail.
        self.assertSpyLastRaised(obj.do_math, ValueError)
        self.assertSpyLastRaised(obj.do_math.spy, ValueError)

        # Check the aliases.
        self.assert_spy_last_raised(obj.do_math, ValueError)
        kgb.asserts.assert_spy_last_raised(obj.do_math, ValueError)

    def test_assertSpyLastRaised_with_expected_no_exception(self):
        """Testing SpyAgency.assertSpyLastRaised with expected completion
        without raising
        """
        obj = MathClass()
        self.spy_on(obj.do_math)

        obj.do_math(1)
        obj.do_math(2)

        # These should not fail.
        self.assertSpyLastRaised(obj.do_math, None)
        self.assertSpyLastRaised(obj.do_math.spy, None)

    def test_assertSpyLastRaised_without_expected_exception(self):
        """Testing SpyAgency.assertSpyLastRaised without expected exception
        raised
        """
        def _do_math(_self, a, *args, **kwargs):
            if a == 1:
                raise KeyError
            elif a == 2:
                raise ValueError

        obj = MathClass()
        self.spy_on(obj.do_math, call_fake=_do_math)

        try:
            obj.do_math(1)
        except KeyError:
            pass

        try:
            obj.do_math(2)
        except ValueError:
            pass

        msg = (
            'The last call to do_math did not raise KeyError. It last '
            'raised ValueError.'
        )

        with self._check_assertion(msg):
            self.assertSpyLastRaised(obj.do_math, KeyError)

        with self._check_assertion(msg):
            self.assertSpyLastRaised(obj.do_math.spy, KeyError)

    def test_assertSpyLastRaised_without_raised(self):
        """Testing SpyAgency.assertSpyLastRaised without exception raised"""
        obj = MathClass()
        self.spy_on(obj.do_math)

        obj.do_math(1)
        obj.do_math(2)

        msg = 'The last call to do_math did not raise an exception.'

        with self._check_assertion(msg):
            self.assertSpyLastRaised(obj.do_math, KeyError)

        with self._check_assertion(msg):
            self.assertSpyLastRaised(obj.do_math.spy, KeyError)

    def test_assertSpyRaisedMessage_with_expected(self):
        """Testing SpyAgency.assertSpyRaised with expected exception and
        message raised
        """
        def _do_math(_self, a, *args, **kwargs):
            if a == 1:
                raise AttributeError('Bad key!')
            elif a == 2:
                raise ValueError('Bad value!')

        obj = MathClass()
        self.spy_on(obj.do_math, call_fake=_do_math)

        try:
            obj.do_math(1)
        except AttributeError:
            pass

        try:
            obj.do_math(2)
        except ValueError:
            pass

        # These should not fail.
        self.assertSpyRaisedMessage(obj.do_math, AttributeError, 'Bad key!')
        self.assertSpyRaisedMessage(obj.do_math.calls[0], AttributeError,
                                    'Bad key!')
        self.assertSpyRaisedMessage(obj.do_math.spy, ValueError, 'Bad value!')
        self.assertSpyRaisedMessage(obj.do_math.spy.calls[1], ValueError,
                                    'Bad value!')

        # Check the aliases.
        self.assert_spy_raised_message(obj.do_math, AttributeError, 'Bad key!')
        kgb.asserts.assert_spy_raised_message(obj.do_math, AttributeError,
                                              'Bad key!')

    def test_assertSpyRaisedMessage_without_expected(self):
        """Testing SpyAgency.assertSpyRaisedMessage without expected exception
        and message raised
        """
        def _do_math(_self, a, *args, **kwargs):
            if a == 1:
                raise AttributeError('Bad key!')
            elif a == 2:
                raise ValueError('Bad value!')

        obj = MathClass()
        self.spy_on(obj.do_math, call_fake=_do_math)

        try:
            obj.do_math(1)
        except AttributeError:
            pass

        try:
            obj.do_math(2)
        except ValueError:
            pass

        # Note that we may end up with different string types with different
        # prefixes on different versions of Python, so we need to repr these.
        msg = (
            'No call to do_math raised AttributeError with message %r.\n'
            '\n'
            'The following exceptions have been raised:\n'
            '\n'
            'Call 0:\n'
            '  exception=AttributeError\n'
            '  message=%r\n'
            '\n'
            'Call 1:\n'
            '  exception=ValueError\n'
            '  message=%r'
            % ('Bad key...', str('Bad key!'), str('Bad value!'))
        )

        with self._check_assertion(msg):
            self.assertSpyRaisedMessage(obj.do_math, AttributeError,
                                        'Bad key...')

        with self._check_assertion(msg):
            self.assertSpyRaisedMessage(obj.do_math.spy, AttributeError,
                                        'Bad key...')

        msg = (
            'This call to do_math did not raise AttributeError with message'
            ' %r.\n'
            '\n'
            'It raised:\n'
            '\n'
            'exception=AttributeError\n'
            'message=%r'
            % ('Bad key...', str('Bad key!'))
        )

        with self._check_assertion(msg):
            self.assertSpyRaisedMessage(obj.do_math.calls[0], AttributeError,
                                        'Bad key...')

    def test_assertSpyRaisedMessage_without_raised(self):
        """Testing SpyAgency.assertSpyRaisedMessage without exception raised
        """
        obj = MathClass()
        self.spy_on(obj.do_math)

        obj.do_math(1)
        obj.do_math(2)

        msg = 'No call to do_math raised an exception.'

        with self._check_assertion(msg):
            self.assertSpyRaisedMessage(obj.do_math, KeyError, '...')

        with self._check_assertion(msg):
            self.assertSpyRaisedMessage(obj.do_math.spy, KeyError, '...')

    def test_assertSpyLastRaisedMessage_with_expected(self):
        """Testing SpyAgency.assertSpyLastRaised with expected exception and
        message raised
        """
        def _do_math(_self, a, *args, **kwargs):
            if a == 1:
                raise AttributeError('Bad key!')
            elif a == 2:
                raise ValueError('Bad value!')

        obj = MathClass()
        self.spy_on(obj.do_math, call_fake=_do_math)

        try:
            obj.do_math(1)
        except AttributeError:
            pass

        try:
            obj.do_math(2)
        except ValueError:
            pass

        # These should not fail.
        self.assertSpyLastRaisedMessage(obj.do_math, ValueError, 'Bad value!')
        self.assertSpyLastRaisedMessage(obj.do_math.spy, ValueError,
                                        'Bad value!')

        # Check the aliases.
        self.assert_spy_last_raised_message(obj.do_math, ValueError,
                                            'Bad value!')
        kgb.asserts.assert_spy_last_raised_message(obj.do_math, ValueError,
                                                   'Bad value!')

    def test_assertSpyLastRaisedMessage_without_expected(self):
        """Testing SpyAgency.assertSpyLastRaisedMessage without expected
        exception and message raised
        """
        def _do_math(_self, a, *args, **kwargs):
            if a == 1:
                raise AttributeError('Bad key!')
            elif a == 2:
                raise ValueError('Bad value!')

        obj = MathClass()
        self.spy_on(obj.do_math, call_fake=_do_math)

        try:
            obj.do_math(1)
        except AttributeError:
            pass

        try:
            obj.do_math(2)
        except ValueError:
            pass

        # Note that we may end up with different string types with different
        # prefixes on different versions of Python, so we need to repr these.
        msg = (
            'The last call to do_math did not raise AttributeError with '
            'message %r.\n'
            '\n'
            'It last raised:\n'
            '\n'
            'exception=ValueError\n'
            'message=%r'
            % ('Bad key!', str('Bad value!'))
        )

        with self._check_assertion(msg):
            self.assertSpyLastRaisedMessage(obj.do_math, AttributeError,
                                            'Bad key!')

        with self._check_assertion(msg):
            self.assertSpyLastRaisedMessage(obj.do_math.spy, AttributeError,
                                            'Bad key!')

    def test_assertSpyLastRaisedMessage_without_raised(self):
        """Testing SpyAgency.assertSpyLastRaisedMessage without exception
        raised
        """
        obj = MathClass()
        self.spy_on(obj.do_math)

        obj.do_math(1)
        obj.do_math(2)

        msg = 'The last call to do_math did not raise an exception.'

        with self._check_assertion(msg):
            self.assertSpyLastRaisedMessage(obj.do_math, KeyError, '...')

        with self._check_assertion(msg):
            self.assertSpyLastRaisedMessage(obj.do_math.spy, KeyError, '...')

    @contextmanager
    def _check_assertion(self, msg):
        """Check that the expected assertion and message is raised.

        Args:
            msg (unicode):
                The assertion message.

        Context:
            The context used to run an assertion.
        """
        with self.assertRaises(AssertionError) as ctx:
            yield

        self.assertEqual(str(ctx.exception), msg)
