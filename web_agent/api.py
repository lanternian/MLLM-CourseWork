from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .agent import WebAgent
from .chat import format_markdown_reply
from .config import Settings
from .planner import PlanningError, QwenVLPlanner


class ChatRequest(BaseModel):
    task: str = Field(..., min_length=1)
    url: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    reply: str
    result: dict[str, Any]


@dataclass
class AppState:
    settings: Settings
    planner: QwenVLPlanner
    agent: WebAgent


class AgentAPI:
    def __init__(self, settings: Settings):
        planner = QwenVLPlanner(settings)
        self.state = AppState(settings=settings, planner=planner, agent=WebAgent(settings, planner))

    def create_app(self) -> FastAPI:
        app = FastAPI(title="Web Agent API", version="0.1.0")
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        @app.get("/health")
        def health() -> dict[str, str]:
            return {"status": "ok"}

        @app.post("/api/chat", response_model=ChatResponse)
        def chat(request: ChatRequest) -> ChatResponse:
            try:
                result = self.state.agent.run(task=request.task, start_url=request.url)
            except PlanningError as exc:
                raise HTTPException(status_code=500, detail=str(exc)) from exc
            reply = format_markdown_reply(result)
            return ChatResponse(reply=reply, result=result.model_dump())

        return app


def create_app(settings: Settings) -> FastAPI:
    return AgentAPI(settings).create_app()
