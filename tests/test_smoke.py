"""Smoke tests for the apron_scim package skeleton."""

import apron_scim


def test_package_imports():
    assert apron_scim.__name__ == "apron_scim"


def test_scim_error_is_exported():
    assert issubclass(apron_scim.ScimError, Exception)
