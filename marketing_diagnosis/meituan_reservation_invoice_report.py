from __future__ import annotations

from typing import Any, Callable

from marketing_diagnosis import reporting_runtime_v51 as runtime


OLD_LABEL = "预约开票"
NEW_LABEL = "预约发票"


def rewrite_reservation_invoice(document: str) -> str:
    """Use the confirmed item-20 name throughout the Meituan HTML."""

    return document.replace(OLD_LABEL, NEW_LABEL)


def _install() -> None:
    if hasattr(runtime, "_reservation_invoice_original_build_html"):
        return

    original: Callable[[dict[str, Any]], str] = runtime.build_html
    runtime._reservation_invoice_original_build_html = original

    def build_html(result: dict[str, Any]) -> str:
        return rewrite_reservation_invoice(original(result))

    runtime.build_html = build_html


_install()


__all__ = ["rewrite_reservation_invoice"]
