"""Generate metric documentation from the registry.

python scripts/generate_docs.py          # write docs/metric_catalog.md and docs/interpretation/
python scripts/generate_docs.py --check  # exit 1 if committed docs are stale
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from openfactsheet.metrics.catalog_docs import render_all

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if generated docs are stale")
    args = parser.parse_args()

    files = render_all()
    stale = []
    for rel, content in files.items():
        path = ROOT / rel
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current != content:
            stale.append(rel)
            if not args.check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8", newline="\n")

    generated = set(files)
    orphans = [
        p.relative_to(ROOT).as_posix()
        for p in (ROOT / "docs" / "interpretation").glob("*.md")
        if p.relative_to(ROOT).as_posix() not in generated
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
    print(f"Updated {len(stale)} of {len(files)} files; removed {len(orphans)} orphan page(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
