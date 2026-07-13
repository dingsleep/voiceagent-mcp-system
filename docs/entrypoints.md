# Project Entrypoints

这份文档把项目入口讲清楚，避免读者把 demo、原服务、训练脚本和 benchmark 混在一起。

## 本地可跑 Demo

| Entrypoint | Purpose | Command |
| --- | --- | --- |
| `voice_agent_mcp/cli.py` | 无密钥 CLI 演示链路 | `python -m voice_agent_mcp.cli --query "北京明天天气怎么样"` |
| `voice_agent_mcp/api.py` | 无密钥 HTTP demo | `python -m voice_agent_mcp.api` |
| `eval/evaluate_demo.py` | Demo 离线评测 | `python eval/evaluate_demo.py` |
| `scripts/check_project.py` | 发布前自检 | `python scripts/check_project.py` |
| `scripts/check_env.py` | 环境变量自检 | `python scripts/check_env.py` |
| `scripts/check_text_quality.py` | README / docs / examples 文本质量检查 | `python scripts/check_text_quality.py --strict` |
| `scripts/check_release.py` | GitHub 上传前检查 | `python scripts/check_release.py --strict` |

## 原完整链路

| Entrypoint | Purpose | Notes |
| --- | --- | --- |
| `start.py` | Socket.IO 对话网关 | 依赖 Redis、LLM API、NLU / Reject / Intent 服务 |
| `dialog.py` | Socket.IO 交互客户端 | 连接 `ENTRY_URL`，用于手动发送多轮 query |
| `function_call/chatnlu_infer.py` | NLU 服务入口 | 保留 `/chatnlu-server/v1` 接口 |
| `mcp_core/music_server.py` | MCP 风格音乐工具服务 | 原工具服务示例 |
| `mcp_core/amp_server.py` | MCP 风格地图/车控工具服务 | 原工具服务示例 |
| `mcp_core/mcp_client.py` | MCP client 调用封装 | 被 DM 或工具调用链路使用 |

## 模型与评测

| Path | Purpose |
| --- | --- |
| `train/run.py` | BERT 意图 / 拒识模型训练入口 |
| `train/intent_infer.py` | 意图模型推理 |
| `train/reject_infer.py` | 拒识模型推理 |
| `test/intent_benchmark.py` | 意图识别 benchmark |
| `test/nlu_benchmark.py` | NLU benchmark |
| `test/reject_benchmark.py` | 拒识 benchmark |

## Legacy Smoke Examples

`examples/legacy/` 保存的是需要外部服务和 `.env` 的手动验证脚本，不属于默认测试链路。

| Script | Purpose |
| --- | --- |
| `examples/legacy/llm_api_smoke.py` | 验证 OpenAI-compatible LLM API 是否可用 |
| `examples/legacy/function_call_smoke.py` | 验证 Function Calling JSON 请求 |
| `examples/legacy/function_call_raw_smoke.py` | 验证原 NLU raw JSON 请求形态 |
| `examples/legacy/socketio_multi_turn_smoke.py` | 验证原 Socket.IO 多轮链路 |

默认贡献和展示优先跑 `scripts/check_project.py`。只有在部署了原完整链路依赖后，才需要运行 `examples/legacy/`。
