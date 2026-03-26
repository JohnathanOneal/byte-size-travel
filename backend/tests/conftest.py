import sqlite3

import pytest
from fastapi.testclient import TestClient

from bst.db import create_schema, get_connection
from bst.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def db() -> sqlite3.Connection:
    conn = get_connection(":memory:")
    create_schema(conn)
    yield conn
    conn.close()


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--network",
        action="store_true",
        default=False,
        help="run tests that require network access",
    )
    parser.addoption(
        "--ai",
        action="store_true",
        default=False,
        help="run tests that call the OpenAI API",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    for mark_name in ("network", "ai"):
        if config.getoption(f"--{mark_name}"):
            continue
        skip = pytest.mark.skip(reason=f"needs --{mark_name} option to run")
        for item in items:
            if mark_name in item.keywords:
                item.add_marker(skip)
