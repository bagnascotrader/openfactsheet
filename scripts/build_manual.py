"""Build the OpenFactsheet reference manual (PDF) from the code and documents.

python scripts/build_manual.py                   # write docs/manual/openfactsheet-manual.pdf
python scripts/build_manual.py --output out.pdf  # write elsewhere
python scripts/build_manual.py --check           # exit 1 if the committed PDF is stale

The PDF is committed and must match its sources: any change to a metric, a
docstring or a document requires rebuilding it. --check compares the source
digest recorded in the PDF with the current sources; it needs no compiler.

Building needs the docs extra: pip install -e ".[docs]". It uses no network and
no system fonts (decision 0034). Every formula and every internal link must
compile; the build fails instead of skipping anything.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from openfactsheet.manual.build import MANUAL_PDF, ManualBuildError, build_manual, check_committed

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / MANUAL_PDF)
    parser.add_argument(
        "--check", action="store_true", help="fail if the committed PDF does not match its sources"
    )
    args = parser.parse_args()

    if args.check:
        problem = check_committed(ROOT)
        if problem:
            print(problem)
            print('Run: pip install -e ".[docs]" && python scripts/build_manual.py')
            return 1
        print(f"{MANUAL_PDF} matches its sources.")
        return 0

    try:
        result = build_manual(ROOT, args.output)
    except ManualBuildError as exc:
        sys.stderr.reconfigure(errors="replace")  # type: ignore[union-attr]
        print(f"Manual build failed:\n{exc}", file=sys.stderr)
        return 1
    size = args.output.stat().st_size / 1e6
    print(
        f"Manual OK: {result.pages} pages, {len(result.anchors)} named destinations, "
        f"{size:.1f} MB, dated {result.date}, sources {result.digest[:12]}\n  {args.output}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
