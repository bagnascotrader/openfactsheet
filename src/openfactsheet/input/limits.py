"""Resource limits for untrusted input files (safety limits, not methodology).

OpenFactsheet reads files that users receive from third parties: CSV and Excel
exports, PDF factsheets, screenshots. A hostile or corrupt file must fail with a
clear :class:`~openfactsheet.exceptions.InputError` instead of exhausting memory
or CPU. The limits below are defined in this one place.

They are **safety limits, not analysis parameters**: they never change a metric
value. An input inside the limits is analyzed exactly as before; an input outside
them is refused with an explanation. They are set far above any real return
history (a 100-year monthly table is a few kilobytes; an A4 page rendered at the
canonical OCR resolution of 300 dpi is about 8.7 million pixels).

The limits are documented in ``SECURITY.md``. Changing them is a code change
reviewed like any other; they are deliberately not arguments of
:func:`openfactsheet.analyze`.
"""

from __future__ import annotations

from pathlib import Path

from openfactsheet.exceptions import InputError, OCRExtractionError

#: Largest input file read (CSV/TXT/TSV, Excel, PDF, image), in bytes. Also bounds
#: pasted table text (in UTF-8 bytes).
MAX_INPUT_FILE_BYTES = 64 * 1024 * 1024

#: Largest total *uncompressed* size of the parts of an Excel (.xlsx/.xlsm) zip
#: package, in bytes (guards against zip bombs; Python's ``zipfile`` never
#: returns more bytes than a member declares).
MAX_EXCEL_UNCOMPRESSED_BYTES = 256 * 1024 * 1024

#: Largest image (width x height, in pixels) decoded for OCR, both for image
#: files and for rendered scanned PDF pages. Pillow's own decompression-bomb
#: warning starts at about 89 million pixels; this is stricter and explicit.
MAX_IMAGE_PIXELS = 50_000_000

#: Most pages read from one PDF. Factsheets have a handful of pages.
MAX_PDF_PAGES = 200

#: Seconds allowed for one external Tesseract process before it is stopped.
TESSERACT_TIMEOUT_SECONDS = 120


def _mib(n: int) -> str:
    return f"{n / (1024 * 1024):.0f} MiB"


def check_file_size(path: Path) -> None:
    """Refuse a file larger than :data:`MAX_INPUT_FILE_BYTES`."""
    size = path.stat().st_size
    if size > MAX_INPUT_FILE_BYTES:
        raise InputError(
            f"{path.name} is {_mib(size)}, above OpenFactsheet's input safety limit of "
            f"{_mib(MAX_INPUT_FILE_BYTES)}. A return history is far smaller than this; "
            "the file was not read."
        )


def check_text_size(text: str) -> None:
    """Refuse pasted text larger than :data:`MAX_INPUT_FILE_BYTES` (UTF-8)."""
    size = len(text.encode("utf-8", errors="replace"))
    if size > MAX_INPUT_FILE_BYTES:
        raise InputError(
            f"The pasted text is {_mib(size)}, above OpenFactsheet's input safety limit of "
            f"{_mib(MAX_INPUT_FILE_BYTES)}; it was not parsed."
        )


def check_pixels(width: int, height: int, what: str) -> None:
    """Refuse an image (or a page render) above :data:`MAX_IMAGE_PIXELS`."""
    pixels = int(width) * int(height)
    if pixels > MAX_IMAGE_PIXELS:
        raise OCRExtractionError(
            f"{what} is {width} x {height} pixels ({pixels:,}), above OpenFactsheet's image "
            f"safety limit of {MAX_IMAGE_PIXELS:,} pixels; it was not decoded."
        )


def check_excel_package(path: Path) -> None:
    """Refuse an Excel zip package whose parts expand beyond the safety limit.

    Legacy binary ``.xls`` files are not zip packages and are left to the reader.
    """
    import zipfile

    if not zipfile.is_zipfile(path):
        return
    try:
        with zipfile.ZipFile(path) as package:
            total = sum(info.file_size for info in package.infolist())
    except (zipfile.BadZipFile, OSError) as exc:
        raise InputError(f"Could not read Excel file {path.name!r}: {exc}") from exc
    if total > MAX_EXCEL_UNCOMPRESSED_BYTES:
        raise InputError(
            f"{path.name} expands to {_mib(total)}, above OpenFactsheet's safety limit of "
            f"{_mib(MAX_EXCEL_UNCOMPRESSED_BYTES)} for an Excel workbook; it was not read."
        )


__all__ = [
    "MAX_EXCEL_UNCOMPRESSED_BYTES",
    "MAX_IMAGE_PIXELS",
    "MAX_INPUT_FILE_BYTES",
    "MAX_PDF_PAGES",
    "TESSERACT_TIMEOUT_SECONDS",
    "check_excel_package",
    "check_file_size",
    "check_pixels",
    "check_text_size",
]
