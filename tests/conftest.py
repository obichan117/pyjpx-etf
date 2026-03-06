from unittest.mock import patch

import pytest

from pyjpx_etf.config import config as _config


@pytest.fixture(autouse=True)
def _isolate_db(request, tmp_path):
    """Prevent unit tests from reading real DB and auto-sync.

    Skipped for integration tests which need real DB access.
    """
    if "integration" in request.keywords:
        yield
        return

    import pyjpx_etf.etf as _etf_mod

    original = _config.db_path
    _config.db_path = tmp_path / "no-such.db"
    _etf_mod._db_checked = False
    with patch.object(_etf_mod, "_ensure_db"):
        yield
    _config.db_path = original
    _etf_mod._db_checked = False


def pytest_addoption(parser):
    parser.addoption(
        "--integration", action="store_true", default=False, help="run integration tests"
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--integration"):
        return
    skip = pytest.mark.skip(reason="need --integration option to run")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip)
