"""A spy agency to manage spies."""

from __future__ import unicode_literals

from pprint import pformat

from kgb.spies import FunctionSpy, SpyCall
from unittest.util import safe_repr


class SpyAgency(object):
    """Manages spies.

    A SpyAgency can be instantiated or mixed into a
    :py:class:`unittest.TestCase` in order to provide spies.

    Every spy created through this agency will be tracked, and can be later
    be removed (individually or at once).

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

        self.spies = []

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
            self.fail('%s has not been spied on.'
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
            self.fail('%s was not called.' % self._format_spy_or_call(spy))

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

            self.fail(
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

            self.fail(msg % (self._format_spy_or_call(spy), call_count,
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
                self.fail(
                    'This call to %s was not passed args=%s, kwargs=%s.\n'
                    '\n'
                    'It was called with:\n'
                    '\n'
                    '%s'
                    % (
                        self._format_spy_or_call(spy_or_call),
                        safe_repr(expected_args),
                        safe_repr(expected_kwargs),
                        self._format_spy_call_args(spy_or_call),
                    ))
            else:
                self.fail(
                    'No call to %s was passed args=%s, kwargs=%s.\n'
                    '\n'
                    'The following calls were recorded:\n'
                    '\n'
                    '%s'
                    % (
                        self._format_spy_or_call(spy_or_call),
                        safe_repr(expected_args),
                        safe_repr(expected_kwargs),
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
            self.fail(
                'The last call to %s was not passed args=%s, kwargs=%s.\n'
                '\n'
                'It was last called with:\n'
                '\n'
                '%s'
                % (
                    self._format_spy_or_call(spy),
                    safe_repr(expected_args),
                    safe_repr(expected_kwargs),
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
                self.fail(
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
                self.fail(
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
            self.fail(
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
                    self.fail(
                        'This call to %s did not raise %s. It raised %s.'
                        % (
                            self._format_spy_or_call(spy_or_call),
                            exception_cls.__name__,
                            self._format_spy_call_raised(spy_or_call),
                        ))
                else:
                    self.fail('This call to %s did not raise an exception.'
                              % self._format_spy_or_call(spy_or_call))
            else:
                has_raised = any(
                    call.exception is not None
                    for call in spy_or_call.calls
                )

                if has_raised:
                    self.fail(
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
                    self.fail('No call to %s raised an exception.'
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
                self.fail(
                    'The last call to %s did not raise %s. It last '
                    'raised %s.'
                    % (
                        self._format_spy_or_call(spy),
                        exception_cls.__name__,
                        self._format_spy_call_raised(spy.last_call),
                    ))
            else:
                self.fail('The last call to %s did not raise an exception.'
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
                    self.fail(
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
                    self.fail('This call to %s did not raise an exception.'
                              % self._format_spy_or_call(spy_or_call))
            else:
                has_raised = any(
                    call.exception is not None
                    for call in spy_or_call.calls
                )

                if has_raised:
                    self.fail(
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
                    self.fail('No call to %s raised an exception.'
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
                self.fail(
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
                self.fail('The last call to %s did not raise an exception.'
                          % self._format_spy_or_call(spy))

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
