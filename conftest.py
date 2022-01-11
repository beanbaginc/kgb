"""Configures pytest for kgb.

This will conditionally ignore Python 3 test files on Python 2.
"""

from __future__ import unicode_literals

import sys


if sys.version_info[0] < 3:
    collect_ignore_glob = ['kgb/tests/py3/*']
