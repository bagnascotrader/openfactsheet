"""Every decision rule in the code must be documented in docs/reference/criteria.md."""

from __future__ import annotations

import re
from pathlib import Path

from openfactsheet.interpretation.templates import RULES

ROOT = Path(__file__).resolve().parents[2]
CRITERIA = ROOT / "docs" / "reference" / "criteria.md"
SRC = ROOT / "src" / "openfactsheet"


def _finding_ids() -> set[str]:
    ids: set[str] = set()
    pattern = re.compile(r'DiagnosticFinding\(\s*"([a-z_]+)"')
    for path in SRC.rglob("*.py"):
        ids.update(pattern.findall(path.read_text(encoding="utf-8")))
    return ids


def test_finding_ids_are_discovered() -> None:
    assert len(_finding_ids()) >= 15


def test_every_diagnostic_finding_is_documented() -> None:
    text = CRITERIA.read_text(encoding="utf-8")
    missing = sorted(i for i in _finding_ids() if f"`{i}`" not in text)
    assert not missing, f"Document these diagnostic findings in criteria.md: {missing}"


def test_every_interpretation_rule_is_documented() -> None:
    text = CRITERIA.read_text(encoding="utf-8")
    missing = [rule.__name__ for rule in RULES if f"`{rule.__name__}`" not in text]
    assert not missing, f"Document these interpretation rules in criteria.md: {missing}"
