import types


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

        if call_fake:
            assert callable(call_fake)
            self.func = call_fake
        elif call_original:
            self.func = self.orig_func
        else:
            self.func = None

        if hasattr(func, 'im_self'):
            if func.im_self:
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
            # The result is that we've completely hijacked the original
            # function, making it call our own forwarding function instead.
            # It's a wonderful trick that is fully legal, but really dirty.
            # Somehow, it really fits in with the idea of spies, though.
            def forwarding_call(*args, **kwargs):
                from inspect import currentframe
                from kgb.spies import FunctionSpy

                code = currentframe().f_code

                return FunctionSpy._code_maps[code](*args, **kwargs)

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
