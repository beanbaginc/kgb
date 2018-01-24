from __future__ import unicode_literals

import traceback


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

    def __init__(self, spy, func, func_argspec, incompatible_func,
                 incompatible_func_argspec):
        """Initialize the error.

        Args:
            func (callable):
                The function containing the original signature.

            incompatible_func (callable):
                The function that was not compatible.
        """
        super(IncompatibleFunctionError, self).__init__(
            'The function signature of %r (%s) is not compatible with %r (%s).'
            % (incompatible_func,
               spy._format_arg_spec(incompatible_func_argspec),
               func,
               spy._format_arg_spec(func_argspec)))
