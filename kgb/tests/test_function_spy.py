from __future__ import unicode_literals

import inspect
import types

from kgb.spies import FUNC_CODE_ATTR, FUNC_NAME_ATTR
from kgb.tests.base import MathClass, TestCase


def do_math(a=1, b=2, *args, **kwargs):
    return a - b


def fake_do_math(self, a=1, b=2, *args, **kwargs):
    return a - b


def fake_class_do_math(self, a=1, b=2, *args, **kwargs):
    return a - b


def something_awesome():
    return 'Tada!'


def fake_something_awesome():
    return '\o/'


class FunctionSpyTests(TestCase):
    """Test cases for kgb.spies.FunctionSpy."""

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
        self.assertEqual(getattr(spy.func, FUNC_NAME_ATTR),
                         getattr(fake_something_awesome, FUNC_NAME_ATTR))
        self.assertEqual(spy.orig_func, something_awesome)
        self.assertEqual(spy.func_name, 'something_awesome')
        self.assertEqual(spy.owner, None)
        self.assertIsInstance(something_awesome, types.FunctionType)

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
        self.assertIsInstance(obj.do_math, types.MethodType)

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
        self.assertIsInstance(MathClass.class_do_math, types.MethodType)

    def test_construction_with_call_original_false(self):
        """Testing FunctionSpy construction with call_original=False"""
        obj = MathClass()
        spy = self.agency.spy_on(obj.do_math, call_original=False)

        self.assertEqual(spy.func, None)
        self.assertEqual(obj.do_math, spy)
        self.assertEqual(spy.func_name, 'do_math')
        self.assertEqual(spy.owner, obj)
        self.assertIsInstance(obj.do_math, types.MethodType)

    def test_construction_with_call_original_true(self):
        """Testing FunctionSpy construction with call_original=True"""
        spy = self.agency.spy_on(something_awesome, call_original=True)

        self.assertTrue(hasattr(something_awesome, 'spy'))
        self.assertEqual(something_awesome.spy, spy)
        self.assertEqual(getattr(spy.func, FUNC_NAME_ATTR),
                         getattr(something_awesome, FUNC_NAME_ATTR))
        self.assertEqual(spy.orig_func, something_awesome)
        self.assertEqual(spy.func_name, 'something_awesome')
        self.assertEqual(spy.owner, None)
        self.assertIsInstance(something_awesome, types.FunctionType)

    def test_construction_with_call_original_true_and_bound_method(self):
        """Testing FunctionSpy construction with call_original=True and bound method"""
        obj = MathClass()
        orig_do_math = obj.do_math

        spy = self.agency.spy_on(obj.do_math, call_original=True)

        self.assertEqual(spy.func, orig_do_math)
        self.assertEqual(obj.do_math, spy)
        self.assertEqual(spy.func_name, 'do_math')
        self.assertEqual(spy.owner, obj)
        self.assertIsInstance(obj.do_math, types.MethodType)

    def test_construction_with_call_original_and_classmethod(self):
        """Testing FunctionSpy construction with call_original and classmethod"""
        spy = self.agency.spy_on(MathClass.class_do_math, call_original=True)

        self.assertEqual(spy.func, self.orig_class_do_math)
        self.assertEqual(MathClass.class_do_math, spy)
        self.assertEqual(spy.func_name, 'class_do_math')
        self.assertEqual(spy.owner, MathClass)
        self.assertIsInstance(MathClass.class_do_math, types.MethodType)

    def test_construction_with_falsy_im_self(self):
        """Testing FunctionSpy construction with a falsy function.im_self"""
        class MyObject(dict):
            def foo(self):
                pass

        my_object = MyObject()
        orig_foo = my_object.foo

        # Ensure it's falsy.
        self.assertFalse(my_object)

        spy = self.agency.spy_on(my_object.foo)

        self.assertEqual(spy.func, orig_foo)
        self.assertEqual(my_object.foo, spy)
        self.assertNotEqual(MyObject.foo, spy)
        self.assertEqual(spy.func_name, 'foo')
        self.assertEqual(spy.owner, my_object)
        self.assertIsInstance(my_object.foo, types.MethodType)

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

    def test_call_with_call_original_true_and_function(self):
        """Testing FunctionSpy calls with call_original=True and function"""
        self.agency.spy_on(something_awesome, call_original=True)
        result = something_awesome()

        self.assertEqual(result, 'Tada!')
        self.assertTrue(hasattr(something_awesome, 'spy'))
        self.assertEqual(len(something_awesome.spy.calls), 1)
        self.assertEqual(len(something_awesome.spy.calls[0].args), 0)
        self.assertEqual(len(something_awesome.spy.calls[0].kwargs), 0)

    def test_call_with_call_original_true_and_function_args(self):
        """Testing FunctionSpy calls with call_original=True and function
        with all positional arguments
        """
        self.agency.spy_on(do_math, call_original=True)
        result = do_math(10, 20)

        self.assertEqual(result, -10)
        self.assertEqual(len(do_math.spy.calls), 1)
        self.assertEqual(do_math.spy.calls[0].args, (10, 20))
        self.assertEqual(len(do_math.spy.calls[0].kwargs), 0)

    def test_call_with_call_original_true_and_function_kwargs(self):
        """Testing FunctionSpy calls with call_original=True and function
        with all keyword arguments
        """
        self.agency.spy_on(do_math, call_original=True)
        result = do_math(b=10, a=20)

        self.assertEqual(result, 10)
        self.assertEqual(len(do_math.spy.calls), 1)
        self.assertEqual(len(do_math.spy.calls[0].args), 0)
        self.assertEqual(do_math.spy.calls[0].kwargs, {
            'a': 20,
            'b': 10
        })

    def test_call_with_call_original_true_and_function_mixed(self):
        """Testing FunctionSpy calls with call_original=True and function
        with all mixed argument types
        """
        self.agency.spy_on(do_math, call_original=True)
        result = do_math(10, b=20, unused=True)

        self.assertEqual(result, -10)
        self.assertEqual(len(do_math.spy.calls), 1)
        self.assertEqual(do_math.spy.calls[0].args, (10,))
        self.assertEqual(do_math.spy.calls[0].kwargs, {
            'b': 20,
            'unused': True,
        })

    def test_call_with_call_original_true_and_bound_method(self):
        """Testing FunctionSpy calls with call_original=True and bound method"""
        obj = MathClass()

        self.agency.spy_on(obj.do_math, call_original=True)
        result = obj.do_math()

        self.assertEqual(result, 3)
        self.assertEqual(len(obj.do_math.calls), 1)
        self.assertEqual(len(obj.do_math.calls[0].args), 0)
        self.assertEqual(len(obj.do_math.calls[0].kwargs), 0)

    def test_call_with_call_original_true_and_bound_method_args(self):
        """Testing FunctionSpy calls with call_original=True and bound method
        with all positional arguments
        """
        obj = MathClass()

        self.agency.spy_on(obj.do_math, call_original=True)
        result = obj.do_math(10, 20)

        self.assertEqual(result, 30)
        self.assertEqual(len(obj.do_math.calls), 1)
        self.assertEqual(obj.do_math.calls[0].args, (10, 20))
        self.assertEqual(len(obj.do_math.calls[0].kwargs), 0)

    def test_call_with_call_original_true_and_bound_method_kwargs(self):
        """Testing FunctionSpy calls with call_original=True and bound method
        with all keyword arguments
        """
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

    def test_call_with_call_original_true_and_classmethod(self):
        """Testing FunctionSpy calls with call_original=True and classmethod"""
        self.agency.spy_on(MathClass.class_do_math, call_original=True)
        result = MathClass.class_do_math()

        self.assertEqual(result, 10)
        self.assertEqual(len(MathClass.class_do_math.calls), 1)
        self.assertEqual(len(MathClass.class_do_math.calls[0].args), 0)
        self.assertEqual(len(MathClass.class_do_math.calls[0].kwargs), 0)

    def test_call_with_call_original_true_and_classmethod_args(self):
        """Testing FunctionSpy calls with call_original=True and classmethod
        with all positional arguments
        """
        self.agency.spy_on(MathClass.class_do_math, call_original=True)
        result = MathClass.class_do_math(10, 20)

        self.assertEqual(result, 200)
        self.assertEqual(len(MathClass.class_do_math.calls), 1)
        self.assertEqual(MathClass.class_do_math.calls[0].args, (10, 20))
        self.assertEqual(len(MathClass.class_do_math.calls[0].kwargs), 0)

    def test_call_with_call_original_true_and_classmethod_kwargs(self):
        """Testing FunctionSpy calls with call_original=True and classmethod
        with all keyword arguments
        """
        self.agency.spy_on(MathClass.class_do_math, call_original=True)
        result = MathClass.class_do_math(a=10, b=20)

        self.assertEqual(result, 200)
        self.assertEqual(len(MathClass.class_do_math.calls), 1)
        self.assertEqual(len(MathClass.class_do_math.calls[0].args), 0)
        self.assertEqual(MathClass.class_do_math.calls[0].kwargs, {
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
        orig_code = getattr(something_awesome, FUNC_CODE_ATTR)
        spy = self.agency.spy_on(something_awesome, call_fake=lambda: 'spy!')

        self.assertTrue(hasattr(something_awesome, 'spy'))
        self.assertEqual(something_awesome.spy, spy)
        self.assertEqual(something_awesome(), 'spy!')

        spy.unspy()
        self.assertFalse(hasattr(something_awesome, 'spy'))
        self.assertEqual(getattr(something_awesome, FUNC_CODE_ATTR), orig_code)
        self.assertEqual(something_awesome(), 'Tada!')

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

    def test_getargspec_with_function(self):
        """Testing FunctionSpy in inspect.getargspec() with function"""
        self.agency.spy_on(do_math)

        args, varargs, keywords, defaults = inspect.getargspec(do_math)
        self.assertEqual(args, ['a', 'b'])
        self.assertEqual(varargs, 'args')
        self.assertEqual(keywords, 'kwargs')
        self.assertEqual(defaults, (1, 2))

    def test_getargspec_with_bound_method(self):
        """Testing FunctionSpy in inspect.getargspec() with bound method"""
        obj = MathClass()
        self.agency.spy_on(obj.do_math)

        args, varargs, keywords, defaults = inspect.getargspec(obj.do_math)
        self.assertEqual(args, ['self', 'a', 'b'])
        self.assertEqual(varargs, 'args')
        self.assertEqual(keywords, 'kwargs')
        self.assertEqual(defaults, (1, 2))

    def test_getargspec_with_classmethod(self):
        """Testing FunctionSpy in inspect.getargspec() with classmethod"""
        obj = MathClass()
        self.agency.spy_on(obj.class_do_math)

        args, varargs, keywords, defaults = \
            inspect.getargspec(obj.class_do_math)
        self.assertEqual(args, ['cls', 'a', 'b'])
        self.assertEqual(varargs, 'args')
        self.assertEqual(keywords, 'kwargs')
        self.assertEqual(defaults, (2, 5))
