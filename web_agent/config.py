from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    api_key: str
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    model: str = "qwen2.5-vl-72b-instruct"
    headless: bool = False
    max_steps: int = 15
    timeout_ms: int = 20_000
    viewport_width: int = 1440
    viewport_height: int = 900
    artifacts_dir: Path = Path("artifacts")

    @classmethod
    def from_env(cls) -> "Settings":
        api_key = (
            os.getenv("DASHSCOPE_API_KEY")
            or os.getenv("QWEN_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or ""
        )
        return cls(
            api_key=api_key,
            base_url=os.getenv(
                "WEB_AGENT_BASE_URL",
                "https://dashscope.aliyuncs.com/compatible-mode/v1",
            ),
            model=os.getenv("WEB_AGENT_MODEL", "qwen3.7-plus"),
            headless=_as_bool(os.getenv("WEB_AGENT_HEADLESS", "false")),
            max_steps=int(os.getenv("WEB_AGENT_MAX_STEPS", "15")),
            timeout_ms=int(os.getenv("WEB_AGENT_TIMEOUT_MS", "20000")),
            artifacts_dir=Path(os.getenv("WEB_AGENT_ARTIFACTS_DIR", "artifacts")),
        )


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}

