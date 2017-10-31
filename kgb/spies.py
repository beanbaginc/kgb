from __future__ import absolute_import

import inspect
import types


_UNSET_ARG = object()


class SpyCall(object):
    """Records arguments made to a spied function call.

    SpyCalls are created and stored by a FunctionSpy every time it is
    called. They're accessible through the FunctionSpy's ``calls`` attribute.
    """
    def __init__(self, args, kwargs):
        self.args = args
        self.kwargs = kwargs


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
    _code_maps = {}

    def __init__(self, agency, func, call_fake=None, call_original=True):
        assert callable(func)
        assert hasattr(func, 'func_name')
        assert hasattr(func, 'im_self') or hasattr(func, 'func_globals')

        self.agency = agency
        self.func_name = func.func_name
        self.orig_func = func
        self.calls = []
        self.owner = None
        self.spy = self
        self._argspec = None

        if call_fake:
            assert callable(call_fake)
            self.func = call_fake
        elif call_original:
            self.func = self.orig_func
        else:
            self.func = None

        if hasattr(func, 'im_self'):
            if func.im_self is not None:
                # This is a bound function on an instance of a class.
                self.owner = func.im_self
            else:
                # This is an unbound function on a class.
                self.owner = func.im_class

            setattr(self.owner, self.func_name, self)
        else:
            # Standard functions can't be replaced. Unlike a bound function,
            # we can't reliably figure out what dictionary it lives in (it
            # could be a locals() inside another function), and even if we
            # replace that, we can't replace all the copies that have been
            # imported up to this point.
            #
            # The only option is to change what happens when we call the
            # function. That's easier said than done. We can't just replace
            # the __call__ method on it, like you would a class.
            #
            # What we must do is replace the func_code backing it. This
            # must be done carefully. The "co_freevars" and "co_cellvars"
            # fields must remain the same between the old func_code and
            # the new one. The actual bytecode and most of the rest of
            # the fields can be taken from another function (the
            # "forwarding_call" function defined inline below).
            #
            # Unfortunately, we no longer have access to "self" (since we
            # replaced "co_freevars"). Instead, we store a global mapping
            # of func_codes to spies.
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
            # by way of the original func.func_defaults attribute.
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
            self._argspec = inspect.getargspec(func)

            # This is just to avoid a PyFlakes warning, since it doesn't know
            # about what's going on in that exec().
            forwarding_call = None

            exec(
                'def forwarding_call(%(params)s):\n'
                '    from inspect import currentframe as _kgb_curframe\n'
                '    from kgb.spies import FunctionSpy as _kgb_cls\n'
                ''
                '    _kgb_frame = _kgb_curframe()\n'
                '    _kgb_spy = _kgb_cls._code_maps[_kgb_frame.f_code]\n'
                ''
                '    exec("_kgb_result = _kgb_spy(%%s)"\n'
                '         %% _kgb_spy._format_call_args(_kgb_frame))\n'
                '    return _kgb_result'
                % {
                    'params': inspect.formatargspec(
                        formatvalue=lambda value: '=_UNSET_ARG',
                        *self._argspec)[1:-1],
                }
            )

            self._old_code = func.func_code
            temp_code = forwarding_call.func_code
            new_code = types.CodeType(temp_code.co_argcount,
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
                                      self._old_code.co_cellvars)
            FunctionSpy._code_maps[new_code] = self

            func.spy = self
            func.func_code = new_code
            assert self._old_code != new_code

            if self.func is self.orig_func:
                # If we're calling the original function above, we need
                # to replace what we're calling with something that acts
                # like the original function. Otherwise, we'll just call
                # the forwarding_call above in an infinite loop.
                self.func = types.FunctionType(self._old_code,
                                               self.func.func_globals,
                                               self.func.func_name,
                                               self.func.func_defaults,
                                               self.func.func_closure)

    @property
    def __class__(self):
        """Return a suitable class name for this spy.

        This is used to fool :py:func:`isinstance` into thinking this spy is
        a method, when representing an instance method. This is needed in
        order to allow functions like :py:func:`inspect.getargspec` to work
        on Python 2.x and 3.x.

        Standard functions do not need a simulated type, since the functions
        themselves are not replaced by an instance of the spy.

        Returns:
            type:
            :py:data:`types.MethodType`, if representing a bound method.
            Otherwise, it's the actual class of the spy.
        """
        if self.owner is not None:
            return types.MethodType

        return FunctionSpy

    @property
    def called(self):
        """Returns whether or not the spy was ever called."""
        return len(self.calls) > 0

    @property
    def last_call(self):
        """Returns the last call made to this function.

        If this function hasn't been called yet, this will return None.
        """
        if self.calls:
            return self.calls[-1]

        return None

    def unspy(self, unregister=True):
        """Removes the spy from the function, restoring the original.

        The spy will, by default, be removed from the registry's
        list of spies. This can be disabled by passing unregister=False,
        but don't do that. That's for internal use.
        """
        if hasattr(self.orig_func, 'im_self'):
            setattr(self.owner, self.func_name, self.orig_func)
        else:
            assert hasattr(self.orig_func, 'spy')
            del FunctionSpy._code_maps[self.orig_func.func_code]
            del self.orig_func.spy
            self.orig_func.func_code = self._old_code

        if unregister:
            self.agency.spies.remove(self)

    def called_with(self, *args, **kwargs):
        """Returns whether the spy was ever called with the given arguments."""
        for call in self.calls:
            if call.args == args and call.kwargs == kwargs:
                return True

        return False

    def last_called_with(self, *args, **kwargs):
        """Returns whether the spy was last called with the given arguments."""
        call = self.last_call

        if call and call.args == args and call.kwargs == kwargs:
            return True

        return False

    def reset_calls(self):
        """Resets the list of calls recorded by this spy."""
        self.calls = []

    def __call__(self, *args, **kwargs):
        """Calls the function.

        The call will be recorded.

        If the spy was set to call the original function or a fake function,
        the function will be called.
        """
        self.calls.append(SpyCall(args, kwargs))

        if self.func is None:
            return None
        elif (self.func is not self.orig_func and
              hasattr(self.orig_func, 'im_self')):
            return self.func.__call__(self.owner, *args, **kwargs)
        else:
            return self.func(*args, **kwargs)

    def __getattr__(self, name):
        """Return an attribute from the function.

        Any attributes being fetched that aren't part of the spy will be
        fetched from the function itself. This includes variables like
        ``im_self`` and ``func_code``.

        This only supports instance methods, since standard functions are
        still functions and won't go through a spy for attribute lookups.

        Args:
            name (unicode):
                The name of the attribute to return.

        Returns:
            object:
            The resulting attribute.

        Raises:
            AttributeError:
                The attribute was not found.
        """
        if self.owner is None:
            try:
                return self.__dict__[name]
            except KeyError:
                raise AttributeError(name)

        return getattr(self.orig_func, name)

    def __repr__(self):
        if hasattr(self.orig_func, 'im_self'):
            if hasattr(self.owner, '__name__'):
                class_name = self.owner.__name__
                method_type = 'classmethod'
            else:
                class_name = self.owner.__class__.__name__
                method_type = 'bound method'

            return '<Spy for %s %s.%s of %r>' % (method_type, class_name,
                                                 self.func_name, self.owner)
        else:
            return '<Spy for %s>' % self.func_name

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
        return ord(caller_frame.f_code.co_code[caller_frame.f_lasti + 1])

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
        func_args = argspec.args
        f_locals = frame.f_locals

        result = func_args[:num_pos_args] + [
            '%s=%s' % (arg_name, arg_name)
            for arg_name in func_args[num_pos_args:]
            if f_locals[arg_name] is not _UNSET_ARG
        ]

        if argspec.varargs:
            result.append('*%s' % argspec.varargs)

        if argspec.keywords:
            result.append('**%s' % argspec.keywords)

        return ', '.join(result)
