"""Standalone context managers for working with spies."""

from __future__ import unicode_literals

from contextlib import contextmanager

from kgb.agency import SpyAgency


@contextmanager
def spy_on(*args, **kwargs):
    """Spy on a function.

    By default, the spy will allow the call to go through to the original
    function. This can be disabled by passing ``call_original=False`` when
    initiating the spy. If disabled, the original function will never be
    called.

    This can also be passed a ``call_fake`` parameter pointing to another
    function to call instead of the original. If passed, this will take
    precedence over ``call_original``.

    The spy will only remain throughout the duration of the context.

    See :py:class:`~kgb.spies.FunctionSpy` for more details on arguments.

    Args:
        *args (tuple):
            Positional arguments to pass to
            :py:class:`~kgb.spies.FunctionSpy`.

        **kwargs (dict):
            Keyword arguments to pass to
            :py:class:`~kgb.spies.FunctionSpy`.

    Context:
        kgb.spies.FunctionSpy:
        The newly-created spy.
    """
    agency = SpyAgency()
    spy = agency.spy_on(*args, **kwargs)

    try:
        yield spy
    finally:
        spy.unspy()
