"""Generated documentation must match the registry (CLAUDE.md section 35: no drift)."""

from __future__ import annotations

from pathlib import Path

from openfactsheet.manual.export import render_manual_data
from openfactsheet.metrics.catalog_docs import render_all
from openfactsheet.metrics.registry import all_metrics

ROOT = Path(__file__).resolve().parents[2]


def test_generated_docs_are_up_to_date() -> None:
    files = {**render_all(), **render_manual_data(ROOT)}
    stale = [
        rel
        for rel, content in files.items()
        if not (ROOT / rel).exists() or (ROOT / rel).read_text(encoding="utf-8") != content
    ]
    assert not stale, f"Run `python scripts/generate_docs.py`; stale: {stale}"


def test_every_metric_has_a_page_answering_all_twelve_questions() -> None:
    files = render_all()
    for d in all_metrics():
        page = files[f"docs/interpretation/{d.id}.md"]
        for n in range(1, 13):
            assert f"## {n}. " in page, (d.id, n)
