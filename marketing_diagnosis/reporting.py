from pathlib import Path
import json


def build_markdown(result):
    lines = ["# OTA Marketing Report", "", "## Metrics"]
    for name, payload in (result.get("metrics") or {}).items():
        lines.append(f"### {name}")
        if isinstance(payload, dict):
            for key, value in payload.items():
                lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("## Notes")
    for item in result.get("notes") or []:
        lines.append(f"- [{item.get('level')}] {item.get('title')}: {item.get('suggestion')}")
    lines.append("")
    lines.append("## Actions")
    for index, item in enumerate(result.get("actions") or [], 1):
        lines.append(f"{index}. {item}")
    lines.append("")
    lines.append("## Boundary")
    lines.append("This tool only creates marketing reports. It does not write prices or approvals.")
    return "\n".join(lines)


def write_reports(result, output_dir):
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    json_path = path / "report.json"
    md_path = path / "report.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(build_markdown(result), encoding="utf-8")
    return {"report_json": str(json_path), "report_markdown": str(md_path)}
