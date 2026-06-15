from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Callable

import yaml

from .agent import WebAgent
from .models import RunResult, Scenario


SITE_BLOCK_MARKERS = (
    "安全验证",
    "验证码",
    "captcha",
    "访问受限",
    "access denied",
    "verify you are human",
)


def load_scenarios(path: Path) -> list[Scenario]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [Scenario.model_validate(item) for item in data["scenarios"]]


def validate_result(result: RunResult, scenario: Scenario) -> bool:
    criteria = scenario.success
    checks = []
    if criteria.url_contains:
        checks.append(
            any(value.lower() in result.final_url.lower() for value in criteria.url_contains)
        )
    if criteria.title_contains:
        checks.append(
            any(
                value.lower() in result.final_title.lower()
                for value in criteria.title_contains
            )
        )
    if criteria.text_contains:
        checks.append(
            any(
                value.lower() in result.final_text.lower()
                for value in criteria.text_contains
            )
        )
    return bool(checks) and all(checks)


def run_evaluation(
    scenarios: list[Scenario],
    agent_factory: Callable[[], WebAgent],
    output_dir: Path,
    repeats_override: int | None = None,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    evaluation_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    records = []
    for scenario in scenarios:
        repeats = repeats_override or scenario.repeats
        for repeat in range(1, repeats + 1):
            run_id = f"{evaluation_id}_{scenario.id}_{repeat:02d}"
            result = agent_factory().run(
                task=scenario.task,
                start_url=scenario.start_url,
                run_id=run_id,
            )
            validated = validate_result(result, scenario)
            if not validated and result.failure_type is None:
                result.failure_type = classify_failed_result(result)
                if result.error is None:
                    result.error = _failure_message(result.failure_type)
            records.append(
                {
                    "scenario_id": scenario.id,
                    "site": scenario.site,
                    "repeat": repeat,
                    "validated_success": validated,
                    **result.model_dump(),
                }
            )
            _write_json(output_dir / "runs.json", records)

    summary = summarize_records(records)
    _write_json(output_dir / "summary.json", summary)
    (output_dir / "summary.md").write_text(
        render_markdown_summary(summary),
        encoding="utf-8",
    )
    return summary


def classify_failed_result(result: RunResult) -> str:
    page_evidence = " ".join(
        [result.final_url, result.final_title, result.final_text]
    ).lower()
    if any(marker.lower() in page_evidence for marker in SITE_BLOCK_MARKERS):
        return "execution_failure"
    return "planning_failure" if result.completed else "execution_failure"


def _failure_message(failure_type: str) -> str:
    if failure_type == "execution_failure":
        return "Success criteria were not met because execution or site access was blocked"
    return "The agent stopped without satisfying the configured success criteria"


def summarize_records(records: list[dict]) -> dict:
    total = len(records)
    success_count = sum(bool(record["validated_success"]) for record in records)
    failures = Counter(
        record.get("failure_type") or "unclassified_failure"
        for record in records
        if not record["validated_success"]
    )
    by_scenario = {}
    for scenario_id in sorted({record["scenario_id"] for record in records}):
        selected = [record for record in records if record["scenario_id"] == scenario_id]
        passed = sum(bool(record["validated_success"]) for record in selected)
        by_scenario[scenario_id] = {
            "runs": len(selected),
            "successes": passed,
            "success_rate": passed / len(selected) if selected else 0.0,
        }
    return {
        "generated_at": datetime.now().astimezone().isoformat(),
        "total_runs": total,
        "successes": success_count,
        "success_rate": success_count / total if total else 0.0,
        "failure_types": dict(failures),
        "by_scenario": by_scenario,
    }


def render_markdown_summary(summary: dict) -> str:
    lines = [
        "# 网页多模态 Agent 评测汇总",
        "",
        f"- 总测试次数：{summary['total_runs']}",
        f"- 成功次数：{summary['successes']}",
        f"- 总成功率：{summary['success_rate']:.2%}",
        "",
        "## 各场景结果",
        "",
        "| 场景 | 次数 | 成功 | 成功率 |",
        "|---|---:|---:|---:|",
    ]
    for scenario_id, values in summary["by_scenario"].items():
        lines.append(
            f"| {scenario_id} | {values['runs']} | {values['successes']} | "
            f"{values['success_rate']:.2%} |"
        )
    lines.extend(["", "## 失败类型", ""])
    if summary["failure_types"]:
        for failure_type, count in summary["failure_types"].items():
            lines.append(f"- {failure_type}: {count}")
    else:
        lines.append("- 无")
    return "\n".join(lines) + "\n"


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
