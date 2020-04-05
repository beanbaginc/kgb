"""A spy agency to manage spies."""

from __future__ import unicode_literals

from kgb.spies import FunctionSpy


class SpyAgency(object):
    """Manages spies.

    A SpyAgency can be instantiated or mixed into a
    :py:class:`unittest.TestCase` in order to provide spies.

    Every spy created through this agency will be tracked, and can be later
    be removed (individually or at once).

    Attributes:
        spies (set of kgb.spies.FunctionSpy):
            All spies currently registered with this agency.
    """

    def __init__(self, *args, **kwargs):
        """Initialize the spy agency.

        Args:
            *args (tuple):
                Positional arguments to pass on to any other class (if using
                this as a mixin).

            **kwargs (dict):
                Keyword arguments to pass on to any other class (if using
                this as a mixin).
        """
        super(SpyAgency, self).__init__(*args, **kwargs)

        self.spies = set()

    def tearDown(self):
        """Tear down a test suite.

        This is used when SpyAgency is mixed into a TestCase. It will
        automatically remove all spies when tearing down.
        """
        super(SpyAgency, self).tearDown()
        self.unspy_all()

    def spy_on(self, *args, **kwargs):
        """Spy on a function.

        By default, the spy will allow the call to go through to the original
        function. This can be disabled by passing ``call_original=False`` when
        initiating the spy. If disabled, the original function will never be
        called.

        This can also be passed a ``call_fake`` parameter pointing to another
        function to call instead of the original. If passed, this will take
        precedence over ``call_original``.

        See :py:class:`~kgb.spies.FunctionSpy` for more details on arguments.

        Args:
            *args (tuple):
                Positional arguments to pass to
                :py:class:`~kgb.spies.FunctionSpy`.

            **kwargs (dict):
                Keyword arguments to pass to
                :py:class:`~kgb.spies.FunctionSpy`.

        Returns:
            kgb.spies.FunctionSpy:
            The resulting spy.
        """
        spy = FunctionSpy(self, *args, **kwargs)
        self.spies.add(spy)
        return spy

    def unspy(self, func):
        """Stop spying on a function.

        Args:
            func (callable):
                The function to stop spying on.

        Raises:
            ValueError:
                The provided function was not spied on.
        """
        try:
            spy = func.spy
        except AttributeError:
            raise ValueError('Function %r has not been spied on.' % func)

        assert spy in self.spies

        spy.unspy()

    def unspy_all(self):
        """Stop spying on all functions tracked by this agency."""
        for spy in self.spies:
            spy.unspy(unregister=False)

        self.spies = []
