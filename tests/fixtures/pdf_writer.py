"""Minimal, dependency-free writer of text-only PDF pages (test fixtures only).

Produces byte-for-byte deterministic PDF 1.4 files with standard Helvetica text
placed at explicit coordinates, which is how factsheet generators lay out
monthly-return tables. Used to test embedded-text PDF ingestion (decision 0030)
without committing opaque binaries.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

TextItem = tuple[float, float, str]  # (x, y, text) in points; y from the bottom
PAGE_SIZE = (842.0, 595.0)  # A4 landscape


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _content(items: Sequence[TextItem], size: float) -> bytes:
    ops = [
        f"BT /F1 {size:g} Tf 1 0 0 1 {x:.2f} {y:.2f} Tm ({_escape(t)}) Tj ET" for x, y, t in items
    ]
    return "\n".join(ops).encode("latin-1")


def write_pdf(path: Path, pages: Sequence[Sequence[TextItem]], font_size: float = 9.0) -> Path:
    """Write ``pages`` (each a list of text items) to ``path`` and return it."""
    objects: list[bytes] = []
    n_pages = len(pages)
    page_ids = [3 + 2 * i for i in range(n_pages)]
    font_id = 3 + 2 * n_pages
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {n_pages} >>".encode())
    for i, items in enumerate(pages):
        content = _content(items, font_size)
        objects.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_SIZE[0]:g} {PAGE_SIZE[1]:g}] "
                f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {page_ids[i] + 1} 0 R >>"
            ).encode()
        )
        objects.append(
            f"<< /Length {len(content)} >>\nstream\n".encode() + content + b"\nendstream"
        )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    ).encode()
    path.write_bytes(bytes(out))
    return path


MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def monthly_table_page(
    rows: Sequence[tuple[int, Sequence[str | None], str | None]],
    *,
    title: str = "Example Fund - Monthly net returns (%)",
    top: float = 480.0,
    x0: float = 60.0,
    col: float = 52.0,
    row_height: float = 16.0,
    ytd_header: str | None = "YTD",
    extra: Sequence[TextItem] = (),
) -> list[TextItem]:
    """A factsheet-style monthly table: year rows, right-aligned month cells, optional YTD.

    ``rows`` holds ``(year, twelve cells (None = empty), ytd cell or None)``.
    Cells are right-aligned by shifting their x by an approximate text width.
    """
    items: list[TextItem] = [(x0, top + 40, title), *extra]

    def right(x_right: float, text: str) -> float:
        return x_right - 4.6 * len(text)

    header_y = top
    for j, m in enumerate(MONTHS):
        items.append((right(x0 + col * (j + 2), m), header_y, m))
    if ytd_header:
        items.append((right(x0 + col * 14, ytd_header), header_y, ytd_header))
    for i, (year, cells, ytd) in enumerate(rows):
        y = header_y - row_height * (i + 1)
        items.append((x0, y, str(year)))
        for j, cell in enumerate(cells):
            if cell:
                items.append((right(x0 + col * (j + 2), cell), y, cell))
        if ytd_header and ytd:
            items.append((right(x0 + col * 14, ytd), y, ytd))
    return items
