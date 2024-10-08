from __future__ import unicode_literals

import functools
import inspect
import re
import sys
import traceback
import types
import unittest
from contextlib import contextmanager
from warnings import catch_warnings

from kgb.errors import ExistingSpyError, IncompatibleFunctionError
from kgb.pycompat import text_type
from kgb.signature import FunctionSig
from kgb.tests.base import MathClass, TestCase


has_getargspec = hasattr(inspect, 'getargspec')
has_getfullargspec = hasattr(inspect, 'getfullargspec')


def require_getargspec(func):
    """Require getargspec for a unit test.

    If not available, the test will be skippd.

    Args:
        func (callable):
            The unit test function to decorate.
    """
    @functools.wraps(func)
    def _wrap(*args, **kwargs):
        if has_getargspec:
            with catch_warnings(record=True):
                return func(*args, **kwargs)
        else:
            raise unittest.SkipTest(
                'inspect.getargspec is not available on Python %s.%s.%s'
                % sys.version_info[:3])

    return _wrap


def do_math(a=1, b=2, *args, **kwargs):
    return a - b


def do_math_pos(a, b):
    return a - b


def do_math_mixed(a, b=2, *args, **kwargs):
    return a - b


def fake_do_math(self, a, b, *args, **kwargs):
    assert isinstance(self, MathClass)

    return a - b


def fake_class_do_math(cls, a, b, *args, **kwargs):
    assert issubclass(cls, MathClass)

    return a - b


def something_awesome():
    return 'Tada!'


def fake_something_awesome():
    return r'\o/'


@contextmanager
def do_context(a=1, b=2):
    yield a + b


class AdderObject(object):
    def func(self):
        assert isinstance(self, AdderObject)

        return [self.add_one(i) for i in (1, 2, 3)]

    def add_one(self, i):
        assert isinstance(self, AdderObject)

        return i + 1

    @classmethod
    def class_func(cls):
        assert cls is AdderObject

        return [cls.class_add_one(i) for i in (1, 2, 3)]

    @classmethod
    def class_add_one(cls, i):
        assert issubclass(cls, AdderObject)

        return i + 1


class AdderSubclass(AdderObject):
    pass


class slippery_func(object):
    count = 0

    def __init__(self):
        pass

    def __call__(self, method):
        self.method = method
        return self

    def __get__(self, obj, objtype=None):
        @functools.wraps(self.method)
        def _wrapper(*args, **kwargs):
            return self.method(obj, _wrapper.counter)

        _wrapper.counter = self.count
        type(self).count += 1

        return _wrapper


class SlipperyFuncObject(object):
    @slippery_func()
    def my_func(self, value):
        return value


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
        self.assertEqual(
            getattr(spy.func, FunctionSig.FUNC_NAME_ATTR),
            getattr(fake_something_awesome, FunctionSig.FUNC_NAME_ATTR))
        self.assertEqual(spy.orig_func, something_awesome)
        self.assertEqual(spy.func_name, 'something_awesome')
        self.assertEqual(spy.func_type, spy.TYPE_FUNCTION)
        self.assertIsInstance(something_awesome, types.FunctionType)

    def test_construction_with_call_fake_and_bound_method(self):
        """Testing FunctionSpy construction with call_fake and bound method"""
        obj = MathClass()
        orig_method = obj.do_math
        spy = self.agency.spy_on(obj.do_math, call_fake=fake_do_math)

        self.assertTrue(hasattr(obj.do_math, 'spy'))
        self.assertIs(obj.do_math.spy, spy)
        self.assertIsNot(obj.do_math, orig_method)
        self.assertFalse(hasattr(MathClass.do_math, 'spy'))

        self.assertEqual(spy.func, fake_do_math)
        self.assertEqual(spy.func_name, 'do_math')
        self.assertEqual(spy.func_type, spy.TYPE_BOUND_METHOD)
        self.assertIsInstance(obj.do_math, types.MethodType)

    def test_construction_with_call_fake_and_unbound_method(self):
        """Testing FunctionSpy construction with call_fake and unbound method
        """
        orig_method = MathClass.do_math
        spy = self.agency.spy_on(MathClass.do_math, call_fake=fake_do_math)

        self.assertTrue(hasattr(MathClass.do_math, 'spy'))
        self.assertIs(MathClass.do_math.spy, spy)
        self.assertEqual(spy.func, fake_do_math)
        self.assertEqual(spy.func_name, 'do_math')
        self.assertEqual(spy.func_type, spy.TYPE_UNBOUND_METHOD)
        self.assertEqual(spy.owner, MathClass)

        if isinstance(orig_method, types.FunctionType):
            # Python 3
            self.assertIs(MathClass.do_math, orig_method)
        elif isinstance(orig_method, types.MethodType):
            # Python 2
            self.assertIsNot(MathClass.do_math, orig_method)
        else:
            self.fail('Method has an unexpected type %r' % type(orig_method))

        obj = MathClass()
        self.assertTrue(hasattr(obj.do_math, 'spy'))
        self.assertIs(obj.do_math.spy, MathClass.do_math.spy)
        self.assertIsInstance(obj.do_math, types.MethodType)

    def test_construction_with_call_fake_and_classmethod(self):
        """Testing FunctionSpy construction with call_fake and classmethod"""
        def fake_class_do_math(cls, *args, **kwargs):
            return 42

        orig_method = MathClass.class_do_math
        spy = self.agency.spy_on(MathClass.class_do_math,
                                 call_fake=fake_class_do_math)

        self.assertTrue(hasattr(MathClass.class_do_math, 'spy'))
        self.assertIs(MathClass.class_do_math.spy, spy)
        self.assertIs(MathClass.class_do_math, orig_method)

        self.assertEqual(spy.func, fake_class_do_math)
        self.assertEqual(spy.orig_func, self.orig_class_do_math)
        self.assertEqual(spy.func_name, 'class_do_math')
        self.assertIsInstance(MathClass.class_do_math, types.MethodType)

    def test_construction_with_call_original_false(self):
        """Testing FunctionSpy construction with call_original=False"""
        obj = MathClass()
        spy = self.agency.spy_on(obj.do_math, call_original=False)

        self.assertTrue(hasattr(obj.do_math, 'spy'))
        self.assertIs(obj.do_math.spy, spy)

        self.assertIsNone(spy.func)
        self.assertEqual(spy.func_name, 'do_math')
        self.assertIsInstance(obj.do_math, types.MethodType)

    def test_construction_with_call_original_true(self):
        """Testing FunctionSpy construction with call_original=True"""
        spy = self.agency.spy_on(something_awesome, call_original=True)

        self.assertTrue(hasattr(something_awesome, 'spy'))
        self.assertEqual(something_awesome.spy, spy)
        self.assertEqual(
            getattr(spy.func, FunctionSig.FUNC_NAME_ATTR),
            getattr(something_awesome, FunctionSig.FUNC_NAME_ATTR))
        self.assertEqual(spy.orig_func, something_awesome)
        self.assertEqual(spy.func_name, 'something_awesome')
        self.assertIsInstance(something_awesome, types.FunctionType)

    def test_construction_with_call_original_true_and_bound_method(self):
        """Testing FunctionSpy construction with call_original=True and bound
        method
        """
        obj = MathClass()
        orig_do_math = obj.do_math

        spy = self.agency.spy_on(obj.do_math, call_original=True)

        self.assertTrue(hasattr(obj.do_math, 'spy'))
        self.assertIs(obj.do_math.spy, spy)
        self.assertFalse(hasattr(MathClass.do_math, 'spy'))

        self.assertEqual(spy.orig_func, orig_do_math)
        self.assertEqual(spy.func_name, 'do_math')
        self.assertEqual(spy.func_type, spy.TYPE_BOUND_METHOD)
        self.assertIsInstance(obj.do_math, types.MethodType)

    def test_construction_with_call_original_and_classmethod(self):
        """Testing FunctionSpy construction with call_original and classmethod
        """
        spy = self.agency.spy_on(MathClass.class_do_math, call_original=True)

        self.assertTrue(hasattr(MathClass.class_do_math, 'spy'))
        self.assertIs(MathClass.class_do_math.spy, spy)

        self.assertEqual(spy.orig_func, self.orig_class_do_math)
        self.assertEqual(spy.func_name, 'class_do_math')
        self.assertEqual(spy.func_type, spy.TYPE_BOUND_METHOD)
        self.assertIsInstance(MathClass.class_do_math, types.MethodType)

    def test_construction_with_function_and_owner(self):
        """Testing FunctionSpy constructions with function and owner passed"""
        with self.assertRaises(ValueError) as cm:
            self.agency.spy_on(do_math, owner=AdderObject)

        self.assertEqual(text_type(cm.exception),
                         'This function has no owner, but an owner was '
                         'passed to spy_on().')

    def test_init_with_slippery_bound_method(self):
        """Testing FunctionSpy construction with new slippery function
        generated dynamically from accessing a spied-on bound method from
        instance
        """
        obj = SlipperyFuncObject()

        # Verify that we're producing a different function on each access.
        func1 = obj.my_func
        func2 = obj.my_func
        self.assertIsInstance(func1, types.FunctionType)
        self.assertIsInstance(func2, types.FunctionType)
        self.assertIsNot(func1, func2)

        spy = self.agency.spy_on(obj.my_func,
                                 owner=obj,
                                 call_original=True)

        self.assertTrue(hasattr(obj.my_func, 'spy'))
        self.assertIs(obj.my_func.spy, spy)

        self.assertEqual(spy.func_name, 'my_func')
        self.assertEqual(spy.func_type, spy.TYPE_BOUND_METHOD)
        self.assertIsInstance(obj.my_func, types.MethodType)

        slippery_func.count = 0
        func1 = obj.my_func
        func2 = obj.my_func
        self.assertIs(func1, func2)

        # Since the functions are wrapped, we'll be getting a new value each
        # time we invoke them (and not when accessing the attributes as we
        # did above).
        self.assertEqual(func1(), 0)
        self.assertEqual(func1(), 1)
        self.assertEqual(func2(), 2)
        self.assertEqual(len(obj.my_func.calls), 3)

    def test_init_with_slippery_unbound_method(self):
        """Testing FunctionSpy construction with new slippery function
        generated dynamically from accessing a spied-on unbound method from
        instance
        """
        with self.assertRaises(ValueError) as cm:
            self.agency.spy_on(SlipperyFuncObject.my_func,
                               owner=SlipperyFuncObject)

        self.assertEqual(
            text_type(cm.exception),
            'Unable to spy on unbound slippery methods (those that return '
            'a new function on each attribute access). Please spy on an '
            'instance instead.')

    def test_construction_with_classmethod_on_parent(self):
        """Testing FunctionSpy construction with classmethod from parent of
        class
        """
        class MyParent(object):
            @classmethod
            def foo(self):
                pass

        class MyObject(MyParent):
            pass

        obj = MyObject()
        orig_method = obj.foo

        spy = self.agency.spy_on(MyObject.foo)

        self.assertTrue(hasattr(MyObject.foo, 'spy'))
        self.assertFalse(hasattr(MyParent.foo, 'spy'))
        self.assertIs(MyObject.foo.spy, spy)
        self.assertEqual(spy.func_name, 'foo')
        self.assertEqual(spy.func_type, spy.TYPE_BOUND_METHOD)
        self.assertEqual(spy.owner, MyObject)

        if isinstance(orig_method, types.FunctionType):
            # Python 3
            self.assertIs(MyObject.foo, orig_method)
        elif isinstance(orig_method, types.MethodType):
            # Python 2
            self.assertIsNot(MyObject.foo, orig_method)
        else:
            self.fail('Method has an unexpected type %r' % type(orig_method))

        obj2 = MyObject()
        self.assertTrue(hasattr(obj2.foo, 'spy'))
        self.assertIs(obj2.foo.spy, MyObject.foo.spy)
        self.assertIsInstance(obj2.foo, types.MethodType)

        obj3 = MyParent()
        self.assertFalse(hasattr(obj3.foo, 'spy'))

    def test_construction_with_unbound_method_on_parent(self):
        """Testing FunctionSpy construction with unbound method from parent of
        class
        """
        obj = AdderSubclass()
        orig_method = obj.func

        spy = self.agency.spy_on(AdderSubclass.func, owner=AdderSubclass)

        self.assertTrue(hasattr(AdderSubclass.func, 'spy'))
        self.assertFalse(hasattr(AdderObject.func, 'spy'))
        self.assertIs(AdderSubclass.func.spy, spy)
        self.assertEqual(spy.func_name, 'func')
        self.assertEqual(spy.func_type, spy.TYPE_UNBOUND_METHOD)
        self.assertEqual(spy.owner, AdderSubclass)

        if isinstance(orig_method, types.FunctionType):
            # Python 3
            self.assertIs(AdderSubclass.func, orig_method)
        elif isinstance(orig_method, types.MethodType):
            # Python 2
            self.assertIsNot(AdderSubclass.func, orig_method)
        else:
            self.fail('Method has an unexpected type %r' % type(orig_method))

        obj2 = AdderSubclass()
        self.assertTrue(hasattr(obj2.func, 'spy'))
        self.assertIs(obj2.func.spy, AdderSubclass.func.spy)
        self.assertIsInstance(obj2.func, types.MethodType)

        obj3 = AdderObject()
        self.assertFalse(hasattr(obj3.func, 'spy'))

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

        self.assertEqual(spy.orig_func, orig_foo)
        self.assertNotEqual(MyObject.foo, spy)
        self.assertEqual(spy.func_name, 'foo')
        self.assertEqual(spy.func_type, spy.TYPE_BOUND_METHOD)
        self.assertIsInstance(my_object.foo, types.MethodType)

    def test_construction_with_existing_spy(self):
        """Testing FunctionSpy constructions with function already spied on"""
        def setup_spy():
            self.agency.spy_on(do_math)

        setup_spy()

        with self.assertRaises(ExistingSpyError) as cm:
            self.agency.spy_on(do_math)

        self.assertIn(', in setup_spy', text_type(cm.exception))

    def test_construction_with_bound_method_and_custom_setattr(self):
        """Testing FunctionSpy constructions with a bound method on a class
        containing a custom __setattr__
        """
        class MyObject(object):
            def __setattr__(self, key, value):
                assert False

            def foo(self):
                pass

        obj = MyObject()
        orig_foo = obj.foo

        spy = self.agency.spy_on(obj.foo)
        self.assertEqual(spy.orig_func, orig_foo)
        self.assertNotEqual(MyObject.foo, spy)
        self.assertEqual(spy.func_name, 'foo')
        self.assertEqual(spy.func_type, spy.TYPE_BOUND_METHOD)
        self.assertIsInstance(obj.foo, types.MethodType)
        self.assertTrue(hasattr(obj.foo, 'spy'))
        self.assertTrue(hasattr(obj.foo, 'called_with'))

        obj2 = MyObject()
        self.assertFalse(hasattr(obj2.foo, 'spy'))

    def test_construction_with_bound_method_and_bad_owner(self):
        """Testing FunctionSpy constructions with a bound method and an
        explicit owner not matching the class
        """
        class MyObject(object):
            def foo(self):
                pass

        class BadObject(object):
            def foo(self):
                pass

        obj = MyObject()

        with self.assertRaises(ValueError) as cm:
            self.agency.spy_on(obj.foo, owner=BadObject)

        self.assertEqual(text_type(cm.exception),
                         'The owner passed does not match the actual owner '
                         'of the bound method.')

    def test_construction_with_owner_without_method(self):
        """Testing FunctionSpy constructions with an owner passed that does
        not provide the spied method
        """
        class MyObject(object):
            def foo(self):
                pass

        obj = MyObject()

        with self.assertRaises(ValueError) as cm:
            self.agency.spy_on(obj.foo, owner=AdderObject)

        self.assertEqual(text_type(cm.exception),
                         'The owner passed does not contain the spied method.')

    def test_construction_with_non_function(self):
        """Testing FunctionSpy constructions with non-function"""
        with self.assertRaises(ValueError) as cm:
            self.agency.spy_on(42)

        self.assertEqual(text_type(cm.exception),
                         '42 cannot be spied on. It does not appear to be a '
                         'valid function or method.')

    def test_construction_with_call_fake_non_function(self):
        """Testing FunctionSpy constructions with call_fake as non-function"""
        with self.assertRaises(ValueError) as cm:
            self.agency.spy_on(do_math, call_fake=True)

        self.assertEqual(text_type(cm.exception),
                         'True cannot be used for call_fake. It does not '
                         'appear to be a valid function or method.')

    def test_construction_with_call_fake_compatibility(self):
        """Testing FunctionSpy constructions with call_fake with signature
        compatibility
        """
        def source1(a, b):
            pass

        def source2(a, b, *args):
            pass

        def source3(c=1, d=2):
            pass

        def source4(c=1, d=2, **kwargs):
            pass

        with self.assertRaises(IncompatibleFunctionError):
            self.agency.spy_on(
                source1,
                call_fake=lambda a, b, c: None)

        with self.assertRaises(IncompatibleFunctionError):
            self.agency.spy_on(
                source1,
                call_fake=lambda a: None)

        with self.assertRaises(IncompatibleFunctionError):
            self.agency.spy_on(
                source1,
                call_fake=lambda **kwargs: None)

        with self.assertRaises(IncompatibleFunctionError):
            self.agency.spy_on(
                source2,
                call_fake=lambda a, b: None)

        with self.assertRaises(IncompatibleFunctionError):
            self.agency.spy_on(
                source3,
                call_fake=lambda c=1: None)

        with self.assertRaises(IncompatibleFunctionError):
            self.agency.spy_on(
                source4,
                call_fake=lambda c=1, d=2, e=3: None)

        with self.assertRaises(IncompatibleFunctionError):
            self.agency.spy_on(
                source4,
                call_fake=lambda c=1, d=2: None)

        self.agency.spy_on(source1, call_fake=lambda a, b: None)
        source1.unspy()

        self.agency.spy_on(source1, call_fake=lambda *args: None)
        source1.unspy()

        self.agency.spy_on(source4, call_fake=lambda c=1, d=2, **kwargs: None)
        source4.unspy()

        self.agency.spy_on(source4, call_fake=lambda c=1, **kwargs: None)
        source4.unspy()

        self.agency.spy_on(source4, call_fake=lambda c, d=None, **kwargs: None)
        source4.unspy()

        self.agency.spy_on(source4, call_fake=lambda c, e, **kwargs: None)
        source4.unspy()

        self.agency.spy_on(source4, call_fake=lambda **kwargs: None)
        source4.unspy()

    def test_construction_with_old_style_class(self):
        """Testing FunctionSpy with old-style class"""
        class MyClass:
            def test_func(self):
                return 100

        obj = MyClass()

        self.agency.spy_on(obj.test_func, call_fake=lambda obj: 200)
        self.assertEqual(obj.test_func(), 200)

    def test_call_with_fake(self):
        """Testing FunctionSpy calls with call_fake"""
        self.agency.spy_on(something_awesome,
                           call_fake=fake_something_awesome)
        result = something_awesome()

        self.assertEqual(result, r'\o/')
        self.assertEqual(len(something_awesome.spy.calls), 1)
        self.assertEqual(len(something_awesome.spy.calls[0].args), 0)
        self.assertEqual(len(something_awesome.spy.calls[0].kwargs), 0)

    def test_call_with_fake_and_bound_method(self):
        """Testing FunctionSpy calls with call_fake and bound method"""
        obj = MathClass()

        self.agency.spy_on(obj.do_math, call_fake=fake_do_math)
        result = obj.do_math()

        self.assertEqual(result, -1)
        self.assertEqual(len(obj.do_math.calls), 1)
        self.assertTrue(obj.do_math.last_called_with(
            a=1,
            b=2))

    def test_call_with_fake_and_unbound_method(self):
        """Testing FunctionSpy calls with call_fake and unbound method"""
        self.agency.spy_on(MathClass.do_math, call_fake=fake_do_math)

        obj = MathClass()
        result = obj.do_math()

        self.assertEqual(result, -1)
        self.assertEqual(len(obj.do_math.calls), 1)
        self.assertTrue(obj.do_math.last_called_with(
            a=1,
            b=2))

    def test_call_with_fake_and_classmethod(self):
        """Testing FunctionSpy calls with call_fake and classmethod"""
        self.agency.spy_on(MathClass.class_do_math,
                           call_fake=fake_class_do_math)
        result = MathClass.class_do_math()

        self.assertEqual(result, -3)
        self.assertEqual(len(MathClass.class_do_math.calls), 1)
        self.assertTrue(MathClass.class_do_math.last_called_with(
            a=2,
            b=5))

    def test_call_with_fake_and_contextmanager(self):
        """Testing FunctionSpy calls with call_fake and context manager"""
        @contextmanager
        def fake_do_context(a=1, b=2):
            yield a * b

        self.agency.spy_on(do_context,
                           call_fake=fake_do_context)

        with do_context(a=5) as ctx:
            result = ctx

        self.assertEqual(result, 10)
        self.assertEqual(len(do_context.calls), 1)
        self.assertEqual(do_context.calls[0].args, ())
        self.assertEqual(do_context.calls[0].kwargs, {'a': 5})

    def test_call_with_fake_and_contextmanager_func_raises_exception(self):
        """Testing FunctionSpy calls with call_fake and context manager and
        function raises exception
        """
        e = Exception('oh no')

        @contextmanager
        def fake_do_context(*args, **kwargs):
            raise e

        self.agency.spy_on(do_context,
                           call_fake=fake_do_context)

        with self.assertRaisesRegex(Exception, 'oh no'):
            with do_context(a=5):
                pass

        self.assertEqual(len(do_context.calls), 1)
        self.assertEqual(do_context.calls[0].args, ())
        self.assertEqual(do_context.calls[0].kwargs, {'a': 5})
        self.assertEqual(do_context.calls[0].exception, e)

    def test_call_with_fake_and_contextmanager_body_raises_exception(self):
        """Testing FunctionSpy calls with call_fake and context manager and
        context body raises exception
        """
        e = Exception('oh no')

        @contextmanager
        def fake_do_context(a=1, b=2):
            yield a * b

        self.agency.spy_on(do_context,
                           call_fake=fake_do_context)

        with self.assertRaisesRegex(Exception, 'oh no'):
            with do_context(a=5):
                raise e

        self.assertEqual(len(do_context.calls), 1)
        self.assertEqual(do_context.calls[0].args, ())
        self.assertEqual(do_context.calls[0].kwargs, {'a': 5})
        self.assertIsNone(do_context.calls[0].exception)

    def test_call_with_exception(self):
        e = ValueError('oh no')

        def orig_func(arg1=None, arg2=None):
            # Create enough of a difference in code positions between this
            # and the forwarding functions, to ensure the exception's
            # position count is higher than that of the forwarding function.
            #
            # This is important for sanity checks on Python 3.11.
            try:
                if 1:
                    if 2:
                        try:
                            a = 1
                            b = a
                            a = 2
                        except Exception:
                            raise
                    else:
                        c = [1, 2, 3, 4, 5]
                        a = c
            except Exception:
                raise

            for i in range(10):
                try:
                    d = [1, 2, 3, 4, 5]
                    a = d
                    b = a
                    d = b
                except Exception:
                    raise

            # We should be good. We'll verify counts later.
            raise e

        # Verify the above.
        orig_func_code = orig_func.__code__
        supports_co_positions = hasattr(orig_func_code, 'co_positions')

        if supports_co_positions:
            orig_positions_count = len(list(orig_func_code.co_positions()))
        else:
            orig_positions_count = None

        # Now spy.
        self.agency.spy_on(orig_func)

        if supports_co_positions:
            spy_positions_count = len(list(orig_func.__code__.co_positions()))

            # Make sure we had enough padding up above.
            self.assertGreater(orig_positions_count, spy_positions_count)

        # Now test.
        try:
            orig_func()
        except Exception as ex:
            # This should fail if we've built the CodeType wrong and have a
            # resulting offset issue. The act of pretty-printing the exception
            # triggers the noticeable co_positions() issue.
            traceback.print_exception(*sys.exc_info())

        self.assertEqual(len(orig_func.calls), 1)
        self.assertIs(orig_func.calls[0].exception, e)

    def test_call_with_fake_and_args(self):
        """Testing FunctionSpy calls with call_fake and arguments"""
        obj = MathClass()

        self.agency.spy_on(obj.do_math_pos, call_fake=fake_do_math)
        result = obj.do_math_pos(10, 20)

        self.assertEqual(result, -10)
        self.assertEqual(len(obj.do_math_pos.calls), 1)
        self.assertEqual(obj.do_math_pos.calls[0].args, (10, 20))
        self.assertEqual(obj.do_math_pos.calls[0].kwargs, {})

    def test_call_with_fake_and_args_for_kwargs(self):
        """Testing FunctionSpy calls with call_fake and positional arguments
        in place of keyword arguments
        """
        obj = MathClass()

        self.agency.spy_on(obj.do_math, call_fake=fake_do_math)
        result = obj.do_math(10, 20)

        self.assertEqual(result, -10)
        self.assertEqual(len(obj.do_math.calls), 1)
        self.assertEqual(obj.do_math.calls[0].args, ())
        self.assertEqual(obj.do_math.calls[0].kwargs, {
            'a': 10,
            'b': 20,
        })

    def test_call_with_fake_and_kwargs(self):
        """Testing FunctionSpy calls with call_fake and keyword arguments"""
        obj = MathClass()

        self.agency.spy_on(obj.do_math, call_fake=fake_do_math)
        result = obj.do_math(a=10, b=20)

        self.assertEqual(result, -10)
        self.assertEqual(len(obj.do_math.calls), 1)
        self.assertEqual(len(obj.do_math.calls[0].args), 0)
        self.assertEqual(obj.do_math.calls[0].kwargs, {
            'a': 10,
            'b': 20,
        })

    def test_call_with_original_false(self):
        """Testing FunctionSpy calls with call_original=False"""
        obj = MathClass()

        self.agency.spy_on(obj.do_math, call_original=False)
        result = obj.do_math()

        self.assertIsNone(result)
        self.assertEqual(len(obj.do_math.calls), 1)
        self.assertTrue(obj.do_math.last_called_with(a=1, b=2))

    def test_call_with_all_original_false_and_args(self):
        """Testing FunctionSpy calls with call_original=False and positional
        arguments
        """
        obj = MathClass()

        self.agency.spy_on(obj.do_math_pos, call_original=False)
        result = obj.do_math_pos(10, 20)

        self.assertIsNone(result)
        self.assertEqual(len(obj.do_math_pos.calls), 1)
        self.assertEqual(obj.do_math_pos.calls[0].args, (10, 20))
        self.assertEqual(obj.do_math_pos.calls[0].kwargs, {})

    def test_call_with_all_original_false_and_args_for_kwargs(self):
        """Testing FunctionSpy calls with call_original=False and positional
        arguments in place of keyword arguments
        """
        obj = MathClass()

        self.agency.spy_on(obj.do_math, call_original=False)
        result = obj.do_math(10, 20)

        self.assertEqual(result, None)
        self.assertEqual(len(obj.do_math.calls), 1)
        self.assertEqual(obj.do_math.calls[0].args, ())
        self.assertEqual(obj.do_math.calls[0].kwargs, {
            'a': 10,
            'b': 20,
        })

    def test_call_with_original_false_and_kwargs(self):
        """Testing FunctionSpy calls with call_original=False and keyword
        arguments
        """
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

    def test_call_with_original_true_and_function(self):
        """Testing FunctionSpy calls with call_original=True and function"""
        self.agency.spy_on(something_awesome, call_original=True)
        result = something_awesome()

        self.assertEqual(result, 'Tada!')
        self.assertTrue(hasattr(something_awesome, 'spy'))
        self.assertEqual(len(something_awesome.spy.calls), 1)
        self.assertEqual(len(something_awesome.spy.calls[0].args), 0)
        self.assertEqual(len(something_awesome.spy.calls[0].kwargs), 0)

    def test_call_with_original_true_and_function_args(self):
        """Testing FunctionSpy calls with call_original=True and function
        with all positional arguments
        """
        self.agency.spy_on(do_math_pos, call_original=True)
        result = do_math_pos(10, 20)

        self.assertEqual(result, -10)
        self.assertEqual(len(do_math_pos.spy.calls), 1)
        self.assertEqual(do_math_pos.spy.calls[0].args, (10, 20))
        self.assertEqual(len(do_math_pos.spy.calls[0].kwargs), 0)

    def test_call_with_original_true_and_function_args_for_kwargs(self):
        """Testing FunctionSpy calls with call_original=True and function
        with all positional arguments in place of keyword arguments
        """
        self.agency.spy_on(do_math, call_original=True)
        result = do_math(10, 20)

        self.assertEqual(result, -10)
        self.assertEqual(len(do_math.spy.calls), 1)
        self.assertEqual(do_math.spy.calls[0].args, ())
        self.assertEqual(do_math.spy.calls[0].kwargs, {
            'a': 10,
            'b': 20,
        })

    def test_call_with_original_true_and_function_kwargs(self):
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

    def test_call_with_original_true_and_function_mixed(self):
        """Testing FunctionSpy calls with call_original=True and function
        with all mixed argument types
        """
        self.agency.spy_on(do_math, call_original=True)
        result = do_math(10, b=20, unused=True)

        self.assertEqual(result, -10)
        self.assertEqual(len(do_math.spy.calls), 1)
        self.assertEqual(do_math.spy.calls[0].args, ())
        self.assertEqual(do_math.spy.calls[0].kwargs, {
            'a': 10,
            'b': 20,
            'unused': True,
        })

        self.agency.spy_on(do_math_pos, call_original=True)
        result = do_math_pos(10, b=20)

        self.assertEqual(result, -10)
        self.assertEqual(len(do_math_pos.spy.calls), 1)
        self.assertEqual(do_math_pos.spy.calls[0].args, (10, 20))
        self.assertEqual(do_math_pos.spy.calls[0].kwargs, {})

        self.agency.spy_on(do_math_mixed, call_original=True)
        result = do_math_mixed(10, b=20, unused=True)

        self.assertEqual(result, -10)
        self.assertEqual(len(do_math_mixed.spy.calls), 1)
        self.assertEqual(do_math_mixed.spy.calls[0].args, (10,))
        self.assertEqual(do_math_mixed.spy.calls[0].kwargs, {
            'b': 20,
            'unused': True,
        })

    def test_call_with_original_true_and_bound_method(self):
        """Testing FunctionSpy calls with call_original=True and bound method
        """
        obj = MathClass()

        self.agency.spy_on(obj.do_math, call_original=True)
        result = obj.do_math()

        self.assertEqual(result, 3)
        self.assertEqual(len(obj.do_math.calls), 1)
        self.assertTrue(obj.do_math.last_called_with(a=1, b=2))

    def test_call_with_original_true_and_bound_method_args(self):
        """Testing FunctionSpy calls with call_original=True and bound method
        with all positional arguments
        """
        obj = MathClass()

        self.agency.spy_on(obj.do_math_pos, call_original=True)
        result = obj.do_math_pos(10, 20)

        self.assertEqual(result, 30)
        self.assertEqual(len(obj.do_math_pos.calls), 1)
        self.assertEqual(obj.do_math_pos.calls[0].args, (10, 20))
        self.assertEqual(len(obj.do_math_pos.calls[0].kwargs), 0)

    def test_call_with_original_true_and_bound_method_args_for_kwargs(self):
        """Testing FunctionSpy calls with call_original=True and bound method
        with all positional arguments in place of keyword arguments
        """
        obj = MathClass()

        self.agency.spy_on(obj.do_math, call_original=True)
        result = obj.do_math(10, 20)

        self.assertEqual(result, 30)
        self.assertEqual(len(obj.do_math.calls), 1)
        self.assertEqual(obj.do_math.calls[0].args, ())
        self.assertEqual(obj.do_math.calls[0].kwargs, {
            'a': 10,
            'b': 20,
        })

    def test_call_with_original_true_and_bound_method_kwargs(self):
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

    def test_call_with_original_true_and_unbound_method(self):
        """Testing FunctionSpy calls with call_original=True and unbound method
        """
        self.agency.spy_on(MathClass.do_math, call_original=True)

        obj = MathClass()
        result = obj.do_math()

        self.assertEqual(result, 3)
        self.assertEqual(len(MathClass.do_math.calls), 1)
        self.assertTrue(MathClass.do_math.last_called_with(a=1, b=2))

    def test_call_with_original_true_and_unbound_method_args(self):
        """Testing FunctionSpy calls with call_original=True and unbound
        method with all positional arguments
        """
        self.agency.spy_on(MathClass.do_math_pos, call_original=True)

        obj = MathClass()
        result = obj.do_math_pos(10, 20)

        self.assertEqual(result, 30)
        self.assertEqual(len(MathClass.do_math_pos.calls), 1)
        self.assertTrue(MathClass.do_math_pos.last_called_with(10, 20))

    def test_call_with_original_true_and_unbound_method_args_for_kwargs(self):
        """Testing FunctionSpy calls with call_original=True and unbound
        method with all positional arguments in place of keyword arguments
        """
        self.agency.spy_on(MathClass.do_math, call_original=True)

        obj = MathClass()
        result = obj.do_math(10, 20)

        self.assertEqual(result, 30)
        self.assertEqual(len(MathClass.do_math.calls), 1)
        self.assertTrue(MathClass.do_math.last_called_with(a=10, b=20))

    def test_call_with_original_true_and_unbound_method_kwargs(self):
        """Testing FunctionSpy calls with call_original=True and unbound method
        with all keyword arguments
        """
        self.agency.spy_on(MathClass.do_math, call_original=True)

        obj = MathClass()
        result = obj.do_math(a=10, b=20)

        self.assertEqual(result, 30)
        self.assertEqual(len(MathClass.do_math.calls), 1)
        self.assertEqual(len(MathClass.do_math.calls[0].args), 0)
        self.assertTrue(MathClass.do_math.last_called_with(a=10, b=20))

    def test_call_with_original_true_and_classmethod(self):
        """Testing FunctionSpy calls with call_original=True and classmethod"""
        self.agency.spy_on(MathClass.class_do_math, call_original=True)
        result = MathClass.class_do_math()

        self.assertEqual(result, 10)
        self.assertEqual(len(MathClass.class_do_math.calls), 1)
        self.assertTrue(MathClass.class_do_math.last_called_with(a=2, b=5))

    def test_call_with_original_true_and_classmethod_args(self):
        """Testing FunctionSpy calls with call_original=True and classmethod
        with all positional arguments
        """
        self.agency.spy_on(MathClass.class_do_math_pos, call_original=True)
        result = MathClass.class_do_math_pos(10, 20)

        self.assertEqual(result, 200)
        self.assertEqual(len(MathClass.class_do_math_pos.calls), 1)
        self.assertEqual(MathClass.class_do_math_pos.calls[0].args, (10, 20))
        self.assertEqual(len(MathClass.class_do_math_pos.calls[0].kwargs), 0)

    def test_call_with_original_true_and_classmethod_args_for_kwargs(self):
        """Testing FunctionSpy calls with call_original=True and classmethod
        with all positional arguments in place of keyword arguments
        """
        self.agency.spy_on(MathClass.class_do_math, call_original=True)
        result = MathClass.class_do_math(10, 20)

        self.assertEqual(result, 200)
        self.assertEqual(len(MathClass.class_do_math.calls), 1)
        self.assertEqual(MathClass.class_do_math.calls[0].args, ())
        self.assertEqual(MathClass.class_do_math.calls[0].kwargs, {
            'a': 10,
            'b': 20,
        })

    def test_call_with_original_true_and_classmethod_kwargs(self):
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

    def test_call_with_inline_function_using_closure_vars(self):
        """Testing FunctionSpy calls for inline function using a closure's
        variables
        """
        d = {}

        def func():
            d['called'] = True

        self.agency.spy_on(func)

        func()
        self.assertTrue(func.called)
        self.assertEqual(d, {'called': True})

    def test_call_with_inline_function_using_closure_vars_and_args(self):
        """Testing FunctionSpy calls for inline function using a closure's
        variables and function with arguments
        """
        d = {}

        def func(a, b, c):
            d['call_result'] = a + b + c

        self.agency.spy_on(func)

        func(1, 2, c=3)
        self.assertTrue(func.called)
        self.assertEqual(d, {'call_result': 6})

    def test_call_with_function_providing_closure_vars(self):
        """Testing FunctionSpy calls for function providing variables for an
        inline function
        """
        def func():
            d = {}

            def inline_func():
                d['called'] = True

            inline_func()

            return d

        self.agency.spy_on(func)

        d = func()
        self.assertTrue(func.called)
        self.assertEqual(d, {'called': True})

    def test_call_with_function_providing_closure_access_args(self):
        """Testing FunctionSpy calls with an inline function accessing
        parent's arguments
        """
        # NOTE: This originally caused a crash on Python 3.13 beta 2.
        #       See: https://github.com/beanbaginc/kgb/issues/11
        def func(arg):
            def inline_func():
                print(arg)

            return 123

        self.agency.spy_on(func)

        d = func(42)
        self.assertEqual(d, 123)
        self.assertTrue(func.called)

    def test_call_with_bound_method_with_list_comprehension_and_self(self):
        """Testing FunctionSpy calls for bound method using a list
        comprehension referencing 'self'
        """
        obj = AdderObject()
        self.agency.spy_on(obj.func)

        result = obj.func()
        self.assertTrue(obj.func.called)
        self.assertEqual(result, [2, 3, 4])

    def test_call_with_unbound_method_with_list_comprehension_and_self(self):
        """Testing FunctionSpy calls for unbound method using a list
        comprehension referencing 'self'
        """
        self.agency.spy_on(AdderObject.func)

        obj = AdderObject()
        result = obj.func()
        self.assertTrue(obj.func.called)
        self.assertEqual(result, [2, 3, 4])

    def test_call_with_classmethod_with_list_comprehension_and_self(self):
        """Testing FunctionSpy calls for classmethod using a list
        comprehension referencing 'cls'
        """
        self.agency.spy_on(AdderObject.class_func)

        result = AdderObject.class_func()
        self.assertTrue(AdderObject.class_func.called)
        self.assertEqual(result, [2, 3, 4])

    def test_call_original_with_orig_func_and_function(self):
        """Testing FunctionSpy.call_original with spy on function set up using
        call_original=True
        """
        self.agency.spy_on(do_math,
                           call_original=True)

        result = do_math.call_original(10, 20)
        self.assertEqual(result, -10)

        self.assertFalse(do_math.called)

    def test_call_original_with_orig_func_and_bound_method(self):
        """Testing FunctionSpy.call_original with spy on bound method set up
        using call_original=True
        """
        obj = AdderObject()
        self.agency.spy_on(obj.add_one,
                           call_original=True)

        result = obj.add_one.call_original(5)
        self.assertEqual(result, 6)

        self.assertFalse(obj.add_one.called)

    def test_call_original_with_orig_func_and_unbound_method(self):
        """Testing FunctionSpy.call_original with spy on unbound method set up
        using call_original=True
        """
        self.agency.spy_on(AdderObject.add_one,
                           call_original=True)

        obj = AdderObject()
        result = obj.add_one.call_original(obj, 5)
        self.assertEqual(result, 6)

        self.assertFalse(AdderObject.add_one.called)
        self.assertFalse(obj.add_one.called)

    def test_call_original_with_orig_func_and_classmethod(self):
        """Testing FunctionSpy.call_original with spy on classmethod set up
        using call_original=True
        """
        self.agency.spy_on(AdderObject.class_add_one,
                           call_original=True)

        result = AdderObject.class_add_one.call_original(5)
        self.assertEqual(result, 6)

        self.assertFalse(AdderObject.class_add_one.called)

    def test_call_original_with_no_func_and_function(self):
        """Testing FunctionSpy.call_original with spy on function set up using
        call_original=False
        """
        self.agency.spy_on(do_math)

        result = do_math.call_original(10, 20)
        self.assertEqual(result, -10)

        self.assertFalse(do_math.called)

    def test_call_original_with_no_func_and_bound_method(self):
        """Testing FunctionSpy.call_original with spy on bound method set up
        using call_original=False
        """
        obj = MathClass()
        self.agency.spy_on(obj.do_math)

        result = obj.do_math.call_original(10, 20)
        self.assertEqual(result, 30)

        self.assertFalse(obj.do_math.called)

    def test_call_original_with_no_func_and_unbound_method(self):
        """Testing FunctionSpy.call_original with spy on unbound method set up
        using call_original=False
        """
        self.agency.spy_on(MathClass.do_math)

        obj = MathClass()
        result = obj.do_math.call_original(obj, 10, 20)
        self.assertEqual(result, 30)

        self.assertFalse(MathClass.do_math.called)
        self.assertFalse(obj.do_math.called)

    def test_call_original_with_no_func_and_classmethod(self):
        """Testing FunctionSpy.call_original with spy on classmethod set up
        using call_original=False
        """
        self.agency.spy_on(MathClass.class_do_math)

        result = MathClass.class_do_math.call_original(10, 20)
        self.assertEqual(result, 200)

        self.assertFalse(MathClass.class_do_math.called)

    def test_call_original_with_fake_func_and_function(self):
        """Testing FunctionSpy.call_original with spy on function set up using
        call_fake=
        """
        self.agency.spy_on(do_math,
                           call_fake=fake_do_math)

        result = do_math.call_original(10, 20)
        self.assertEqual(result, -10)

        self.assertFalse(do_math.called)

    def test_call_original_with_fake_func_and_bound_method(self):
        """Testing FunctionSpy.call_original with spy on bound method set up
        using call_fake=
        """
        obj = MathClass()
        self.agency.spy_on(obj.do_math,
                           call_fake=fake_do_math)

        result = obj.do_math.call_original(10, 20)
        self.assertEqual(result, 30)

        self.assertFalse(obj.do_math.called)

    def test_call_original_with_fake_func_and_unbound_method(self):
        """Testing FunctionSpy.call_original with spy on unbound method set up
        using call_fake=
        """
        self.agency.spy_on(MathClass.do_math,
                           call_fake=fake_do_math)

        obj = MathClass()
        result = obj.do_math.call_original(obj, 10, 20)
        self.assertEqual(result, 30)

        self.assertFalse(MathClass.do_math.called)
        self.assertFalse(obj.do_math.called)

    def test_call_original_with_fake_func_and_classmethod(self):
        """Testing FunctionSpy.call_original with spy on classmethod set up
        using call_fake=
        """
        self.agency.spy_on(MathClass.class_do_math,
                           call_fake=fake_class_do_math)

        result = MathClass.class_do_math.call_original(10, 20)
        self.assertEqual(result, 200)

        self.assertFalse(MathClass.class_do_math.called)

    def test_call_original_with_unbound_method_no_instance(self):
        """Testing FunctionSpy.call_original with spy on unbound method set up
        using call_original=True without passing instance
        """
        self.agency.spy_on(AdderObject.add_one,
                           call_original=True)

        obj = AdderObject()

        message = re.escape(
            'The first argument to add_one.call_original() must be an '
            'instance of kgb.tests.test_function_spy.AdderObject, since this '
            'is an unbound method.'
        )

        with self.assertRaisesRegex(TypeError, message):
            obj.add_one.call_original(5)

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
        self.assertTrue(last_call.called_with(a=20, b=30))

    def test_last_call_with_no_calls(self):
        """Testing FunctionSpy.last_call on uncalled function"""
        obj = MathClass()
        self.agency.spy_on(obj.do_math)

        self.assertEqual(len(obj.do_math.calls), 0)

        last_call = obj.do_math.last_call
        self.assertEqual(last_call, None)

    def test_unspy(self):
        """Testing FunctionSpy.unspy"""
        orig_code = getattr(something_awesome, FunctionSig.FUNC_CODE_ATTR)
        spy = self.agency.spy_on(something_awesome, call_fake=lambda: 'spy!')

        self.assertTrue(hasattr(something_awesome, 'spy'))
        self.assertEqual(something_awesome.spy, spy)
        self.assertEqual(something_awesome(), 'spy!')

        spy.unspy()
        self.assertFalse(hasattr(something_awesome, 'spy'))
        self.assertEqual(getattr(something_awesome,
                                 FunctionSig.FUNC_CODE_ATTR),
                         orig_code)
        self.assertEqual(something_awesome(), 'Tada!')

    def test_unspy_and_bound_method(self):
        """Testing FunctionSpy.unspy and bound method"""
        obj = MathClass()
        func_dict = obj.do_math.__dict__.copy()

        spy = self.agency.spy_on(obj.do_math)
        self.assertNotEqual(obj.do_math.__dict__, func_dict)

        spy.unspy()
        self.assertEqual(obj.do_math.__dict__, func_dict)

    def test_unspy_with_bound_method_and_custom_setattr(self):
        """Testing FunctionSpy.unspy with a bound method on a class containing
        a custom __setattr__
        """
        class MyObject(object):
            def __setattr__(self, key, value):
                assert False

            def foo(self):
                pass

        obj = MyObject()
        func_dict = obj.foo.__dict__.copy()

        spy = self.agency.spy_on(obj.foo)
        self.assertNotEqual(obj.foo.__dict__, func_dict)

        spy.unspy()
        self.assertEqual(obj.foo.__dict__, func_dict)

    def test_unspy_and_unbound_method(self):
        """Testing FunctionSpy.unspy and unbound method"""
        func_dict = MathClass.do_math.__dict__.copy()

        spy = self.agency.spy_on(MathClass.do_math)
        self.assertNotEqual(MathClass.do_math.__dict__, func_dict)

        spy.unspy()
        self.assertEqual(MathClass.do_math.__dict__, func_dict)

    def test_unspy_with_classmethod(self):
        """Testing FunctionSpy.unspy with classmethod"""
        func_dict = MathClass.class_do_math.__dict__.copy()

        spy = self.agency.spy_on(MathClass.class_do_math)
        self.assertNotEqual(MathClass.class_do_math.__dict__, func_dict)

        spy.unspy()
        self.assertEqual(MathClass.class_do_math.__dict__, func_dict)

    def test_unspy_with_classmethod_on_parent(self):
        """Testing FunctionSpy.unspy with classmethod on parent class"""
        class MyParent(object):
            @classmethod
            def foo(self):
                pass

        class MyObject(MyParent):
            pass

        parent_func_dict = MyParent.foo.__dict__.copy()
        obj_func_dict = MyObject.foo.__dict__.copy()

        spy = self.agency.spy_on(MyObject.foo)
        self.assertNotEqual(MyObject.foo.__dict__, obj_func_dict)
        self.assertEqual(MyParent.foo.__dict__, parent_func_dict)

        spy.unspy()
        self.assertEqual(MyObject.foo.__dict__, obj_func_dict)
        self.assertEqual(MyParent.foo.__dict__, parent_func_dict)

    def test_unspy_with_unbound_method_on_parent(self):
        """Testing FunctionSpy.unspy with unbound method on parent class"""
        class MyParent(object):
            def foo(self):
                pass

        class MyObject(MyParent):
            pass

        parent_func_dict = MyParent.foo.__dict__.copy()
        obj_func_dict = MyObject.foo.__dict__.copy()

        spy = self.agency.spy_on(MyObject.foo, owner=MyObject)
        self.assertNotEqual(MyObject.foo.__dict__, obj_func_dict)
        self.assertEqual(MyParent.foo.__dict__, parent_func_dict)

        spy.unspy()
        self.assertEqual(MyObject.foo.__dict__, obj_func_dict)
        self.assertEqual(MyParent.foo.__dict__, parent_func_dict)

    def test_unspy_with_slippery_bound_method(self):
        """Testing FunctionSpy.unspy with slippery function generated by
        spied-on bound method
        """
        obj = SlipperyFuncObject()
        spy = self.agency.spy_on(obj.my_func, owner=obj)
        spy.unspy()

        self.assertFalse(hasattr(obj.my_func, 'spy'))
        self.assertNotIn('my_func', obj.__dict__)

        # Make sure the old behavior has reverted.
        slippery_func.count = 0

        func1 = obj.my_func
        func2 = obj.my_func
        self.assertIsNot(func1, func2)

        # These will have already had their values set, so we should get
        # stable results again.
        self.assertEqual(func1(), 0)
        self.assertEqual(func1(), 0)
        self.assertEqual(func2(), 1)
        self.assertEqual(func2(), 1)

        # These will trigger new counter increments when re-generating the
        # function in the decorator.
        self.assertEqual(obj.my_func(), 2)
        self.assertEqual(obj.my_func(), 3)

    def test_called_with(self):
        """Testing FunctionSpy.called_with"""
        obj = MathClass()
        self.agency.spy_on(obj.do_math_mixed)

        obj.do_math_mixed(1, b=2)
        obj.do_math_mixed(3, b=4)

        self.assertTrue(obj.do_math_mixed.called_with(1, b=2))
        self.assertTrue(obj.do_math_mixed.called_with(3, b=4))
        self.assertTrue(obj.do_math_mixed.called_with(a=1, b=2))
        self.assertTrue(obj.do_math_mixed.called_with(a=3, b=4))
        self.assertFalse(obj.do_math_mixed.called_with(1, 2))
        self.assertFalse(obj.do_math_mixed.called_with(3, 4))
        self.assertFalse(obj.do_math_mixed.called_with(5, b=6))

    def test_called_with_and_keyword_args(self):
        """Testing FunctionSpy.called_with and keyword arguments"""
        obj = MathClass()
        self.agency.spy_on(obj.do_math_mixed)

        obj.do_math_mixed(a=1, b=2)
        obj.do_math_mixed(a=3, b=4)

        self.assertTrue(obj.do_math_mixed.called_with(1, b=2))
        self.assertTrue(obj.do_math_mixed.called_with(3, b=4))
        self.assertTrue(obj.do_math_mixed.called_with(a=1, b=2))
        self.assertTrue(obj.do_math_mixed.called_with(a=3, b=4))
        self.assertFalse(obj.do_math_mixed.called_with(5, b=6))

    def test_called_with_and_partial_args(self):
        """Testing FunctionSpy.called_with and partial arguments"""
        obj = MathClass()
        self.agency.spy_on(obj.do_math_mixed)

        obj.do_math_mixed(1, 2)
        obj.do_math_mixed(3, 4)

        self.assertTrue(obj.do_math_mixed.called_with(1))
        self.assertTrue(obj.do_math_mixed.called_with(3))
        self.assertFalse(obj.do_math_mixed.called_with(4))
        self.assertFalse(obj.do_math_mixed.called_with(1, 2, 3))

    def test_called_with_and_partial_kwargs(self):
        """Testing FunctionSpy.called_with and partial keyword arguments"""
        obj = MathClass()
        self.agency.spy_on(obj.do_math_mixed)

        obj.do_math_mixed(a=1, b=2)
        obj.do_math_mixed(a=3, b=4)

        self.assertTrue(obj.do_math_mixed.called_with(1))
        self.assertTrue(obj.do_math_mixed.called_with(b=2))
        self.assertTrue(obj.do_math_mixed.called_with(3))
        self.assertTrue(obj.do_math_mixed.called_with(b=4))
        self.assertTrue(obj.do_math_mixed.called_with(a=1, b=2))
        self.assertTrue(obj.do_math_mixed.called_with(a=3, b=4))
        self.assertFalse(obj.do_math_mixed.called_with(1, 2))
        self.assertFalse(obj.do_math_mixed.called_with(3, 4))
        self.assertFalse(obj.do_math_mixed.called_with(a=4))
        self.assertFalse(obj.do_math_mixed.called_with(a=1, b=2, c=3))
        self.assertFalse(obj.do_math_mixed.called_with(a=1, b=4))
        self.assertFalse(obj.do_math_mixed.called_with(a=3, b=2))

    def test_last_called_with(self):
        """Testing FunctionSpy.last_called_with"""
        obj = MathClass()
        self.agency.spy_on(obj.do_math_mixed)

        obj.do_math_mixed(1, 2)
        obj.do_math_mixed(3, 4)

        self.assertFalse(obj.do_math_mixed.last_called_with(1, a=2))
        self.assertTrue(obj.do_math_mixed.last_called_with(3, b=4))

    def test_last_called_with_and_keyword_args(self):
        """Testing FunctionSpy.last_called_with and keyword arguments"""
        obj = MathClass()
        self.agency.spy_on(obj.do_math_mixed)

        obj.do_math_mixed(a=1, b=2)
        obj.do_math_mixed(a=3, b=4)

        self.assertTrue(obj.do_math_mixed.last_called_with(3, b=4))
        self.assertFalse(obj.do_math_mixed.last_called_with(1, b=2))
        self.assertFalse(obj.do_math_mixed.last_called_with(1, b=2, c=3))

    def test_last_called_with_and_partial_args(self):
        """Testing FunctionSpy.called_with and partial arguments"""
        obj = MathClass()
        self.agency.spy_on(obj.do_math_mixed)

        obj.do_math_mixed(1, 2)
        obj.do_math_mixed(3, 4)

        self.assertTrue(obj.do_math_mixed.last_called_with(3))
        self.assertTrue(obj.do_math_mixed.last_called_with(3, b=4))
        self.assertFalse(obj.do_math_mixed.last_called_with(3, b=4, c=5))
        self.assertFalse(obj.do_math_mixed.last_called_with(1, b=2))

    def test_last_called_with_and_partial_kwargs(self):
        """Testing FunctionSpy.called_with and partial keyword arguments"""
        obj = MathClass()
        self.agency.spy_on(obj.do_math_mixed)

        obj.do_math_mixed(a=1, b=2)
        obj.do_math_mixed(a=3, b=4)

        self.assertTrue(obj.do_math_mixed.last_called_with(3))
        self.assertTrue(obj.do_math_mixed.last_called_with(b=4))
        self.assertFalse(obj.do_math_mixed.last_called_with(a=1))
        self.assertFalse(obj.do_math_mixed.last_called_with(b=2))
        self.assertFalse(obj.do_math_mixed.last_called_with(b=3))
        self.assertFalse(obj.do_math_mixed.last_called_with(3, 4))
        self.assertFalse(obj.do_math_mixed.last_called_with(a=1, b=2, c=3))
        self.assertFalse(obj.do_math_mixed.last_called_with(a=1, c=3))

    def test_returned(self):
        """Testing FunctionSpy.returned"""
        obj = MathClass()
        self.agency.spy_on(obj.do_math)

        obj.do_math(1, 2)
        obj.do_math(3, 4)

        self.assertTrue(obj.do_math.returned(3))
        self.assertTrue(obj.do_math.returned(7))
        self.assertFalse(obj.do_math.returned(10))
        self.assertFalse(obj.do_math.returned(None))

    def test_last_returned(self):
        """Testing FunctionSpy.last_returned"""
        obj = MathClass()
        self.agency.spy_on(obj.do_math)

        obj.do_math(1, 2)
        obj.do_math(3, 4)

        self.assertFalse(obj.do_math.last_returned(3))
        self.assertTrue(obj.do_math.last_returned(7))
        self.assertFalse(obj.do_math.last_returned(None))

    def test_raised(self):
        """Testing FunctionSpy.raised"""
        obj = MathClass()
        self.agency.spy_on(obj.do_math)

        with self.assertRaises(TypeError):
            obj.do_math(1, 'a')

        self.assertTrue(obj.do_math.raised(TypeError))
        self.assertFalse(obj.do_math.raised(ValueError))
        self.assertFalse(obj.do_math.raised(None))

    def test_last_raised(self):
        """Testing FunctionSpy.last_raised"""
        obj = MathClass()
        self.agency.spy_on(obj.do_math)

        with self.assertRaises(TypeError):
            obj.do_math(1, 'a')

        self.assertTrue(obj.do_math.last_raised(TypeError))
        self.assertFalse(obj.do_math.last_raised(None))

        obj.do_math(1, 4)

        self.assertFalse(obj.do_math.last_raised(TypeError))
        self.assertTrue(obj.do_math.last_raised(None))

    def test_raised_with_message(self):
        """Testing FunctionSpy.raised_with_message"""
        obj = MathClass()
        self.agency.spy_on(obj.do_math)

        with self.assertRaises(TypeError):
            obj.do_math(1, 'a')

        self.assertTrue(obj.do_math.raised_with_message(
            TypeError,
            "unsupported operand type(s) for +: 'int' and '%s'"
            % text_type.__name__))
        self.assertFalse(obj.do_math.raised_with_message(
            ValueError,
            "unsupported operand type(s) for +: 'int' and '%s'"
            % text_type.__name__))
        self.assertFalse(obj.do_math.raised_with_message(TypeError, None))

    def test_last_raised_with_message(self):
        """Testing FunctionSpy.last_raised_with_message"""
        obj = MathClass()
        self.agency.spy_on(obj.do_math)

        with self.assertRaises(TypeError):
            obj.do_math(1, 'a')

        self.assertTrue(obj.do_math.last_raised_with_message(
            TypeError,
            "unsupported operand type(s) for +: 'int' and '%s'"
            % text_type.__name__))
        self.assertFalse(obj.do_math.last_raised_with_message(TypeError, None))

    def test_reset_calls(self):
        """Testing FunctionSpy.reset_calls"""
        obj = MathClass()
        self.agency.spy_on(obj.do_math)

        obj.do_math(1, 2)
        self.assertEqual(len(obj.do_math.calls), 1)
        self.assertEqual(obj.do_math.last_call, obj.do_math.calls[-1])
        self.assertTrue(obj.do_math.called)

        obj.do_math.reset_calls()
        self.assertEqual(len(obj.do_math.calls), 0)
        self.assertIsNone(obj.do_math.last_call)
        self.assertFalse(obj.do_math.called)

    def test_repr(self):
        """Testing FunctionSpy.__repr__"""
        self.agency.spy_on(something_awesome)

        self.assertTrue(hasattr(something_awesome, 'spy'))
        self.assertTrue(repr(something_awesome.spy),
                        '<Spy for something_awesome (0 calls)>')

    def test_repr_and_function(self):
        """Testing FunctionSpy.__repr__ and function"""
        self.agency.spy_on(do_math)

        self.assertEqual(repr(do_math.spy),
                         '<Spy for function do_math (0 calls)>')

    def test_repr_and_bound_method(self):
        """Testing FunctionSpy.__repr__ and bound method"""
        obj = MathClass()
        self.agency.spy_on(obj.do_math)

        obj.do_math()

        self.assertEqual(repr(obj.do_math.spy),
                         '<Spy for bound method MathClass.do_math '
                         'of %r (1 call)>' % obj)

    def test_repr_and_unbound_method(self):
        """Testing FunctionSpy.__repr__ and unbound method"""
        self.agency.spy_on(MathClass.do_math)

        self.assertEqual(repr(MathClass.do_math.spy),
                         '<Spy for unbound method MathClass.do_math '
                         'of %r (0 calls)>' % MathClass)

    def test_repr_with_classmethod(self):
        """Testing FunctionSpy.__repr__ with classmethod"""
        self.agency.spy_on(MathClass.class_do_math)

        self.assertEqual(
            repr(MathClass.class_do_math.spy),
            '<Spy for classmethod MathClass.class_do_math of %r (0 calls)>'
            % MathClass)

    @require_getargspec
    def test_getargspec_with_function(self):
        """Testing FunctionSpy in inspect.getargspec() with function"""
        self.agency.spy_on(do_math)

        args, varargs, keywords, defaults = inspect.getargspec(do_math)
        self.assertEqual(args, ['a', 'b'])
        self.assertEqual(varargs, 'args')
        self.assertEqual(keywords, 'kwargs')
        self.assertEqual(defaults, (1, 2))

    @require_getargspec
    def test_getargspec_with_bound_method(self):
        """Testing FunctionSpy in inspect.getargspec() with bound method"""
        obj = MathClass()
        self.agency.spy_on(obj.do_math)

        args, varargs, keywords, defaults = inspect.getargspec(obj.do_math)
        self.assertEqual(args, ['self', 'a', 'b'])
        self.assertEqual(varargs, 'args')
        self.assertEqual(keywords, 'kwargs')
        self.assertEqual(defaults, (1, 2))

    @require_getargspec
    def test_getargspec_with_unbound_method(self):
        """Testing FunctionSpy in inspect.getargspec() with unbound method"""
        self.agency.spy_on(MathClass.do_math)

        args, varargs, keywords, defaults = \
            inspect.getargspec(MathClass.do_math)
        self.assertEqual(args, ['self', 'a', 'b'])
        self.assertEqual(varargs, 'args')
        self.assertEqual(keywords, 'kwargs')
        self.assertEqual(defaults, (1, 2))

    @require_getargspec
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
