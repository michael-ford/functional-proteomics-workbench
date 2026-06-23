from datetime import UTC, datetime

import pytest


@pytest.fixture
def utc_now() -> datetime:
    return datetime(2026, 6, 23, 12, 0, tzinfo=UTC)


@pytest.fixture
def ulid() -> str:
    return "01KVTZB2476W9E04JG7NFWHRNY"
