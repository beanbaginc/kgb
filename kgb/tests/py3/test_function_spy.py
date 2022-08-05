import functools
import inspect
import logging
import sys
from unittest import SkipTest

from kgb.tests.base import TestCase


logger = logging.getLogger('kgb')


def require_func_pos_only_args(func):
    """Require positional-only arguments for a function.

    If not available, the test will be skippd.

    Args:
        func (callable):
            The unit test function to decorate.
    """
    @functools.wraps(func)
    def _wrap(*args, **kwargs):
        if sys.version_info[:2] >= (3, 8):
            return func(*args, **kwargs)
        else:
            raise SkipTest('inspect.getargspec is not available on Python 3.8')

    return _wrap


class FunctionSpyTests(TestCase):
    """Python 3 unit tests for kgb.spies.FunctionSpy."""

    def test_spy_with_function_copies_attribute_state(self):
        """Testing FunctionSpy with functions copies all attribute states"""
        def func(a: str, b: int = 1, *, c: int = 3) -> bool:
            return False

        self.agency.spy_on(func)
        spy_func = func.spy.func

        self.assertIsNot(spy_func, func)
        self.assertEqual(
            spy_func.__kwdefaults__,
            {
                'c': 3,
            })
        self.assertEqual(
            spy_func.__annotations__,
            {
                'a': str,
                'b': int,
                'c': int,
                'return': bool,
            })

    def test_spy_with_bound_methods_copies_attribute_state(self):
        """Testing FunctionSpy with bound methods copies all attribute states
        """
        class A:
            def func(a: str, b: int = 1, *, c: int = 3) -> bool:
                return False

        a = A()
        self.agency.spy_on(a.func)
        spy_func = a.func.spy.func

        self.assertIsNot(spy_func, a.func)
        self.assertEqual(
            spy_func.__kwdefaults__,
            {
                'c': 3,
            })
        self.assertEqual(
            spy_func.__annotations__,
            {
                'a': str,
                'b': int,
                'c': int,
                'return': bool,
            })

    def test_spy_with_unbound_methods_copies_attribute_state(self):
        """Testing FunctionSpy with unbound methods copies all attribute states
        """
        class A:
            def func(a: str, b: int = 1, *, c: int = 3) -> bool:
                return False

        self.agency.spy_on(A.func)
        spy_func = A.func.spy.func

        self.assertIsNot(spy_func, A.func)
        self.assertEqual(
            spy_func.__kwdefaults__,
            {
                'c': 3,
            })
        self.assertEqual(
            spy_func.__annotations__,
            {
                'a': str,
                'b': int,
                'c': int,
                'return': bool,
            })

    @require_func_pos_only_args
    def test_call_with_function_and_positional_only_args(self):
        """Testing FunctionSpy calls with function containing positional-only
        arguments
        """
        func = self.make_func("""
            def func(a, b=1, /):
                return a * b
        """)

        self.agency.spy_on(func)
        result = func(2, 5)

        self.assertEqual(result, 10)
        self.assertEqual(len(func.spy.calls), 1)
        self.assertEqual(func.spy.calls[0].args, (2, 5))
        self.assertEqual(func.spy.calls[0].kwargs, {})

    @require_func_pos_only_args
    def test_call_with_function_and_positional_only_args_no_pos_passed(self):
        """Testing FunctionSpy calls with function containing positional-only
        arguments and no positional argument passed
        """
        func = self.make_func("""
            def func(a, b=2, /):
                return a * b
        """)

        self.agency.spy_on(func)
        result = func(2)

        self.assertEqual(result, 4)
        self.assertEqual(len(func.spy.calls), 1)
        self.assertEqual(func.spy.calls[0].args, (2, 2))
        self.assertEqual(func.spy.calls[0].kwargs, {})

    def test_call_with_function_and_keyword_only_args(self):
        """Testing FunctionSpy calls with function containing keyword-only
        arguments
        """
        def func(a, *, b=2):
            return a * b

        self.agency.spy_on(func)
        result = func(2, b=5)

        self.assertEqual(result, 10)
        self.assertEqual(len(func.spy.calls), 1)
        self.assertEqual(func.spy.calls[0].args, (2,))
        self.assertEqual(func.spy.calls[0].kwargs, {'b': 5})

    def test_call_with_function_and_keyword_only_args_no_kw_passed(self):
        """Testing FunctionSpy calls with function containing keyword-only
        arguments and no keyword passed
        """
        def func(a, *, b=2):
            return a * b

        self.agency.spy_on(func)
        result = func(2)

        self.assertEqual(result, 4)
        self.assertEqual(len(func.spy.calls), 1)
        self.assertEqual(func.spy.calls[0].args, (2,))
        self.assertEqual(func.spy.calls[0].kwargs, {'b': 2})

    def test_init_with_unbound_method_decorator_bad_func_name(self):
        """Testing FunctionSpy construction with a decorator not preserving
        an unbound method name
        """
        def bad_deco(func):
            def _wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            return _wrapper

        class MyObject(object):
            @bad_deco
            def my_method(self):
                pass

        self.agency.spy_on(logger.warning)

        self.agency.spy_on(MyObject.my_method,
                           owner=MyObject)

        self.agency.assertSpyCalledWith(
            logger.warning,
            "%r doesn't have a function named \"%s\". This "
            "appears to be a decorator that doesn't "
            "preserve function names. Try passing "
            "func_name= when setting up the spy.",
            MyObject,
            '_wrapper')

    def test_init_with_unbound_method_decorator_corrected_func_name(self):
        """Testing FunctionSpy construction with a decorator not preserving
        an unbound method name and explicit func_name= provided
        """
        def bad_deco(func):
            def _wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            return _wrapper

        class MyObject(object):
            @bad_deco
            def my_method(self):
                pass

        self.agency.spy_on(logger.warning)

        self.agency.spy_on(MyObject.my_method,
                           owner=MyObject,
                           func_name='my_method')

        self.agency.assertSpyNotCalled(logger.warning)

    def test_getfullargspec_with_function(self):
        """Testing FunctionSpy in inspect.getfullargspec() with function"""
        def func(a, b=2):
            return a * b

        self.agency.spy_on(func)

        argspec = inspect.getfullargspec(func)

        self.assertEqual(argspec.args, ['a', 'b'])
        self.assertIsNone(argspec.varargs)
        self.assertIsNone(argspec.varkw)
        self.assertEqual(argspec.defaults, (2,))
        self.assertEqual(argspec.kwonlyargs, [])
        self.assertIsNone(argspec.kwonlydefaults)
        self.assertEqual(argspec.annotations, {})

    @require_func_pos_only_args
    def test_getfullargspec_with_function_pos_only(self):
        """Testing FunctionSpy in inspect.getfullargspec() with function and
        positional-only arguments
        """
        func = self.make_func("""
            def func(a, b=2, /, c=3):
                return a * b
        """)

        self.agency.spy_on(func)

        argspec = inspect.getfullargspec(func)

        self.assertEqual(argspec.args, ['a', 'b', 'c'])
        self.assertIsNone(argspec.varargs)
        self.assertIsNone(argspec.varkw)
        self.assertEqual(argspec.defaults, (2, 3))
        self.assertEqual(argspec.kwonlyargs, [])
        self.assertIsNone(argspec.kwonlydefaults)
        self.assertEqual(argspec.annotations, {})

    def test_getfullargspec_with_function_keyword_only(self):
        """Testing FunctionSpy in inspect.getfullargspec() with function and
        keyword-only arguments
        """
        def func(*, a, b=2):
            return a * b

        self.agency.spy_on(func)

        argspec = inspect.getfullargspec(func)

        self.assertEqual(argspec.args, [])
        self.assertIsNone(argspec.varargs)
        self.assertIsNone(argspec.varkw)
        self.assertIsNone(argspec.defaults)
        self.assertEqual(argspec.kwonlyargs, ['a', 'b'])
        self.assertEqual(argspec.kwonlydefaults, {
            'b': 2,
        })
        self.assertEqual(argspec.annotations, {})

    def test_getfullargspec_with_function_annotations(self):
        """Testing FunctionSpy in inspect.getfullargspec() with function and
        annotations
        """
        def func(a: int, b: int = 2) -> int:
            return a * b

        self.agency.spy_on(func)

        argspec = inspect.getfullargspec(func)

        self.assertEqual(argspec.args, ['a', 'b'])
        self.assertIsNone(argspec.varargs)
        self.assertIsNone(argspec.varkw)
        self.assertEqual(argspec.defaults, (2,))
        self.assertEqual(argspec.kwonlyargs, [])
        self.assertIsNone(argspec.kwonlydefaults)
        self.assertEqual(argspec.annotations, {
            'a': int,
            'b': int,
            'return': int,
        })

    def test_getfullargspec_with_bound_method(self):
        """Testing FunctionSpy in inspect.getfullargspec() with bound method"""
        class MyObject:
            def func(self, a, b=2):
                return a * b

        obj = MyObject()
        self.agency.spy_on(obj.func)

        argspec = inspect.getfullargspec(obj.func)

        self.assertEqual(argspec.args, ['self', 'a', 'b'])
        self.assertIsNone(argspec.varargs)
        self.assertIsNone(argspec.varkw)
        self.assertEqual(argspec.defaults, (2,))
        self.assertEqual(argspec.kwonlyargs, [])
        self.assertIsNone(argspec.kwonlydefaults)
        self.assertEqual(argspec.annotations, {})

    @require_func_pos_only_args
    def test_getfullargspec_with_bound_method_pos_only(self):
        """Testing FunctionSpy in inspect.getfullargspec() with bound method
        and positional-only arguments
        """
        MyObject = self.make_func(
            """
            class MyObject:
                def func(self, a, b=2, /, c=3):
                    return a * b
            """,
            func_name='MyObject')

        obj = MyObject()
        self.agency.spy_on(obj.func)

        argspec = inspect.getfullargspec(obj.func)

        self.assertEqual(argspec.args, ['self', 'a', 'b', 'c'])
        self.assertIsNone(argspec.varargs)
        self.assertIsNone(argspec.varkw)
        self.assertEqual(argspec.defaults, (2, 3))
        self.assertEqual(argspec.kwonlyargs, [])
        self.assertIsNone(argspec.kwonlydefaults)
        self.assertEqual(argspec.annotations, {})

    def test_getfullargspec_with_bound_method_keyword_only(self):
        """Testing FunctionSpy in inspect.getfullargspec() with bound method
        and keyword-only arguments
        """
        class MyObject:
            def func(self, *, a, b=2):
                return a * b

        obj = MyObject()
        self.agency.spy_on(obj.func)

        argspec = inspect.getfullargspec(obj.func)

        self.assertEqual(argspec.args, ['self'])
        self.assertIsNone(argspec.varargs)
        self.assertIsNone(argspec.varkw)
        self.assertIsNone(argspec.defaults)
        self.assertEqual(argspec.kwonlyargs, ['a', 'b'])
        self.assertEqual(argspec.kwonlydefaults, {
            'b': 2,
        })
        self.assertEqual(argspec.annotations, {})

    def test_getfullargspec_with_bound_method_annotations(self):
        """Testing FunctionSpy in inspect.getfullargspec() with bound method
        and annotations
        """
        class MyObject:
            def func(self, a: int, b: int = 2) -> int:
                return a * b

        obj = MyObject()
        self.agency.spy_on(obj.func)

        argspec = inspect.getfullargspec(obj.func)

        self.assertEqual(argspec.args, ['self', 'a', 'b'])
        self.assertIsNone(argspec.varargs)
        self.assertIsNone(argspec.varkw)
        self.assertEqual(argspec.defaults, (2,))
        self.assertEqual(argspec.kwonlyargs, [])
        self.assertIsNone(argspec.kwonlydefaults)
        self.assertEqual(argspec.annotations, {
            'a': int,
            'b': int,
            'return': int,
        })

    def test_getfullargspec_with_unbound_method(self):
        """Testing FunctionSpy in inspect.getfullargspec() with unbound method
        """
        class MyObject:
            def func(self, a, b=2):
                return a * b

        self.agency.spy_on(MyObject.func)

        argspec = inspect.getfullargspec(MyObject.func)

        self.assertEqual(argspec.args, ['self', 'a', 'b'])
        self.assertIsNone(argspec.varargs)
        self.assertIsNone(argspec.varkw)
        self.assertEqual(argspec.defaults, (2,))
        self.assertEqual(argspec.kwonlyargs, [])
        self.assertIsNone(argspec.kwonlydefaults)
        self.assertEqual(argspec.annotations, {})

    @require_func_pos_only_args
    def test_getfullargspec_with_unbound_method_pos_only(self):
        """Testing FunctionSpy in inspect.getfullargspec() with unbound method
        and positional-only arguments
        """
        MyObject = self.make_func(
            """
            class MyObject:
                def func(self, a, b=2, /, c=3):
                    return a * b
            """,
            func_name='MyObject')

        self.agency.spy_on(MyObject.func)

        argspec = inspect.getfullargspec(MyObject.func)

        self.assertEqual(argspec.args, ['self', 'a', 'b', 'c'])
        self.assertIsNone(argspec.varargs)
        self.assertIsNone(argspec.varkw)
        self.assertEqual(argspec.defaults, (2, 3))
        self.assertEqual(argspec.kwonlyargs, [])
        self.assertIsNone(argspec.kwonlydefaults)
        self.assertEqual(argspec.annotations, {})

    def test_getfullargspec_with_unbound_method_keyword_only(self):
        """Testing FunctionSpy in inspect.getfullargspec() with unbound method
        and keyword-only arguments
        """
        class MyObject:
            def func(self, *, a, b=2):
                return a * b

        self.agency.spy_on(MyObject.func)

        argspec = inspect.getfullargspec(MyObject.func)

        self.assertEqual(argspec.args, ['self'])
        self.assertIsNone(argspec.varargs)
        self.assertIsNone(argspec.varkw)
        self.assertIsNone(argspec.defaults)
        self.assertEqual(argspec.kwonlyargs, ['a', 'b'])
        self.assertEqual(argspec.kwonlydefaults, {
            'b': 2,
        })
        self.assertEqual(argspec.annotations, {})

    def test_getfullargspec_with_unbound_method_annotations(self):
        """Testing FunctionSpy in inspect.getfullargspec() with unbound method
        and annotations
        """
        class MyObject:
            def func(self, a: int, b: int = 2) -> int:
                return a * b

        self.agency.spy_on(MyObject.func)

        argspec = inspect.getfullargspec(MyObject.func)

        self.assertEqual(argspec.args, ['self', 'a', 'b'])
        self.assertIsNone(argspec.varargs)
        self.assertIsNone(argspec.varkw)
        self.assertEqual(argspec.defaults, (2,))
        self.assertEqual(argspec.kwonlyargs, [])
        self.assertIsNone(argspec.kwonlydefaults)
        self.assertEqual(argspec.annotations, {
            'a': int,
            'b': int,
            'return': int,
        })

    def test_getfullargspec_with_classmethod(self):
        """Testing FunctionSpy in inspect.getfullargspec() with classmethod
        """
        class MyObject:
            @classmethod
            def func(cls, a, b=2):
                return a * b

        self.agency.spy_on(MyObject.func)

        argspec = inspect.getfullargspec(MyObject.func)

        self.assertEqual(argspec.args, ['cls', 'a', 'b'])
        self.assertIsNone(argspec.varargs)
        self.assertIsNone(argspec.varkw)
        self.assertEqual(argspec.defaults, (2,))
        self.assertEqual(argspec.kwonlyargs, [])
        self.assertIsNone(argspec.kwonlydefaults)
        self.assertEqual(argspec.annotations, {})

    @require_func_pos_only_args
    def test_getfullargspec_with_classmethod_pos_only(self):
        """Testing FunctionSpy in inspect.getfullargspec() with classmethod
        and positional-only arguments
        """
        MyObject = self.make_func(
            """
            class MyObject:
                @classmethod
                def func(cls, a, b=2, /, c=3):
                    return a * b
            """,
            func_name='MyObject')

        self.agency.spy_on(MyObject.func)

        argspec = inspect.getfullargspec(MyObject.func)

        self.assertEqual(argspec.args, ['cls', 'a', 'b', 'c'])
        self.assertIsNone(argspec.varargs)
        self.assertIsNone(argspec.varkw)
        self.assertEqual(argspec.defaults, (2, 3))
        self.assertEqual(argspec.kwonlyargs, [])
        self.assertIsNone(argspec.kwonlydefaults)
        self.assertEqual(argspec.annotations, {})

    def test_getfullargspec_with_classmethod_keyword_only(self):
        """Testing FunctionSpy in inspect.getfullargspec() with classmethod
        and keyword-only arguments
        """
        class MyObject:
            @classmethod
            def func(cls, *, a, b=2):
                return a * b

        self.agency.spy_on(MyObject.func)

        argspec = inspect.getfullargspec(MyObject.func)

        self.assertEqual(argspec.args, ['cls'])
        self.assertIsNone(argspec.varargs)
        self.assertIsNone(argspec.varkw)
        self.assertIsNone(argspec.defaults)
        self.assertEqual(argspec.kwonlyargs, ['a', 'b'])
        self.assertEqual(argspec.kwonlydefaults, {
            'b': 2,
        })
        self.assertEqual(argspec.annotations, {})

    def test_getfullargspec_with_classmethod_annotations(self):
        """Testing FunctionSpy in inspect.getfullargspec() with classmethod
        and annotations
        """
        class MyObject:
            @classmethod
            def func(cls, a: int, b: int = 2) -> int:
                return a * b

        self.agency.spy_on(MyObject.func)

        argspec = inspect.getfullargspec(MyObject.func)

        self.assertEqual(argspec.args, ['cls', 'a', 'b'])
        self.assertIsNone(argspec.varargs)
        self.assertIsNone(argspec.varkw)
        self.assertEqual(argspec.defaults, (2,))
        self.assertEqual(argspec.kwonlyargs, [])
        self.assertIsNone(argspec.kwonlydefaults)
        self.assertEqual(argspec.annotations, {
            'a': int,
            'b': int,
            'return': int,
        })
