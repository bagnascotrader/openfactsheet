"""Regenerate golden full-report JSON files in tests/golden/.

Golden files pin the complete canonical output. Any diff must be reviewed
consciously: it means a metric value, status, warning or methodology text changed.

    python scripts/update_golden.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.golden.cases import GOLDEN_DIR, build_case, case_names  # noqa: E402


def main() -> None:
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    for name in case_names():
        path = GOLDEN_DIR / f"{name}.json"
        path.write_text(build_case(name).to_json() + "\n", encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
