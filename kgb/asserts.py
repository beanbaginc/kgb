"""Independent assertion functions.

These assertion functions can be used in pytest or in other places where
:py:class:`kgb.SpyAgency` can't be mixed.

Version Added:
    7.0
"""

from __future__ import unicode_literals

from kgb.agency import SpyAgency


_agency = SpyAgency()

__all__ = []


for name in vars(SpyAgency):
    if name.startswith('assert_'):
        globals()[name] = getattr(_agency, name)
        __all__.append(name)
