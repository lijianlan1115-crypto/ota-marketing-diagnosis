from __future__ import annotations

"""Compatibility entry for the customer-facing v24 report renderer.

The server already imports ``reporting_v7`` through ``reporting_v3``. Keeping
this module as the stable entry means the deployment does not need another
manual import rewrite when the exact v24 renderer is upgraded.
"""

from marketing_diagnosis.reporting_v9 import build_html, build_markdown, write_reports

__all__ = ["build_html", "build_markdown", "write_reports"]
