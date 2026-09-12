"""Data the reference manual is built from (decision 0034).

Everything here is read from the code and the repository's Markdown documents,
never typed twice:

- ``metrics.json``: :func:`~openfactsheet.metrics.catalog_docs.metric_record` for
  every registered metric (the same record the Markdown pages render from), plus
  the decision notes that discuss it;
- ``api.json``: signatures and docstrings of everything in ``openfactsheet.__all__``;
- ``bibliography.json``: the academic references, deduplicated, with the metrics
  citing them;
- ``methodology.json``: the canonical conventions and minimum-data policies;
- ``documents.json``: the Markdown documents included in the manual, in order;
- ``package.json``: name, version, description, license, dependencies, URLs.

``scripts/generate_docs.py`` writes these to ``docs/manual/data/`` and its
``--check`` fails when they are stale. :func:`prepare_markdown` rewrites the
Markdown documents for the manual at build time (links between documents become
links between manual topics).
"""

from __future__ import annotations

import dataclasses
import enum
import inspect
import json
import posixpath
import re
import sys
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

from openfactsheet.manual import api_anchor, decision_anchor

DATA_DIR = "docs/manual/data"

# Markdown documents in the manual: (part, source, anchor, title override).
_DOCUMENTS: tuple[tuple[str, str, str, str | None], ...] = (
    ("overview", "docs/index.md", "doc-index", "Introduction"),
    ("overview", "docs/getting_started.md", "doc-getting_started", None),
    ("methodology", "docs/methodology.md", "doc-methodology", None),
    ("methodology", "docs/assumptions.md", "doc-assumptions", None),
    ("methodology", "docs/reference/criteria.md", "doc-criteria", None),
    ("methodology", "docs/reference/notation.md", "doc-notation", None),
    ("methodology", "docs/reference/policies.md", "doc-policies", None),
    ("methodology", "docs/reference/report_schema.md", "doc-report_schema", None),
    ("decisions", "docs/methodology/decisions/README.md", "doc-decisions", None),
    ("validation", "docs/validation/reference_implementations.md", "doc-validation", None),
)
_DECISIONS_DIR = "docs/methodology/decisions"

# Generated pages whose content is part III of the manual.
_ALIASES = {
    "docs/metric_catalog.md": "part-metrics",
    "docs/reference/formulas.md": "part-metrics",
    "docs/interpretation": "part-metrics",
}

_GENERATED_COMMENT = re.compile(r"^<!--.*?-->\s*$", re.MULTILINE)
_DECISION_FILE = re.compile(r"^(\d{4})-.+\.md$")


def _dumps(obj: Any) -> str:
    return json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


# --- package ----------------------------------------------------------------


def package_data(root: Path) -> dict[str, Any]:
    from openfactsheet.policy.methodology_version import METHODOLOGY_VERSION
    from openfactsheet.version import __version__

    if sys.version_info >= (3, 11):
        import tomllib
    else:  # pragma: no cover - Python 3.10 (tomli is in the dev extra)
        import tomli as tomllib

    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    return {
        "name": project["name"],
        "version": __version__,
        "methodology_version": METHODOLOGY_VERSION,
        "description": project["description"],
        "license": project["license"],
        "requires_python": project["requires-python"],
        "authors": [a["name"] for a in project["authors"]],
        "dependencies": project["dependencies"],
        "extras": {k: v for k, v in project["optional-dependencies"].items() if k != "dev"},
        "urls": project["urls"],
    }


# --- metrics ----------------------------------------------------------------


def _decision_texts(root: Path) -> dict[str, str]:
    out = {}
    for path in sorted((root / _DECISIONS_DIR).glob("*.md")):
        m = _DECISION_FILE.match(path.name)
        if m:
            out[m.group(1)] = path.read_text(encoding="utf-8")
    return out


def metrics_data(root: Path) -> dict[str, Any]:
    from openfactsheet.metrics.catalog_docs import metric_record
    from openfactsheet.metrics.registry import all_metrics
    from openfactsheet.models.metric import CATEGORY_TITLES
    from openfactsheet.policy.methodology_version import METHODOLOGY_VERSION

    decisions = _decision_texts(root)
    records = []
    for d in all_metrics():
        record = metric_record(d)
        # Decision notes the metric's documentation cites ("decision 0021"), and notes
        # that name the metric in code (`sharpe_ratio` or `sharpe_ratio = ...`).
        own_text = json.dumps(record)
        cited = set(re.findall(r"[Dd]ecisions? (\d{4})", own_text))
        named = re.compile(rf"`{re.escape(d.id)}\b")
        record["decisions"] = [
            n for n, text in decisions.items() if n in cited or named.search(text)
        ]
        records.append(record)
    categories = [
        {"id": c, "title": t, "metrics": [r["id"] for r in records if r["category"] == c]}
        for c, t in CATEGORY_TITLES.items()
    ]
    return {
        "methodology_version": METHODOLOGY_VERSION,
        "categories": [c for c in categories if c["metrics"]],
        "metrics": records,
    }


def methodology_data() -> dict[str, Any]:
    from openfactsheet.policy.defaults import canonical_methodology
    from openfactsheet.policy.thresholds import MIN_DATA_POLICIES

    m = canonical_methodology()
    return {
        "version": m.version,
        "conventions": m.to_dict(),
        "min_data_policies": [dataclasses.asdict(p) for p in MIN_DATA_POLICIES.values()],
    }


# --- bibliography -----------------------------------------------------------

_CITATION = re.compile(r"^(?P<authors>.+?)\s*\((?P<year>\d{4})\)\.?\s*(?P<rest>.*)$")


def _bib_key(authors: str, year: str) -> str:
    first = re.split(r"[,&\s]", authors.strip(), maxsplit=1)[0]
    ascii_name = re.sub(r"[^a-z]", "", first.lower()) or "ref"
    return f"{ascii_name}{year}"


def bibliography_data(metrics: dict[str, Any]) -> dict[str, Any]:
    entries: dict[str, dict[str, Any]] = {}
    for record in metrics["metrics"]:
        for ref in record["references"]:
            entry = entries.setdefault(
                ref["citation"], {"citation": ref["citation"], "url": ref["url"], "cited_by": []}
            )
            entry["cited_by"].append(record["id"])
    used: dict[str, int] = {}
    out = []
    for citation in sorted(entries, key=lambda c: (c.lower(), c)):
        entry = entries[citation]
        m = _CITATION.match(citation)
        if m:
            authors, year = m.group("authors"), m.group("year")
            base = _bib_key(authors, year)
        else:  # no year: first word and first title word, e.g. "morningstarupside"
            authors, year = citation.split(".", 1)[0], None
            words = re.findall(r"[A-Za-z]+", citation)
            base = "".join(w.lower() for w in words[:1] + words[2:3])
        used[base] = used.get(base, 0) + 1
        key = base if used[base] == 1 else f"{base}{chr(ord('a') + used[base] - 1)}"
        out.append({**entry, "key": key, "anchor": f"ref-{key}", "authors": authors, "year": year})
    return {"entries": out}


# --- API --------------------------------------------------------------------

_SECTION_NAMES = {
    "Args": "arguments",
    "Arguments": "arguments",
    "Parameters": "arguments",
    "Attributes": "fields",
    "Returns": "value",
    "Raises": "raises",
    "Examples": "examples",
    "Example": "examples",
    "Notes": "details",
    "Note": "details",
}
_SECTION = re.compile(r"^(\w+):$")
_ITEM = re.compile(r"^(?P<name>\*{0,2}[A-Za-z_]\w*)(?:\s*\((?P<type>[^)]*)\))?:\s*(?P<text>.*)$")


def _rst_to_markdown(text: str, topics: set[str]) -> str:
    """Docstring markup to Markdown: ``code``, :func:`x`, :class:`X`."""

    def role(m: re.Match[str]) -> str:
        kind, target = m.group(1), m.group(2).strip("~").split(".")[-1]
        label = f"{target}()" if kind in ("func", "meth") else target
        return f"[`{label}`](#{api_anchor(target)})" if target in topics else f"`{label}`"

    text = re.sub(r":(func|class|meth|attr|mod|data|exc):`([^`]+)`", role, text)
    return re.sub(r"``([^`]+)``", r"`\1`", text)


def _items(lines: list[str]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    base = min((len(line) - len(line.lstrip()) for line in lines if line.strip()), default=0)
    for raw in lines:
        if not raw.strip():
            continue
        line = raw[base:]
        m = _ITEM.match(line) if not line.startswith(" ") else None
        if m:
            items.append({"name": m.group("name"), "text": m.group("text").strip()})
        elif items:
            # A compound word split at its hyphen ("Benchmark-" / "relative") is rejoined.
            sep = "" if re.search(r"[A-Za-z]-$", items[-1]["text"]) else " "
            items[-1]["text"] = f"{items[-1]['text']}{sep}{line.strip()}".strip()
    return items


def parse_docstring(doc: str | None, topics: set[str]) -> dict[str, Any]:
    """Split a Google-style docstring into manual sections (all text as Markdown)."""
    sections: dict[str, list[str]] = {"body": []}
    current = "body"
    for line in (doc or "").splitlines():
        m = _SECTION.match(line)
        if m and m.group(1) in _SECTION_NAMES:
            current = _SECTION_NAMES[m.group(1)]
            sections.setdefault(current, [])
            continue
        sections[current].append(line)

    def text(key: str) -> str:
        cleaned = inspect.cleandoc("\n".join(sections.get(key, [])))
        cleaned = re.sub(r"(?<=[A-Za-z]-)\n\s*(?=[a-z])", "", cleaned)
        return _rst_to_markdown(cleaned, topics)

    description, _, details = text("body").partition("\n\n")
    extra = text("details")
    return {
        "description": description.replace("\n", " "),
        "details": "\n\n".join(p for p in (details.strip(), extra) if p),
        "arguments": [
            {**i, "text": _rst_to_markdown(i["text"], topics)}
            for i in _items(sections.get("arguments", []))
        ],
        "fields": [
            {**i, "text": _rst_to_markdown(i["text"], topics)}
            for i in _items(sections.get("fields", []))
        ],
        "value": text("value"),
        "raises": text("raises"),
        "examples": inspect.cleandoc("\n".join(sections.get("examples", []))),
    }


def _usage(name: str, func: Callable[..., Any], *, method: bool = False) -> str:
    sig = inspect.signature(func)
    parts: list[str] = []
    star_done = False
    for p in sig.parameters.values():
        if method and p.name == "self":
            continue
        if p.kind is p.VAR_POSITIONAL:
            parts.append(f"*{p.name}")
            star_done = True
        elif p.kind is p.VAR_KEYWORD:
            parts.append(f"**{p.name}")
        else:
            if p.kind is p.KEYWORD_ONLY and not star_done:
                parts.append("*")
                star_done = True
            default = "" if p.default is p.empty else f"={p.default!r}"
            parts.append(f"{p.name}{default}")
    return f"{name}({', '.join(parts)})"


def _parameters(func: Callable[..., Any], *, method: bool = False) -> list[dict[str, str]]:
    out = []
    for p in inspect.signature(func).parameters.values():
        if method and p.name == "self":
            continue
        annotation = "" if p.annotation is p.empty else str(p.annotation).strip("'")
        default = "" if p.default is p.empty else repr(p.default)
        out.append({"name": p.name, "annotation": annotation, "default": default})
    return out


def _function_topic(name: str, func: Callable[..., Any], topics: set[str]) -> dict[str, Any]:
    doc = parse_docstring(inspect.getdoc(func), topics)
    returns = inspect.signature(func).return_annotation
    return {
        "name": name,
        "anchor": api_anchor(name),
        "kind": "function",
        "usage": f"ofs.{_usage(name, func)}",
        "parameters": _parameters(func),
        "returns": "" if returns is inspect.Signature.empty else str(returns).strip("'"),
        **doc,
    }


def _members(cls: type, topics: set[str]) -> Iterator[dict[str, Any]]:
    for name, member in sorted(vars(cls).items()):
        if name.startswith("_"):
            continue
        if isinstance(member, property):
            doc = parse_docstring(inspect.getdoc(member), topics)
            yield {"name": name, "kind": "property", "usage": name, "parameters": [], **doc}
        elif inspect.isfunction(member):
            doc = parse_docstring(inspect.getdoc(member), topics)
            yield {
                "name": name,
                "kind": "method",
                "usage": _usage(name, member, method=True),
                "parameters": _parameters(member, method=True),
                **doc,
            }


def _class_topic(name: str, cls: type, topics: set[str]) -> dict[str, Any]:
    doc = parse_docstring(inspect.getdoc(cls), topics)
    topic: dict[str, Any] = {
        "name": name,
        "anchor": api_anchor(name),
        "kind": "enum" if issubclass(cls, enum.Enum) else "class",
        "module": cls.__module__,
        "members": list(_members(cls, topics)),
        **doc,
    }
    if issubclass(cls, enum.Enum):
        topic["values"] = [{"name": m.name, "value": str(m.value)} for m in cls]
    return topic


def api_data() -> dict[str, Any]:
    import openfactsheet as ofs
    from openfactsheet.compare.comparison import Comparison

    public: dict[str, Any] = {n: getattr(ofs, n) for n in ofs.__all__}
    # Returned by ofs.compare() but not constructed by users.
    public["Comparison"] = Comparison
    functions = sorted(n for n, o in public.items() if inspect.isfunction(o))
    exceptions = sorted(
        n for n, o in public.items() if inspect.isclass(o) and issubclass(o, BaseException)
    )
    classes = sorted(
        n
        for n, o in public.items()
        if inspect.isclass(o) and n not in exceptions and not n.startswith("_")
    )
    constants = sorted(n for n in public if n not in {*functions, *exceptions, *classes})
    topics = {*functions, *classes, "exceptions", "constants"}

    out: list[dict[str, Any]] = [_function_topic(n, public[n], topics) for n in functions]
    out += [_class_topic(n, public[n], topics) for n in classes]
    out.append(
        {
            "name": "Exceptions",
            "anchor": api_anchor("exceptions"),
            "kind": "exceptions",
            "description": "Errors raised by OpenFactsheet. Input corruption fails early; a "
            "metric that cannot be computed never raises but is reported with a status and "
            "a reason.",
            "classes": [
                {
                    "name": n,
                    "anchor": api_anchor(n),
                    "base": public[n].__mro__[1].__name__,
                    **parse_docstring(inspect.getdoc(public[n]), topics),
                }
                for n in exceptions
            ],
        }
    )
    out.append(
        {
            "name": "Constants",
            "anchor": api_anchor("constants"),
            "kind": "constants",
            "description": "Version identifiers embedded in every report.",
            "constants": [
                {"name": n, "anchor": api_anchor(n), "value": str(public[n])} for n in constants
            ],
        }
    )
    return {"topics": out}


# --- documents --------------------------------------------------------------


def _title(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    raise ValueError("Markdown document without a '# ' title")


def documents_data(root: Path) -> dict[str, Any]:
    docs = []
    for part, source, anchor, title in _DOCUMENTS:
        text = (root / source).read_text(encoding="utf-8")
        docs.append(
            {"part": part, "source": source, "anchor": anchor, "title": title or _title(text)}
        )
    for path in sorted((root / _DECISIONS_DIR).glob("*.md")):
        m = _DECISION_FILE.match(path.name)
        if not m:
            continue
        title = _title(path.read_text(encoding="utf-8"))
        docs.append(
            {
                "part": "decisions",
                "source": f"{_DECISIONS_DIR}/{path.name}",
                "anchor": decision_anchor(m.group(1)),
                "number": m.group(1),
                "title": re.sub(r"^\d{4}\s*[—-]\s*", "", title),
            }
        )
    return {"documents": docs}


def _split_code(text: str) -> Iterator[tuple[bool, str]]:
    """Yield (is_code, chunk): fenced blocks and inline code spans are code."""
    pattern = re.compile(r"(^```.*?^```[ \t]*$|`[^`\n]+`)", re.MULTILINE | re.DOTALL)
    pos = 0
    for m in pattern.finditer(text):
        yield False, text[pos : m.start()]
        yield True, m.group(0)
        pos = m.end()
    yield False, text[pos:]


def prepare_markdown(root: Path, document: dict[str, Any], repository: str) -> str:
    """A document's Markdown as the manual renders it.

    The title line and generated-file comments are dropped (the manual prints its
    own heading). Links to other documents in the manual become links to their
    topics; links to heading anchors keep working through the per-document label
    prefix; any other repository path becomes a link to the file on GitHub.
    """
    from openfactsheet.metrics.registry import all_metrics

    text = (root / document["source"]).read_text(encoding="utf-8")
    text = _GENERATED_COMMENT.sub("", text)
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("# "):
            del lines[i]
            break
    text = "\n".join(lines).strip() + "\n"

    anchors = {d["source"]: d["anchor"] for d in documents_data(root)["documents"]}
    metric_ids = {d.id for d in all_metrics()}
    here = posixpath.dirname(document["source"])

    def target(link: str) -> str:
        if re.match(r"^[a-z]+:", link):
            return link
        path, _, fragment = link.partition("#")
        if not path:
            return f"#{document['anchor']}-{fragment}"
        resolved = posixpath.normpath(posixpath.join(here, path)).rstrip("/")
        if resolved in anchors:
            anchor = anchors[resolved]
            return f"#{anchor}-{fragment}" if fragment else f"#{anchor}"
        m = re.fullmatch(r"docs/interpretation/(\w+)\.md", resolved)
        if m and m.group(1) in metric_ids:
            return f"#metric-{m.group(1)}"
        if resolved in _ALIASES:
            return f"#{_ALIASES[resolved]}"
        kind = "tree" if (root / resolved).is_dir() else "blob"
        return f"{repository}/{kind}/main/{resolved}" + (f"#{fragment}" if fragment else "")

    link = re.compile(r"(?<!!)\[(?P<text>[^\]\n]*)\]\((?P<target>[^)\s]+)\)")
    return "".join(
        chunk if is_code else link.sub(lambda m: f"[{m['text']}]({target(m['target'])})", chunk)
        for is_code, chunk in _split_code(text)
    )


# --- all --------------------------------------------------------------------


def manual_data(root: Path) -> dict[str, Any]:
    """Every data file of the manual, keyed by file stem."""
    metrics = metrics_data(root)
    return {
        "api": api_data(),
        "bibliography": bibliography_data(metrics),
        "documents": documents_data(root),
        "methodology": methodology_data(),
        "metrics": metrics,
        "package": package_data(root),
    }


def render_manual_data(root: Path) -> dict[str, str]:
    """Repository-relative path to content of each committed data file."""
    return {f"{DATA_DIR}/{k}.json": _dumps(v) for k, v in manual_data(root).items()}
