from kgb.tests.base import TestCase


class FunctionSpyTests(TestCase):
    """Python 3 unit tests for kgb.spies.FunctionSpy."""

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
