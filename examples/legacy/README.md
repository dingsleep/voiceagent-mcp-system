# Legacy Smoke Examples

这里保存原完整链路的手动 smoke 脚本。它们需要 `.env`、外部 LLM API、Socket.IO 网关或 NLU 服务，不属于默认单元测试。

## Scripts

| Script | Purpose |
| --- | --- |
| `llm_api_smoke.py` | 测试 OpenAI-compatible LLM endpoint |
| `function_call_smoke.py` | 测试 Function Calling 请求 |
| `function_call_raw_smoke.py` | 测试原 NLU raw JSON 请求 |
| `socketio_multi_turn_smoke.py` | 使用 `test/data/multi_test.txt` 跑 Socket.IO 多轮样例 |

## Run

```bash
python examples/legacy/llm_api_smoke.py
python examples/legacy/function_call_smoke.py
python examples/legacy/function_call_raw_smoke.py
python examples/legacy/socketio_multi_turn_smoke.py
```

默认项目验证请运行：

```bash
python scripts/check_project.py
```
