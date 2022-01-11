"""Call tracking and checks for spiess."""

from __future__ import unicode_literals

from kgb.pycompat import iteritems, text_type
from kgb.signature import FunctionSig
from kgb.utils import format_spy_kwargs


class SpyCall(object):
    """Records arguments made to a spied function call.

    SpyCalls are created and stored by a FunctionSpy every time it is
    called. They're accessible through the FunctionSpy's ``calls`` attribute.
    """

    def __init__(self, spy, args, kwargs):
        """Initialize the call.

        Args:
            spy (kgb.spies.FunctionSpy):
                The function spy that the call was made on.

            args (tuple):
                A tuple of positional arguments from the spy. These correspond
                to positional arguments in the function's signature.

            kwargs (dict):
                A dictionary of keyword arguments from the spy. These
                correspond to keyword arguments in the function's signature.
        """
        self.spy = spy
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

        pos_args = self.spy._sig.arg_names

        if self.spy.func_type in (FunctionSig.TYPE_BOUND_METHOD,
                                  FunctionSig.TYPE_UNBOUND_METHOD):
            pos_args = pos_args[1:]

        all_args = dict(zip(pos_args, self.args))
        all_args.update(self.kwargs)

        for key, value in iteritems(kwargs):
            if key not in all_args or all_args[key] != value:
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
        return '<SpyCall(args=%r, kwargs=%s, returned=%r, raised=%r)>' % (
            self.args, format_spy_kwargs(self.kwargs), self.return_value,
            self.exception)
