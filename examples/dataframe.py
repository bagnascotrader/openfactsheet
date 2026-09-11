"""Load a wide monthly-return table and export the canonical report."""

from pathlib import Path

import openfactsheet as ofs

HERE = Path(__file__).parent

series = ofs.load(HERE / "monthly_table.csv", name="Monthly table fund")
print(series.input_diagnostics.to_text())  # what OpenFactsheet believes it received

report = ofs.analyze(series)
print(report.metrics.to_frame()[["name", "value", "status", "confidence"]])

report.to_json(HERE / "factsheet_example.json")
report.to_html(HERE / "factsheet_example.html")
print("\nWrote factsheet_example.json and factsheet_example.html")
