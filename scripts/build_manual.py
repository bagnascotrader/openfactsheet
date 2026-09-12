"""Build the OpenFactsheet reference manual (PDF) from the code and documents.

python scripts/build_manual.py                   # docs/manual/build/openfactsheet-manual.pdf
python scripts/build_manual.py --output out.pdf
python scripts/build_manual.py --check           # compile to a temporary file and verify

Needs the docs extra: pip install -e ".[docs]". Uses no network and no system
fonts (decision 0034). Every formula and every internal link must compile; the
build fails instead of skipping anything.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import tempfile
from pathlib import Path

from openfactsheet.manual.build import ManualBuildError, build_manual

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "docs" / "manual" / "build" / "openfactsheet-manual.pdf"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true", help="build to a temporary file only")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "manual.pdf" if args.check else args.output
        try:
            result = build_manual(ROOT, output)
        except ManualBuildError as exc:
            sys.stderr.reconfigure(errors="replace")  # type: ignore[union-attr]
            print(f"Manual build failed:\n{exc}", file=sys.stderr)
            return 1
        digest = hashlib.sha256(output.read_bytes()).hexdigest()[:16]
        print(
            f"Manual OK: {result.pages} pages, {len(result.anchors)} named destinations, "
            f"dated {result.date}, sha256 {digest}" + ("" if args.check else f"\n  {output}")
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
