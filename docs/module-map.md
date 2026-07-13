# Module Map

## Runtime chain

| Step | File | Responsibility |
| --- | --- | --- |
| Gateway | `start.py` | Receives Socket.IO requests, orchestrates downstream services, emits streaming frames |
| Query rewrite | `client/rewrite.py` | Resolves references and omitted information with conversation history |
| Arbitration | `client/arbitration.py` | Routes request to task / faq / chat path |
| Reject | `client/reject.py` | Filters noise or unsupported input |
| Correlation | `client/correlation.py` | Checks whether a short query is related to previous context |
| Chat fallback | `client/stream_chat.py` | Streams general chat response |
| NLU client | `client/nlu.py` | Calls NLU service and returns structured result |
| NLG | `client/nlg.py` | Converts tool result into user-facing spoken response |

## Task understanding

| File | Responsibility |
| --- | --- |
| `function_call/chatnlu_infer.py` | BERT recall + Function Calling NLU flow |
| `function_call/function.py` | Function schema library for vehicle, media, weather, map, phone, and settings intents |
| `function_call/slot_process.py` | Slot normalization and post-processing |
| `function_call/dm/factory.py` | Dispatches domain managers |
| `function_call/dm/weather.py` | Weather domain execution |
| `function_call/dm/maps.py` | Map domain execution |
| `function_call/dm/music.py` | Music domain execution |

## MCP tools

| File | Responsibility |
| --- | --- |
| `mcp_core/mcp_client.py` | MCP stdio client wrapper |
| `mcp_core/amp_server.py` | Amap MCP tool server |
| `mcp_core/music_server.py` | Music MCP tool server |

## Training and evaluation

| File | Responsibility |
| --- | --- |
| `train/run.py` | Training entry |
| `train/train_eval.py` | Train / validate / test loop |
| `train/models/bert.py` | Intent classifier |
| `train/models/bert_tiny.py` | Reject classifier |
| `train/data_helper.py` | BERT data preprocessing |
| `test/*_benchmark.py` | Locust benchmark scripts |
| `e2e_score.py` | End-to-end scoring helper |

## Added engineering layer

| File | Responsibility |
| --- | --- |
| `voice_agent_mcp/agent.py` | Zero-dependency runnable agent facade |
| `voice_agent_mcp/api.py` | HTTP demo service |
| `voice_agent_mcp/cli.py` | CLI demo |
| `tests/test_agent.py` | Smoke tests for task, multi-turn rewrite, and reject paths |
