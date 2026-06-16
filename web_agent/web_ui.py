from __future__ import annotations

import gradio as gr

from .agent import WebAgent
from .chat import format_markdown_reply
from .config import Settings
from .planner import QwenVLPlanner


def create_app(settings: Settings) -> gr.Blocks:
    planner = QwenVLPlanner(settings)
    agent = WebAgent(settings, planner)

    def run_chat(task: str, url: str, history: list[dict[str, str]]):
        task = (task or "").strip()
        url = (url or "").strip()
        history = list(history or [])

        if not task:
            history.append({"role": "assistant", "content": "请输入任务描述。"})
            return history, history, ""
        if not url:
            history.append({"role": "assistant", "content": "请输入起始网址。"})
            return history, history, ""

        history.append({"role": "user", "content": task})
        history.append({"role": "assistant", "content": "正在执行，请稍候..."})
        result = agent.run(task=task, start_url=url)
        history[-1] = {"role": "assistant", "content": format_markdown_reply(result)}
        return history, history, ""

    with gr.Blocks(title="Web Agent Chat") as demo:
        gr.Markdown("# Web Agent Chat\n输入任务和起始网址，Agent 会返回 Markdown 格式结果。")
        with gr.Row():
            url_box = gr.Textbox(label="起始网址", value="https://www.baidu.com/", placeholder="https://www.baidu.com/")
        task_box = gr.Textbox(
            label="任务",
            placeholder="例如：搜索 Mind2Web 数据集，看到搜索结果后结束任务",
            lines=4,
        )
        send_btn = gr.Button("发送并执行", variant="primary")
        chat = gr.Chatbot(label="对话", height=620)
        state = gr.State([])

        send_btn.click(
            fn=run_chat,
            inputs=[task_box, url_box, state],
            outputs=[chat, state, task_box],
        )

        task_box.submit(
            fn=run_chat,
            inputs=[task_box, url_box, state],
            outputs=[chat, state, task_box],
        )

    return demo


def launch(settings: Settings, share: bool = False) -> None:
    app = create_app(settings)
    app.launch(server_name="127.0.0.1", server_port=7860, share=share)
