"""Spy-related errors."""

from __future__ import unicode_literals

import traceback


class InternalKGBError(Exception):
    """An internal error about the inner workings of KGB."""

    def __init__(self, msg):
        """Initialize the error.

        Args:
            msg (unicode):
                The message to display. A general message about contacting
                support will be appended to this.
        """
        super(InternalKGBError, self).__init__(
            '%s\n\n'
            'This is an internal error in KGB. Please report it!'
            % msg)


class ExistingSpyError(ValueError):
    """An error for when an existing spy was found on a function.

    This will provide a helpful error message explaining what went wrong,
    showing a backtrace of the original spy's setup in order to help diagnose
    the problem.
    """

    def __init__(self, func):
        """Initialize the error.

        Args:
            func (callable):
                The function containing an existing spy.
        """
        super(ExistingSpyError, self).__init__(
            'The function %(func)r has already been spied on. Here is where '
            'that spy was set up:\n\n'
            '%(stacktrace)s\n'
            'You may have encountered a crash in that test preventing the '
            'spy from being unregistered. Try running that test manually.'
            % {
                'func': func,
                'stacktrace': ''.join(traceback.format_stack(
                    func.spy.init_frame.f_back)[-4:]),
            })


class IncompatibleFunctionError(ValueError):
    """An error for when a function signature is incompatible.

    This is used for the ``call_fake`` function passed in when setting up a
    spy.
    """

    def __init__(self, func, func_sig, incompatible_func,
                 incompatible_func_sig):
        """Initialize the error.

        Args:
            func (callable):
                The function containing the original signature.

            func_sig (kgb.signature.FunctionSig):
                The signature of ``func``.

            incompatible_func (callable):
                The function that was not compatible.

            incompatible_func_sig (kgb.signature.FunctionSig):
                The signature of ``incompatible_func``.
        """
        super(IncompatibleFunctionError, self).__init__(
            'The function signature of %r (%s) is not compatible with %r (%s).'
            % (incompatible_func,
               incompatible_func_sig.format_arg_spec(),
               func,
               func_sig.format_arg_spec()))


class UnexpectedCallError(AssertionError):
    """A call was made to a spy that was not expected."""
