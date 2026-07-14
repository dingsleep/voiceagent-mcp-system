# Function Schema Remediation Plan

This plan is intentionally conservative: do not delete or merge schema entries until real traffic, training labels, and slot mappings are checked together.

## Current Findings

- Total tool definitions: 455
- Unique tool names: 448
- Duplicate tool definitions: 7
- Validation issues: 16
- Structural schema errors: 0
- Slot config coverage issues: 0

## Duplicate Names

| Function | Count | Suggested action |
| --- | ---: | --- |
| `Search_Music` | 3 | Compare descriptions and slot schemas, keep the most complete one, migrate examples/tests |
| `Search_Radio` | 2 | Merge if slot schema is identical |
| `Change_Nav_Sign` | 2 | Check whether they represent different navigation views before merging |
| `Play_Local_Radio` | 2 | Merge if both target the same local radio action |
| `Go_POI` | 2 | Risky: this is a core navigation function, compare against benchmark labels first |
| `Unknown` | 2 | Keep one global fallback only |

## Config Coverage Issues

Some functions exist in `function_call/function.py` but are missing from `config/class.txt`.

Remaining class mapping gaps:

- `Close_Cruise_Broadcast`
- `Open_Cruise_Broadcast`
- `Nav_To_Home`
- `Nav_To_Company`
- `Cancel_High_Way_First`
- `Avoid_Fee`
- `Set_Meeting_Place`
- `Radio_Am`
- `Radio_Fm`
- `Query_Destination_Weather`

Suggested order:

1. Add missing intent mappings to `class.txt` only when training labels or benchmark cases exist.
2. For navigation and media functions, check benchmark data before changing mapping.
3. Retrain or remap the intent classifier if new class IDs are introduced.

## Fixed Slot Config Coverage

The following missing `config/slot_intent.json` mappings were added:

- `Close_Cruise_Broadcast`
- `Open_Cruise_Broadcast`
- `Nav_To_Home`
- `Nav_To_Company`
- `Avoid_Fee`
- `List_Repeat`
- `View_Play_Album`
- `Set_Meeting_Place`
- `Radio_Am`
- `Radio_Fm`
- `Open_Two_Both`
- `Close_Two_Both`

This reduces slot coverage issues to zero.

## Fixed Schema Issue

`Call_Emergency` previously declared required field `Contact`, but the actual property was `Emergency`.

Fixed by changing `required` to `["Emergency"]`.

## Do Not Do Yet

- Do not split `function_call/function.py` until duplicate and config coverage issues are resolved.
- Do not rename tool functions before checking `config/class.txt`, `config/slot_intent.json`, training labels, and benchmark files.
- Do not delete duplicate schemas without regression tests.

## Runtime Handling

The raw catalog intentionally remains unchanged for auditability. The full NLU
service now selects one canonical schema for each duplicate function name
before sending candidates to an OpenAI-compatible tool-calling API. Selection
prefers the schema with more declared properties, then the longer description.
This prevents duplicate function names from invalidating a tool-call request
while source-level deduplication remains a separate governance task.

Remote NLU responses also carry a `source` and `fallback_reason`. This keeps a
legacy mock fallback visible to the runnable demo and to remote evaluation,
rather than misreporting it as a successful LLM tool call.
