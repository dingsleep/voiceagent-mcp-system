# Roadmap

## Phase 1: GitHub-ready baseline

- Keep original modules and data structure.
- Exclude large model weights from git.
- Add README, module map, mock demo, and smoke tests.
- Make the project understandable without private API keys.

## Phase 2: Full-chain cleanup

- Fix legacy encoding issues in Chinese comments and prompts.
- Move environment parsing into a single settings module.
- Add timeout and retry defaults for all downstream HTTP calls.
- Split `function_call/function.py` by domain to improve reviewability.
- Replace ad-hoc print logs in MCP modules with structured logging.

## Phase 3: Real MCP and LLM integration

- Wrap weather, map, and music tools with a FastMCP server.
- Add an OpenAI-compatible LLM client interface.
- Use the same interface for arbitration, rewrite, NLU Function Calling, NLG, and chat fallback.
- Add latency metrics for each stage.

## Phase 4: Resume-grade evaluation

- Add a reproducible benchmark command.
- Report intent accuracy, reject F1, slot accuracy, E2E accuracy, and p95 latency.
- Add a small public sample dataset if the original training data cannot be redistributed.
