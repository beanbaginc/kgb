from __future__ import absolute_import, unicode_literals

import copy
import inspect
import types

from kgb.calls import SpyCall
from kgb.errors import (ExistingSpyError,
                        IncompatibleFunctionError,
                        InternalKGBError)
from kgb.pycompat import iterkeys, pyver
from kgb.signature import FunctionSig, _UNSET_ARG
from kgb.utils import is_attr_defined_on_ancestor


class FunctionSpy(object):
    """A spy infiltrating a function.

    A FunctionSpy takes the place of another function. It will record any
    calls made to the function for later inspection.

    By default, a FunctionSpy will allow the call to go through to the
    original function. This can be disabled by passing call_original=False
    when initiating the spy. If disabled, the original function will never be
    called.

    This can also be passed a call_fake parameter pointing to another
    function to call instead of the original. If passed, this will take
    precedence over call_original.
    """

    #: The spy represents a standard function.
    TYPE_FUNCTION = FunctionSig.TYPE_FUNCTION

    #: The spy represents a bound method.
    #:
    #: Bound methods are functions on an instance of a class, or classmethods.
    TYPE_BOUND_METHOD = FunctionSig.TYPE_BOUND_METHOD

    #: The spy represents an unbound method.
    #:
    #: Unbound methods are standard methods on a class.
    TYPE_UNBOUND_METHOD = FunctionSig.TYPE_UNBOUND_METHOD

    _PROXY_METHODS = [
        'call_original', 'called_with', 'last_called_with',
        'raised', 'last_raised', 'returned', 'last_returned',
        'raised_with_message', 'last_raised_with_message',
        'reset_calls', 'unspy',
    ]

    _FUNC_ATTR_DEFAULTS = {
        'calls': [],
        'called': False,
        'last_call': None,
    }

    _spy_map = {}

    def __init__(self, agency, func, call_fake=None, call_original=True,
                 op=None, owner=_UNSET_ARG, func_name=None):
        """Initialize the spy.

        This will begin spying on the provided function or method, injecting
        new code into the function to help record how it was called and
        what it returned, and adding methods and state onto the function
        for callers to access in order to get those results.

        Version Added:
            7.0:
            Added support for specifying an explicit function name using
            ``func_name=``.

        Version Added:
            5.0:
            Added support for specifying an instance in ``owner`` when spying
            on bound methods using decorators that return plain functions.

        Args:
            agency (kgb.agency.SpyAgency):
                The spy agency that manages this spy.

            func (callable):
                The function or method to spy on.

            call_fake (callable, optional):
                The optional function to call when this function is invoked.

                This cannot be specified if ``op`` is provided.

            call_original (bool, optional):
                Whether to call the original function when the spy is
                invoked. If ``False``, no function will be called.

                This is ignored if ``call_fake`` or ``op`` are provided.

            op (kgb.spies.BaseOperation, optional):
                An operation to perform.

                This cannot be specified if ``call_fake`` is provided.

            owner (type or object, optional):
                The owner of the function or method.

                If spying on an unbound method, this **must** be set to the
                class that owns it.

                If spying on a bound method that identifies as a plain
                function (which may happen if the method is decorated and
                dynamically returns a new function on access), this should
                be the instance of the object you're spying on.

            func_name (str, optional):
                An explicit name for the function. This will be used instead
                of the function's specified name, and is usually a sign of a
                bad decorator.

                Version Added:
                    7.0
        """
        # Start off by grabbing the current frame. This will be needed for
        # some errors.
        self.init_frame = inspect.currentframe()

        # Check the parameters passed to make sure that invalid data wasn't
        # provided.
        if op is not None and call_fake is not None:
            raise ValueError('op and call_fake cannot both be provided.')

        if hasattr(func, 'spy'):
            raise ExistingSpyError(func)

        if (not callable(func) or
            not hasattr(func, FunctionSig.FUNC_NAME_ATTR) or
            not (hasattr(func, FunctionSig.METHOD_SELF_ATTR) or
                 hasattr(func, FunctionSig.FUNC_GLOBALS_ATTR))):
            raise ValueError('%r cannot be spied on. It does not appear to '
                             'be a valid function or method.'
                             % func)

        # Construct a signature for the function and begin closely inspecting
        # the parameters, making sure everything will be compatible so we
        # don't have unexpected breakages when setting up or calling spies.
        sig = FunctionSig(func=func,
                          owner=owner,
                          func_name=func_name)
        self._sig = sig

        # If the caller passed an explicit owner, check to see if it's at all
        # valid. Note that it may have been handled above (for unbound
        # methods).
        if owner is not _UNSET_ARG and owner is not self.owner:
            if self.func_type == self.TYPE_FUNCTION:
                raise ValueError(
                    'This function has no owner, but an owner was passed '
                    'to spy_on().')
            else:
                if not hasattr(owner, self.func_name):
                    raise ValueError('The owner passed does not contain the '
                                     'spied method.')
                elif (self.func_type == self.TYPE_BOUND_METHOD or
                      (pyver[0] == 2 and
                       self.func_type == self.TYPE_UNBOUND_METHOD)):
                    raise ValueError(
                        'The owner passed does not match the actual owner of '
                        'the bound method.')

        # We cannot currently spy on unbound methods that result in slippery
        # functions, so check for that and bail early.
        if (sig.is_slippery and
            self.func_type == self.TYPE_UNBOUND_METHOD):
            raise ValueError('Unable to spy on unbound slippery methods '
                             '(those that return a new function on each '
                             'attribute access). Please spy on an instance '
                             'instead.')

        # If call_fake was provided, check that it's valid and has a
        # compatible function signature.
        if op is not None:
            # We've already checked this above, but check it again.
            assert call_fake is None

            call_fake = op.setup(self)
            assert call_fake is not None

        if call_fake is not None:
            if not callable(call_fake):
                raise ValueError('%r cannot be used for call_fake. It does '
                                 'not appear to be a valid function or method.'
                                 % call_fake)

            call_fake_sig = FunctionSig(call_fake,
                                        func_name=func_name)

            if not sig.is_compatible_with(call_fake_sig):
                raise IncompatibleFunctionError(
                    func=func,
                    func_sig=sig,
                    incompatible_func=call_fake,
                    incompatible_func_sig=call_fake_sig)

        # Now that we're done validating, we can start setting state and
        # patching things.
        self.agency = agency
        self.orig_func = func
        self._real_func = sig.real_func
        self._call_orig_func = self._clone_function(self.orig_func)

        if self._get_owner_needs_patching():
            # We need to store the original attribute value for the function,
            # as defined in the class that owns it. That may be the provided
            # or calculated owner, or a parent of it.
            #
            # This is needed because the function provided may not actually be
            # what's defined on the class. What's defined might be a decorator
            # that returns a function, and it might not even be the same
            # function each time it's accessed.
            self._owner_func_attr_value = \
                self.owner.__dict__.get(self.func_name)

            # Now we can patch the owner to prevent conflicts between spies.
            self._patch_owner()
        else:
            self._owner_func_attr_value = self.orig_func

        # Determine what we're going to invoke when the spy is called.
        if call_fake:
            self.func = call_fake
        elif call_original:
            self.func = self.orig_func
        else:
            self.func = None

        # Build our proxy function. This is the spy itself, the function that
        # will actually be invoked when the spied-on function is called.
        self._build_proxy_func(func)

        # If we're calling the original function above, we need to replace what
        # we're calling with something that acts like the original function.
        # Otherwise, we'll just call the forwarding_call above in an infinite
        # loop.
        if self.func is self.orig_func:
            self.func = self._clone_function(self.func,
                                             code=self._old_code)

    @property
    def func_type(self):
        """The type of function being spied on.

        This will be one of :py:attr:`TYPE_FUNCTION`,
        :py:attr:`TYPE_UNBOUND_METHOD`, or :py:attr:`TYPE_BOUND_METHOD`.

        Type:
            int
        """
        return self._sig.func_type

    @property
    def func_name(self):
        """The name of the function being spied on.

        Type:
            str
        """
        return self._sig.func_name

    @property
    def owner(self):
        """The owner of the method, if a bound or unbound method.

        This will be ``None`` if there is no owner.

        Type:
            type
        """
        return self._sig.owner

    @property
    def called(self):
        """Whether or not the spy was ever called."""
        try:
            return self._real_func.called
        except AttributeError:
            return False

    @property
    def calls(self):
        """The list of calls made to the function.

        Each is an instance of :py:class:`SpyCall`.
        """
        try:
            return self._real_func.calls
        except AttributeError:
            return []

    @property
    def last_call(self):
        """The last call made to this function.

        If a spy hasn't been called yet, this will be ``None``.
        """
        try:
            return self._real_func.last_call
        except AttributeError:
            return None

    def unspy(self, unregister=True):
        """Remove the spy from the function, restoring the original.

        The spy will, by default, be removed from the registry's
        list of spies. This can be disabled by passing ``unregister=False``,
        but don't do that. That's for internal use.

        Args:
            unregister (bool, optional):
                Whether to unregister the spy from the associated agency.
        """
        real_func = self._real_func
        owner = self.owner

        assert hasattr(real_func, 'spy')

        del FunctionSpy._spy_map[id(self)]
        del real_func.spy

        for attr_name in iterkeys(self._FUNC_ATTR_DEFAULTS):
            delattr(real_func, attr_name)

        for func_name in self._PROXY_METHODS:
            delattr(real_func, func_name)

        setattr(real_func, FunctionSig.FUNC_CODE_ATTR, self._old_code)

        if owner is not None:
            self._set_method(owner, self.func_name,
                             self._owner_func_attr_value)

        if unregister:
            self.agency.spies.remove(self)

    def call_original(self, *args, **kwargs):
        """Call the original function being spied on.

        The function will behave as normal, and will not trigger any spied
        behavior or call tracking.

        Args:
            *args (tuple):
                The positional arguments to pass to the function.

            **kwargs (dict):
                The keyword arguments to pass to the function.

        Returns:
            object:
            The return value of the function.

        Raises:
            Exception:
                Any exceptions raised by the function.
        """
        if self.func_type == self.TYPE_BOUND_METHOD:
            return self._call_orig_func(self.owner, *args, **kwargs)
        else:
            if self.func_type == self.TYPE_UNBOUND_METHOD:
                if not args or not isinstance(args[0], self.owner):
                    raise TypeError(
                        'The first argument to %s.call_original() must be '
                        'an instance of %s.%s, since this is an unbound '
                        'method.'
                        % (self._call_orig_func.__name__,
                           self.owner.__module__,
                           self.owner.__name__))

            return self._call_orig_func(*args, **kwargs)

    def called_with(self, *args, **kwargs):
        """Return whether the spy was ever called with the given arguments.

        This will check each and every recorded call to see if the arguments
        and keyword arguments match up. If at least one call does match, this
        will return ``True``.

        Not every argument and keyword argument made in the call must be
        provided to this method. These can be a subset of the positional and
        keyword arguments in the call, but cannot contain any arguments not
        made in the call.

        Args:
            *args (tuple):
                The positional arguments made in the call, or a subset of
                those arguments (starting with the first argument).

            **kwargs (dict):
                The keyword arguments made in the call, or a subset of those
                arguments.

        Returns:
            bool:
            ``True`` if there's at least one call matching these arguments.
            ``False`` if no call matches.
        """
        return any(
            call.called_with(*args, **kwargs)
            for call in self.calls
        )

    def last_called_with(self, *args, **kwargs):
        """Return whether the spy was last called with the given arguments.

        Not every argument and keyword argument made in the call must be
        provided to this method. These can be a subset of the positional and
        keyword arguments in the call, but cannot contain any arguments not
        made in the call.

        Args:
            *args (tuple):
                The positional arguments made in the call, or a subset of
                those arguments (starting with the first argument).

            **kwargs (dict):
                The keyword arguments made in the call, or a subset of those
                arguments.

        Returns:
            bool:
            ``True`` if the last call's arguments match the provided arguments.
            ``False`` if they do not.
        """
        call = self.last_call

        return call is not None and call.called_with(*args, **kwargs)

    def returned(self, value):
        """Return whether the spy was ever called and returned the given value.

        This will check each and every recorded call to see if any of them
        returned the given value.  If at least one call did, this will return
        ``True``.

        Args:
            value (object):
                The expected returned value from the call.

        Returns:
            bool:
            ``True`` if there's at least one call that returned this value.
            ``False`` if no call returned the value.
        """
        return any(
            call.returned(value)
            for call in self.calls
        )

    def last_returned(self, value):
        """Return whether the spy's last call returned the given value.

        Args:
            value (object):
                The expected returned value from the call.

        Returns:
            bool:
            ``True`` if the last call returned this value. ``False`` if it
            did not.
        """
        call = self.last_call

        return call is not None and call.returned(value)

    def raised(self, exception_cls):
        """Return whether the spy was ever called and raised this exception.

        This will check each and every recorded call to see if any of them
        raised an exception of a given type. If at least one call does match,
        this will return ``True``.

        Args:
            exception_cls (type):
                The expected type of exception raised by a call.

        Returns:
            bool:
            ``True`` if there's at least one call raising the given exception
            type. ``False`` if no call matches.
        """
        return any(
            call.raised(exception_cls)
            for call in self.calls
        )

    def last_raised(self, exception_cls):
        """Return whether the spy's last call raised this exception.

        Args:
            exception_cls (type):
                The expected type of exception raised by a call.

        Returns:
            bool:
            ``True`` if the last call raised the given exception type.
            ``False`` if it did not.
        """
        call = self.last_call

        return call is not None and call.raised(exception_cls)

    def raised_with_message(self, exception_cls, message):
        """Return whether the spy's calls ever raised this exception/message.

        This will check each and every recorded call to see if any of them
        raised an exception of a given type with the given message. If at least
        one call does match, this will return ``True``.

        Args:
            exception_cls (type):
                The expected type of exception raised by a call.

            message (unicode):
                The expected message from the exception.

        Returns:
            bool:
            ``True`` if there's at least one call raising the given exception
            type and message. ``False`` if no call matches.
        """
        return any(
            call.raised_with_message(exception_cls, message)
            for call in self.calls
        )

    def last_raised_with_message(self, exception_cls, message):
        """Return whether the spy's last call raised this exception/message.

        Args:
            exception_cls (type):
                The expected type of exception raised by a call.

            message (unicode):
                The expected message from the exception.

        Returns:
            bool:
            ``True`` if the last call raised the given exception type and
            message. ``False`` if it did not.
        """
        call = self.last_call

        return (call is not None and
                call.raised_with_message(exception_cls, message))

    def reset_calls(self):
        """Reset the list of calls recorded by this spy."""
        self._real_func.calls = []
        self._real_func.called = False
        self._real_func.last_call = None

    def __call__(self, *args, **kwargs):
        """Call the original function or fake function for the spy.

        This will be called automatically when calling the spied function,
        recording the call and the results from the call.

        Args:
            *args (tuple):
                Positional arguments passed to the function.

            **kwargs (dict):
                All dictionary arguments either passed to the function or
                default values for unspecified keyword arguments in the
                function signature.

        Returns:
            object:
            The result of the function call.
        """
        record_args = args

        if self.func_type in (self.TYPE_BOUND_METHOD,
                              self.TYPE_UNBOUND_METHOD):
            record_args = record_args[1:]

        sig = self._sig
        real_func = self._real_func
        func = self.func

        call = SpyCall(self, record_args, kwargs)
        real_func.calls.append(call)
        real_func.called = True
        real_func.last_call = call

        if func is None:
            result = None
        else:
            try:
                if sig.has_getter:
                    # This isn't a standard function. It's a descriptor with
                    # a __get__() method. We need to fetch the value it
                    # returns.
                    result = sig.defined_func.__get__(self.owner)

                    if sig.is_slippery:
                        # Since we know this represents a slippery function,
                        # we need to take the function from the descriptor's
                        # result and call it.
                        result = result(*args, **kwargs)
                else:
                    # This is a typical function/method. We can call it
                    # directly.
                    result = func(*args, **kwargs)
            except Exception as e:
                call.exception = e
                raise

            call.return_value = result

        return result

    def __repr__(self):
        """Return a string representation of the spy.

        This is mainly used for debugging information. It will show some
        details on the spied function and call log.

        Returns:
            unicode:
            The resulting string representation.
        """
        func_type = self.func_type

        if func_type == self.TYPE_FUNCTION:
            func_type_str = 'function'
            qualname = self.func_name
        else:
            owner = self.owner

            if func_type == self.TYPE_BOUND_METHOD:
                # It's important we use __class__ instead of type(), because
                # we may be dealing with an old-style class.
                owner_cls = self.owner.__class__

                if owner_cls is type:
                    class_name = owner.__name__
                    func_type_str = 'classmethod'
                else:
                    class_name = owner_cls.__name__
                    func_type_str = 'bound method'
            elif func_type == self.TYPE_UNBOUND_METHOD:
                class_name = owner.__name__
                func_type_str = 'unbound method'

            qualname = '%s.%s of %r' % (class_name, self.func_name, owner)

        call_count = len(self.calls)

        if call_count == 1:
            calls_str = 'call'
        else:
            calls_str = 'calls'

        return '<Spy for %s %s (%d %s)>' % (func_type_str, qualname,
                                            len(self.calls), calls_str)

    def _get_owner_needs_patching(self):
        """Return whether the owner (if any) needs to be patched.

        Owners need patching if they're an instance, if the function is
        slippery, or if the function is defined on an ancestor of the class
        and not the class itself.

        See :py:meth:`_patch_owner` for what patching entails.

        Returns:
            bool:
            ``True`` if the owner needs patching. ``False`` if it does not.
        """
        owner = self.owner

        return (owner is not None and
                (not inspect.isclass(owner) or
                 self._sig.is_slippery or
                 is_attr_defined_on_ancestor(owner, self.func_name)))

    def _patch_owner(self):
        """Patch the owner.

        This will create a new method in place of an existing one on the
        owner, in order to ensure that the owner has its own unique copy
        for spying purposes.

        Patching the owner will avoid collisions between spies in the event
        that the method being spied on is defined by a parent of the owner,
        rather than the owner itself.

        See :py:meth:`_get_owner_needs_patching` the conditions under which
        patching will occur.
        """
        # Construct a replacement function for this method, and
        # re-assign it to the owner. We do this in order to prevent
        # two spies on the same method on two separate instances
        # of the class, or two subclasses of a common class owning the
        # method from conflicting with each other.
        real_func = self._clone_function(self._real_func)
        owner = self.owner

        if self.func_type == self.TYPE_BOUND_METHOD:
            method_type_args = [real_func, owner]

            if pyver[0] >= 3:
                method_type_args.append(owner)

            self._set_method(owner, self.func_name,
                             types.MethodType(real_func, self.owner))
        else:
            self._set_method(owner, self.func_name, real_func)

        self._real_func = real_func

    def _build_proxy_func(self, func):
        """Build the proxy function used to forward calls to this spy.

        This will construct a new function compatible with the signature of
        the provided function, which will call this spy whenever it's called.
        The bytecode of the provided function will be set to that of the
        generated proxy function. See the comment within this function for
        details on how this works.

        Args:
            func (callable):
                The function to proxy.
        """
        # Prior to kgb 2.0, we attempted to optimistically replace
        # methods on a class with a FunctionSpy, forwarding on calls to the
        # fake or original function. This was the design since kgb 1.0, but
        # wasn't sufficient. We realized in the first release that this
        # wouldn't work for standard functions, and so we had two designs:
        # One for methods, one for standard functions.
        #
        # In kgb 2.0, in an effort to standardize behavior, we moved fully
        # to the method originally used for standard functions (largely due
        # to the fact that in Python 3, unbound methods are just standard
        # functions).
        #
        # Standard functions can't be replaced. Unlike a bound function,
        # we can't reliably figure out what dictionary it lives in (it
        # could be a locals() inside another function), and even if we
        # replace that, we can't replace all the copies that have been
        # imported up to this point.
        #
        # The only option is to change what happens when we call the
        # function. That's easier said than done. We can't just replace
        # the __call__ method on it, like you could on a fake method for
        # a class.
        #
        # What we must do is replace the code backing it. This must be
        # done carefully. The "co_freevars" and "co_cellvars" fields must
        # remain the same between the old code and the new one. The
        # actual bytecode and most of the rest of the fields can be taken
        # from another function (the "forwarding_call" function defined
        # inline below).
        #
        # Unfortunately, we no longer have access to "self" (since we
        # replaced "co_freevars"). Instead, we store a global mapping
        # of codes to spies.
        #
        # We also must build the function dynamically, using exec().
        # The reason is that we want to accurately mimic the function
        # signature of the original function (in terms of specifying
        # the correct positional and keyword arguments). The way we format
        # arguments depends on the version of Python. We maintain
        # compatibility through the FunctionSig.format_arg_spec() methods
        # (which has implementations for both Python 2 and 3).
        #
        # We do use different values for the default keyword arguments,
        # which is actually okay. Within the function, these will all be
        # set to a special value (_UNSET_ARG), which is used later for
        # determining which keyword arguments were provided and which
        # were not. Anything attempting to inspect this function with
        # getargspec(), getfullargspec(), or inspect.Signature will get the
        # defaults from the original function, by way of the
        # original func.func_defaults attribute (on Python 2) or
        # __defaults__ (on Python 3).
        #
        # This forwarding function then needs to call the forwarded
        # function in exactly the same manner as it was called. That is,
        # if a keyword argument's value was passed in as a positional
        # argument, or a positional argument was specified as a keyword
        # argument in the call, then the forwarded function must be
        # called the same way, for argument tracking and signature
        # compatibility.
        #
        # In order to do this, we have to find out how forwarding_call was
        # called. This can be done by inspecting the bytecode of the
        # call in the parent frame and getting the number of positional
        # and keyword arguments used. From there, we can determine which
        # argument slots were specified and start looking for any keyword
        # arguments not set to _UNSET_ARG, passing them through to the
        # original function in the same order. Doing this requires
        # another exec() call in order to build out those arguments.
        #
        # Within the function, all imports and variables are prefixed to
        # avoid the possibility of collisions with arguments.
        #
        # Since we're only overriding the code, all other attributes (like
        # func_defaults, __doc__, etc.) will make use of those from
        # the original function.
        #
        # The result is that we've completely hijacked the original
        # function, making it call our own forwarding function instead.
        # It's a wonderful bag of tricks that are fully legal, but really
        # dirty. Somehow, it all really fits in with the idea of spies,
        # though.
        sig = self._sig
        spy_id = id(self)
        real_func = self._real_func

        forwarding_call = self._compile_forwarding_call_func(
            func=func,
            sig=sig,
            spy_id=spy_id)

        old_code, new_code = self._build_spy_code(func, forwarding_call)
        self._old_code = old_code
        setattr(real_func, FunctionSig.FUNC_CODE_ATTR, new_code)

        # Update our spy lookup map so the proxy function can easily find
        # the spy instance.
        FunctionSpy._spy_map[spy_id] = self

        # Update the attributes on the function. we'll be placing all spy
        # state and some proxy methods pointing to this spy, so that we can
        # easily access them through the function.
        real_func.spy = self
        real_func.__dict__.update(copy.deepcopy(self._FUNC_ATTR_DEFAULTS))

        for proxy_func_name in self._PROXY_METHODS:
            assert not hasattr(real_func, proxy_func_name)
            setattr(real_func, proxy_func_name, getattr(self, proxy_func_name))

    def _compile_forwarding_call_func(self, func, sig, spy_id):
        """Compile a forwarding call function for the spy.

        This will build the Python code for a function that approximates the
        function we're spying on, with the same function definition and
        closure behavior.

        Version Added:
            7.1

        Args:
            func (callable):
                The function being spied on.

            sig (kgb.signature.BaseFunctionSig):
                The function signature to use for this function.

            spy_id (int):
                The ID used for the spy registration.

        Returns:
            callable:
            The resulting forwarding function.
        """
        closure_vars = func.__code__.co_freevars
        use_closure = bool(closure_vars)

        # If the function is in a closure, we'll need to mirror the closure
        # state by using the referenced variables within _kgb_forwarding_call
        # and by defining those variables within a closure.
        #
        # Start by setting up a string that will use each closure.
        if use_closure:
            # This is an efficient way of referencing each variable without
            # side effects (at least in Python 2.7 through 3.11). Tuple
            # operations are fast and compact, and don't risk any inadvertent
            # invocation of the variables.
            use_closure_vars_str = (
                '        (%s)\n'
                % ', '.join(func.__code__.co_freevars)
            )
        else:
            # No closure, so nothing to set up.
            use_closure_vars_str = ''

        # Now define the forwarding call. This will always be nested within
        # either a closure of an if statement, letting us build a single
        # version at the right indentation level, keeping this as fast and
        # portable as possible.
        forwarding_call_str = (
            '    def _kgb_forwarding_call(%(params)s):\n'
            '        from kgb.spies import FunctionSpy as _kgb_cls\n'
            '%(use_closure_vars)s'
            '        _kgb_l = locals()\n'
            '        return _kgb_cls._spy_map[%(spy_id)s](%(call_args)s)\n'
            % {
                'call_args': sig.format_forward_call_args(),
                'params': sig.format_arg_spec(),
                'spy_id': spy_id,
                'use_closure_vars': use_closure_vars_str,
            }
        )

        if use_closure:
            # We now need to put _kgb_forwarding_call in a closure, to mirror
            # the behavior of the spied function. The closure will provide
            # the closure variables, and will return the function we can
            # later use.
            func_code_str = (
                'def _kgb_forwarding_call_closure(%(params)s):\n'
                '%(forwarding_call)s'
                '    return _kgb_forwarding_call\n'
                % {
                    'forwarding_call': forwarding_call_str,
                    'params': ', '.join(
                        '%s=None' % _var
                        for _var in closure_vars
                    )
                }
            )
        else:
            # No closure, so just define the function as-is. We will need to
            # wrap in an "if 1:" though, just to ensure indentation is fine.
            func_code_str = (
                'if 1:\n'
                '%s'
                % forwarding_call_str
            )

        # We can now build our function.
        exec_locals = {}

        try:
            eval(compile(func_code_str, '<string>', 'exec'),
                 globals(), exec_locals)
        except Exception as e:
            raise InternalKGBError(
                'Unable to compile a spy function for %(func)r: %(error)s'
                '\n\n'
                '%(code)s'
                % {
                    'code': func_code_str,
                    'error': e,
                    'func': func,
                })

        # Grab the resulting compiled function out of the locals.
        if use_closure:
            # It's in our closure, so call that and get the result.
            forwarding_call = exec_locals['_kgb_forwarding_call_closure']()
        else:
            forwarding_call = exec_locals['_kgb_forwarding_call']

        assert forwarding_call is not None

        return forwarding_call

    def _build_spy_code(self, func, forwarding_call):
        """Build a CodeType to inject into the spied function.

        This will create a function bytecode object that contains a mix of
        attributes from the original function and the forwarding call. The
        result can be injected directly into the spied function, containing
        just the right data to impersonate the function and call our own
        logic.

        Version Added:
            7.1

        Args:
            func (callable):
                The function being spied on.

            forwarding_call (callable):
                The spy forwarding call we built.

        Returns:
            tuple:
            A 2-tuple containing:

            1. The spied function's code object (:py:class:`types.CodeType`).
            1. The new spy code object (:py:class:`types.CodeType`).
        """
        old_code = getattr(func, FunctionSig.FUNC_CODE_ATTR)
        temp_code = getattr(forwarding_call, FunctionSig.FUNC_CODE_ATTR)

        assert old_code != temp_code

        if hasattr(old_code, 'replace'):
            # Python >= 3.8
            #
            # It's important we replace the code instead of building a new
            # one when possible. On Python 3.11, this will ensure that
            # state needed for exceptions (co_positions()) will be set
            # correctly.
            replace_kwargs = {
                'co_name': old_code.co_name,
                'co_freevars': old_code.co_freevars,
                'co_cellvars': old_code.co_cellvars,
            }

            if pyver >= (3, 11):
                replace_kwargs['co_qualname'] = old_code.co_qualname

            new_code = temp_code.replace(**replace_kwargs)
        else:
            # Python <= 3.7
            #
            # We have to build this manually, using a combination of the
            # two. We won't bother with anything newer than Python 3.7.
            code_args = [temp_code.co_argcount]

            if pyver >= (3, 0):
                code_args.append(temp_code.co_kwonlyargcount)

            code_args += [
                temp_code.co_nlocals,
                temp_code.co_stacksize,
                temp_code.co_flags,
                temp_code.co_code,
                temp_code.co_consts,
                temp_code.co_names,
                temp_code.co_varnames,
                temp_code.co_filename,
                old_code.co_name,
                temp_code.co_firstlineno,
                temp_code.co_lnotab,
                old_code.co_freevars,
                old_code.co_cellvars,
            ]

            new_code = types.CodeType(*code_args)

        assert new_code != old_code
        assert new_code != temp_code

        return old_code, new_code

    def _clone_function(self, func, code=None):
        """Clone a function, optionally providing new bytecode.

        This will create a new function that contains all the state of the
        original (including annotations and any default argument values).

        Args:
            func (types.FunctionType):
                The function to clone.

            code (types.CodeType, optional):
                The new bytecode for the function. If not specified, the
                original function's bytecode will be used.

        Returns:
            types.FunctionType:
            The new function.
        """
        cloned_func = types.FunctionType(
            code or getattr(func, FunctionSig.FUNC_CODE_ATTR),
            getattr(func, FunctionSig.FUNC_GLOBALS_ATTR),
            getattr(func, FunctionSig.FUNC_NAME_ATTR),
            getattr(func, FunctionSig.FUNC_DEFAULTS_ATTR),
            getattr(func, FunctionSig.FUNC_CLOSURE_ATTR))

        if pyver[0] >= 3:
            # Python 3.x doesn't support providing any of the new
            # metadata introduced in Python 3.x to the constructor of
            # FunctionType. We have to set those manually.
            for attr in ('__annotations__', '__kwdefaults__'):
                setattr(cloned_func, attr, copy.deepcopy(getattr(func, attr)))

        return cloned_func

    def _set_method(self, owner, name, method):
        """Set a new method on an object.

        This will set the method (or delete the attribute for one if setting
        ``None``).

        If setting on a class, this will use a standard
        :py:func:`setattr`/:py:func:`delattr`.

        If setting on an instance, this will use a standard
        :py:meth:`object.__setattr__`/:py:meth:`object.__delattr__` (in order
        to avoid triggering a subclass-defined version of
        :py:meth:`~object.__setattr__`/:py:meth:`~object.__delattr__`, which
        might lose or override our spy).

        Args:
            owner (type or object):
                The class or instance to set the method on.

            name (unicode):
                The name of the attribute to set for the method.

            method (types.MethodType):
                The method to set (or ``None`` to delete).
        """
        if inspect.isclass(owner):
            if method is None:
                delattr(owner, name)
            else:
                setattr(owner, name, method)
        elif method is None:
            try:
                object.__delattr__(owner, name)
            except TypeError as e:
                if str(e) == "can't apply this __delattr__ to instance object":
                    # This is likely Python 2.6, or early 2.7, where we can't
                    # run object.__delattr__ on old-style classes. We have to
                    # fall back to modifying __dict__. It's not ideal but
                    # doable.
                    del owner.__dict__[name]
        else:
            try:
                object.__setattr__(owner, name, method)
            except TypeError as e:
                if str(e) == "can't apply this __setattr__ to instance object":
                    # Similarly as above, we have to default to dict
                    # manipulation on this version of Python.
                    owner.__dict__[name] = method
