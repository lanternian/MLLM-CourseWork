from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Protocol

from openai import OpenAI

from .config import Settings
from .models import Action, Observation, StepRecord


SYSTEM_PROMPT = """
You are the planning component of a multimodal web agent.
Use the annotated screenshot and visible element list to choose exactly one next action.
The red labels e0, e1, ... identify elements and must be used for click/fill actions.

Return one JSON object only. Supported forms:
{"type":"click","element_id":"e3","reason":"..."}
{"type":"fill","element_id":"e2","text":"...","reason":"..."}
{"type":"press","element_id":"e2","key":"Enter","reason":"..."}
{"type":"scroll","delta_y":600,"reason":"..."}
{"type":"wait","milliseconds":1000,"reason":"..."}
{"type":"goto","url":"https://...","reason":"..."}
{"type":"finish","success":true,"answer":"...","reason":"..."}
{"type":"finish","success":false,"failure_type":"execution_failure","answer":"...","reason":"..."}

Rules:
1. Do not invent element ids.
2. Prefer DOM element ids over coordinate reasoning.
3. Perform only one atomic action.
4. Finish only when the user's goal is visibly satisfied or clearly impossible.
5. Keep text input exactly aligned with the user's request.
6. For a failed finish, classify it as recognition_failure, planning_failure,
   or execution_failure. Captchas and site access blocks are execution failures.
7. After filling a search input, prefer pressing Enter on that same input instead
   of visually guessing a search button.
""".strip()


class PlanningError(RuntimeError):
    pass


class Planner(Protocol):
    def next_action(
        self,
        task: str,
        observation: Observation,
        history: list[StepRecord],
    ) -> Action:
        ...


class QwenVLPlanner:
    def __init__(self, settings: Settings):
        if not settings.api_key:
            raise PlanningError(
                "No API key configured. Set DASHSCOPE_API_KEY, QWEN_API_KEY, "
                "or OPENAI_API_KEY."
            )
        self.settings = settings
        self.client = OpenAI(
            api_key=settings.api_key,
            base_url=settings.base_url,
        )

    def next_action(
        self,
        task: str,
        observation: Observation,
        history: list[StepRecord],
    ) -> Action:
        image_url = _image_data_url(observation.annotated_screenshot_path)
        element_text = "\n".join(
            element.prompt_line() for element in observation.elements
        )
        history_text = "\n".join(
            f"{item.step}: {item.action.type} {item.action.element_id or ''} "
            f"{item.action.text or item.action.key or ''}"
            for item in history[-6:]
        )
        prompt = (
            f"User task: {task}\n"
            f"Current URL: {observation.url}\n"
            f"Page title: {observation.title}\n\n"
            f"Recent actions:\n{history_text or '(none)'}\n\n"
            f"Visible elements:\n{element_text or '(none)'}\n\n"
            f"Visible page text:\n{observation.body_text[:6000]}"
        )
        try:
            response = self.client.chat.completions.create(
                model=self.settings.model,
                temperature=0.1,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": image_url},
                            },
                        ],
                    },
                ],
            )
            content = response.choices[0].message.content
            if not isinstance(content, str):
                raise PlanningError("Model returned non-text content")
            return parse_action(content)
        except PlanningError:
            raise
        except Exception as exc:
            raise PlanningError(f"Model planning failed: {exc}") from exc


def parse_action(content: str) -> Action:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```json", "", 1).replace("```", "").strip()
    decoder = json.JSONDecoder()
    for index, char in enumerate(cleaned):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(cleaned[index:])
            return Action.model_validate(value)
        except (json.JSONDecodeError, ValueError):
            continue
    raise PlanningError(f"Model did not return a valid action: {content[:300]}")


def _image_data_url(path: str) -> str:
    image_path = Path(path)
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    mime = "image/jpeg" if image_path.suffix.lower() in {".jpg", ".jpeg"} else "image/png"
    return f"data:{mime};base64,{encoded}"
