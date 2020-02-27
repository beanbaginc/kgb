"""Python compatibility functions and types."""

from __future__ import unicode_literals

import sys


pyver = sys.version_info[:2]

if pyver[0] == 2:
    text_type = unicode

    def iterkeys(d):
        return d.iterkeys()

    def iteritems(d):
        return d.iteritems()
else:
    text_type = str

    def iterkeys(d):
        return iter(d.keys())

    def iteritems(d):
        return iter(d.items())
