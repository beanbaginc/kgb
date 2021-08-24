"""Planned operations for spies to perform."""

from __future__ import unicode_literals

from kgb.errors import UnexpectedCallError


class BaseSpyOperation(object):
    """Base class for a spy operation.

    Spy operations can be performed when a spied-on function is called,
    handling it according to a plan provided by the caller. They're registered
    by passing ``op=`` when spying on the function.

    There are a handful of built-in operations in KGB, but projects can
    subclass this and define their own.
    """

    def handle_call(self, spy_call, *args, **kwargs):
        """Handle a call to this operation.

        Args:
            spy_call (kgb.calls.SpyCall):
                The call to handle.

            *args (tuple):
                Positional arguments passed into the call. This will be
                normalized to not contain an object instance for bound
                method or class methods.

            **kwargs (tuple):
                Keyword arguments passed into the call.

        Returns:
            object:
            The value to return to the caller of the spied function.

        Raises:
            Exception:
                Any exception to raise to the caller of the spied function.
        """
        raise NotImplementedError

    def setup(self, spy, force_unbound=False):
        """Set up the operation.

        This associates the spy with the operation, and then returns a fake
        function to set for the spy, which will in turn call the operation's
        handler.

        Args:
            spy (kgb.spies.FunctionSpy):
                The spy this operation is for.

            force_unbound (bool, optional):
                Whether to force building an unbound fake function. This is
                needed for any functions called by an operation itself (and
                is thus used for nested operations).

                Version Added:
                    6.1

        Returns:
            callable:
            The fake function to set up with the spy.
        """
        self.spy = spy

        if spy.func_type == spy.TYPE_BOUND_METHOD and not force_unbound:
            def fake_func(_self, *args, **kwargs):
                return self._on_spy_call(*args, **kwargs)
        else:
            def fake_func(*args, **kwargs):
                return self._on_spy_call(*args, **kwargs)

        return fake_func

    def _on_spy_call(self, *args, **kwargs):
        """Internal handler for a call to this operation.

        This normalizes and sanity-checks the arguments and then calls
        :py:meth:`handle_call`.

        Args:
            *args (tuple):
                All positional arguments made in the call. This may include the
                object instance for bound methods or the class for
                classmethods.

            **kwargs (dict):
                All keyword arguments made in the call.

        Returns:
            object:
            The value to return to the caller of the spied function.

        Raises:
            Exception:
                Any exception to raise to the caller of the spied function.
        """
        spy = self.spy
        spy_call = spy.last_call

        if spy.func_type == spy.TYPE_UNBOUND_METHOD:
            assert spy_call.called_with(*args[1:], **kwargs)
        else:
            assert spy_call.called_with(*args, **kwargs)

        return self.handle_call(spy_call, *args, **kwargs)


class BaseMatchingSpyOperation(BaseSpyOperation):
    """Base class for a operation that handles calls based on matched rules.

    This helps subclasses to call consumer-defined handlers for calls based on
    some kind of conditions. For instance, based on arguments, or the order in
    which calls are made.
    """

    def __init__(self, calls):
        """Initialize the operation.

        By default, this takes a list of configurations for matching calls,
        which the subclass will use to validate and handle a call.

        The calls are a list of dictionaries with the following keys:

        ``args`` (:py:class:`tuple`, optional):
            Positional arguments for a match.

        ``kwargs`` (:py:class:`dict`, optional):
            Keyword arguments for a match.

        ``call_fake`` (:py:class:`callable`, optional):
            A function to call when all arguments have matched. This takes
            precedence over ``call_original``.

        ``call_original`` (:py:class:`bool`, optional):
            Whether to call the original function. This is the default if
            ``call_fake`` is not provided.

        ``op`` (:py:class:`BaseSpyOperation`, optional):
            A spy operation to call instead of ``call_fake`` or
            ``call_original``.

        Subclasses may define custom keys.

        Version Changed:
            6.1:
            Added support for ``op``.

        Args:
            calls (list of dict):
                A list of call match configurations.
        """
        super(BaseMatchingSpyOperation, self).__init__()

        self._calls = calls

    def setup(self, spy, **kwargs):
        """Set up the operation.

        This invokes the common behavior for setting up a spy operation, and
        then goes through all registered calls to see if any call-provided
        operations also need to be set up.

        Version Added:
            6.1

        Args:
            spy (kgb.spies.FunctionSpy):
                The spy this operation is for.

            **kwargs (dict):
                Additional keyword arguments to pass to the parent.

        Returns:
            callable:
            The fake function to set up with the spy.
        """
        result = super(BaseMatchingSpyOperation, self).setup(spy, **kwargs)

        new_calls = []

        # Convert any operations into fake functions.
        #
        # Note that we have to force the resulting fake function to be
        # unbound, since all fake functions provided to an operation are
        # called without an owner.
        for call in self._calls:
            if 'op' in call:
                call = call.copy()
                call['call_fake'] = call.pop('op').setup(spy,
                                                         force_unbound=True)

            new_calls.append(call)

        self._calls = new_calls

        return result

    def get_call_match_config(self, spy_call):
        """Return a call match configuration for a call.

        This will typically be one of the call match configurations provided
        during initialization.

        Subclasses must override this to return a dictionary containing
        information that can be used to assert, track, and handle a call.
        If they can't find a suitable call, they must raise
        :py:class:`kgb.errors.UnexpectedCallError`.

        Args:
            spy_call (kgb.calls.SpyCall):
                The call to return a match for.

        Returns:
            dict:
            The call match configuration.

        Raises:
            kgb.errors.UnexpectedCallError:
                A call match configuration could not be found. Details should
                be in the error message.
        """
        raise NotImplementedError

    def validate_call(self, call_match_config):
        """Validate that the last call matches the call configuration.

        This will assert that the last call matches the ``args`` and ``kwargs``
        from the given call match configuration.

        Subclasses can override this to check other conditions.

        Args:
            call_match_config (dict):
                The call match configuration returned from
                :py:meth:`get_call_match_config` for the last call.

        Raises:
            AssertionError:
                The call did not match the configuration.
        """
        self.spy.agency.assertSpyCalledWith(
            self.spy.last_call,
            *call_match_config.get('args', ()),
            **call_match_config.get('kwargs', {}))

    def handle_call(self, spy_call, *args, **kwargs):
        """Handle a call to this operation.

        This will find a suitable call match configuration, if one was
        provided, and then call one of the following, in order of preference:

        1. The spy operation (if ``op`` is set)
        2. The fake function (if ``call_fake`` was provided)
        3. The original function (if ``call_original`` is not set to
           ``False``)

        If none of the above are invoked, ``None`` will be returned instead.

        Version Changed:
            6.1:
            Added support for ``op``.

        Args:
            spy_call (kgb.calls.SpyCall):
                The call to handle.

            *args (tuple):
                Positional arguments passed into the call. This will be
                normalized to not contain an object instance for bound
                method or class methods.

            **kwargs (tuple):
                Keyword arguments passed into the call.

        Returns:
            object:
            The value to return to the caller of the spied function.
            This may be returned by a fake or original function.

        Raises:
            AssertionError:
                The call did not match the returned configuration.

            Exception:
                Any exception to raise to the caller of the spied function.
                This may be raised by a fake or original function.

            kgb.errors.UnexpectedCallError:
                A call match configuration could not be found. Details should
                be in the error message.
        """
        call_match_config = self.get_call_match_config(spy_call)
        assert call_match_config is not None

        self.validate_call(call_match_config)

        # We'll be respecting these arguments in the order that FunctionSpy
        # would with its parameters.
        func = call_match_config.get('call_fake')

        if func is not None:
            return func(*args, **kwargs)

        if call_match_config.get('call_original', True):
            return self.spy.call_original(*args, **kwargs)

        return None


class SpyOpMatchAny(BaseMatchingSpyOperation):
    """A operation for handling one or more expected calls in any order.

    This is used to list the calls (specifying positional and keyword
    arguments) that are expected to be made, raising an error if any calls are
    made that weren't expected.

    Each of those expected sets of arguments can optionally result in a call to
    a fake function or the original function. This can be specified per set of
    arguments.

    Example:
        spy_on(traps.trigger, op=SpyOpMatchAny([
            {
                'args': ('hallway_lasers',),
                'call_fake': _send_wolves,
            },
            {
                'args': ('trap_tile',),
                'call_fake': _spill_hot_oil,
            },
            {
                'args': ('infrared_camera',),
                'kwargs': {
                    'sector': 'underground_passage',
                },
                'call_original': False,
            },
        ]))
    """

    def __init__(self, calls):
        """Initialize the operation.

        This takes a list of configurations for matching calls, which can be
        called in any order.
        those calls are expected.

        The calls are a list of dictionaries with the following keys:

        ``args`` (:py:class:`tuple`, optional):
            Positional arguments for a match.

        ``kwargs`` (:py:class:`dict`, optional):
            Keyword arguments for a match.

        ``call_fake`` (:py:class:`callable`, optional):
            A function to call when all arguments have matched. This takes
            precedence over ``call_original``.

        ``call_original`` (:py:class:`bool`, optional):
            Whether to call the original function. This is the default if
            ``call_fake`` is not provided.

        Args:
            calls (list of dict):
                A list of call match configurations.
        """
        super(SpyOpMatchAny, self).__init__(calls)

    def get_call_match_config(self, spy_call):
        """Return a call match configuration for a call.

        This will check if there are any call match configurations provided
        during initialization that match the call.

        Args:
            spy_call (kgb.calls.SpyCall):
                The call to return a match for.

        Returns:
            dict:
            The call match configuration.

        Raises:
            kgb.errors.UnexpectedCallError:
                A call match configuration could not be found. Details should
                be in the error message.
        """
        for call_match_config in self._calls:
            if spy_call.called_with(*call_match_config.get('args', ()),
                                    **call_match_config.get('kwargs', {})):
                return call_match_config

        raise UnexpectedCallError(
            '%(spy)s was not called with any expected arguments.'
            % {
                'spy': self.spy.func_name,
            })


class SpyOpMatchInOrder(BaseMatchingSpyOperation):
    """A operation for handling expected calls in a given order.

    This is used to list the calls (specifying positional and keyword
    arguments) that are expected to be made, in the order they should be made,
    raising an error if too many calls were made or a call didn't match the
    expected arguments.

    Each of those expected sets of arguments can optionally result in a call to
    a fake function or the original function. This can be specified per set of
    arguments.

    Example:
        spy_on(lockbox.enter_code, op=SpyOpMatchInOrder([
            {
                'args': (1, 2, 3, 4, 5, 6),
                'call_original': False,
            },
            {
                'args': (9, 0, 2, 1, 0, 0),
                'call_fake': _start_countdown,
            },
            {
                'args': (4, 8, 15, 16, 23, 42),
                'kwargs': {
                    'secret_button_pushed': True,
                },
                'call_original': True,
            },
            {
                'args': (4, 8, 15, 16, 23, 42),
                'kwargs': {
                    'secret_button_pushed': True,
                },
                'op': SpyOpRaise(Exception('Oh no')),
            },
        ]))
    """

    def __init__(self, calls):
        """Initialize the operation.

        This takes a list of configurations for matching calls, in the order
        those calls are expected.

        The calls are a list of dictionaries with the following keys:

        ``args`` (:py:class:`tuple`, optional):
            Positional arguments for a match.

        ``kwargs`` (:py:class:`dict`, optional):
            Keyword arguments for a match.

        ``call_fake`` (:py:class:`callable`, optional):
            A function to call when all arguments have matched. This takes
            precedence over ``call_original``.

        ``call_original`` (:py:class:`bool`, optional):
            Whether to call the original function. This is the default if
            ``call_fake`` is not provided.

        ``op`` (:py:class:`BaseSpyOperation`, optional):
            A spy operation to call instead of ``call_fake`` or
            ``call_original``.

        Args:
            calls (list of dict):
                A list of call match configurations.
        """
        super(SpyOpMatchInOrder, self).__init__(calls)

        self._next = 0

    def get_call_match_config(self, spy_call):
        """Return a call match configuration for a call.

        This will check if the spy call matches the next call match
        configuration in the list provided by the consumer.

        Args:
            spy_call (kgb.calls.SpyCall):
                The call to return a match for.

        Returns:
            dict:
            The call match configuration.

        Raises:
            kgb.errors.UnexpectedCallError:
                Too many calls were made to the function.
        """
        i = self._next

        try:
            call_match_config = self._calls[i]
        except IndexError:
            raise UnexpectedCallError(
                '%(spy)s was called %(num_calls)s time(s), but only '
                '%(expected_calls)s call(s) were expected. Latest call: '
                '%(latest_call)s'
                % {
                    'expected_calls': len(self._calls),
                    'latest_call': spy_call,
                    'num_calls': i + 1,
                    'spy': self.spy.func_name,
                })

        self._next += 1

        return call_match_config


class SpyOpRaise(BaseSpyOperation):
    """An operation for raising an exception.

    This is used to simulate a failure of some sort in a function or method.

    Example:
        spy_on(pen.emit_poison, op=SpyOpRaise(PoisonEmptyError()))
    """

    def __init__(self, exc):
        """Initialize the operation.

        Args:
            exc (Exception):
                The exception instance to raise when the function is called.
        """
        self.exc = exc

    def handle_call(self, *args, **kwargs):
        """Handle a call to this operation.

        This will raise the exception provided to the operation.

        Args:
            *args (tuple, ignored):
                Positional arguments passed into the call.

            **kwargs (tuple, ignored):
                Keyword arguments passed into the call.

        Raises:
            Exception:
                The exception provided to the operation.
        """
        raise self.exc


class SpyOpRaiseInOrder(SpyOpMatchInOrder):
    """An operation for raising exceptions in the order of calls.

    This is similar to :py:class:`SpyOpRaise`, but will raise a different
    exception for each call, based on a provided list.

    Example:
        spy_on(our_agent.get_identities, op=SpyOpRaiseInOrder([
            PoisonEmptyError(),
            Kaboom(),
            MissingPenError(),
        ]))
    """

    def __init__(self, exceptions):
        """Initialize the operation.

        Args:
            exceptions (list of Exception):
                The list of exceptions, one for each function call.
        """
        super(SpyOpRaiseInOrder, self).__init__([
            {
                'op': SpyOpRaise(exc),
            }
            for exc in exceptions
        ])


class SpyOpReturn(BaseSpyOperation):
    """An operation for returning a value.

    This is used to simulate a simple result from a function call without
    having to override the method or provide a lambda.

    Example:
        spy_on(our_agent.get_identity, op=SpyOpReturn('nobody...'))
    """

    def __init__(self, return_value):
        """Initialize the operation.

        Args:
            return_value (object):
                The value to return when the function is called.
        """
        self.return_value = return_value

    def handle_call(self, *args, **kwargs):
        """Handle a call to this operation.

        This will return the value provided to the operation.

        Args:
            *args (tuple, ignored):
                Positional arguments passed into the call.

            **kwargs (tuple, ignored):
                Keyword arguments passed into the call.

        Returns:
            object:
            The return value provided to the operation.
        """
        return self.return_value


class SpyOpReturnInOrder(SpyOpMatchInOrder):
    """An operation for returning a value.

    This is similar to :py:class:`SpyOpReturn`, but will return a different
    value for each call, based on a provided list.

    Example:
        spy_on(our_agent.get_identities, op=SpyOpReturnInOrder([
            'nobody...',
            'who?',
            'never heard of them...',
        ]))
    """

    def __init__(self, return_values):
        """Initialize the operation.

        Args:
            return_values (list):
                The list of values, one for each function call.
        """
        super(SpyOpReturnInOrder, self).__init__([
            {
                'op': SpyOpReturn(value),
            }
            for value in return_values
        ])
