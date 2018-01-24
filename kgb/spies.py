from __future__ import absolute_import, unicode_literals

import copy
import inspect
import sys
import types


pyver = sys.version_info[0]

if pyver == 2:
    FUNC_CLOSURE_ATTR = 'func_closure'
    FUNC_CODE_ATTR = 'func_code'
    FUNC_DEFAULTS_ATTR = 'func_defaults'
    FUNC_GLOBALS_ATTR = 'func_globals'
    FUNC_NAME_ATTR = 'func_name'
    METHOD_SELF_ATTR = 'im_self'

    text_type = unicode

    def iterkeys(d):
        return d.iterkeys()

    def iteritems(d):
        return d.iteritems()
else:
    FUNC_CLOSURE_ATTR = '__closure__'
    FUNC_CODE_ATTR = '__code__'
    FUNC_DEFAULTS_ATTR = '__defaults__'
    FUNC_GLOBALS_ATTR = '__globals__'
    FUNC_NAME_ATTR = '__name__'
    METHOD_SELF_ATTR = '__self__'

    text_type = str

    def iterkeys(d):
        return iter(d.keys())

    def iteritems(d):
        return iter(d.items())

_UNSET_ARG = object()


class SpyCall(object):
    """Records arguments made to a spied function call.

    SpyCalls are created and stored by a FunctionSpy every time it is
    called. They're accessible through the FunctionSpy's ``calls`` attribute.
    """

    def __init__(self, args, kwargs):
        self.args = args
        self.kwargs = kwargs
        self.return_value = None
        self.exception = None

    def called_with(self, *args, **kwargs):
        """Return whether this call was made with the given arguments.

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
            ``True`` if the call's arguments match the provided arguments.
            ``False`` if they do not.
        """
        if len(args) > len(self.args):
            return False

        if self.args[:len(args)] != args:
            return False

        for key, value in iteritems(kwargs):
            if key not in self.kwargs or self.kwargs[key] != value:
                return False

        return True

    def returned(self, value):
        """Return whether this call returned the given value.

        Args:
            value (object):
                The expected returned value from the call.

        Returns:
            bool:
            ``True`` if this call returned the given value. ``False`` if it
            did not.
        """
        return self.return_value == value

    def raised(self, exception_cls):
        """Return whether this call raised this exception.

        Args:
            exception_cls (type):
                The expected type of exception raised by the call.

        Returns:
            bool:
            ``True`` if this call raised the given exception type.
            ``False`` if it did not.
        """
        return ((self.exception is None and exception_cls is None) or
                type(self.exception) is exception_cls)

    def raised_with_message(self, exception_cls, message):
        """Return whether this call raised this exception and message.

        Args:
            exception_cls (type):
                The expected type of exception raised by the call.

            message (unicode):
                The expected message from the exception.

        Returns:
            bool:
            ``True`` if this call raised the given exception type and message.
            ``False`` if it did not.
        """
        return (self.exception is not None and
                self.raised(exception_cls) and
                text_type(self.exception) == message)

    def __repr__(self):
        return '<SpyCall(args=%r, kwargs=%r, returned=%r, raised=%r>' % (
            self.args, self.kwargs, self.return_value, self.exception)


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
    TYPE_FUNCTION = 0

    #: The spy represents a bound method.
    #:
    #: Bound methods are functions on an instance of a class, or classmethods.
    TYPE_BOUND_METHOD = 1

    #: The spy represents an unbound method.
    #:
    #: Unbound methods are standard methods on a class.
    TYPE_UNBOUND_METHOD = 2

    _PROXY_METHODS = [
        'called_with', 'last_called_with',
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

    def __init__(self, agency, func, call_fake=None, call_original=True):
        assert not hasattr(func, 'spy')
        assert callable(func)
        assert hasattr(func, FUNC_NAME_ATTR)
        assert (hasattr(func, METHOD_SELF_ATTR) or
                hasattr(func, FUNC_GLOBALS_ATTR))

        self.agency = agency
        self.func_type = self.TYPE_FUNCTION
        self.func_name = getattr(func, FUNC_NAME_ATTR)
        self.orig_func = func
        self.owner = None
        self._argspec = None

        if hasattr(func, '__func__'):
            # This is an instancemethod on a class. Grab the real function
            # from it.
            real_func = func.__func__
        else:
            real_func = func

        # Determine if this is a method, and if so, what type and what owns it.
        if pyver == 2 and inspect.ismethod(func):
            owner = getattr(func, METHOD_SELF_ATTR)

            if owner is None:
                self.func_type = self.TYPE_UNBOUND_METHOD
                self.owner = func.im_class
            else:
                self.func_type = self.TYPE_BOUND_METHOD
                self.owner = owner
        elif pyver >= 3:
            # Python 3 does not officially have unbound methods. Methods on
            # instances are easily identified as types.MethodType, but
            # unbound methods are just standard functions without something
            # like __self__ to point to the parent class.
            #
            # However, the owner can generally be inferred (but not always!).
            # Python 3.3 introduced __qualname__, which is a string
            # identifying the path to the class within the containing module.
            # The path is expected to be traversable, unless it contains
            # "<locals>" in it, in which case it's defined somewhere you can't
            # get to it (like in a function).
            #
            # So to determine if it's an unbound method, we check to see what
            # __qualname__ looks like, and then we try to find it. If we can,
            # we grab the owner and identify it as an unbound method. If not,
            # it stays as a standard function.
            if inspect.ismethod(func):
                self.func_type = self.TYPE_BOUND_METHOD
                self.owner = getattr(func, METHOD_SELF_ATTR)
            elif ('.' in func.__qualname__ and
                  '<locals>' not in func.__qualname__):
                owner = inspect.getmodule(real_func)

                for part in real_func.__qualname__.split('.')[:-1]:
                    try:
                        owner = getattr(owner, part)
                    except AttributeError:
                        owner = None
                        break

                if owner is not None:
                    self.func_type = self.TYPE_UNBOUND_METHOD
                    self.owner = owner

        if self.owner is not None:
            # Construct a replacement function for this method, and
            # re-assign it to the instance. We do this in order to
            # prevent two spies on the same function on two separate
            # instances of the class from conflicting with each other.
            real_func = types.FunctionType(
                getattr(real_func, FUNC_CODE_ATTR),
                getattr(real_func, FUNC_GLOBALS_ATTR),
                self.func_name,
                getattr(real_func, FUNC_DEFAULTS_ATTR),
                getattr(real_func, FUNC_CLOSURE_ATTR))

            method_type_args = [real_func, self.owner]

            if pyver >= 3:
                method_type_args.append(self.owner)

            setattr(self.owner, self.func_name,
                    types.MethodType(real_func, self.owner))

        self._real_func = real_func

        if call_fake:
            assert callable(call_fake)
            self.func = call_fake
        elif call_original:
            self.func = self.orig_func
        else:
            self.func = None

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
        # the correct positional and keyword arguments). Python provides
        # a handy function to do most of this (inspect.formatargspec()).
        #
        # We do use different values for the default keyword arguments,
        # which is actually okay. Within the function, these will all be
        # set to a special value (_UNSET_ARG), which is used later for
        # determining which keyword arguments were provided and which
        # were not. Anything attempting to inspect this function with
        # getargspec will get the defaults from the original function,
        # by way of the original func.func_defaults attribute (on Python 2)
        # or __defaults__ (on Python 3).
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
        self._argspec = self._get_arg_spec(func)

        exec_locals = {}

        exec(
            'def forwarding_call(%(params)s):\n'
            '    from inspect import currentframe as _kgb_curframe\n'
            '    from kgb.spies import FunctionSpy as _kgb_cls\n'
            ''
            '    _kgb_frame = _kgb_curframe()\n'
            '    _kgb_spy = _kgb_cls._spy_map[%(spy_id)s]\n'
            '    _kgb_locals = locals()\n'
            ''
            '    exec("result = _kgb_spy(%%s)"\n'
            '         %% _kgb_spy._format_call_args(_kgb_frame),\n'
            '         {}, _kgb_locals)\n'
            '    return _kgb_locals["result"]\n'
            % {
                'params': self._format_arg_spec(),
                'spy_id': id(self),
            },
            globals(), exec_locals)

        forwarding_call = exec_locals['forwarding_call']

        assert forwarding_call is not None

        self._old_code = getattr(func, FUNC_CODE_ATTR)
        temp_code = getattr(forwarding_call, FUNC_CODE_ATTR)

        code_args = [temp_code.co_argcount]

        if pyver >= 3:
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
            self._old_code.co_name,
            temp_code.co_firstlineno,
            temp_code.co_lnotab,
            self._old_code.co_freevars,
            self._old_code.co_cellvars,
        ]

        new_code = types.CodeType(*code_args)
        setattr(real_func, FUNC_CODE_ATTR, new_code)
        assert self._old_code != new_code

        FunctionSpy._spy_map[id(self)] = self
        real_func.spy = self
        real_func.__dict__.update(copy.deepcopy(self._FUNC_ATTR_DEFAULTS))

        for proxy_func_name in self._PROXY_METHODS:
            assert not hasattr(real_func, proxy_func_name)
            setattr(real_func, proxy_func_name, getattr(self, proxy_func_name))

        if self.func is self.orig_func:
            # If we're calling the original function above, we need
            # to replace what we're calling with something that acts
            # like the original function. Otherwise, we'll just call
            # the forwarding_call above in an infinite loop.
            self.func = types.FunctionType(
                self._old_code,
                getattr(self.func, FUNC_GLOBALS_ATTR),
                self.func_name,
                getattr(self.func, FUNC_DEFAULTS_ATTR),
                getattr(self.func, FUNC_CLOSURE_ATTR))

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
        assert hasattr(self._real_func, 'spy')

        del FunctionSpy._spy_map[id(self)]
        del self._real_func.spy

        for attr_name in iterkeys(self._FUNC_ATTR_DEFAULTS):
            delattr(self._real_func, attr_name)

        for func_name in self._PROXY_METHODS:
            delattr(self._real_func, func_name)

        setattr(self._real_func, FUNC_CODE_ATTR, self._old_code)

        if self.owner is not None:
            setattr(self.owner, self.func_name, self.orig_func)

        if unregister:
            self.agency.spies.remove(self)

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

        call = SpyCall(record_args, kwargs)
        self._real_func.calls.append(call)
        self._real_func.called = True
        self._real_func.last_call = call

        if self.func is None:
            result = None
        else:
            try:
                result = self.func(*args, **kwargs)
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
        if self.func_type == self.TYPE_FUNCTION:
            func_type_str = 'function'
            qualname = self.func_name
        else:
            if self.func_type == self.TYPE_BOUND_METHOD:
                if self.owner.__class__ is type:
                    class_name = self.owner.__name__
                    func_type_str = 'classmethod'
                else:
                    class_name = self.owner.__class__.__name__
                    func_type_str = 'bound method'
            elif self.func_type == self.TYPE_UNBOUND_METHOD:
                class_name = self.owner.__name__
                func_type_str = 'unbound method'

            qualname = '%s.%s of %r' % (class_name, self.func_name, self.owner)

        call_count = len(self.calls)

        if call_count == 1:
            calls_str = 'call'
        else:
            calls_str = 'calls'

        return '<Spy for %s %s (%d %s)>' % (func_type_str, qualname,
                                            len(self.calls), calls_str)

    def _get_caller_pos_arg_counts(self, caller_frame):
        """Return the number of positional arguments from a caller.

        This will find out how many positional arguments were
        passed by the caller of a function. It does this by inspecting the
        bytecode of the call, which contains counts for the numbers of both
        types of arguments. For our usage, we only need the positional count.

        Args:
            caller_frame (frame):
                The latest frame of the caller of a function.

        Returns:
            int:
            The number of positional arguments.
        """
        num_args = caller_frame.f_code.co_code[caller_frame.f_lasti + 1]

        if pyver == 2:
            # In Python 2, this is represented as a character instead of an
            # integer.
            num_args = ord(num_args)

        if self.func_type in (self.TYPE_BOUND_METHOD,
                              self.TYPE_UNBOUND_METHOD):
            # The argument list is going to implicitly include "self", which
            # won't be shown as a positional argument in the frame above. We
            # have to manually factor this in here.
            num_args += 1

        return num_args

    def _format_call_args(self, frame):
        """Format arguments to pass in for forwarding a call.

        This takes the frame of the function being called and builds a string
        representing the positional and keyword arguments to pass in to a
        forwarded function. It does this by retrieving the number of
        positional and keyword arguments made when calling the forwarding
        function, figuring out which positional and keyword arguments those
        represent, and passing in the equivalent arguments in the forwarding
        call for use in the forwarded call.

        Args:
            frame (frame):
                The latest frame of the forwarding function.

        Returns:
            bytes:
            A string representing the arguments to pass when forwarding a call.
        """
        num_pos_args = self._get_caller_pos_arg_counts(frame.f_back)
        argspec = self._argspec
        func_args = argspec['args']
        f_locals = frame.f_locals

        keyword_args = func_args[num_pos_args:]

        if pyver >= 3:
            keyword_args += argspec['kwonly_args']

        result = func_args[:num_pos_args] + [
            '%s=%s' % (arg_name, arg_name)
            for arg_name in keyword_args
            if f_locals[arg_name] is not _UNSET_ARG
        ]

        if argspec['args_name']:
            result.append('*%s' % argspec['args_name'])

        if argspec['kwargs_name']:
            result.append('**%s' % argspec['kwargs_name'])

        return ', '.join(result)

    def _get_arg_spec(self, func):
        """Return the argument specification for a function.

        This will return some information on a function, depending on whether
        we're running on Python 2 or 3. The information consists of the list of
        arguments the function takes, the name of the ``*args`` and
        ``**kwargs`` arguments, and any default values for keyword arguments.
        If running on Python 3, the list of keyword-only arguments are also
        returned.

        Args:
            func (callable):
                The function to introspect.

        Returns:
            dict:
            A dictionary of information on the function.
        """
        if pyver == 2:
            argspec = inspect.getargspec(func)

            return {
                'args': argspec.args,
                'args_name': argspec.varargs,
                'kwargs_name': argspec.keywords,
                'defaults': argspec.defaults,
            }
        else:
            argspec = inspect.getfullargspec(func)

            return {
                'args': argspec.args,
                'args_name': argspec.varargs,
                'kwargs_name': argspec.varkw,
                'defaults': argspec.defaults,
                'kwonly_args': argspec.kwonlyargs,
                'kwonly_defaults': argspec.kwonlydefaults,
            }

    def _format_arg_spec(self):
        """Format the spied function's arguments for a new function definition.

        This will build a list of parameters for a function definition based on
        the argument specification found when introspecting a spied function.
        This consists of positional arguments, keyword arguments, and
        keyword-only arguments.

        Returns:
            unicode:
            A string representing an argument list for a function definition.
        """
        argspec = self._argspec
        kwargs = {
            'args': argspec['args'],
            'varargs': argspec['args_name'],
            'varkw': argspec['kwargs_name'],
            'defaults': argspec['defaults'],
            'formatvalue': lambda value: '=_UNSET_ARG',
        }

        if pyver >= 3:
            kwargs.update({
                'kwonlyargs': argspec['kwonly_args'],
                'kwonlydefaults': argspec['kwonly_defaults'],
            })

        return inspect.formatargspec(**kwargs)[1:-1]
