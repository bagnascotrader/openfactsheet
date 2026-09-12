"""Compile the reference manual with Typst (decision 0034).

Needs the ``docs`` extra (``pip install openfactsheet[docs]``) and a source
checkout: the template, the vendored Typst packages and the Markdown documents
live in the repository, not in the installed package. The build never uses the
network or system fonts: packages come from ``docs/manual/packages`` and fonts
are the ones embedded in Typst.

The PDF is committed (``docs/manual/openfactsheet-manual.pdf``). It carries the
SHA-256 digest of everything it was built from, in its keywords, so
:func:`check_committed` can tell whether it matches the current sources without
compiling anything and on any platform.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openfactsheet.manual.export import manual_data, prepare_markdown

TEMPLATE = "openfactsheet-manual.typ"
MANUAL_DIR = "docs/manual"
MANUAL_PDF = "docs/manual/openfactsheet-manual.pdf"
DIGEST_PREFIX = "openfactsheet-sources-sha256:"
# PDF/A needs a document date. An unreleased version has none, so its PDF carries
# the Unix epoch (1970-01-01) and its title page says "unreleased".
UNRELEASED_TIMESTAMP = 0
_TEXT_SUFFIXES = {".typ", ".md", ".toml", ".json", ".txt", ""}


class ManualBuildError(RuntimeError):
    """The manual did not compile, or lacks a topic's named destination."""


@dataclass(frozen=True)
class BuildResult:
    path: Path
    pages: int
    anchors: frozenset[str]
    date: str
    digest: str


@dataclass(frozen=True)
class Sources:
    """Everything the manual is built from, and its digest."""

    files: dict[str, bytes]  # staged path -> content (template, lib, data, documents)
    packages: dict[str, bytes]  # vendored Typst packages (used in place, not staged)
    data: dict[str, Any]
    date: str
    timestamp: int
    typst_version: str
    digest: str


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


def release_date(root: Path, version: str) -> str | None:
    """The version's release date from CHANGELOG.md (``## [0.1.0] — 2026-10-01``)."""
    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    m = re.search(
        rf"^## \[{re.escape(version)}\]\s*[—–-]\s*(\d{{4}}-\d{{2}}-\d{{2}})\s*$",
        changelog,
        re.MULTILINE,
    )
    return m.group(1) if m else None


def _date(root: Path, version: str) -> tuple[str, int]:
    """Displayed date and PDF timestamp: SOURCE_DATE_EPOCH, the release date, or unreleased.

    The date comes from the sources, never from the clock or git, so the same
    sources always give the same manual.
    """
    if os.environ.get("SOURCE_DATE_EPOCH"):
        ts = int(os.environ["SOURCE_DATE_EPOCH"])
        return dt.datetime.fromtimestamp(ts, tz=dt.timezone.utc).date().isoformat(), ts
    released = release_date(root, version)
    if released is None:
        return "unreleased", UNRELEASED_TIMESTAMP
    day = dt.datetime.strptime(released, "%Y-%m-%d").replace(tzinfo=dt.timezone.utc)
    return released, int(day.timestamp())


def _read(path: Path) -> bytes:
    content = path.read_bytes()
    # Text sources hash the same on every platform, whatever the checkout's line endings.
    return content.replace(b"\r\n", b"\n") if path.suffix in _TEXT_SUFFIXES else content


def _pinned_typst(data: dict[str, Any]) -> str:
    for requirement in data["package"]["extras"].get("docs", []):
        m = re.fullmatch(r"typst==([\w.]+)", requirement.replace(" ", ""))
        if m:
            return m.group(1)
    raise ManualBuildError("The docs extra must pin the Typst compiler exactly (typst==X.Y.Z).")


def collect_sources(root: Path) -> Sources:
    """Gather the manual's sources in memory and compute their digest."""
    src = root / MANUAL_DIR
    data = manual_data(root)
    files: dict[str, bytes] = {TEMPLATE: _read(src / TEMPLATE)}
    for path in sorted((src / "lib").rglob("*")):
        if path.is_file():
            files[f"lib/{path.relative_to(src / 'lib').as_posix()}"] = _read(path)
    for name, obj in data.items():
        files[f"data/{name}.json"] = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    repository = data["package"]["urls"]["Homepage"]
    for doc in data["documents"]["documents"]:
        files[f"md/{doc['anchor']}.md"] = prepare_markdown(root, doc, repository).encode("utf-8")
    packages = {
        p.relative_to(src / "packages").as_posix(): _read(p)
        for p in sorted((src / "packages").rglob("*"))
        if p.is_file()
    }
    typst_version = _pinned_typst(data)
    date, timestamp = _date(root, data["package"]["version"])

    h = hashlib.sha256()
    for label, group in (("file", files), ("package", packages)):
        for rel, content in sorted(group.items()):
            h.update(f"{label}:{rel}:{len(content)}\n".encode())
            h.update(content)
    h.update(f"date:{date}:{timestamp}\ntypst:{typst_version}\n".encode())
    return Sources(files, packages, data, date, timestamp, typst_version, h.hexdigest())


def committed_digest(pdf: Path) -> str | None:
    """The source digest recorded in a built manual, or ``None``."""
    from pypdf import PdfReader

    if not pdf.exists():
        return None
    metadata = PdfReader(pdf).metadata
    keywords = str(metadata.get("/Keywords", "")) if metadata is not None else ""
    m = re.search(re.escape(DIGEST_PREFIX) + r"([0-9a-f]{64})", keywords)
    return m.group(1) if m else None


def check_committed(root: Path) -> str | None:
    """``None`` when the committed PDF matches the sources, else what is wrong."""
    pdf = root / MANUAL_PDF
    recorded = committed_digest(pdf)
    if recorded is None:
        return f"{MANUAL_PDF} is missing or has no source digest."
    if recorded != collect_sources(root).digest:
        return f"{MANUAL_PDF} is stale: its sources changed since it was built."
    return None


def build_manual(root: Path, output: Path) -> BuildResult:
    """Compile the manual to ``output`` and verify every expected named destination."""
    import pikepdf
    import typst
    from pypdf import PdfReader

    sources = collect_sources(root)
    installed = _installed_typst()
    if installed != sources.typst_version:
        raise ManualBuildError(
            f"Typst {sources.typst_version} is required (installed: {installed}); "
            'run pip install -e ".[docs]".'
        )
    with tempfile.TemporaryDirectory(prefix="ofs-manual-") as tmp:
        build_dir = Path(tmp)
        for rel, content in sources.files.items():
            (build_dir / rel).parent.mkdir(parents=True, exist_ok=True)
            (build_dir / rel).write_bytes(content)
        raw = build_dir / "raw.pdf"
        try:
            typst.compile(
                str(build_dir / TEMPLATE),
                output=str(raw),
                root=str(build_dir),
                package_path=str(root / MANUAL_DIR / "packages"),
                ignore_system_fonts=True,
                timestamp=sources.timestamp,
                pdf_standards=["a-2b"],
                sys_inputs={
                    "date": sources.date,
                    "typst": sources.typst_version,
                    "digest": sources.digest,
                },
            )
        except typst.TypstError as exc:
            # The diagnostic names the file, line and column of the staged sources.
            raise ManualBuildError(getattr(exc, "diagnostic", None) or str(exc)) from exc
        # Typst writes the accessibility structure tree as uncompressed objects;
        # packing them into object streams (allowed by PDF/A-2) makes the file
        # about 60% smaller without changing any content.
        output.parent.mkdir(parents=True, exist_ok=True)
        with pikepdf.open(raw) as pdf:
            pdf.save(
                output,
                object_stream_mode=pikepdf.ObjectStreamMode.generate,
                deterministic_id=True,
            )
    reader = PdfReader(output)
    anchors = frozenset(reader.named_destinations)
    missing = expected_anchors(sources.data) - anchors
    if missing:
        raise ManualBuildError(f"Manual is missing named destinations: {sorted(missing)}")
    if committed_digest(output) != sources.digest:
        raise ManualBuildError("The built manual does not record its source digest.")
    return BuildResult(
        path=output,
        pages=len(reader.pages),
        anchors=anchors,
        date=sources.date,
        digest=sources.digest,
    )


def _installed_typst() -> str:
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version("typst")
    except PackageNotFoundError:
        return "not installed"
