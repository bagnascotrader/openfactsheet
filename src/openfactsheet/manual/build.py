"""Compile the reference manual with Typst (decision 0034).

Needs the ``docs`` extra (``pip install openfactsheet[docs]``) and a source
checkout: the template, the vendored Typst packages and the Markdown documents
live in the repository, not in the installed package. The build never uses the
network or system fonts: packages come from ``docs/manual/packages`` and fonts
are the ones embedded in Typst, so the same sources give the same PDF.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openfactsheet.manual.export import manual_data, prepare_markdown

TEMPLATE = "openfactsheet-manual.typ"
MANUAL_DIR = "docs/manual"


class ManualBuildError(RuntimeError):
    """The manual did not compile, or lacks a topic's named destination."""


@dataclass(frozen=True)
class BuildResult:
    path: Path
    pages: int
    anchors: frozenset[str]
    date: str


def expected_anchors(data: dict[str, Any]) -> set[str]:
    """Named destinations the manual must contain: every metric, API topic and document."""
    anchors = {m["anchor"] for m in data["metrics"]["metrics"]}
    anchors |= {f"category-{c['id']}" for c in data["metrics"]["categories"]}
    for topic in data["api"]["topics"]:
        anchors.add(topic["anchor"])
        anchors |= {c["anchor"] for c in topic.get("classes", []) + topic.get("constants", [])}
    anchors |= {d["anchor"] for d in data["documents"]["documents"]}
    anchors |= {e["anchor"] for e in data["bibliography"]["entries"]}
    anchors |= {
        "part-overview",
        "part-api",
        "part-metrics",
        "part-methodology",
        "part-decisions",
        "part-validation",
        "bibliography",
        "topic-index",
    }
    return anchors


def source_date(root: Path) -> int:
    """Build timestamp: ``SOURCE_DATE_EPOCH``, else the last commit's time, else 0.

    A fixed timestamp keeps the PDF reproducible; the commit time dates the
    manual by the sources it documents rather than by when it was compiled.
    """
    if os.environ.get("SOURCE_DATE_EPOCH"):
        return int(os.environ["SOURCE_DATE_EPOCH"])
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%ct"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        return int(out)
    except (OSError, subprocess.CalledProcessError, ValueError):
        return 0


def stage(root: Path, build_dir: Path) -> dict[str, Any]:
    """Write the template, generated data and prepared documents to ``build_dir``."""
    src = root / MANUAL_DIR
    shutil.copy2(src / TEMPLATE, build_dir / TEMPLATE)
    shutil.copytree(src / "lib", build_dir / "lib", dirs_exist_ok=True)
    data = manual_data(root)
    (build_dir / "data").mkdir(exist_ok=True)
    for name, obj in data.items():
        (build_dir / "data" / f"{name}.json").write_text(
            json.dumps(obj, ensure_ascii=False), encoding="utf-8"
        )
    (build_dir / "md").mkdir(exist_ok=True)
    repository = data["package"]["urls"]["Homepage"]
    for doc in data["documents"]["documents"]:
        (build_dir / "md" / f"{doc['anchor']}.md").write_text(
            prepare_markdown(root, doc, repository), encoding="utf-8"
        )
    return data


def build_manual(root: Path, output: Path) -> BuildResult:
    """Compile the manual to ``output`` and verify every expected named destination."""
    import typst
    from pypdf import PdfReader

    timestamp = source_date(root)
    date = dt.datetime.fromtimestamp(timestamp, tz=dt.timezone.utc).date().isoformat()
    with tempfile.TemporaryDirectory(prefix="ofs-manual-") as tmp:
        build_dir = Path(tmp)
        data = stage(root, build_dir)
        output.parent.mkdir(parents=True, exist_ok=True)
        try:
            typst.compile(
                str(build_dir / TEMPLATE),
                output=str(output),
                root=str(build_dir),
                package_path=str(root / MANUAL_DIR / "packages"),
                ignore_system_fonts=True,
                timestamp=timestamp,
                pdf_standards=["a-2b"],
                sys_inputs={"date": date, "typst": _typst_version()},
            )
        except typst.TypstError as exc:
            # The diagnostic names the file, line and column; keep the staged
            # sources' names so the location can be traced back.
            raise ManualBuildError(getattr(exc, "diagnostic", None) or str(exc)) from exc
    reader = PdfReader(output)
    anchors = frozenset(reader.named_destinations)
    missing = expected_anchors(data) - anchors
    if missing:
        raise ManualBuildError(f"Manual is missing named destinations: {sorted(missing)}")
    return BuildResult(path=output, pages=len(reader.pages), anchors=anchors, date=date)


def _typst_version() -> str:
    from importlib.metadata import version

    return version("typst")
