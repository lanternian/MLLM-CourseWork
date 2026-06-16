from __future__ import annotations

from .models import RunResult


def format_markdown_reply(result: RunResult) -> str:
    status = "✅ 成功" if result.success else "⚠️ 未成功"
    lines = [
        "### Agent 执行结果",
        "",
        f"- 状态：{status}",
        f"- 完成：{'是' if result.completed else '否'}",
        f"- 步数：{result.steps}",
        f"- 起始地址：{result.start_url}",
        f"- 最终地址：{result.final_url or '(空)'}",
    ]
    if result.final_title:
        lines.append(f"- 页面标题：{result.final_title}")
    if result.answer:
        lines.extend(["", "### 最终回答", "", result.answer])
    if result.error:
        lines.extend(["", "### 错误信息", "", result.error])
    lines.extend(["", f"- 产物目录：`{result.artifact_dir}`"])
    return "\n".join(lines)
