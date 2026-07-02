from pathlib import Path
import json


def build_markdown(result):
    lines = ["# OTA Marketing Report", ""]
    lines.append(f"- final_score: {result.get('final_score', 'missing')}")
    lines.append(f"- risk_level: {result.get('risk_level', 'missing')}")
    lines.append(f"- status: {result.get('status', 'missing')}")
    lines.append("")
    lines.append("## Module Scores")
    for item in result.get("module_scores") or []:
        lines.append(f"- {item.get('module_id')} {item.get('module_name')}: {item.get('score')}/{item.get('weight')} ({item.get('rate')})")
    lines.append("")
    lines.append("## Metrics")
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
    lines.append("## Data Quality")
    lines.append(json.dumps(result.get("data_quality") or {}, ensure_ascii=False, indent=2))
    return "\n".join(lines)


def write_reports(result, output_dir):
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    json_path = path / "report.json"
    md_path = path / "report.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(build_markdown(result), encoding="utf-8")
    return {"report_json": str(json_path), "report_markdown": str(md_path)}
