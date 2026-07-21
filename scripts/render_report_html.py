from __future__ import annotations

import argparse
import json
from pathlib import Path

from marketing_diagnosis.reporting_v2 import build_dual_channel_html


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Render an existing report.json into one dual-channel HTML file. "
            "Use ?channel=meituan or ?channel=ctrip to switch channels."
        )
    )
    parser.add_argument("--input", required=True, help="Path to an existing report.json")
    parser.add_argument(
        "--output",
        required=True,
        help="Path to the single dual-channel HTML, for example 双渠道诊断报告预览.html",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    result = json.loads(input_path.read_text(encoding="utf-8"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_dual_channel_html(result), encoding="utf-8")

    print(output_path)
    print(f"美团：{output_path.as_uri()}?channel=meituan")
    print(f"携程：{output_path.as_uri()}?channel=ctrip")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
