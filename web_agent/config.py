from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


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
        return cls.from_dict(_load_env_config())

    @classmethod
    def from_file(cls, path: str | Path) -> "Settings":
        config_path = Path(path)
        data: dict[str, Any] = {}
        if config_path.exists():
            data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Settings":
        api_key = str(
            data.get("api_key")
            or data.get("dashscope_api_key")
            or data.get("qwen_api_key")
            or data.get("openai_api_key")
            or ""
        )
        return cls(
            api_key=api_key,
            base_url=str(
                data.get("base_url")
                or data.get("web_agent_base_url")
                or "https://dashscope.aliyuncs.com/compatible-mode/v1"
            ),
            model=str(data.get("model") or data.get("web_agent_model") or "qwen3.7-plus"),
            headless=_to_bool(data.get("headless"), default=False),
            max_steps=int(data.get("max_steps") or 15),
            timeout_ms=int(data.get("timeout_ms") or 20_000),
            viewport_width=int(data.get("viewport_width") or 1440),
            viewport_height=int(data.get("viewport_height") or 900),
            artifacts_dir=Path(data.get("artifacts_dir") or "artifacts"),
        )


def _load_env_config() -> dict[str, Any]:
    return {
        "api_key": os.getenv("DASHSCOPE_API_KEY")
        or os.getenv("QWEN_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or "",
        "base_url": os.getenv(
            "WEB_AGENT_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
        ),
        "model": os.getenv("WEB_AGENT_MODEL", "qwen3.7-plus"),
        "headless": _to_bool(os.getenv("WEB_AGENT_HEADLESS"), default=False),
        "max_steps": int(os.getenv("WEB_AGENT_MAX_STEPS", "15")),
        "timeout_ms": int(os.getenv("WEB_AGENT_TIMEOUT_MS", "20000")),
        "artifacts_dir": os.getenv("WEB_AGENT_ARTIFACTS_DIR", "artifacts"),
    }


def _to_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}

