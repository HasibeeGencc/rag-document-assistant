"""Smoke test: proves the package imports and pytest is wired up."""


def test_app_package_imports():
    import app

    assert app.__doc__
