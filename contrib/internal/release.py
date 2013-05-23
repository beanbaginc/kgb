#!/usr/bin/env python
#
# Performs a release of kgb. This can only be run by the core developers with
# release permissions.
#

import os
import re
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from kgb import __version__, __version_info__, is_release


PY_VERSIONS = ['2.5', '2.6', '2.7']

LATEST_PY_VERSION = PY_VERSIONS[-1]

PACKAGE_NAME = 'kgb'


def execute(cmdline):
    print ">>> %s" % cmdline

    if os.system(cmdline) != 0:
        sys.stderr.write('!!! Error invoking command.\n')
        sys.exit(1)


def run_setup(target, pyver=LATEST_PY_VERSION):
    execute("python%s ./setup.py release %s" % (pyver, target))


def build_targets():
    for pyver in PY_VERSIONS:
        run_setup("bdist_egg upload", pyver)

    run_setup("sdist upload")


def register_release():
    run_setup("register")


def main():
    if not os.path.exists("setup.py"):
        sys.stderr.write("This must be run from the root of the kgb tree.\n")
        sys.exit(1)

    if not is_release():
        sys.stderr.write('This has not been marked as a release in '
                         'kgb/__init__.py\n')
        sys.exit(1)

    register_release()
    build_targets()


if __name__ == "__main__":
    main()
