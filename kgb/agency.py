from __future__ import unicode_literals

from kgb.spies import FunctionSpy


class SpyAgency(object):
    """Manages spies.

    A SpyAgency can be instantiated or mixed into a TestCase in order
    to provide spies.

    Every spy created through this agency will be tracked, and can be later
    be removed (individually or at once).
    """
    def __init__(self, *args, **kwargs):
        super(SpyAgency, self).__init__(*args, **kwargs)

        self.spies = set()

    def tearDown(self):
        """Tears down a test suite.

        This is used when SpyAgency is mixed into a TestCase. It will
        automatically remove all spies when tearing down.
        """
        super(SpyAgency, self).tearDown()
        self.unspy_all()

    def spy_on(self, *args, **kwargs):
        """Spies on a function.

        By default, the spy will allow the call to go through to the original
        function. This can be disabled by passing call_original=False when
        initiating the spy. If disabled, the original function will never be
        called.

        This can also be passed a call_fake parameter pointing to another
        function to call instead of the original. If passed, this will take
        precedence over call_original.

        The FunctionSpy for this spy is returned.
        """
        spy = FunctionSpy(self, *args, **kwargs)
        self.spies.add(spy)
        return spy

    def unspy(self, func):
        """Stops spying on a function."""
        try:
            spy = func.spy
        except AttributeError:
            raise ValueError('Function %r has not been spied on.' % func)

        assert spy in self.spies

        spy.unspy()

    def unspy_all(self):
        """Stops spying on all functions tracked by this agency."""
        for spy in self.spies:
            spy.unspy(unregister=False)

        self.spies = []
