from __future__ import unicode_literals

import re
import sys

if sys.version_info[:2] >= (2, 7):
    import unittest
else:
    import unittest2 as unittest

from kgb.agency import SpyAgency


class MathClass(object):
    def do_math(self, a=1, b=2, *args, **kwargs):
        return a + b

    def do_math_pos(self, a, b):
        return a + b

    def do_math_mixed(self, a, b=2, *args, **kwargs):
        return a + b

    @classmethod
    def class_do_math(cls, a=2, b=5, *args, **kwargs):
        return a * b

    @classmethod
    def class_do_math_pos(cls, a, b):
        return a * b


class TestCase(unittest.TestCase):
    """Base class for test cases for kgb."""

    ws_re = re.compile(r'\s+')

    def setUp(self):
        self.agency = SpyAgency()
        self.orig_class_do_math = MathClass.class_do_math

    def tearDown(self):
        MathClass.class_do_math = self.orig_class_do_math
        self.agency.unspy_all()

    def shortDescription(self):
        """Return the description of the current test.

        This changes the default behavior to replace all newlines with spaces,
        allowing a test description to span lines. It should still be kept
        short, though.

        Returns:
            bytes:
            The description of the test.
        """
        doc = self._testMethodDoc

        if doc is not None:
            doc = doc.split('\n\n', 1)[0]
            doc = self.ws_re.sub(' ', doc).strip()

        return doc
