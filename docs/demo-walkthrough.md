# Demo Walkthrough

这份文档用于面试或 GitHub 浏览时快速说明：项目不是只打印一句回复，而是保留了任务型对话 Agent 的核心链路。

## 运行命令

```bash
python -m voice_agent_mcp.cli --query "北京明天天气怎么样"
```

## 链路拆解

| Step | Module | Output |
| --- | --- | --- |
| Query Rewrite | `voice_agent_mcp/rewrite.py` | 补全多轮省略表达，产出当前轮可独立理解的 query |
| Arbitration | `voice_agent_mcp/arbitration.py` | 判断 query 是 task、chat 还是 reject |
| NLU | `voice_agent_mcp/nlu.py` | 输出 intent、function、slots |
| Tool Call | `voice_agent_mcp/tools.py` | 根据 function 调用天气、音乐、地图等工具 |
| NLG | `voice_agent_mcp/agent.py` | 把结构化工具结果转成语音播报文案 |
| Streaming Frame | `voice_agent_mcp/frames.py` | 按 delta / final frame 返回，模拟语音助手流式输出 |

## NLU 运行模式

默认使用 `rule` 后端，保证无模型、无网络时仍可演示。设置 `VOICE_AGENT_NLU_BACKEND=remote` 或 CLI 参数 `--nlu-backend remote` 后，Demo 会调用已有的 `/chatnlu-server/v1` 服务。

远程调用携带 `query`、`trace_id` 和 `enable_dm=false`，并校验返回的 `intent`、`function`、`slots`。服务不可达、响应不合法或工具不在 Demo 注册表中时，系统自动回落到规则后端。每个最终 frame 的 `metadata` 会记录后端、降级原因和总耗时，便于定位问题。

远程模式评测必须显式执行 `--allow-network`，并建议写入 `eval/reports/`：

```bash
python eval/evaluate_demo.py --backend remote --allow-network --report eval/reports/remote-report.json
```

报告会分别呈现端到端结果、远程 NLU 成功率、fallback 原因和 P50/P95 延迟；规则后端的默认评测不会请求任何外部服务。

## 示例输出

```text
北京明天天气晴，气温18-27C。
{'intent': 'weather_query', 'function': 'weather.query', 'slots': {'city': '北京', 'date': '明天'}}
```

## 为什么保留 Mock Demo

原完整链路依赖 Redis、LLM API、NLU 服务、Reject 服务、Intent 服务和 MCP 工具服务。面试官或招聘方很难在 10 分钟内配齐这些私有服务。

`voice_agent_mcp/` 的目标不是替代原项目，而是把同一条链路做成无密钥、无外部服务的可运行展示层。这样 GitHub 用户可以先跑通主流程，再查看 `client/`、`function_call/`、`mcp_core/`、`train/` 里的完整实现。

## 可以继续扩展的点

- 把 `voice_agent_mcp/tools.py` 的 mock tool 替换为真实 MCP client。
- 把 `voice_agent_mcp/nlu.py` 替换为 `function_call/chatnlu_infer.py` 或远程 NLU 服务。
- 给每一步增加 latency 统计，形成 rewrite、arbitration、NLU、tool、NLG 的耗时报告。
