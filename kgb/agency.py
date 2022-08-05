"""A spy agency to manage spies."""

from __future__ import unicode_literals

from pprint import pformat
from unittest.util import safe_repr

from kgb.signature import _UNSET_ARG
from kgb.spies import FunctionSpy, SpyCall
from kgb.utils import format_spy_kwargs


class SpyAgency(object):
    """Manages spies.

    A SpyAgency can be instantiated or mixed into a
    :py:class:`unittest.TestCase` in order to provide spies.

    Every spy created through this agency will be tracked, and can be later
    be removed (individually or at once).

    Version Changed:
        7.0:
        Added ``assert_`` versions of all the assertion methods (e.g.,
        ``assert_spy_called_with`` as an alias of ``assertSpyCalledWith``.

    Attributes:
        spies (set of kgb.spies.FunctionSpy):
            All spies currently registered with this agency.
    """

    def __init__(self, *args, **kwargs):
        """Initialize the spy agency.

        Args:
            *args (tuple):
                Positional arguments to pass on to any other class (if using
                this as a mixin).

            **kwargs (dict):
                Keyword arguments to pass on to any other class (if using
                this as a mixin).
        """
        super(SpyAgency, self).__init__(*args, **kwargs)

        self.spies = set()

    def tearDown(self):
        """Tear down a test suite.

        This is used when SpyAgency is mixed into a TestCase. It will
        automatically remove all spies when tearing down.
        """
        super(SpyAgency, self).tearDown()
        self.unspy_all()

    def spy_on(self, *args, **kwargs):
        """Spy on a function.

        By default, the spy will allow the call to go through to the original
        function. This can be disabled by passing ``call_original=False`` when
        initiating the spy. If disabled, the original function will never be
        called.

        This can also be passed a ``call_fake`` parameter pointing to another
        function to call instead of the original. If passed, this will take
        precedence over ``call_original``.

        See :py:class:`~kgb.spies.FunctionSpy` for more details on arguments.

        Args:
            *args (tuple):
                Positional arguments to pass to
                :py:class:`~kgb.spies.FunctionSpy`.

            **kwargs (dict):
                Keyword arguments to pass to
                :py:class:`~kgb.spies.FunctionSpy`.

        Returns:
            kgb.spies.FunctionSpy:
            The resulting spy.
        """
        spy = FunctionSpy(self, *args, **kwargs)
        self.spies.add(spy)
        return spy

    def spy_for(self, func, owner=_UNSET_ARG):
        """Decorate a function that should be a spy for another function.

        This is a convenience over declaring a function and using
        :py:meth:`spy_on` with ``call_fake=``. It's used to quickly and
        easily create a fake function spy for another function.

        Version Added:
            6.0

        Args:
            func (callable):
                The function or method to spy on.

            owner (type or object, optional):
                The owner of the function or method.

                If spying on an unbound method, this **must** be set to the
                class that owns it.

                If spying on a bound method that identifies as a plain
                function (which may happen if the method is decorated and
                dynamically returns a new function on access), this should
                be the instance of the object you're spying on.

        Example:
            @self.spy_for(get_doomsday):
            def _fake_get_doomsday():
                return datetime(year=2038, month=12, day=5,
                                hour=1, minute=2, second=3)
        """
        def _wrap(call_fake):
            self.spy_on(func,
                        owner=owner,
                        call_fake=call_fake)

            return call_fake

        return _wrap

    def unspy(self, func):
        """Stop spying on a function.

        Args:
            func (callable):
                The function to stop spying on.

        Raises:
            ValueError:
                The provided function was not spied on.
        """
        try:
            spy = func.spy
        except AttributeError:
            raise ValueError('Function %r has not been spied on.' % func)

        assert spy in self.spies

        spy.unspy()

    def unspy_all(self):
        """Stop spying on all functions tracked by this agency."""
        for spy in self.spies:
            spy.unspy(unregister=False)

        self.spies.clear()

    def assertHasSpy(self, spy):
        """Assert that a function has a spy.

        This also accepts a spy as an argument, which will always return
        ``True``.

        Args:
            spy (callable or kgb.spies.FunctionSpy):
                The function or spy to check.

        Raises:
            AssertionError:
                The function did not have a spy.
        """
        if not hasattr(spy, 'spy') and not isinstance(spy, FunctionSpy):
            self._kgb_assert_fail('%s has not been spied on.'
                                  % self._format_spy_or_call(spy))

    def assertSpyCalled(self, spy):
        """Assert that a function has been called at least once.

        This will imply :py:meth:`assertHasSpy`.

        Args:
            spy (callable or kgb.spies.FunctionSpy):
                The function or spy to check.

        Raises:
            AssertionError:
                The function was not called.
        """
        self.assertHasSpy(spy)

        if not spy.called:
            self._kgb_assert_fail('%s was not called.'
                                  % self._format_spy_or_call(spy))

    def assertSpyNotCalled(self, spy):
        """Assert that a function has not been called.

        This will imply :py:meth:`assertHasSpy`.

        Args:
            spy (callable or kgb.spies.FunctionSpy):
                The function or spy to check.

        Raises:
            AssertionError:
                The function was called.
        """
        self.assertHasSpy(spy)

        if spy.called:
            call_count = len(spy.calls)

            if call_count == 1:
                msg = (
                    '%s was called 1 time:'
                    % self._format_spy_or_call(spy)
                )
            else:
                msg = (
                    '%s was called %d times:'
                    % (self._format_spy_or_call(spy), call_count)
                )

            self._kgb_assert_fail(
                '%s\n'
                '\n'
                '%s'
                % (
                    msg,
                    self._format_spy_calls(spy, self._format_spy_call_args),
                ))

    def assertSpyCallCount(self, spy, count):
        """Assert that a function was called the given number of times.

        This will imply :py:meth:`assertHasSpy`.

        Args:
            spy (callable or kgb.spies.FunctionSpy):
                The function or spy to check.

            count (int):
                The number of times the function is expected to have been
                called.

        Raises:
            AssertionError:
                The function was not called the specified number of times.
        """
        self.assertHasSpy(spy)

        call_count = len(spy.calls)

        if call_count != count:
            if call_count == 1:
                msg = '%s was called %d time, not %d.'
            else:
                msg = '%s was called %d times, not %d.'

            self._kgb_assert_fail(msg %
                                  (self._format_spy_or_call(spy),
                                   call_count,
                                   count))

    def assertSpyCalledWith(self, spy_or_call, *expected_args,
                            **expected_kwargs):
        """Assert that a function was called with the given arguments.

        If a spy is provided, all calls will be checked for a match.

        This will imply :py:meth:`assertHasSpy`.

        Args:
            spy_or_call (callable or kgb.spies.FunctionSpy):
                The function, spy, or call to check.

            *expected_args (tuple):
                Position arguments expected to be provided in any of the calls.

            **expected_kwargs (dict):
                Keyword arguments expected to be provided in any of the calls.

        Raises:
            AssertionError:
                The function was not called with the provided arguments.
        """
        if isinstance(spy_or_call, FunctionSpy):
            self.assertSpyCalled(spy_or_call)

        if not spy_or_call.called_with(*expected_args, **expected_kwargs):
            if isinstance(spy_or_call, SpyCall):
                self._kgb_assert_fail(
                    'This call to %s was not passed args=%s, kwargs=%s.\n'
                    '\n'
                    'It was called with:\n'
                    '\n'
                    '%s'
                    % (
                        self._format_spy_or_call(spy_or_call),
                        safe_repr(expected_args),
                        format_spy_kwargs(expected_kwargs),
                        self._format_spy_call_args(spy_or_call),
                    ))
            else:
                self._kgb_assert_fail(
                    'No call to %s was passed args=%s, kwargs=%s.\n'
                    '\n'
                    'The following calls were recorded:\n'
                    '\n'
                    '%s'
                    % (
                        self._format_spy_or_call(spy_or_call),
                        safe_repr(expected_args),
                        format_spy_kwargs(expected_kwargs),
                        self._format_spy_calls(
                            spy_or_call,
                            self._format_spy_call_args),
                    ))

    def assertSpyNotCalledWith(self, spy_or_call, *expected_args,
                               **expected_kwargs):
        """Assert that a function was not called with the given arguments.

        If a spy is provided, all calls will be checked for a match.

        This will imply :py:meth:`assertHasSpy`.

        Args:
            spy_or_call (callable or kgb.spies.FunctionSpy):
                The function, spy, or call to check.

            *expected_args (tuple):
                Position arguments not expected to be provided in any of the
                calls.

            **expected_kwargs (dict):
                Keyword arguments not expected to be provided in any of the
                calls.

        Raises:
            AssertionError:
                The function was called with the provided arguments.
        """
        if isinstance(spy_or_call, FunctionSpy):
            self.assertSpyCalled(spy_or_call)

        if spy_or_call.called_with(*expected_args, **expected_kwargs):
            if isinstance(spy_or_call, SpyCall):
                self._kgb_assert_fail(
                    'This call to %s was unexpectedly passed args=%s, '
                    'kwargs=%s.'
                    % (
                        self._format_spy_or_call(spy_or_call),
                        safe_repr(expected_args),
                        format_spy_kwargs(expected_kwargs),
                    ))
            else:
                self._kgb_assert_fail(
                    'A call to %s was unexpectedly passed args=%s, '
                    'kwargs=%s.\n'
                    '\n'
                    'The following calls were recorded:\n'
                    '\n'
                    '%s'
                    % (
                        self._format_spy_or_call(spy_or_call),
                        safe_repr(expected_args),
                        format_spy_kwargs(expected_kwargs),
                        self._format_spy_calls(
                            spy_or_call,
                            self._format_spy_call_args),
                    ))

    def assertSpyLastCalledWith(self, spy, *expected_args, **expected_kwargs):
        """Assert that a function was last called with the given arguments.

        This will imply :py:meth:`assertHasSpy`.

        Args:
            spy (callable or kgb.spies.FunctionSpy):
                The function or spy to check.

            *expected_args (tuple):
                Position arguments expected to be provided in the last call.

            **expected_kwargs (dict):
                Keyword arguments expected to be provided in the last call.

        Raises:
            AssertionError:
                The function was not called last with the provided arguments.
        """
        self.assertSpyCalled(spy)

        if not spy.last_called_with(*expected_args, **expected_kwargs):
            self._kgb_assert_fail(
                'The last call to %s was not passed args=%s, kwargs=%s.\n'
                '\n'
                'It was last called with:\n'
                '\n'
                '%s'
                % (
                    self._format_spy_or_call(spy),
                    safe_repr(expected_args),
                    format_spy_kwargs(expected_kwargs),
                    self._format_spy_call_args(spy.last_call),
                ))

    def assertSpyReturned(self, spy_or_call, return_value):
        """Assert that a function call returned the given value.

        If a spy is provided, all calls will be checked for a match.

        This will imply :py:meth:`assertHasSpy`.

        Args:
            spy_or_call (callable or kgb.spies.FunctionSpy or
                         kgb.spies.SpyCall):
                The function, spy, or call to check.

            return_value (object or type):
                The value expected to be returned by any of the calls.

        Raises:
            AssertionError:
                The function never returned the provided value.
        """
        if isinstance(spy_or_call, FunctionSpy):
            self.assertSpyCalled(spy_or_call)

        if not spy_or_call.returned(return_value):
            if isinstance(spy_or_call, SpyCall):
                self._kgb_assert_fail(
                    'This call to %s did not return %s.\n'
                    '\n'
                    'It returned:\n'
                    '\n'
                    '%s'
                    % (
                        self._format_spy_or_call(spy_or_call),
                        safe_repr(return_value),
                        self._format_spy_call_returned(spy_or_call),
                    ))
            else:
                self._kgb_assert_fail(
                    'No call to %s returned %s.\n'
                    '\n'
                    'The following values have been returned:\n'
                    '\n'
                    '%s'
                    % (
                        self._format_spy_or_call(spy_or_call),
                        safe_repr(return_value),
                        self._format_spy_calls(
                            spy_or_call,
                            self._format_spy_call_returned),
                    ))

    def assertSpyLastReturned(self, spy, return_value):
        """Assert that the last function call returned the given value.

        This will imply :py:meth:`assertHasSpy`.

        Args:
            spy (callable or kgb.spies.FunctionSpy):
                The function or spy to check.

            return_value (object or type):
                The value expected to be returned by the last call.

        Raises:
            AssertionError:
                The function's last call did not return the provided value.
        """
        self.assertSpyCalled(spy)

        if not spy.last_returned(return_value):
            self._kgb_assert_fail(
                'The last call to %s did not return %s.\n'
                '\n'
                'It last returned:\n'
                '\n'
                '%s'
                % (
                    self._format_spy_or_call(spy),
                    safe_repr(return_value),
                    self._format_spy_call_returned(spy.last_call),
                ))

    def assertSpyRaised(self, spy_or_call, exception_cls):
        """Assert that a function call raised the given exception type.

        If a spy is provided, all calls will be checked for a match.

        This will imply :py:meth:`assertHasSpy`.

        Args:
            spy_or_call (callable or kgb.spies.FunctionSpy or
                         kgb.spies.SpyCall):
                The function, spy, or call to check.

            exception_cls (type):
                The exception type expected to be raised by one of the calls.

        Raises:
            AssertionError:
                The function never raised the provided exception type.
        """
        if isinstance(spy_or_call, FunctionSpy):
            self.assertSpyCalled(spy_or_call)

        if not spy_or_call.raised(exception_cls):
            if isinstance(spy_or_call, SpyCall):
                if spy_or_call.exception is not None:
                    self._kgb_assert_fail(
                        'This call to %s did not raise %s. It raised %s.'
                        % (
                            self._format_spy_or_call(spy_or_call),
                            exception_cls.__name__,
                            self._format_spy_call_raised(spy_or_call),
                        ))
                else:
                    self._kgb_assert_fail(
                        'This call to %s did not raise an exception.'
                        % self._format_spy_or_call(spy_or_call))
            else:
                has_raised = any(
                    call.exception is not None
                    for call in spy_or_call.calls
                )

                if has_raised:
                    self._kgb_assert_fail(
                        'No call to %s raised %s.\n'
                        '\n'
                        'The following exceptions have been raised:\n\n'
                        '%s'
                        % (
                            self._format_spy_or_call(spy_or_call),
                            exception_cls.__name__,
                            self._format_spy_calls(
                                spy_or_call,
                                self._format_spy_call_raised),
                        ))
                else:
                    self._kgb_assert_fail(
                        'No call to %s raised an exception.'
                        % self._format_spy_or_call(spy_or_call))

    def assertSpyLastRaised(self, spy, exception_cls):
        """Assert that the last function call raised the given exception type.

        This will imply :py:meth:`assertHasSpy`.

        Args:
            spy (callable or kgb.spies.FunctionSpy):
                The function or spy to check.

            exception_cls (type):
                The exception type expected to be raised by the last call.

        Raises:
            AssertionError:
                The last function call did not raise the provided exception
                type.
        """
        self.assertSpyCalled(spy)

        if not spy.last_raised(exception_cls):
            if spy.last_call.exception is not None:
                self._kgb_assert_fail(
                    'The last call to %s did not raise %s. It last '
                    'raised %s.'
                    % (
                        self._format_spy_or_call(spy),
                        exception_cls.__name__,
                        self._format_spy_call_raised(spy.last_call),
                    ))
            else:
                self._kgb_assert_fail(
                    'The last call to %s did not raise an exception.'
                    % self._format_spy_or_call(spy))

    def assertSpyRaisedMessage(self, spy_or_call, exception_cls, message):
        """Assert that a function call raised the given exception/message.

        If a spy is provided, all calls will be checked for a match.

        This will imply :py:meth:`assertHasSpy`.

        Args:
            spy_or_call (callable or kgb.spies.FunctionSpy or
                         kgb.spies.SpyCall):
                The function, spy, or call to check.

            exception_cls (type):
                The exception type expected to be raised by one of the calls.

            message (bytes or unicode):
                The expected message in a matching extension.

        Raises:
            AssertionError:
                The function never raised the provided exception type with
                the expected message.
        """
        if isinstance(spy_or_call, FunctionSpy):
            self.assertSpyCalled(spy_or_call)

        if not spy_or_call.raised_with_message(exception_cls, message):
            if isinstance(spy_or_call, SpyCall):
                if spy_or_call.exception is not None:
                    self._kgb_assert_fail(
                        'This call to %s did not raise %s with message %r.\n'
                        '\n'
                        'It raised:\n'
                        '\n'
                        '%s'
                        % (
                            self._format_spy_or_call(spy_or_call),
                            exception_cls.__name__,
                            message,
                            self._format_spy_call_raised_with_message(
                                spy_or_call),
                        ))
                else:
                    self._kgb_assert_fail(
                        'This call to %s did not raise an exception.'
                        % self._format_spy_or_call(spy_or_call))
            else:
                has_raised = any(
                    call.exception is not None
                    for call in spy_or_call.calls
                )

                if has_raised:
                    self._kgb_assert_fail(
                        'No call to %s raised %s with message %r.\n'
                        '\n'
                        'The following exceptions have been raised:\n'
                        '\n'
                        '%s'
                        % (
                            self._format_spy_or_call(spy_or_call),
                            exception_cls.__name__,
                            message,
                            self._format_spy_calls(
                                spy_or_call,
                                self._format_spy_call_raised_with_message),
                        ))
                else:
                    self._kgb_assert_fail(
                        'No call to %s raised an exception.'
                        % self._format_spy_or_call(spy_or_call))

    def assertSpyLastRaisedMessage(self, spy, exception_cls, message):
        """Assert that the function last raised the given exception/message.

        This will imply :py:meth:`assertHasSpy`.

        Args:
            spy (callable or kgb.spies.FunctionSpy):
                The function or spy to check.

            exception_cls (type):
                The exception type expected to be raised by the last call.

            message (bytes or unicode):
                The expected message in the matching extension.

        Raises:
            AssertionError:
                The last function call did not raise the provided exception
                type with the expected message.
        """
        self.assertSpyCalled(spy)

        if not spy.last_raised_with_message(exception_cls, message):
            if spy.last_call.exception is not None:
                self._kgb_assert_fail(
                    'The last call to %s did not raise %s with message %r.\n'
                    '\n'
                    'It last raised:\n'
                    '\n'
                    '%s'
                    % (
                        self._format_spy_or_call(spy),
                        exception_cls.__name__,
                        message,
                        self._format_spy_call_raised_with_message(
                            spy.last_call),
                    ))
            else:
                self._kgb_assert_fail(
                    'The last call to %s did not raise an exception.'
                    % self._format_spy_or_call(spy))

    def _kgb_assert_fail(self, msg):
        """Raise an assertion failure.

        If this class is mixed into a unit test suite, this will call the
        main :py:meth:`unittest.TestCase.fail` method. Otherwise, it will
        simply raise an :py:exc:`AssertionError`.

        Args:
            msg (unicode):
                The assertion message.

        Raises:
            AssertionError:
                The assertion error to raise.
        """
        if hasattr(self, 'fail') and hasattr(self, 'failureException'):
            # This is likely mixed in to a unit test.
            self.fail(msg)
        else:
            raise AssertionError(msg)

    def _format_spy_or_call(self, spy_or_call):
        """Format a spy or call for output in an assertion message.

        Args:
            spy_or_call (callable or kgb.spies.FunctionSpy or
                         kgb.spies.SpyCall):
                The spy or call to format.

        Returns:
            unicode:
            The formatted name of the function.
        """
        if isinstance(spy_or_call, FunctionSpy):
            spy = spy_or_call.orig_func
        elif isinstance(spy_or_call, SpyCall):
            spy = spy_or_call.spy.orig_func
        else:
            spy = spy_or_call

        name = spy.__name__

        if isinstance(name, bytes):
            name = name.decode('utf-8')

        return name

    def _format_spy_calls(self, spy, formatter):
        """Format a list of calls for a spy.

        Args:
            spy (callable or kgb.spies.FunctionSpy):
                The spy to format.

            formatter (callable):
                A formatting function used for each recorded call.

        Returns:
            unicode:
            The formatted output of the calls.
        """
        return '\n\n'.join(
            'Call %d:\n%s' % (i, formatter(call, indent=2))
            for i, call in enumerate(spy.calls)
        )

    def _format_spy_call_args(self, call, indent=0):
        """Format a call's arguments.

        Args:
            call (kgb.spies.SpyCall):
                The call containing arguments to format.

            indent (int, optional):
                The indentation level for any output.

        Returns:
            unicode:
            The formatted output of the arguments for the call.
        """
        return '%s\n%s' % (
            self._format_spy_lines(call.args,
                                   prefix='args=',
                                   indent=indent),
            self._format_spy_lines(call.kwargs,
                                   prefix='kwargs=',
                                   indent=indent),
        )

    def _format_spy_call_returned(self, call, indent=0):
        """Format the return value from a call.

        Args:
            call (kgb.spies.SpyCall):
                The call containing a return value to format.

            indent (int, optional):
                The indentation level for any output.

        Returns:
            unicode:
            The formatted return value from the call.
        """
        return self._format_spy_lines(call.return_value,
                                      indent=indent)

    def _format_spy_call_raised(self, call, indent=0):
        """Format the exception type raised by a call.

        Args:
            call (kgb.spies.SpyCall):
                The call that raised an exception to format.

            indent (int, optional):
                The indentation level for any output.

        Returns:
            unicode:
            The formatted name of the exception raised by a call.
        """
        return self._format_spy_lines(call.exception.__class__.__name__,
                                      indent=indent,
                                      format_data=False)

    def _format_spy_call_raised_with_message(self, call, indent=0):
        """Format the exception type and message raised by a call.

        Args:
            call (kgb.spies.SpyCall):
                The call that raised an exception to format.

            indent (int, optional):
                The indentation level for any output.

        Returns:
            unicode:
            The formatted name of the exception and accompanying message raised
            by a call.
        """
        return '%s\n%s' % (
            self._format_spy_lines(call.exception.__class__.__name__,
                                   prefix='exception=',
                                   indent=indent,
                                   format_data=False),
            self._format_spy_lines(str(call.exception),
                                   prefix='message=',
                                   indent=indent),
        )

    def _format_spy_lines(self, data, prefix='', indent=0, format_data=True):
        """Format a multi-line list of output for an assertion message.

        Unless otherwise specified, the provided data will be formatted
        using :py:func:`pprint.pformat`.

        The first line of data will be prefixed, if a prefix is provided.
        Subsequent lines be aligned with the contents after the prefix.

        All line will be indented by the given amount.

        Args:
            data (object):
                The data to format.

            prefix (unicode, optional):
                An optional prefix for the first line in the data.

            indent (int, optional):
                The indentation level for any output.

            format_data (bool, optional):
                Whether to format the provided ``data`` using
                :py:func:`pprint.pformat`.

        Returns:
            unicode:
            The formatted string for the data.
        """
        indent_str = ' ' * indent

        if format_data:
            data = pformat(data)

        data_lines = data.splitlines()
        lines = ['%s%s%s' % (indent_str, prefix, data_lines[0])]

        if len(data_lines) > 1:
            indent_str = ' ' * (indent + len(prefix))

            lines += [
                '%s%s' % (indent_str, line)
                for line in data_lines[1:]
            ]

        return '\n'.join(lines)

    # snake_case versions of the test functions.
    #
    # Useful for pytest and other uses.
    assert_has_spy = assertHasSpy
    assert_spy_called = assertSpyCalled
    assert_spy_not_called = assertSpyNotCalled
    assert_spy_call_count = assertSpyCallCount
    assert_spy_called_with = assertSpyCalledWith
    assert_spy_not_called_with = assertSpyNotCalledWith
    assert_spy_last_called_with = assertSpyLastCalledWith
    assert_spy_returned = assertSpyReturned
    assert_spy_last_returned = assertSpyLastReturned
    assert_spy_raised = assertSpyRaised
    assert_spy_last_raised = assertSpyLastRaised
    assert_spy_raised_message = assertSpyRaisedMessage
    assert_spy_last_raised_message = assertSpyLastRaisedMessage
