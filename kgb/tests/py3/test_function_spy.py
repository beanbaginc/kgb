from kgb.tests.base import TestCase


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

    def test_call_with_function_and_keyword_only_args(self):
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
