#!/usr/bin/env python
from __future__ import print_function, unicode_literals

import os
import sys

import pytest


if __name__ == '__main__':
    print('This is deprecated! Please run pytest instead.')
    print()
    os.chdir(os.path.join(os.path.dirname(__file__), '..'))
    sys.exit(pytest.main(sys.argv[1:]))
