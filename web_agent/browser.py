from __future__ import annotations

from pathlib import Path
from typing import Optional

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

from .config import Settings
from .models import Action, ElementInfo, Observation
from .perception import COLLECT_ELEMENTS_SCRIPT, annotate_screenshot

# 尝试导入stealth库（可选依赖）
try:
    from playwright_stealth import stealth_sync

    STEALTH_AVAILABLE = True
except ImportError:
    STEALTH_AVAILABLE = False
    stealth_sync = None


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
        
        # 反检测：添加启动参数隐藏自动化特征
        launch_args = [
            '--disable-blink-features=AutomationControlled',  # 关键：禁用自动化控制标识
            '--disable-dev-shm-usage',  # 解决Docker环境中的共享内存问题
            '--no-sandbox',  # 禁用沙箱
            '--disable-setuid-sandbox',
            '--disable-web-security',  # 禁用某些web安全特性（谨慎使用）
            '--disable-features=IsolateOrigins,site-per-process',
        ]
        
        # 如果是headless模式，添加额外参数
        if self.settings.headless:
            launch_args.extend([
                '--disable-gpu',
                '--disable-software-rasterizer',
            ])
        
        # 反检测：启动浏览器
        # 注意：channel='chrome' 需要系统中安装了 Google Chrome
        # 如果没有安装，会自动降级到 Playwright 自带的 Chromium
        launch_kwargs = {
            "headless": self.settings.headless,
            "args": launch_args,
        }
        
        # 非 headless 模式时，尝试使用真实 Chrome（反检测效果更好）
        if not self.settings.headless:
            try:
                # 测试是否可以启动 Chrome
                test_browser = self._playwright.chromium.launch(
                    headless=True,  # 先用 headless 模式测试
                    channel='chrome'
                )
                test_browser.close()
                # 如果成功，使用 Chrome
                launch_kwargs["channel"] = 'chrome'
                print("✅ 使用真实 Chrome 浏览器（反检测效果更佳）")
            except Exception as e:
                print(f"⚠️ 未检测到 Chrome，使用 Playwright Chromium: {e}")
        
        self._browser = self._playwright.chromium.launch(**launch_kwargs)
        
        # 反检测：创建上下文时模拟真实浏览器
        context_options = {
            "viewport": {
                "width": self.settings.viewport_width,
                "height": self.settings.viewport_height,
            },
            "locale": "zh-CN",
            "timezone_id": "Asia/Shanghai",
            "extra_http_headers": {
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",  # Do Not Track
                "Upgrade-Insecure-Requests": "1",
            },
        }
        
        self._context = self._browser.new_context(**context_options)
        
        # 反检测：覆盖navigator.webdriver等属性
        self._context.add_init_script("""
            // 覆盖navigator.webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // 覆盖window.chrome
            window.chrome = {
                runtime: {}
            };
            
            // 覆盖permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            // 覆盖插件检测
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // 覆盖语言
            Object.defineProperty(navigator, 'languages', {
                get: () => ['zh-CN', 'zh', 'en']
            });
        """)
        
        self._page = self._context.new_page()
        
        # 应用playwright-stealth（如果可用）
        if STEALTH_AVAILABLE and stealth_sync:
            try:
                stealth_sync(self._page)
                print("✅ Playwright Stealth 已启用")
            except Exception as e:
                print(f"⚠️ Stealth应用失败: {e}")
        
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

    def detect_captcha(self) -> dict:
        """
        检测页面是否存在验证码或人机验证
        返回检测结果字典：{detected: bool, type: str, message: str}
        """
        try:
            page_text = self.page.locator("body").inner_text().lower()
            
            # 定义检测关键词
            captcha_markers = {
                "tcaptcha": ["tcaptcha", "腾讯验证码", "滑块验证"],
                "recaptcha": ["recaptcha", "i'm not a robot", "我不是机器人"],
                "hcaptcha": ["hcaptcha"],
                "generic": ["验证码", "人机验证", "安全验证", "captcha", 
                           "verify you are human", "安全检测", "异常访问"],
                "cloudflare": ["just a moment", "checking your browser", "cloudflare"],
            }
            
            detected_markers = []
            for captcha_type, keywords in captcha_markers.items():
                for keyword in keywords:
                    if keyword in page_text:
                        detected_markers.append((captcha_type, keyword))
            
            if detected_markers:
                # 尝试识别具体类型
                captcha_type = detected_markers[0][0]
                keywords_found = [marker[1] for marker in detected_markers]
                
                return {
                    "detected": True,
                    "type": captcha_type,
                    "message": f"检测到验证码/人机验证 (类型: {captcha_type}, 关键词: {keywords_found})",
                    "keywords": keywords_found
                }
            
            # 检查是否存在常见的验证码iframe或元素
            captcha_elements = [
                "iframe[src*='captcha']",
                "iframe[src*='tcaptcha']",
                "div[class*='captcha']",
                "div[id*='captcha']",
                ".verify-wrap",
                "#tcaptcha_popup",
            ]
            
            for selector in captcha_elements:
                try:
                    if self.page.locator(selector).count() > 0:
                        return {
                            "detected": True,
                            "type": "element_detected",
                            "message": f"检测到验证码元素: {selector}",
                            "keywords": [selector]
                        }
                except:
                    continue
            
            return {"detected": False, "type": None, "message": "未检测到验证码", "keywords": []}
        
        except Exception as e:
            return {"detected": False, "type": "error", "message": f"检测过程出错: {str(e)}", "keywords": []}

    def wait_for_human_intervention(self, max_wait_seconds: int = 120) -> bool:
        """
        等待人工介入完成验证码
        返回是否成功（验证码消失）
        """
        print(f"⚠️ 检测到验证码，请在 {max_wait_seconds} 秒内手动完成验证...")
        print(f"   浏览器窗口已打开，请手动完成验证后，程序将继续执行")
        
        try:
            for i in range(max_wait_seconds // 5):
                self.page.wait_for_timeout(5000)  # 每5秒检查一次
                
                # 检查验证码是否还存在
                result = self.detect_captcha()
                if not result["detected"]:
                    print("✅ 验证码已处理，继续执行...")
                    return True
                
                remaining = max_wait_seconds - (i + 1) * 5
                if remaining > 0:
                    print(f"   等待中... 剩余 {remaining} 秒")
            
            print("❌ 等待超时，验证码未被处理")
            return False
        
        except Exception as e:
            print(f"❌ 等待过程出错: {e}")
            return False

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
