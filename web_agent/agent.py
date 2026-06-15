from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from .browser import BrowserController, ExecutionError, PerceptionError
from .config import Settings
from .models import Action, RunResult, StepRecord
from .planner import Planner, PlanningError


class WebAgent:
    def __init__(self, settings: Settings, planner: Planner):
        self.settings = settings
        self.planner = planner

    def run(
        self,
        task: str,
        start_url: str,
        run_id: str | None = None,
    ) -> RunResult:
        resolved_id = run_id or uuid4().hex[:12]
        artifact_dir = self.settings.artifacts_dir / resolved_id
        history: list[StepRecord] = []
        failure_type = None
        error = None
        completed = False
        success = False
        answer = ""
        final_url = ""
        final_title = ""
        final_text = ""

        browser = BrowserController(self.settings, artifact_dir)
        try:
            browser.start()
            browser.open(start_url)
            for step in range(1, self.settings.max_steps + 1):
                observation = browser.observe(step)
                final_url = observation.url
                final_title = observation.title
                final_text = observation.body_text
                
                # 反检测：检查是否遇到验证码
                captcha_result = browser.detect_captcha()
                if captcha_result["detected"]:
                    print(f"\n⚠️ 步骤 {step}: {captcha_result['message']}")
                    
                    # 等待人工介入
                    if not browser.wait_for_human_intervention(max_wait_seconds=120):
                        failure_type = "execution_failure"
                        error = f"验证码未被处理: {captcha_result['message']}"
                        break
                    
                    # 人工介入后重新观察页面
                    observation = browser.observe(step)
                    final_url = observation.url
                    final_title = observation.title
                    final_text = observation.body_text
                
                action = self.planner.next_action(task, observation, history)
                record = StepRecord(
                    step=step,
                    url=observation.url,
                    title=observation.title,
                    screenshot_path=observation.screenshot_path,
                    annotated_screenshot_path=observation.annotated_screenshot_path,
                    action=action,
                )
                history.append(record)
                if action.type == "finish":
                    _append_record(artifact_dir / "steps.jsonl", record)
                    completed = True
                    success = bool(action.success)
                    answer = action.answer or ""
                    if not success:
                        failure_type = action.failure_type or "planning_failure"
                        error = answer or action.reason or "Task was not completed"
                    break
                try:
                    browser.execute(action)
                except ExecutionError as exc:
                    record.error = str(exc)
                    _append_record(artifact_dir / "steps.jsonl", record)
                    raise
                _append_record(artifact_dir / "steps.jsonl", record)
            else:
                failure_type = "planning_failure"
                error = f"Maximum step count reached: {self.settings.max_steps}"
        except PerceptionError as exc:
            failure_type = "recognition_failure"
            error = str(exc)
        except PlanningError as exc:
            failure_type = "planning_failure"
            error = str(exc)
        except ExecutionError as exc:
            failure_type = "execution_failure"
            error = str(exc)
        except Exception as exc:
            failure_type = "execution_failure"
            error = f"Unexpected browser error: {exc}"
        finally:
            try:
                browser.close()
            except Exception as exc:
                if error is None:
                    failure_type = "execution_failure"
                    error = f"Failed to close browser: {exc}"

        result = RunResult(
            run_id=resolved_id,
            task=task,
            start_url=start_url,
            completed=completed,
            success=success,
            steps=len(history),
            final_url=final_url,
            final_title=final_title,
            final_text=final_text,
            answer=answer,
            failure_type=failure_type,
            error=error,
            artifact_dir=str(artifact_dir),
        )
        (artifact_dir / "result.json").write_text(
            result.model_dump_json(indent=2),
            encoding="utf-8",
        )
        return result


def _append_record(path: Path, record: StepRecord) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record.model_dump(), ensure_ascii=False) + "\n")
