"""Extract text from an uploaded PDF annual report using pdfplumber."""

from __future__ import annotations

import io
from dataclasses import dataclass, field

import pdfplumber

from ..config import settings

_STATEMENT_KEYWORDS = (
    "balance sheet", "statement of financial position", "income statement",
    "statement of profit", "statement of operations", "cash flow",
    "consolidated statement", "retained earnings", "shareholders' equity",
)


@dataclass
class PdfContent:
    full_text: str
    page_texts: list[str] = field(default_factory=list)
    num_pages: int = 0

    @property
    def financial_text(self) -> str:
        """Text from statement pages (falls back to the whole document)."""
        hits = [t for t in self.page_texts if any(k in t.lower() for k in _STATEMENT_KEYWORDS)]
        return "\n".join(hits) if hits else self.full_text


def read_pdf_bytes(data: bytes, max_pages: int | None = None) -> PdfContent:
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        total = len(pdf.pages)
        cap = max_pages or settings.max_pdf_pages
        page_texts = [p.extract_text() or "" for p in pdf.pages[:cap]]
        return PdfContent(full_text="\n".join(page_texts), page_texts=page_texts, num_pages=total)
