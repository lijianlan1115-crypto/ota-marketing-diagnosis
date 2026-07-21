"""Stable imports for the current OTA marketing diagnosis runtime.

New code should import from this module instead of a numbered ``*_vN`` module.
Historical module names continue to work through ``_versioned_runtime``.
"""

from __future__ import annotations

from marketing_diagnosis.data_v4 import normalize_dataset
from marketing_diagnosis.db_loader_v15 import load_database_dataset, load_mysql_dsn_dataset
from marketing_diagnosis.excel_loader_v2 import load_excel_package
from marketing_diagnosis.reporting_v2 import (
    build_ctrip_html,
    build_html,
    build_markdown,
    write_reports,
)
from marketing_diagnosis.rules_v5 import process


__all__ = [
    "build_ctrip_html",
    "build_html",
    "build_markdown",
    "load_database_dataset",
    "load_excel_package",
    "load_mysql_dsn_dataset",
    "normalize_dataset",
    "process",
    "write_reports",
]
