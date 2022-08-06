from __future__ import unicode_literals

from kgb.agency import SpyAgency
from kgb.contextmanagers import spy_on
from kgb.ops import (SpyOpMatchAny,
                     SpyOpMatchInOrder,
                     SpyOpRaise,
                     SpyOpRaiseInOrder,
                     SpyOpReturn,
                     SpyOpReturnInOrder)


# The version of kgb
#
# This is in the format of:
#
#   (Major, Minor, Micro, alpha/beta/rc/final, Release Number, Released)
#
VERSION = (7, 1, 1, 'final', 0, True)


def get_version_string():
    """Return the kgb version as a human-readable string.

    Returns:
        unicode:
        The kgb version.
    """
    version = '%s.%s' % (VERSION[0], VERSION[1])

    if VERSION[2]:
        version += ".%s" % VERSION[2]

    if VERSION[3] != 'final':
        if VERSION[3] == 'rc':
            version += ' RC%s' % VERSION[4]
        else:
            version += ' %s %s' % (VERSION[3], VERSION[4])

    if not is_release():
        version += " (dev)"

    return version


def get_package_version():
    """Return the kgb version as a Python package version string.

    Returns:
        unicode:
        The kgb package version.
    """
    version = '%s.%s' % (VERSION[0], VERSION[1])

    if VERSION[2]:
        version += '.%s' % VERSION[2]

    tag = VERSION[3]

    if tag != 'final':
        if tag == 'alpha':
            tag = 'a'
        elif tag == 'beta':
            tag = 'b'

        version = '%s%s%s' % (version, tag, VERSION[4])

    return version


def is_release():
    """Return whether this is a released version of kgb.

    Returns:
        bool:
        ``True`` if the version is released. ``False`` if it is still in
        development.
    """
    return VERSION[5]


__version_info__ = VERSION[:-1]
__version__ = get_package_version()


__all__ = [
    '__version__',
    '__version_info__',
    'SpyAgency',
    'SpyOpMatchAny',
    'SpyOpMatchInOrder',
    'SpyOpRaise',
    'SpyOpRaiseInOrder',
    'SpyOpReturn',
    'SpyOpReturnInOrder',
    'VERSION',
    'get_package_version',
    'get_version_string',
    'is_release',
    'spy_on',
]
