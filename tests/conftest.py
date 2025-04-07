"""Pytest configuration for the project."""

from pytest_asyncio.plugin import _DEFAULT_FIXTURE_LOOP_SCOPE_UNSET


# Set default fixture scope for asyncio
def pytest_configure(config):
    config.option.asyncio_default_fixture_loop_scope = "function"

    # Disable the deprecation warning about asyncio_default_fixture_loop_scope
    import warnings
    warnings.filterwarnings("ignore", message=_DEFAULT_FIXTURE_LOOP_SCOPE_UNSET)
