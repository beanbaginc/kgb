from __future__ import with_statement
import unittest

from kgb.agency import SpyAgency
from kgb.contextmanagers import spy_on
from kgb.spies import FunctionSpy


def something_awesome():
    return 'Tada!'


def fake_something_awesome():
    return '\o/'


def fake_do_math(self, a=1, b=2):
    return a - b


def fake_class_do_math(self, a=1, b=2):
    return a - b


class MathClass(object):
    def do_math(self, a=1, b=2):
        return a + b

    @classmethod
    def class_do_math(cls, a=2, b=5):
        return a * b


class BaseTestCase(unittest.TestCase):
    """Base class for test cases for kgb."""
    def setUp(self):
        self.agency = SpyAgency()
        self.orig_class_do_math = MathClass.class_do_math

    def tearDown(self):
        MathClass.class_do_math = self.orig_class_do_math
        self.agency.unspy_all()


class FunctionSpyTests(BaseTestCase):
    """Test cases for FunctionSpy."""
    def test_construction_with_call_precedence(self):
        """Testing FunctionSpy construction with call option precedence"""
        spy = self.agency.spy_on(something_awesome,
                                 call_fake=fake_something_awesome,
                                 call_original=True)
        self.assertEqual(spy.func, fake_something_awesome)

    def test_construction_with_call_fake(self):
        """Testing FunctionSpy construction with call_fake"""
        spy = self.agency.spy_on(something_awesome,
                                 call_fake=fake_something_awesome)

        self.assertTrue(hasattr(something_awesome, 'spy'))
        self.assertEqual(something_awesome.spy, spy)
        self.assertEqual(spy.func.func_name, fake_something_awesome.func_name)
        self.assertEqual(spy.orig_func, something_awesome)
        self.assertEqual(spy.func_name, 'something_awesome')
        self.assertEqual(spy.owner, None)

    def test_construction_with_call_fake_and_bound_method(self):
        """Testing FunctionSpy construction with call_fake and bound method"""
        obj = MathClass()
        orig_do_math = obj.do_math

        spy = self.agency.spy_on(obj.do_math, call_fake=fake_do_math)

        self.assertEqual(obj.do_math, spy)
        self.assertEqual(spy.func, fake_do_math)
        self.assertEqual(spy.orig_func, orig_do_math)
        self.assertEqual(spy.func_name, 'do_math')
        self.assertEqual(spy.owner, obj)

    def test_construction_with_call_fake_and_classmethod(self):
        """Testing FunctionSpy construction with call_fake and classmethod"""
        def fake_class_do_math(cls):
            return 42

        spy = self.agency.spy_on(MathClass.class_do_math,
                                 call_fake=fake_class_do_math)

        self.assertEqual(MathClass.class_do_math, spy)
        self.assertEqual(spy.func, fake_class_do_math)
        self.assertEqual(spy.orig_func, self.orig_class_do_math)
        self.assertEqual(spy.func_name, 'class_do_math')
        self.assertEqual(spy.owner, MathClass)

    def test_construction_with_call_original_false(self):
        """Testing FunctionSpy construction with call_original=False"""
        obj = MathClass()
        spy = self.agency.spy_on(obj.do_math, call_original=False)

        self.assertEqual(spy.func, None)
        self.assertEqual(obj.do_math, spy)
        self.assertEqual(spy.func_name, 'do_math')
        self.assertEqual(spy.owner, obj)

    def test_construction_with_call_original_true(self):
        """Testing FunctionSpy construction with call_original=True"""
        spy = self.agency.spy_on(something_awesome, call_original=True)

        self.assertTrue(hasattr(something_awesome, 'spy'))
        self.assertEqual(something_awesome.spy, spy)
        self.assertEqual(spy.func.func_name, something_awesome.func_name)
        self.assertEqual(spy.orig_func, something_awesome)
        self.assertEqual(spy.func_name, 'something_awesome')
        self.assertEqual(spy.owner, None)

    def test_construction_with_call_original_true_and_bound_method(self):
        """Testing FunctionSpy construction with call_original=True and bound method"""
        obj = MathClass()
        orig_do_math = obj.do_math

        spy = self.agency.spy_on(obj.do_math, call_original=True)

        self.assertEqual(spy.func, orig_do_math)
        self.assertEqual(obj.do_math, spy)
        self.assertEqual(spy.func_name, 'do_math')
        self.assertEqual(spy.owner, obj)

    def test_construction_with_call_original_and_classmethod(self):
        """Testing FunctionSpy construction with call_original and classmethod"""
        spy = self.agency.spy_on(MathClass.class_do_math, call_original=True)

        self.assertEqual(spy.func, self.orig_class_do_math)
        self.assertEqual(MathClass.class_do_math, spy)
        self.assertEqual(spy.func_name, 'class_do_math')
        self.assertEqual(spy.owner, MathClass)

    def test_call_with_call_fake(self):
        """Testing FunctionSpy calls with call_fake"""
        self.agency.spy_on(something_awesome,
                           call_fake=fake_something_awesome)
        result = something_awesome()

        self.assertEqual(result, '\o/')
        self.assertEqual(len(something_awesome.spy.calls), 1)
        self.assertEqual(len(something_awesome.spy.calls[0].args), 0)
        self.assertEqual(len(something_awesome.spy.calls[0].kwargs), 0)

    def test_call_with_call_fake_and_bound_method(self):
        """Testing FunctionSpy calls with call_fake and bound method"""
        obj = MathClass()

        self.agency.spy_on(obj.do_math, call_fake=fake_do_math)
        result = obj.do_math()

        self.assertEqual(result, -1)
        self.assertEqual(len(obj.do_math.calls), 1)
        self.assertEqual(len(obj.do_math.calls[0].args), 0)
        self.assertEqual(len(obj.do_math.calls[0].kwargs), 0)

    def test_call_with_call_fake_and_classmethod(self):
        """Testing FunctionSpy calls with call_fake and classmethod"""
        self.agency.spy_on(MathClass.class_do_math,
                           call_fake=fake_class_do_math)
        result = MathClass.class_do_math()

        self.assertEqual(result, -1)
        self.assertEqual(len(MathClass.class_do_math.calls), 1)
        self.assertEqual(len(MathClass.class_do_math.calls[0].args), 0)
        self.assertEqual(len(MathClass.class_do_math.calls[0].kwargs), 0)

    def test_call_with_call_fake_and_args(self):
        """Testing FunctionSpy calls with call_fake and arguments"""
        obj = MathClass()

        self.agency.spy_on(obj.do_math, call_fake=fake_do_math)
        result = obj.do_math(10, 20)

        self.assertEqual(result, -10)
        self.assertEqual(len(obj.do_math.calls), 1)
        self.assertEqual(obj.do_math.calls[0].args, (10, 20))
        self.assertEqual(len(obj.do_math.calls[0].kwargs), 0)

    def test_call_with_call_fake_and_kwargs(self):
        """Testing FunctionSpy calls with call_fake and keyword arguments"""
        obj = MathClass()

        self.agency.spy_on(obj.do_math, call_fake=fake_do_math)
        result = obj.do_math(a=10, b=20)

        self.assertEqual(result, -10)
        self.assertEqual(len(obj.do_math.calls), 1)
        self.assertEqual(len(obj.do_math.calls[0].args), 0)
        self.assertEqual(obj.do_math.calls[0].kwargs, {
            'a': 10,
            'b': 20
        })

    def test_call_with_call_original_false(self):
        """Testing FunctionSpy calls with call_original=False"""
        obj = MathClass()

        self.agency.spy_on(obj.do_math, call_original=False)
        result = obj.do_math()

        self.assertEqual(result, None)
        self.assertEqual(len(obj.do_math.calls), 1)
        self.assertEqual(len(obj.do_math.calls[0].args), 0)
        self.assertEqual(len(obj.do_math.calls[0].kwargs), 0)

    def test_call_with_all_original_false_and_args(self):
        """Testing FunctionSpy calls with call_original=False and arguments"""
        obj = MathClass()

        self.agency.spy_on(obj.do_math, call_original=False)
        result = obj.do_math(10, 20)

        self.assertEqual(result, None)
        self.assertEqual(len(obj.do_math.calls), 1)
        self.assertEqual(obj.do_math.calls[0].args, (10, 20))
        self.assertEqual(len(obj.do_math.calls[0].kwargs), 0)

    def test_call_with_call_original_false_and_kwargs(self):
        """Testing FunctionSpy calls with call_original=False and keyword arguments"""
        obj = MathClass()

        self.agency.spy_on(obj.do_math, call_original=False)
        result = obj.do_math(a=10, b=20)

        self.assertEqual(result, None)
        self.assertEqual(len(obj.do_math.calls), 1)
        self.assertEqual(len(obj.do_math.calls[0].args), 0)
        self.assertEqual(obj.do_math.calls[0].kwargs, {
            'a': 10,
            'b': 20
        })

    def test_call_with_call_original_true(self):
        """Testing FunctionSpy calls with call_original=True"""
        self.agency.spy_on(something_awesome, call_original=True)
        result = something_awesome()

        self.assertEqual(result, 'Tada!')
        self.assertTrue(hasattr(something_awesome, 'spy'))
        self.assertEqual(len(something_awesome.spy.calls), 1)
        self.assertEqual(len(something_awesome.spy.calls[0].args), 0)
        self.assertEqual(len(something_awesome.spy.calls[0].kwargs), 0)

    def test_call_with_call_original_true_and_bound_method(self):
        """Testing FunctionSpy calls with call_original=True and bound method"""
        obj = MathClass()

        self.agency.spy_on(obj.do_math, call_original=True)
        result = obj.do_math()

        self.assertEqual(result, 3)
        self.assertEqual(len(obj.do_math.calls), 1)
        self.assertEqual(len(obj.do_math.calls[0].args), 0)
        self.assertEqual(len(obj.do_math.calls[0].kwargs), 0)

    def test_call_with_call_original_true_and_classmethod(self):
        """Testing FunctionSpy calls with call_origina=True and classmethod"""
        self.agency.spy_on(MathClass.class_do_math, call_original=True)
        result = MathClass.class_do_math()

        self.assertEqual(result, 10)
        self.assertEqual(len(MathClass.class_do_math.calls), 1)
        self.assertEqual(len(MathClass.class_do_math.calls[0].args), 0)
        self.assertEqual(len(MathClass.class_do_math.calls[0].kwargs), 0)

    def test_call_with_call_original_true_and_args(self):
        """Testing FunctionSpy calls with call_original=True and arguments"""
        obj = MathClass()

        self.agency.spy_on(obj.do_math, call_original=True)
        result = obj.do_math(10, 20)

        self.assertEqual(result, 30)
        self.assertEqual(len(obj.do_math.calls), 1)
        self.assertEqual(obj.do_math.calls[0].args, (10, 20))
        self.assertEqual(len(obj.do_math.calls[0].kwargs), 0)

    def test_call_with_call_original_true_and_kwargs(self):
        """Testing FunctionSpy calls with call_original=True and keyword arguments"""
        obj = MathClass()

        self.agency.spy_on(obj.do_math, call_original=True)
        result = obj.do_math(a=10, b=20)

        self.assertEqual(result, 30)
        self.assertEqual(len(obj.do_math.calls), 1)
        self.assertEqual(len(obj.do_math.calls[0].args), 0)
        self.assertEqual(obj.do_math.calls[0].kwargs, {
            'a': 10,
            'b': 20
        })

    def test_called(self):
        """Testing FunctionSpy.called"""
        obj = MathClass()
        self.agency.spy_on(obj.do_math)

        self.assertFalse(obj.do_math.called)

        obj.do_math(10, 20)

        self.assertTrue(obj.do_math.called)

    def test_last_call(self):
        """Testing FunctionSpy.last_call"""
        obj = MathClass()
        self.agency.spy_on(obj.do_math)

        obj.do_math(10, 20)
        obj.do_math(20, 30)

        self.assertEqual(len(obj.do_math.calls), 2)

        last_call = obj.do_math.last_call
        self.assertNotEqual(last_call, None)
        self.assertEqual(last_call.args, (20, 30))

    def test_last_call_with_no_calls(self):
        """Testing FunctionSpy.last_call on uncalled function"""
        obj = MathClass()
        self.agency.spy_on(obj.do_math)

        self.assertEqual(len(obj.do_math.calls), 0)

        last_call = obj.do_math.last_call
        self.assertEqual(last_call, None)

    def test_unspy(self):
        """Testing FunctionSpy.unspy"""
        orig_code = something_awesome.func_code
        spy = self.agency.spy_on(something_awesome)

        self.assertTrue(hasattr(something_awesome, 'spy'))
        self.assertEqual(something_awesome.spy, spy)

        spy.unspy()
        self.assertFalse(hasattr(something_awesome, 'spy'))
        self.assertEqual(something_awesome.func_code, orig_code)

    def test_unspy_and_bound_method(self):
        """Testing FunctionSpy.unspy and bound method"""
        obj = MathClass()
        orig_do_math = obj.do_math

        spy = self.agency.spy_on(obj.do_math)
        self.assertEqual(obj.do_math, spy)

        spy.unspy()
        self.assertEqual(obj.do_math, orig_do_math)

    def test_unspy_with_classmethod(self):
        """Testing FunctionSpy.unspy with classmethod"""
        spy = self.agency.spy_on(MathClass.class_do_math)
        self.assertEqual(MathClass.class_do_math, spy)

        spy.unspy()
        self.assertEqual(MathClass.class_do_math, self.orig_class_do_math)

    def test_called_with(self):
        """Testing FunctionSpy.called_with"""
        obj = MathClass()
        self.agency.spy_on(obj.do_math)

        obj.do_math(1, 2)
        obj.do_math(3, 4)

        self.assertTrue(obj.do_math.called_with(1, 2))
        self.assertTrue(obj.do_math.called_with(3, 4))
        self.assertFalse(obj.do_math.called_with(5, 6))

    def test_last_called_with(self):
        """Testing FunctionSpy.last_called_with"""
        obj = MathClass()
        self.agency.spy_on(obj.do_math)

        obj.do_math(1, 2)
        obj.do_math(3, 4)

        self.assertFalse(obj.do_math.last_called_with(1, 2))
        self.assertTrue(obj.do_math.last_called_with(3, 4))

    def test_reset_calls(self):
        """Testing FunctionSpy.reset_calls"""
        obj = MathClass()
        self.agency.spy_on(obj.do_math)

        obj.do_math(1, 2)
        self.assertEqual(len(obj.do_math.calls), 1)

        obj.do_math.reset_calls()
        self.assertEqual(len(obj.do_math.calls), 0)

    def test_repr(self):
        """Testing FunctionSpy.__repr__"""
        self.agency.spy_on(something_awesome)

        self.assertTrue(hasattr(something_awesome, 'spy'))
        self.assertEqual(repr(something_awesome.spy),
                         '<Spy for something_awesome>')

    def test_repr_and_bound_method(self):
        """Testing FunctionSpy.__repr__ and bound method"""
        obj = MathClass()
        self.agency.spy_on(obj.do_math)

        self.assertEqual(repr(obj.do_math),
                         '<Spy for bound method MathClass.do_math '
                         'of %r>' % obj)

    def test_repr_with_classmethod(self):
        """Testing FunctionSpy.__repr__ with classmethod"""
        self.agency.spy_on(MathClass.class_do_math)

        self.assertEqual(repr(MathClass.class_do_math),
                         '<Spy for classmethod MathClass.class_do_math of %r>'
                         % MathClass)


class SpyAgencyTests(BaseTestCase):
    def test_spy_on(self):
        """Testing SpyAgency.spy_on"""
        obj = MathClass()

        spy = self.agency.spy_on(obj.do_math)
        self.assertEqual(self.agency.spies, [spy])

    def test_unspy(self):
        """Testing SpyAgency.unspy"""
        obj = MathClass()
        orig_do_math = obj.do_math

        spy = self.agency.spy_on(obj.do_math)
        self.assertEqual(self.agency.spies, [spy])

        self.agency.unspy(obj.do_math)
        self.assertEqual(self.agency.spies, [])

        self.assertEqual(obj.do_math, orig_do_math)

    def test_unspy_all(self):
        """Testing SpyAgency.unspy_all"""
        obj = MathClass()
        orig_do_math = obj.do_math

        spy1 = self.agency.spy_on(obj.do_math)
        spy2 = self.agency.spy_on(MathClass.class_do_math)

        self.assertEqual(self.agency.spies, [spy1, spy2])

        self.agency.unspy_all()
        self.assertEqual(self.agency.spies, [])

        self.assertEqual(obj.do_math, orig_do_math)
        self.assertEqual(MathClass.class_do_math, self.orig_class_do_math)


class ContextManagerTests(BaseTestCase):
    """Unit tests for context managers"""
    def test_spy_on(self):
        """Testing spy_on context manager"""
        obj = MathClass()
        orig_do_math = obj.do_math

        with spy_on(obj.do_math):
            self.assertTrue(isinstance(obj.do_math, FunctionSpy))

            result = obj.do_math()
            self.assertEqual(result, 3)

        self.assertEqual(obj.do_math, orig_do_math)


class MixinTests(SpyAgency, unittest.TestCase):
    def test_spy_on(self):
        """Testing SpyAgency mixed in with spy_on"""
        obj = MathClass()

        self.spy_on(obj.do_math)
        self.assertTrue(isinstance(obj.do_math, FunctionSpy))

        result = obj.do_math()
        self.assertEqual(result, 3)

    def test_tear_down(self):
        """Testing SpyAgency mixed in with tearDown"""
        obj = MathClass()
        orig_do_math = obj.do_math

        self.spy_on(obj.do_math)
        self.assertTrue(isinstance(obj.do_math, FunctionSpy))

        self.tearDown()

        self.assertEqual(obj.do_math, orig_do_math)
