"""Re-export the Phase 8.4 INFRA-01..04 fixtures from conftest_infra so the
puller tests under tests/unit_tests/scripts/ can use `in_memory_logger` and
`sample_trade` without duplicating definitions.

Mirrors the same re-export pattern in tests/v3_intelligence/conftest.py:57-64.
Pytest only auto-discovers files literally named conftest.py, so each test
directory that wants the fixtures needs its own conftest.py importing them.
"""
from tests.v3_intelligence.conftest_infra import (  # noqa: F401
    in_memory_logger,
    sample_trade,
)
