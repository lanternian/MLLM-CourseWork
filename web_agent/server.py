from __future__ import annotations

import uvicorn

from .api import create_app
from .config import Settings


def launch(settings: Settings, host: str = "127.0.0.1", port: int = 8000) -> None:
    app = create_app(settings)
    uvicorn.run(app, host=host, port=port)
