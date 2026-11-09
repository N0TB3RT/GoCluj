"""Helpers for the per-run output location (<OUTPUT_DIR>/<YYYY-MM-DD>/<spider>.<ext>)."""

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from gocluj_scraper.parsing.text import TIMEZONE


def run_date() -> str:
    """Today's date (YYYY-MM-DD) in the project timezone."""
    return datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d")


def uri_params(params: dict, spider) -> dict:
    """FEED_URI_PARAMS hook: adds ``run_date`` for the FEEDS path template."""
    return {**params, "run_date": run_date()}


def run_file(output_dir: str, spider_name: str, suffix: str) -> Path:
    """Today's file for a spider, e.g. suffix='jsonl' or 'summary.json'."""
    return Path(output_dir) / run_date() / f"{spider_name}.{suffix}"
