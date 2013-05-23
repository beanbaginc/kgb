#!/usr/bin/env python
import os
import sys

import nose


def run_tests():
    nose_argv = [
        'runtests.py',
        '-v',
        '--with-coverage',
        '--cover-package=kgb',
    ]

    if len(sys.argv) > 2:
        nose_argv += sys.argv[2:]

    nose.run(argv=nose_argv)


if __name__ == '__main__':
    os.chdir(os.path.join(os.path.dirname(__file__), '..', '..'))
    sys.path.insert(0, os.getcwd())
    run_tests()
