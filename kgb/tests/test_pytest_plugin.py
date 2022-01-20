"""Unit tests for kgb.pytest_plugin.

Version Added:
    7.0
"""

from __future__ import unicode_literals

from kgb.agency import SpyAgency
from kgb.tests.base import MathClass


def test_pytest_plugin(spy_agency):
    """Testing pytest spy_agency fixture"""
    assert isinstance(spy_agency, SpyAgency)

    obj = MathClass()

    spy = spy_agency.spy_on(obj.do_math)
    assert spy_agency.spies == {spy}
