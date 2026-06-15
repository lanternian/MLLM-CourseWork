安装

```powershell
python -m pip install -r requirements.txt
python -m playwright install chromium
$env:DASHSCOPE_API_KEY = "你的 API Key"
```

默认模型为 `qwen2.5-vl-72b-instruct`，可通过环境变量调整：

```powershell
$env:WEB_AGENT_MODEL = "qwen2.5-vl-72b-instruct"
$env:WEB_AGENT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
$env:WEB_AGENT_HEADLESS = "false"
```

运行

```powershell
python -m web_agent run `
  --url "https://www.baidu.com/" `
  --task "搜索 Mind2Web 数据集，看到搜索结果后结束任务"
```

# 网页多模态 Agent

本项目按照《网页多模态 Agent 开题报告》实现预期成果前四项：

1. 基于 Playwright 的网页自动操作 Agent。
2. 支持自然语言任务输入并自动点击、输入、滚动和跳转。
3. 融合页面截图与 DOM，标注并识别可交互元素，使用 Qwen2.5-VL 规划动作。
4. 提供百度、哔哩哔哩两个真实网站共 6 个任务 Demo。

## 系统流程

```text
自然语言任务
  -> Playwright 获取截图、DOM 和页面文本
  -> 元素编号与截图标注
  -> Qwen2.5-VL 输出单步 JSON 动作
  -> Playwright 执行动作
  -> 循环观察，直到完成或达到步数上限
```

每次运行会在 `artifacts/<run_id>/` 保存：

- 原始截图 `step_*.png`
- 元素识别截图 `step_*_annotated.jpg`
- 动作序列 `steps.jsonl`
- 最终结果 `result.json`


