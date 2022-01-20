"""Pytest plugin for kgb.

Version Added:
    7.0
"""

from __future__ import unicode_literals

import pytest

from kgb import SpyAgency


@pytest.fixture
def spy_agency():
    """Provide a KGB spy agency to a Pytest unit test.

    Yields:
        kgb.SpyAgency:
        The spy agency.
    """
    agency = SpyAgency()

    try:
        yield agency
    finally:
        agency.unspy_all()
