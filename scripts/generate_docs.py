"""Generate metric documentation and reference-manual data from the code.

python scripts/generate_docs.py          # write docs/metric_catalog.md, docs/interpretation/,
                                         # docs/reference/{formulas,policies}.md,
                                         # docs/ATTRIBUTION.md, docs/manual/data/
python scripts/generate_docs.py --check  # exit 1 if committed files are stale
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from openfactsheet.manual.export import DATA_DIR, render_manual_data
from openfactsheet.metrics.catalog_docs import render_all

ROOT = Path(__file__).resolve().parents[1]
# Directories whose every file is generated: files not generated any more are orphans.
GENERATED_DIRS = (("docs/interpretation", "*.md"), (DATA_DIR, "*.json"))


def generated_files() -> dict[str, str]:
    return {**render_all(), **render_manual_data(ROOT)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if generated docs are stale")
    args = parser.parse_args()

    files = generated_files()
    stale = []
    for rel, content in files.items():
        path = ROOT / rel
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current != content:
            stale.append(rel)
            if not args.check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8", newline="\n")

    orphans = [
        p.relative_to(ROOT).as_posix()
        for directory, pattern in GENERATED_DIRS
        for p in (ROOT / directory).glob(pattern)
        if p.relative_to(ROOT).as_posix() not in files
    ]
    if args.check:
        if stale or orphans:
            print("Stale generated docs:", *stale, *orphans, sep="\n  ")
            print("Run: python scripts/generate_docs.py")
            return 1
        print(f"{len(files)} generated doc files are up to date.")
        return 0
    for rel in orphans:
        (ROOT / rel).unlink()
    print(f"Updated {len(stale)} of {len(files)} files; removed {len(orphans)} orphan file(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
