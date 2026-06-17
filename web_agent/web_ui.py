from __future__ import annotations

import gradio as gr

from .agent import WebAgent
from .chat import format_markdown_reply
from .config import Settings
from .planner import QwenVLPlanner


APP_CSS = """
:root {
    --bg: #070b14;
    --panel: rgba(12, 18, 33, 0.78);
    --panel-strong: rgba(16, 24, 44, 0.92);
    --border: rgba(110, 168, 255, 0.22);
    --border-strong: rgba(110, 168, 255, 0.38);
    --text: #eaf2ff;
    --muted: #93a4c3;
    --accent: #67b7ff;
    --accent-strong: #8f7bff;
    --success: #47d6a5;
}

body {
    background:
        radial-gradient(circle at top, rgba(103, 183, 255, 0.16), transparent 32%),
        radial-gradient(circle at bottom right, rgba(143, 123, 255, 0.14), transparent 28%),
        linear-gradient(180deg, #050814 0%, #0a1020 100%);
    color: var(--text);
}

body::before,
body::after {
    content: "";
    position: fixed;
    inset: auto;
    pointer-events: none;
    z-index: 0;
}

body::before {
    left: 0;
    right: 0;
    bottom: 0;
    height: 260px;
    background:
        linear-gradient(90deg, rgba(103, 183, 255, 0.08) 1px, transparent 1px) 0 0 / 42px 42px,
        linear-gradient(180deg, rgba(143, 123, 255, 0.08) 1px, transparent 1px) 0 0 / 42px 42px;
    mask-image: linear-gradient(180deg, transparent 0%, rgba(0, 0, 0, 0.82) 28%, rgba(0, 0, 0, 0.95) 100%);
    opacity: 0.6;
}

body::after {
    left: 0;
    right: 0;
    bottom: 0;
    height: 190px;
    background:
        radial-gradient(circle at 20% 30%, rgba(103, 183, 255, 0.22), transparent 12%),
        radial-gradient(circle at 42% 55%, rgba(143, 123, 255, 0.18), transparent 14%),
        radial-gradient(circle at 72% 28%, rgba(71, 214, 165, 0.12), transparent 11%),
        radial-gradient(circle at 88% 70%, rgba(103, 183, 255, 0.16), transparent 10%);
    filter: blur(3px);
    opacity: 0.85;
}

.gradio-container {
    position: relative;
    z-index: 1;
    max-width: 1180px !important;
    margin: 0 auto !important;
    padding: 28px 22px 72px !important;
}

#hero-panel {
    border: 1px solid var(--border);
    border-radius: 24px;
    background: linear-gradient(135deg, rgba(16, 24, 44, 0.88), rgba(8, 13, 25, 0.82));
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.35);
    backdrop-filter: blur(18px);
    padding: 22px 24px;
    margin-bottom: 18px;
}

#hero-title {
    font-size: 2rem;
    font-weight: 800;
    letter-spacing: 0.02em;
    margin: 0;
    background: linear-gradient(90deg, #f0f6ff 0%, #7cc7ff 45%, #a58bff 100%);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
}

#hero-subtitle {
    margin-top: 8px;
    color: var(--muted);
    line-height: 1.7;
}

#stats-row {
    margin-top: 16px;
}

.stat-card {
    border: 1px solid var(--border);
    border-radius: 18px;
    background: rgba(10, 16, 31, 0.78);
    padding: 14px 16px;
    min-height: 86px;
}

.stat-label {
    color: var(--muted);
    font-size: 0.82rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin-bottom: 8px;
}

.stat-value {
    color: var(--text);
    font-size: 0.98rem;
    font-weight: 600;
    line-height: 1.45;
    word-break: break-word;
}

#control-panel,
#chat-panel,
#status-panel {
    border: 1px solid var(--border);
    border-radius: 24px;
    background: var(--panel);
    box-shadow: 0 18px 50px rgba(0, 0, 0, 0.24);
    backdrop-filter: blur(16px);
    overflow: hidden;
}

#control-panel {
    padding: 18px 18px 6px;
    margin-bottom: 18px;
}

#chat-panel {
    padding: 16px 18px 18px;
    margin-bottom: 18px;
}

#status-panel {
    padding: 18px;
    margin-top: 8px;
}

#section-title {
    font-size: 1rem;
    font-weight: 700;
    color: var(--text);
    margin-bottom: 10px;
    letter-spacing: 0.02em;
}

#section-hint {
    color: var(--muted);
    font-size: 0.9rem;
    margin-bottom: 14px;
}

input, textarea {
    background: rgba(8, 13, 25, 0.92) !important;
    border: 1px solid rgba(110, 168, 255, 0.18) !important;
    color: var(--text) !important;
    border-radius: 14px !important;
}

input:focus, textarea:focus {
    border-color: var(--border-strong) !important;
    box-shadow: 0 0 0 1px rgba(103, 183, 255, 0.18) !important;
}

button {
    border-radius: 14px !important;
}

#send-btn button,
button.primary {
    background: linear-gradient(135deg, var(--accent), var(--accent-strong)) !important;
    border: none !important;
    color: white !important;
    box-shadow: 0 10px 30px rgba(103, 183, 255, 0.25);
}

#send-btn button:hover,
button.primary:hover {
    transform: translateY(-1px);
}

.gr-chatbot {
    background: rgba(7, 11, 20, 0.58) !important;
    border: 1px solid rgba(110, 168, 255, 0.18) !important;
    border-radius: 18px !important;
}

.gr-chatbot .message {
    border-radius: 16px !important;
}

.gr-chatbot .message.user {
    background: linear-gradient(135deg, rgba(103, 183, 255, 0.18), rgba(143, 123, 255, 0.18)) !important;
    border: 1px solid rgba(103, 183, 255, 0.18) !important;
}

.gr-chatbot .message.bot {
    background: rgba(12, 18, 33, 0.96) !important;
    border: 1px solid rgba(110, 168, 255, 0.14) !important;
}

.status-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 14px;
}

.status-item {
    border: 1px solid rgba(110, 168, 255, 0.16);
    border-radius: 18px;
    background: linear-gradient(180deg, rgba(13, 20, 38, 0.95), rgba(9, 14, 27, 0.84));
    padding: 14px 16px;
    position: relative;
    overflow: hidden;
}

.status-item::before {
    content: "";
    position: absolute;
    left: 0;
    top: 0;
    width: 100%;
    height: 2px;
    background: linear-gradient(90deg, transparent, rgba(103, 183, 255, 0.95), transparent);
    opacity: 0.75;
}

.status-kicker {
    color: var(--muted);
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    margin-bottom: 10px;
}

.status-value {
    color: var(--text);
    font-size: 0.98rem;
    font-weight: 700;
    line-height: 1.4;
}

.status-value.dim {
    color: #b8c7e6;
    font-weight: 500;
}

.status-panel-title {
    font-size: 1rem;
    font-weight: 700;
    color: var(--text);
    margin-bottom: 10px;
}

.status-panel-subtitle {
    color: var(--muted);
    font-size: 0.9rem;
    margin-bottom: 14px;
}

@media (max-width: 900px) {
    .status-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
}
"""


def create_app(settings: Settings) -> gr.Blocks:
    planner = QwenVLPlanner(settings)
    agent = WebAgent(settings, planner)

    def _telemetry_card(label: str, value: str, dim: bool = False) -> str:
        cls = "status-value dim" if dim else "status-value"
        return f"<div class='status-item'><div class='status-kicker'>{label}</div><div class='{cls}'>{value}</div></div>"

    def _telemetry_state(mode: str, model: str, api_status: str, execution: str) -> str:
        return (
            _telemetry_card("Current Mode", mode)
            + _telemetry_card("Model", model)
            + _telemetry_card("API", api_status)
            + _telemetry_card("Execution", execution, dim=True)
        )

    def run_chat(task: str, url: str, history: list[dict[str, str]]):
        task = (task or "").strip()
        url = (url or "").strip()
        history = list(history or [])

        if not task:
            history.append({"role": "assistant", "content": "请输入任务描述。"})
            return history, history, "", _telemetry_state("Idle", settings.model, "DashScope Compatible", "Waiting for incoming task...")
        if not url:
            history.append({"role": "assistant", "content": "请输入起始网址。"})
            return history, history, "", _telemetry_state("Idle", settings.model, "DashScope Compatible", "Waiting for incoming task...")

        history.append({"role": "user", "content": task})
        history.append({"role": "assistant", "content": "正在执行，请稍候..."})
        telemetry_running = _telemetry_state("Running", settings.model, "DashScope Compatible", f"Executing task: {task}")
        result = agent.run(task=task, start_url=url)
        history[-1] = {"role": "assistant", "content": format_markdown_reply(result)}
        telemetry_final = _telemetry_state(
            "Success" if result.success else "Error" if result.error else "Idle",
            settings.model,
            "DashScope Compatible",
            f"Completed in {result.steps} step(s)" if result.completed else (result.error or "Waiting for incoming task..."),
        )
        return history, history, "", telemetry_final

    with gr.Blocks(title="Web Agent Chat", css=APP_CSS) as demo:
        with gr.Column(elem_id="hero-panel"):
            gr.Markdown("<div id='hero-title'>Web Agent Control Console</div>")
            gr.Markdown(
                "<div id='hero-subtitle'>"
                "输入任务与起始网址，系统将调用多模态 Agent 自动执行网页操作，并以 Markdown 形式返回结果。"
                "</div>"
            )
            with gr.Row(elem_id="stats-row"):
                with gr.Column(scale=1, min_width=220):
                    gr.Markdown(
                        "<div class='stat-card'><div class='stat-label'>Mode</div>"
                        "<div class='stat-value'>Interactive Web Agent</div></div>"
                    )
                with gr.Column(scale=1, min_width=220):
                    gr.Markdown(
                        "<div class='stat-card'><div class='stat-label'>Output</div>"
                        "<div class='stat-value'>Markdown Response</div></div>"
                    )
                with gr.Column(scale=1, min_width=220):
                    gr.Markdown(
                        "<div class='stat-card'><div class='stat-label'>Engine</div>"
                        f"<div class='stat-value'>{settings.model}</div></div>"
                    )

        with gr.Column(elem_id="control-panel"):
            gr.Markdown("<div id='section-title'>Mission Inputs</div>")
            gr.Markdown("<div id='section-hint'>填写起始网址与任务描述，然后点击发送。支持中文自然语言指令。</div>")
            with gr.Row():
                url_box = gr.Textbox(
                    label="起始网址",
                    value="https://www.baidu.com/",
                    placeholder="https://www.baidu.com/",
                    scale=2,
                )
            task_box = gr.Textbox(
                label="任务",
                placeholder="例如：搜索 Mind2Web 数据集，看到搜索结果后结束任务",
                lines=4,
            )
            with gr.Row():
                send_btn = gr.Button("发送并执行", variant="primary", elem_id="send-btn")

        with gr.Column(elem_id="chat-panel"):
            gr.Markdown("<div id='section-title'>Conversation Stream</div>")
            gr.Markdown("<div id='section-hint'>下方会显示任务执行过程与最终 Markdown 回复。</div>")
            chat = gr.Chatbot(label="对话", height=620)
            state = gr.State([])

        with gr.Column(elem_id="status-panel"):
            gr.Markdown("<div class='status-panel-title'>System Telemetry</div>")
            telemetry_state = gr.HTML(
                _telemetry_state("Idle", settings.model, "DashScope Compatible", "Waiting for incoming task...")
            )

        send_btn.click(
            fn=run_chat,
            inputs=[task_box, url_box, state],
            outputs=[chat, state, task_box, telemetry_state],
        )

        task_box.submit(
            fn=run_chat,
            inputs=[task_box, url_box, state],
            outputs=[chat, state, task_box, telemetry_state],
        )

    return demo


def launch(settings: Settings, share: bool = False) -> None:
    app = create_app(settings)
    app.launch(server_name="127.0.0.1", server_port=7860, share=share)
