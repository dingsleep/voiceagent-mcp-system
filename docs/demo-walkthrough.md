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
