"""Full-report regression fixtures (CLAUDE.md section 31.4).

A failure means the canonical output changed. If the change is intended,
regenerate with ``python scripts/update_golden.py`` and review the diff.
"""

from __future__ import annotations

import json
import math
from typing import Any

import pytest

from tests.golden.cases import GOLDEN_DIR, build_case, case_names

pytestmark = pytest.mark.golden


def assert_same(actual: Any, expected: Any, path: str = "$") -> None:
    if isinstance(expected, float) and isinstance(actual, float):
        assert math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-12), (
            f"{path}: {actual!r} != {expected!r}"
        )
    elif isinstance(expected, dict):
        assert isinstance(actual, dict), path
        assert set(actual) == set(expected), f"{path}: keys differ {set(actual) ^ set(expected)}"
        for key in expected:
            assert_same(actual[key], expected[key], f"{path}.{key}")
    elif isinstance(expected, list):
        assert isinstance(actual, list) and len(actual) == len(expected), path
        for i, (a, e) in enumerate(zip(actual, expected, strict=True)):
            assert_same(a, e, f"{path}[{i}]")
    else:
        assert actual == expected, f"{path}: {actual!r} != {expected!r}"


@pytest.mark.parametrize("name", case_names())
def test_golden_report(name: str) -> None:
    path = GOLDEN_DIR / f"{name}.json"
    expected = json.loads(path.read_text(encoding="utf-8"))
    actual = json.loads(build_case(name).to_json())
    # The package version may change without changing results.
    expected["provenance"].pop("package_version")
    actual["provenance"].pop("package_version")
    assert_same(actual, expected)
