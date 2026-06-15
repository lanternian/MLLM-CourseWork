from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

from .config import Settings
from .models import Action, ElementInfo, Observation
from .perception import COLLECT_ELEMENTS_SCRIPT, annotate_screenshot


class PerceptionError(RuntimeError):
    pass


class ExecutionError(RuntimeError):
    pass


class BrowserController:
    def __init__(self, settings: Settings, artifact_dir: Path):
        self.settings = settings
        self.artifact_dir = artifact_dir
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    def __enter__(self) -> "BrowserController":
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @property
    def page(self) -> Page:
        if self._context:
            open_pages = [page for page in self._context.pages if not page.is_closed()]
            if open_pages:
                self._page = open_pages[-1]
        if self._page is None:
            raise ExecutionError("Browser page is not available")
        return self._page

    def start(self) -> None:
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=self.settings.headless
        )
        self._context = self._browser.new_context(
            viewport={
                "width": self.settings.viewport_width,
                "height": self.settings.viewport_height,
            },
            locale="zh-CN",
        )
        self._page = self._context.new_page()
        self._page.set_default_timeout(self.settings.timeout_ms)

    def open(self, url: str) -> None:
        try:
            self.page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=self.settings.timeout_ms,
            )
            self.page.wait_for_timeout(800)
        except Exception as exc:
            raise ExecutionError(f"Failed to open {url}: {exc}") from exc

    def observe(self, step: int) -> Observation:
        raw_path = self.artifact_dir / f"step_{step:02d}.png"
        annotated_path = self.artifact_dir / f"step_{step:02d}_annotated.jpg"
        try:
            raw_elements = self.page.evaluate(COLLECT_ELEMENTS_SCRIPT)
            elements = [ElementInfo.model_validate(item) for item in raw_elements]
            self.page.screenshot(path=str(raw_path), full_page=False)
            annotate_screenshot(raw_path, annotated_path, elements)
            body_text = self.page.locator("body").inner_text(timeout=5_000)[:12_000]
            return Observation(
                url=self.page.url,
                title=self.page.title(),
                body_text=body_text,
                screenshot_path=str(raw_path),
                annotated_screenshot_path=str(annotated_path),
                elements=elements,
            )
        except Exception as exc:
            raise PerceptionError(f"Failed to observe page: {exc}") from exc

    def execute(self, action: Action) -> None:
        try:
            if action.type == "goto":
                self.open(action.url or "")
            elif action.type == "click":
                self._element(action.element_id).click()
                self.page.wait_for_timeout(800)
            elif action.type == "fill":
                self._element(action.element_id).fill(action.text or "")
            elif action.type == "press":
                if action.element_id:
                    self._element(action.element_id).press(action.key or "")
                else:
                    self.page.keyboard.press(action.key or "")
                self.page.wait_for_timeout(800)
            elif action.type == "scroll":
                self.page.mouse.wheel(0, action.delta_y or 600)
                self.page.wait_for_timeout(500)
            elif action.type == "wait":
                self.page.wait_for_timeout(action.milliseconds or 1000)
            elif action.type == "finish":
                return
            else:
                raise ExecutionError(f"Unsupported action: {action.type}")
        except ExecutionError:
            raise
        except Exception as exc:
            raise ExecutionError(
                f"Failed to execute {action.type} on {action.element_id}: {exc}"
            ) from exc

    def close(self) -> None:
        if self._context:
            self._context.close()
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()
        self._page = None
        self._context = None
        self._browser = None
        self._playwright = None

    def _element(self, element_id: str | None):
        if not element_id:
            raise ExecutionError("Action does not include element_id")
        selector = f'[data-web-agent-id="{element_id}"]'
        matches = self.page.locator(selector)
        visible_matches = self.page.locator(f"{selector}:visible")
        visible_count = visible_matches.count()
        if visible_count == 0:
            if matches.count() > 0:
                raise ExecutionError(
                    f"Element {element_id} exists but is no longer visible"
                )
            raise ExecutionError(f"Element {element_id} no longer exists")
        if visible_count > 1:
            raise ExecutionError(
                f"Element id {element_id} is not unique: "
                f"{visible_count} visible matches"
            )
        return visible_matches
