"""Document understanding: page layouts, monthly-return tables, OCR and fund profiles.

Every document source (embedded PDF text, OCR of images or scanned pages) is turned
into :class:`~openfactsheet.documents.layout.PageLayout` objects: lines of words
with horizontal positions. Table reconstruction and validation
(:mod:`~openfactsheet.documents.tables`) work on that common layout, so text PDFs
and OCR follow identical rules (decisions 0030 and 0031).
"""
