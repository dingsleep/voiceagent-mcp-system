# Optimization Notes

This repository keeps the original project capability, but changes the way it is packaged and run.

## Optimized in this version

1. **GitHub upload safety**
   - Removed model weights from the upload candidate.
   - Kept training code, configs, vocab files, data layout, and benchmark scripts.
   - Added `.gitignore` rules for checkpoints, model binaries, caches, logs, and secrets.

2. **Runtime configuration**
   - Added `config/settings.py` as the single source for environment variables.
   - Replaced direct import-time crashes from missing environment variables in key clients.
   - Added default local service URLs for the legacy chain.
   - Made LLM settings accept both legacy names (`BASE_URL`, `API_KEY`) and aliases (`LLM_BASE_URL`, `LLM_API_KEY`).
   - Added `scripts/check_env.py` for local environment preflight without contacting external services.

3. **Local runnable path**
   - Added `voice_agent_mcp/` as a zero-dependency demo path.
   - The demo keeps the same chain shape: rewrite -> arbitration -> NLU -> tool -> NLG -> stream.
   - Added CLI, HTTP API, and smoke tests.

4. **Prompt repair**
   - Rewrote corrupted `prompts.py` into readable UTF-8 text.
   - Kept the same constant names so legacy modules can still import it.

5. **Client robustness**
   - `client/rewrite.py` now supports LLM rewrite and local rule fallback.
   - `client/stream_chat.py` now supports real streaming API and local mock response.
   - `client/nlg.py` now supports LLM NLG and deterministic fallback.
   - `client/arbitration.py` now falls back to local rules when the LLM endpoint is not configured.
   - `utils/redis_tool.py` now falls back to in-memory storage when Redis is unavailable.

6. **Verification**
   - `python -m compileall -q .`
   - `python -m unittest discover -s tests`
   - `python -m voice_agent_mcp.cli --query "北京明天天气怎么样"`
   - `python scripts/check_project.py`

7. **Function schema governance**
   - Added `function_call/schema_catalog.py` to inspect the large Function Calling schema library without manually opening a 200KB file.
   - Added duplicate detection, domain classification, class/slot config coverage checks, and basic JSON Schema validation.
   - Added duplicate fingerprint comparison and merge hints so repeated tool names can be reviewed safely before any schema merge.
   - Added `--strict` mode for future CI or release checks once known schema debt is resolved.
   - Added tests to ensure the schema report is generated and covers key domains.
   - Fixed the `Call_Emergency` schema so `required` references the existing `Emergency` property.
   - Fixed `Close_Training_Cmap` -> `Close_Training_Camp` in `config/class.txt`.
   - Added missing low-risk `slot_intent.json` mappings and reduced schema validation issues from 30 to 16.

8. **Evaluation entry**
   - Added `eval/evaluate_demo.py` and `eval/demo_cases.jsonl` for a small reproducible offline evaluation path.
   - The same evaluation shape can be extended to the full Redis + NLU + MCP chain later.

9. **Project explanation**
   - Added `docs/demo-walkthrough.md` to show the runnable chain step by step.
   - Added `docs/entrypoints.md` to separate local demo, legacy service entrypoints, training, benchmark, and manual smoke scripts.
   - Added `docs/legacy-runtime-flow.md` to document the preserved Socket.IO gateway and parallel legacy service flow.
   - Added `docs/function-class-mapping-plan.md` to explain why remaining class mapping gaps should not be patched blindly.
   - Moved root-level one-off smoke scripts into `examples/legacy/` and gave them descriptive names.

10. **Visible text quality**
   - Added `scripts/check_text_quality.py` to detect obvious mojibake in README, docs, examples, and scripts.
   - Added the text quality check to `scripts/check_project.py`.
   - Fixed the chat end frame in `start.py` to send a fresh end-frame payload instead of reusing the begin-frame object.

11. **Release readiness**
   - Added `scripts/check_release.py` to catch model weight files, oversized files, missing docs, and noisy root-level course scripts before GitHub upload.
   - Added release readiness checks to `scripts/check_project.py`.

## Still worth optimizing

1. Split `function_call/function.py` by domain: media, vehicle, map, weather, phone, settings.
2. Clean remaining mojibake comments in legacy training and benchmark files.
3. Add real integration tests for Redis + NLU service + MCP tools.
4. Add p95 latency metrics for rewrite, arbitration, NLU, tool call, NLG, and streaming.
5. Package model weights with GitHub Releases, HuggingFace, or Git LFS instead of normal git.
