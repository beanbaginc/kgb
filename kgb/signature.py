"""Function signature introspection and code generation."""

from __future__ import unicode_literals

import inspect
import logging
import sys
import types

from kgb.errors import InternalKGBError
from kgb.utils import get_defined_attr_value


logger = logging.getLogger('kgb')


class _UnsetArg(object):
    """Internal class for representation unset arguments on functions."""

    def __repr__(self):
        """Return a string representation of this object.

        Returns:
            unicode:
            ``_UNSET_ARG``.
        """
        return '_UNSET_ARG'


_UNSET_ARG = _UnsetArg()


class BaseFunctionSig(object):
    """Base class for a function signature introspector.

    This is responsible for taking a function (and a user-requested owner)
    and determining the actual owner, function type, function name, and
    arguments. It's also responsible for generating code that can be used
    to help define functions or perform calls, for use in spy code generation.

    How this is all done depends entirely on the version of Python. Subclasses
    must implement all this logic.

    Version Changed:
        5.0:
        Added support for the following attributes:

        * :py:attr:`defined_func`.
        * :py:attr:`has_getter`.
        * :py:attr:`has_setter`.
        * :py:attr:`is_slippery`.

    Attributes:
        defined_func (callable or object):
            The actual function (or wrapping object) that's defined on
            somewhere in the owner's class hierarchy (or the function itself if
            this is a standalone function). This may differ from
            :py:attr:`func`.

        has_getter (bool):
            Whether this signature represents a descriptor with a ``__get__``
            method.

        has_setter (bool):
            Whether this signature represents a descriptor with a ``__set__``
            method.

        is_slippery (bool):
            Whether this represents a slippery function. This is a method on
            a class that returns a different function every time its attribute
            is accessed on an instance.

            This occurs when a method decorator is used that wraps a function
            on access and returns the wrapper function, but does not cache the
            wrapper function. These are returned as standard functions and
            not methods.

            Slippery functions can only be detected when an explicit owner is
            provided.
    """

    #: The signature represents a standard function.
    TYPE_FUNCTION = 0

    #: The signature represents a bound method.
    #:
    #: Bound methods are functions on an instance of a class, or classmethods.
    TYPE_BOUND_METHOD = 1

    #: The signature represents an unbound method.
    #:
    #: Unbound methods are standard methods on a class.
    TYPE_UNBOUND_METHOD = 2

    def __init__(self, func, owner=_UNSET_ARG, func_name=None):
        """Initialize the signature.

        Subclasses must override this to parse function types/ownership and
        available arguments. They must call :py:meth:`finalize_state` once
        they've calculated all signature state.

        Args:
            func (callable):
                The function to use for the signature.

            owner (type or object, optional):
                The owning class, as provided when spying on the function.
                This is not stored directly (as it may be invalid), but can
                be used for informative purposes for subclasses.

            func_name (str, optional):
                An explicit name for the function. This will be used instead
                of the function's specified name, and is usually a sign of a
                bad decorator.

                Version Added:
                    7.0
        """
        self.func = func
        self.func_type = self.TYPE_FUNCTION
        self.func_name = func_name or getattr(func, self.FUNC_NAME_ATTR)
        self.owner = None

        if hasattr(func, '__func__'):
            # This is an instancemethod on a class. Grab the real function
            # from it.
            self.real_func = func.__func__
        else:
            self.real_func = func

        self.all_arg_names = []
        self.arg_names = []
        self.kwarg_names = []
        self.args_param_name = []
        self.kwargs_param_name = []
        self.is_slippery = False
        self.has_getter = False
        self.has_setter = False

    def is_compatible_with(self, other_sig):
        """Return whether two function signatures are compatible.

        This will check if the signature for a function (the ``call_fake``
        passed in, technically) is compatible with another (the spied
        function), to help ensure that unit tests with incompatible function
        signatures don't blow up with strange errors later.

        This will attempt to be somewhat flexible in what it considers
        compatible. Basically, so long as all the arguments passed in to
        the source function could be resolved using the argument list in the
        other function (taking into account things like positional argument
        names as keyword arguments), they're considered compatible.

        Args:
            other_sig (BaseFunctionSig):
                The other signature to check for compatibility with.

        Returns:
            bool:
            ``True`` if ``other_sig`` is considered compatible with this
            signature. ``False`` if it is not.
        """
        source_args_name = self.args_param_name
        compat_args_name = other_sig.args_param_name
        source_kwargs_name = self.kwargs_param_name
        compat_kwargs_name = other_sig.kwargs_param_name

        if compat_args_name and compat_kwargs_name:
            return True

        if ((source_args_name and not compat_args_name) or
            (source_kwargs_name and not compat_kwargs_name)):
            return False

        source_args = self.arg_names
        compat_args = other_sig.arg_names
        compat_all_args = set(other_sig.all_arg_names)
        compat_kwargs = set(other_sig.kwarg_names)

        if self.func_type in (self.TYPE_BOUND_METHOD,
                              self.TYPE_UNBOUND_METHOD):
            source_args = source_args[1:]
            compat_args = compat_args[1:]

        if (len(source_args) != len(compat_args) and
            ((len(source_args) < len(compat_args) and not source_args_name and
              not compat_kwargs.issuperset(source_args)) or
             (len(source_args) > len(compat_args) and not compat_args_name))):
            return False

        if (not compat_all_args.issuperset(self.kwarg_names) and
            not compat_kwargs_name):
            return False

        return True

    def format_forward_call_args(self):
        """Format arguments to pass in for forwarding a call.

        This will build a string for use in the forwarding call, which will
        pass every positional and keyword parameter defined for the function
        to forwarded function, along with the ``*args`` and ``**kwargs``,
        if specified.

        Returns:
            unicode:
            A string representing the arguments to pass when forwarding a call.
        """
        _format_arg = self.format_forward_call_arg

        # Build the list of positional and keyword arguments.
        result = [
            _format_arg(arg_name)
            for arg_name in self.arg_names
        ] + [
            '%s=%s' % (arg_name, _format_arg(arg_name))
            for arg_name in self.kwarg_names
        ]

        # Add the variable arguments.
        if self.args_param_name:
            result.append('*%s' % _format_arg(self.args_param_name))

        if self.kwargs_param_name:
            result.append('**%s' % _format_arg(self.kwargs_param_name))

        return ', '.join(result)

    def format_forward_call_arg(self, arg_name):
        """Return a string used to reference an argument in a forwarding call.

        Subclasses must implement this to return code the spy can use when
        generating a function to forward arguments in a call.

        Args:
            arg_name (unicode):
                The name of the argument.

        Returns:
            unicode:
            The string used to format the argument call.
        """
        raise NotImplementedError

    def format_arg_spec(self):
        """Format the function's arguments for a new function definition.

        This will build a list of parameters for a function definition based on
        the argument specification found when introspecting a spied function.
        This consists of all supported argument types for the version of
        Python.

        Returns:
            unicode:
            A string representing an argument list for a function definition.
        """
        raise NotImplementedError

    def finalize_state(self):
        """Finalize the state for the signature.

        This will set any remaining values for the signature based on the
        calculations already performed by the subclasses. This must be called
        at the end of a subclass's :py:meth:`__init__`.
        """
        if self.owner is None:
            self.defined_func = self.func
        else:
            try:
                self.defined_func = get_defined_attr_value(self.owner,
                                                           self.func_name)
            except AttributeError:
                # This was a dynamically-injected function. We won't find it
                # in the class hierarchy. Use the provided function instead.
                self.defined_func = self.func

        if not isinstance(self.defined_func, (types.FunctionType,
                                              types.MethodType,
                                              classmethod,
                                              staticmethod)):
            if hasattr(self.defined_func, '__get__'):
                self.has_getter = True

            if hasattr(self.defined_func, '__set__'):
                self.has_setter = True


class FunctionSigPy2(BaseFunctionSig):
    """Function signature introspector for Python 2.

    This supports introspecting functions and generating code for use in
    spies when running on Python 2.
    """

    FUNC_CLOSURE_ATTR = 'func_closure'
    FUNC_CODE_ATTR = 'func_code'
    FUNC_DEFAULTS_ATTR = 'func_defaults'
    FUNC_GLOBALS_ATTR = 'func_globals'
    FUNC_NAME_ATTR = 'func_name'
    METHOD_SELF_ATTR = 'im_self'

    def __init__(self, func, owner=_UNSET_ARG, func_name=None):
        """Initialize the signature.

        Subclasses must override this to parse function types/ownership and
        available arguments.

        Args:
            func (callable):
                The function to use for the signature.

            owner (type, optional):
                The owning class, as provided when spying on the function.
                The value is ignored for methods on which an owner can be
                calculated, favoring the calculated value instead.

            func_name (str, optional):
                An explicit name for the function. This will be used instead
                of the function's specified name, and is usually a sign of a
                bad decorator.

                Version Added:
                    7.0
        """
        super(FunctionSigPy2, self).__init__(func=func,
                                             owner=owner,
                                             func_name=func_name)

        func_name = self.func_name

        # Figure out the owner and method type.
        if inspect.ismethod(func):
            # This is a bound or unbound method. If it's unbound, and an
            # owner is not specified, we're going to need to warn the user,
            # since things are going to break on Python 3.
            #
            # Otherwise, we're going to determine the bound vs. unbound type
            # and use the owner specified by the method. (The provided owner
            # will be validated in FunctionSpy.)
            method_owner = func.im_self

            if method_owner is None:
                self.func_type = self.TYPE_UNBOUND_METHOD
                self.owner = func.im_class

                if owner is _UNSET_ARG:
                    logger.warning('Unbound method owners can easily be '
                                   'determined on Python 2.x, but not on '
                                   '3.x. Please pass owner= to spy_on() '
                                   'to set a specific owner for %r.',
                                   func)
            else:
                self.func_type = self.TYPE_BOUND_METHOD
                self.owner = method_owner
        elif owner is not _UNSET_ARG:
            # This is a standard function, but an owner (as an instance) has
            # been provided. Find out if the owner has this function (either
            # the actual instance or one with the same name and bytecode),
            # and if so, treat this as a bound method.
            #
            # This is necessary when trying to spy on a decorated method that
            # generates functions dynamically (using something like
            # functools.wraps). We call these "slippery functions." A
            # real-world example is something like Stripe's
            # stripe.Customer.delete() method, which is a different function
            # every time you call it.
            owner_func = getattr(owner, func_name, None)

            if (owner_func is not None and
                (owner_func is func or
                 owner_func.func_code is func.func_code)):
                if inspect.isclass(owner):
                    self.func_type = self.TYPE_UNBOUND_METHOD
                else:
                    self.func_type = self.TYPE_BOUND_METHOD

                self.owner = owner
                self.is_slippery = owner_func is not func

        # Load information on the arguments.
        argspec = inspect.getargspec(func)
        all_args = argspec.args
        defaults = argspec.defaults

        if all_args and defaults:
            num_defaults = len(defaults)
            keyword_args = all_args[-num_defaults:]
            pos_args = all_args[:-num_defaults]
        else:
            pos_args = all_args
            keyword_args = []

        self.all_arg_names = argspec.args
        self.arg_names = pos_args
        self.kwarg_names = keyword_args
        self.args_param_name = argspec.varargs
        self.kwargs_param_name = argspec.keywords
        self._defaults = argspec.defaults

        self.finalize_state()

    def format_forward_call_arg(self, arg_name):
        """Return a string used to reference an argument in a forwarding call.

        Args:
            arg_name (unicode):
                The name of the argument.

        Returns:
            unicode:
            The string used to format the argument call.
        """
        return arg_name

    def format_arg_spec(self):
        """Format the function's arguments for a new function definition.

        This will build a list of parameters for a function definition based on
        the argument specification found when introspecting a spied function.
        This consists of all positional arguments, keyword arguments, and the
        special ``*args`` and ``**kwargs`` arguments.

        Returns:
            unicode:
            A string representing an argument list for a function definition.
        """
        return inspect.formatargspec(
            args=self.all_arg_names,
            varargs=self.args_param_name,
            varkw=self.kwargs_param_name,
            defaults=self._defaults,
            formatvalue=lambda value: '=_UNSET_ARG')[1:-1]


class FunctionSigPy3(BaseFunctionSig):
    """Function signature introspector for Python 3.

    This supports introspecting functions and generating code for use in
    spies when running on Python 3.

    There are some differences in function capabilities between Python 3.x
    releases (such as the addition of positional-only keyword arguments).
    This class provides compatibility for all these versions, currently up
    through Python 3.8.
    """

    FUNC_CLOSURE_ATTR = '__closure__'
    FUNC_CODE_ATTR = '__code__'
    FUNC_DEFAULTS_ATTR = '__defaults__'
    FUNC_GLOBALS_ATTR = '__globals__'
    FUNC_NAME_ATTR = '__name__'
    METHOD_SELF_ATTR = '__self__'

    def __init__(self, func, owner=_UNSET_ARG, func_name=None):
        """Initialize the signature.

        Subclasses must override this to parse function types/ownership and
        available arguments.

        Args:
            func (callable):
                The function to use for the signature.

            owner (type, optional):
                The owning class, as provided when spying on the function.
                This is used only when spying on unbound or slippery methods.

            func_name (str, optional):
                An explicit name for the function. This will be used instead
                of the function's specified name, and is usually a sign of a
                bad decorator.

                Version Added:
                    7.0
        """
        super(FunctionSigPy3, self).__init__(func=func,
                                             owner=owner,
                                             func_name=func_name)

        if not hasattr(inspect, '_signature_from_callable'):
            raise InternalKGBError(
                'Python %s.%s does not have inspect._signature_from_callable, '
                'which is needed in order to generate a Signature from a '
                'function.'
                % sys.version_info[:2])

        func_name = self.func_name

        # Figure out the owner and method type.
        #
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
            self.owner = func.__self__
        elif '.' in func.__qualname__:
            if owner is not _UNSET_ARG:
                self.owner = owner

                try:
                    self.is_slippery = (
                        owner is not _UNSET_ARG and
                        getattr(owner, func_name) is not func
                    )
                except AttributeError:
                    if '<locals>' in func.__qualname__:
                        logger.warning(
                            "%r doesn't have a function named \"%s\". This "
                            "appears to be a decorator that doesn't "
                            "preserve function names. Try passing "
                            "func_name= when setting up the spy.",
                            owner, func_name)
                    else:
                        logger.warning(
                            "%r doesn't have a function named \"%s\". It's "
                            "not clear why this is. Try passing func_name= "
                            "when setting up the spy.",
                            owner, func_name)

                if owner is _UNSET_ARG or inspect.isclass(owner):
                    self.func_type = self.TYPE_UNBOUND_METHOD
                else:
                    self.func_type = self.TYPE_BOUND_METHOD
            elif '<locals>' in func.__qualname__:
                # We can only assume this is a function. It might not be.
                self.func_type = self.TYPE_FUNCTION
            else:
                real_func = self.real_func
                method_owner = inspect.getmodule(real_func)

                for part in real_func.__qualname__.split('.')[:-1]:
                    try:
                        method_owner = getattr(method_owner, part)
                    except AttributeError:
                        method_owner = None
                        break

                if method_owner is not None:
                    self.func_type = self.TYPE_UNBOUND_METHOD
                    self.owner = method_owner

                logger.warning('Determined the owner of %r to be %r, '
                               'but it may be wrong. Please pass '
                               'owner= to spy_on() to set a specific '
                               'owner.',
                               func, self.owner)

        # Load information on the arguments.
        sig = inspect._signature_from_callable(
            func,
            follow_wrapper_chains=False,
            skip_bound_arg=False,
            sigcls=inspect.Signature)

        all_args = []
        args = []
        kwargs = []

        for param in sig.parameters.values():
            kind = param.kind
            name = param.name

            if kind is param.POSITIONAL_OR_KEYWORD:
                # Standard arguments -- either positional or keyword.
                all_args.append(name)

                if param.default is param.empty:
                    args.append(name)
                else:
                    kwargs.append(name)
            elif kind is param.POSITIONAL_ONLY:
                # Positional-only arguments (Python 3.8+).
                all_args.append(name)
                args.append(name)
            elif kind is param.KEYWORD_ONLY:
                # Keyword-only arguments (Python 3+).
                kwargs.append(name)
            elif kind is param.VAR_POSITIONAL:
                # *args
                self.args_param_name = name
            elif kind is param.VAR_KEYWORD:
                # **kwargs
                self.kwargs_param_name = name

        self.all_arg_names = all_args
        self.arg_names = args
        self.kwarg_names = kwargs
        self._sig = sig

        self.finalize_state()

    def format_forward_call_arg(self, arg_name):
        """Return a string used to reference an argument in a forwarding call.

        Args:
            arg_name (unicode):
                The name of the argument.

        Returns:
            unicode:
            The string used to format the argument call.
        """
        # Starting in Python 3, something changed with variables. Due to
        # the way we generate the hybrid code object, we can't always
        # reference the local variables directly. Sometimes we can, but
        # other times we have to get them from locals(). We can't always
        # get them from there, though, so instead we conditionally check
        # both. This is wordy, but necessary.
        return '_kgb_l["%(arg)s"] if "%(arg)s" in _kgb_l else %(arg)s' % {
            'arg': arg_name,
        }

    def format_arg_spec(self):
        """Format the function's arguments for a new function definition.

        This will build a list of parameters for a function definition based on
        the argument specification found when introspecting a spied function.
        This consists of all positional arguments, positional-only arguments,
        keyword arguments, keyword-only arguments, and the special ``*args``
        and ``**kwargs`` arguments.

        Returns:
            unicode:
            A string representing an argument list for a function definition.
        """
        parameters = []

        # Make a copy of the Signature and its parameters, but leave out
        # all type annotations.
        for orig_param in self._sig.parameters.values():
            default = orig_param.default

            if (orig_param.kind is orig_param.POSITIONAL_OR_KEYWORD and
                default is not orig_param.empty):
                default = _UNSET_ARG

            parameters.append(inspect.Parameter(
                name=orig_param.name,
                kind=orig_param.kind,
                default=default))

        sig = inspect.Signature(parameters=parameters)

        return str(sig)[1:-1]


if sys.version_info[0] == 2:
    FunctionSig = FunctionSigPy2
elif sys.version_info[0] == 3:
    FunctionSig = FunctionSigPy3
else:
    raise Exception('Unsupported Python version')
