# VoiceAgent MCP System

[![CI](https://github.com/dingsleep/voiceagent-mcp-system/actions/workflows/ci.yml/badge.svg)](https://github.com/dingsleep/voiceagent-mcp-system/actions/workflows/ci.yml)

> A production-oriented vehicle multi-turn task Agent built with fine-tuned Chinese RoBERTa models, DeepSeek Function Calling, dialogue state, and MCP-backed live tools.

![Vehicle Agent walkthrough](docs/演示动画.gif)

## Why This Project

This is not a prompt-only chatbot. The project starts from a real NLU training pipeline, then turns trained intent/reject models into an observable and runnable vehicle-Agent console:

- Fine-tuned Chinese RoBERTa models handle reject detection, intent recall, confidence scoring, and Top-K candidate routing.
- DeepSeek Function Calling is constrained to a compact catalog of verified executable tools instead of receiving an uncontrolled tool dump.
- Deterministic multi-turn actions such as navigation slot filling, waypoint edits, music consent, and cockpit confirmations bypass remote LLM calls.
- AMap MCP services provide live weather, POI search, geocoding, nearby-service search, and real driving routes.
- The web console exposes model/tool Trace evidence, latency, token usage, fallback reasons, maps, and simulated cockpit state.

## Architecture

![System architecture](docs/架构图.png)

## Highlights

### 1. Training First, Then Engineering

The repository preserves the original training and data-governance workflow rather than replacing it with a toy demo.

| Model | Test Accuracy | Macro F1 | Additional Result |
| --- | ---: | ---: | --- |
| Intent `bert.clean-v1` | 86.17% | 82.76% | Top-3 96.03%, Top-5 97.23% |
| Intent `bert.clean-balanced-v1` | **87.79%** | **85.18%** | Top-3 97.04%, Top-5 97.92% |
| Reject `bert_tiny.clean-v1` | 89.09% | 88.69% | Validation-calibrated threshold 0.6162 |

- The intent model covers **439 vehicle-domain training labels** and returns Top-K candidates with confidence.
- The training workflow audits duplicate queries, conflicting labels, data leakage, and class imbalance.
- Balanced training improves Macro F1 by **2.42 percentage points** over the clean baseline on the same held-out test split.
- The public console truthfully exposes only verified runnable capabilities; broad intent coverage is not misrepresented as hundreds of executable tools.

Read the evidence: [training and evaluation](docs/training-and-evaluation.md) and [model experiment results](docs/model-experiment-results.md).

### 2. Hybrid Decision Pipeline

```text
User input
  -> Reject BERT
  -> Intent BERT Top-K recall
  -> deterministic dialogue state OR constrained DeepSeek Function Calling
  -> MCP / live service execution
  -> traceable response, map, cockpit state, and metrics
```

The two decision paths solve different problems:

| Path | Used For | Benefit |
| --- | --- | --- |
| Dialogue state | origin/destination filling, `Add_Via`, music platform choice, cockpit confirmation/cancel | deterministic, low latency, no unnecessary LLM call |
| DeepSeek Function Calling | ambiguous task parsing and structured tool/slot decisions | flexible language understanding under a small, executable tool contract |

Examples of local state resolution:

```text
导航到徐州东站
我从徐州站出发
路上要经过云龙湖
```

The Agent preserves origin, destination, and waypoints, then requests a new real driving route. Bare location input such as `徐州站` is also accepted while the dialogue is waiting for an origin.

### 3. Function Calling Optimization With Evidence

The fine-tuned intent model is used as a **candidate retriever**, not bypassed by the LLM:

- High-confidence intent, for example `0.996`: send only Top-1 runnable tool candidate.
- Medium/low-confidence intent: send at most Top-3 candidates.
- Legacy tool definitions are deduplicated and a public-demo compact schema keeps only runnable contracts.
- Long descriptions, duplicate fields, and unsupported functions are excluded from remote prompts without renaming executable tools.

One verified navigation trace reduced candidate schema payload from **688 chars to 191 chars** while retaining the same `Go_POI` execution contract.

### 4. Real Tool Execution, Not Mocked Output

| Capability | Execution Evidence |
| --- | --- |
| Weather | AMap live weather MCP tool |
| Destination / POI search | AMap text search MCP tool |
| Nearby charging / parking | browser location or manual location + AMap nearby search |
| Driving navigation | AMap geocoding + driving route API + rendered route polyline |
| Add waypoint | real multi-leg route: origin -> waypoint(s) -> destination |
| Music | explicit QQ Music / NetEase search consent, or copyright-clear local demo audio |
| Cockpit controls | session-scoped simulator with visible simulated label; no real vehicle control |

The console has verified a real route of `徐州火车站 -> 云龙湖 -> 徐州东站`: two driving legs, returned distance/duration, and full route polyline for the embedded map.

### 5. Performance Baseline and Observability

The project includes a fixed 20-case live benchmark. It separately records Reject, Intent BERT, DeepSeek FC, tool latency, prompt/completion tokens, P50/P95, and remote fallback rate.

| Stage | Baseline P50 |
| --- | ---: |
| Reject BERT | 16 ms |
| Intent BERT | 46 ms |
| DeepSeek Function Calling | 1.6 s |
| Function Calling total tokens | 470 |

The benchmark guided an actual optimization decision: deterministic cockpit commands now go directly through dialogue state. A verified `打开空调` request completes in about **31 ms** without a DeepSeek call.

The console Trace makes the runtime evidence visible to an interviewer:

- reject backend, confidence, and latency
- Intent BERT Top-K and latency
- Function Calling candidate count, schema size, token usage, and latency
- live-tool provider, tool name, and latency
- decision policy, dialogue context, and fallback reason

## Runnable Demo

### Prerequisites

- Python environment: `tx_agent`
- Install the repository requirements for the selected runtime mode
- The default demo can run without an API key. Live AMap and DeepSeek features require local `.env` configuration.

### Start the Web Console

```bash
conda run -n tx_agent python -m voice_agent_mcp.api
```

Open <http://127.0.0.1:8080/>.

Try these flows:

```text
播放薛之谦的音乐
导航到徐州东站
我从徐州站出发
路上要经过云龙湖
附近充电站
打开空调
温度再低一点
打开后备箱
确认执行
```

### Run Tests

```bash
conda run -n tx_agent python -m unittest discover -s tests -p "test_*.py"
```

### Run the 20-Case Live Baseline

This command is intentionally explicit because it can call local model services and configured remote providers.

```bash
conda run -n tx_agent python -m eval.evaluate_demo ^
  --backend remote ^
  --allow-network ^
  --case-file eval/performance_cases.jsonl ^
  --report eval/reports/performance-baseline-local.json
```

## Connect Local Models and Live Services

Copy the template locally and configure only your own machine:

```bash
copy .env.example .env
```

Then start the local services in this order:

```bash
conda run -n tx_agent python -m train.intent_infer
conda run -n tx_agent python -m function_call.chatnlu_infer
conda run -n tx_agent python -m voice_agent_mcp.api
```

`.env` is ignored by Git. Never commit a DeepSeek key, AMap key, token, credential, or private checkpoint. The repository only includes `.env.example` with placeholders.

## Project Structure

```text
voice_agent_mcp/       Runnable web console, hybrid Agent, state machine, live tools
function_call/         Function Calling schema catalog, candidate selection, NLU bridge
train/                 Intent/reject training, inference, checkpoints selection
mcp_core/              AMap-oriented MCP tools and service adapters
eval/                  Offline evaluation and 20-case performance baseline
tests/                 Unit and integration-oriented regression tests
docs/                  Architecture, walkthrough, experiments, and engineering notes
```

## Engineering Guardrails

- IP sliding-window rate limiting protects locally configured provider budgets.
- Session IDs isolate cockpit state and multi-turn dialogue memory.
- Navigation, weather, POI, and nearby-service results are not treated as long-lived model cache entries.
- Remote NLU failures are surfaced through `fallback_reason` instead of being hidden.
- Cockpit execution is explicitly simulated in both the UI and tool Trace.

## Resume-Ready Summary

**Vehicle Multi-turn Task Agent | Fine-tuned Chinese RoBERTa + DeepSeek Function Calling + MCP**

- Built a hybrid vehicle Agent that combines fine-tuned reject/intent models, confidence-aware Function Calling, deterministic dialogue state, and MCP-backed live services.
- Improved long-tail intent quality through data audit, de-duplication, leakage prevention, and balanced training; achieved **87.79% Accuracy / 85.18% Macro F1** on the balanced intent model.
- Reduced Function Calling prompt overhead with compact schemas and confidence-aware candidate routing; exposed token, latency, tool, and fallback evidence in a runnable web console.
- Delivered real AMap weather, POI, nearby-service, multi-leg route, and map rendering workflows with session-scoped simulated cockpit controls and IP rate limiting.

## Notes

- This repository does not train or distribute an ASR model. It accepts text or upstream ASR transcripts.
- Pretrained weights, local checkpoints, `.env`, and generated local benchmark reports are intentionally excluded from version control.
- See [demo walkthrough](docs/demo-walkthrough.md), [entrypoints](docs/entrypoints.md), and [schema report](docs/function-schema-report.md) for implementation details.
