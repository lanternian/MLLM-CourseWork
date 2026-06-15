from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, model_validator


ActionType = Literal["goto", "click", "fill", "press", "scroll", "wait", "finish"]
FailureType = Literal["recognition_failure", "planning_failure", "execution_failure"]


class ElementInfo(BaseModel):
    element_id: str
    tag: str
    role: str = ""
    input_type: str = ""
    text: str = ""
    aria_label: str = ""
    placeholder: str = ""
    href: str = ""
    value: str = ""
    x: float
    y: float
    width: float
    height: float

    def prompt_line(self) -> str:
        attributes = [
            f"id={self.element_id}",
            f"tag={self.tag}",
            f"role={self.role}" if self.role else "",
            f"type={self.input_type}" if self.input_type else "",
            f"text={self.text!r}" if self.text else "",
            f"aria={self.aria_label!r}" if self.aria_label else "",
            f"placeholder={self.placeholder!r}" if self.placeholder else "",
            f"href={self.href!r}" if self.href else "",
            f"value={self.value!r}" if self.value else "",
        ]
        return " | ".join(item for item in attributes if item)


class Observation(BaseModel):
    url: str
    title: str
    body_text: str
    screenshot_path: str
    annotated_screenshot_path: str
    elements: list[ElementInfo]


class Action(BaseModel):
    type: ActionType
    element_id: str | None = None
    text: str | None = None
    key: str | None = None
    delta_y: int | None = None
    url: str | None = None
    milliseconds: int | None = None
    success: bool | None = None
    failure_type: FailureType | None = None
    answer: str | None = None
    reason: str = ""

    @model_validator(mode="after")
    def validate_required_fields(self) -> "Action":
        required = {
            "goto": ("url",),
            "click": ("element_id",),
            "fill": ("element_id", "text"),
            "press": ("key",),
            "finish": ("success",),
        }
        missing = [
            field
            for field in required.get(self.type, ())
            if getattr(self, field) is None
        ]
        if missing:
            raise ValueError(f"{self.type} requires: {', '.join(missing)}")
        return self


class StepRecord(BaseModel):
    step: int
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    url: str
    title: str
    screenshot_path: str
    annotated_screenshot_path: str
    action: Action
    error: str | None = None


class RunResult(BaseModel):
    run_id: str
    task: str
    start_url: str
    completed: bool
    success: bool
    steps: int
    final_url: str = ""
    final_title: str = ""
    final_text: str = ""
    answer: str = ""
    failure_type: FailureType | None = None
    error: str | None = None
    artifact_dir: str


class SuccessCriteria(BaseModel):
    url_contains: list[str] = Field(default_factory=list)
    title_contains: list[str] = Field(default_factory=list)
    text_contains: list[str] = Field(default_factory=list)


class Scenario(BaseModel):
    id: str
    site: str
    start_url: str
    task: str
    repeats: int = 10
    success: SuccessCriteria
