"""Runtime settings for the optional AI-powered PDF upload feature.

The core dashboard (8 pre-loaded companies, ratio engine, Altman Z'',
narrative) has no AI dependency and works with no API key at all. Only the
ad-hoc "upload any annual report" feature needs ANTHROPIC_API_KEY, and it
degrades to a clear message (not a crash) when the key is missing.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PKG_DIR = Path(__file__).resolve().parent
BASE_DIR = PKG_DIR.parent


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str | None = os.getenv("ANTHROPIC_API_KEY") or None
    extraction_model: str = os.getenv("SOLVENCYSCAN_EXTRACTION_MODEL", "claude-sonnet-4-6")
    max_pdf_pages: int = int(os.getenv("SOLVENCYSCAN_MAX_PDF_PAGES", "60"))

    @property
    def has_api_key(self) -> bool:
        return bool(self.anthropic_api_key)


settings = Settings()
