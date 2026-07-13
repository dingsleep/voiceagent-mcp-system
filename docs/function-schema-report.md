# Function Schema Quality Report

Generated with:

```bash
python -m function_call.schema_catalog --markdown docs/function-schema-report.md
```

## Summary

| Metric | Value |
| --- | ---: |
| Total tool definitions | 455 |
| Unique tool names | 448 |
| Duplicate tool definitions | 7 |
| Functions in class config | 438 |
| Validation issues | 16 |

## Domain Distribution

| Domain | Tools |
| --- | ---: |
| calendar_schedule | 4 |
| climate_control | 44 |
| dialog_control | 12 |
| driving_assistance | 19 |
| life_service | 3 |
| media | 62 |
| navigation_map | 69 |
| other | 54 |
| phone_connectivity | 20 |
| scene_mode | 8 |
| seat_control | 22 |
| system_settings | 64 |
| vehicle_body | 44 |
| vehicle_service | 4 |
| voice_assistant | 20 |
| weather_info | 6 |

## Duplicate Tool Names

| Function | Count |
| --- | ---: |
| `Change_Nav_Sign` | 2 |
| `Go_POI` | 2 |
| `Play_Local_Radio` | 2 |
| `Search_Music` | 3 |
| `Search_Radio` | 2 |
| `Unknown` | 2 |

## Duplicate Definition Details

### `Change_Nav_Sign`

### `Go_POI`

### `Play_Local_Radio`

### `Search_Music`

### `Search_Radio`

### `Unknown`


## Duplicate Merge Analysis

| Function | Same schema | Hint | Fingerprints |
| --- | --- | --- | --- |
| `Change_Nav_Sign` | True | safe_candidate: definitions have the same schema and description | `415e6b7dffb4` |
| `Go_POI` | False | do_not_merge_yet: core intent with different slot contracts | `50e00e462bd7`, `e57df1efa272` |
| `Play_Local_Radio` | False | manual_review: duplicate name has different slot contracts | `84587b5e0e5b`, `b230912bae64` |
| `Search_Music` | False | do_not_merge_yet: core intent with different slot contracts | `21d24b2b2162`, `3592d3af16de`, `43077bfffc2f` |
| `Search_Radio` | False | do_not_merge_yet: core intent with different slot contracts | `377f1fbc174f`, `41c89aab871b` |
| `Unknown` | False | review_description: schema is aligned but descriptions differ | `aea6e9250572`, `c3f4f3cd9b66` |

## Validation Issue Types

| Issue | Count |
| --- | ---: |
| `duplicate_name` | 6 |
| `not_in_class_config` | 10 |

## Sample Issues

- `not_in_class_config` at `tools1[192]:Close_Cruise_Broadcast`: function not listed in config/class.txt
- `not_in_class_config` at `tools1[193]:Open_Cruise_Broadcast`: function not listed in config/class.txt
- `not_in_class_config` at `tools1[204]:Nav_To_Home`: function not listed in config/class.txt
- `not_in_class_config` at `tools1[205]:Nav_To_Company`: function not listed in config/class.txt
- `not_in_class_config` at `tools1[250]:Cancel_High_Way_First`: function not listed in config/class.txt
- `not_in_class_config` at `tools1[255]:Avoid_Fee`: function not listed in config/class.txt
- `not_in_class_config` at `tools1[271]:Set_Meeting_Place`: function not listed in config/class.txt
- `not_in_class_config` at `tools1[309]:Radio_Am`: function not listed in config/class.txt
- `not_in_class_config` at `tools1[310]:Radio_Fm`: function not listed in config/class.txt
- `not_in_class_config` at `tools1[415]:Query_Destination_Weather`: function not listed in config/class.txt
- `duplicate_name` at `Search_Music`: appears 3 times
- `duplicate_name` at `Search_Radio`: appears 2 times
- `duplicate_name` at `Change_Nav_Sign`: appears 2 times
- `duplicate_name` at `Play_Local_Radio`: appears 2 times
- `duplicate_name` at `Go_POI`: appears 2 times
- `duplicate_name` at `Unknown`: appears 2 times

## Config Coverage

### Tools missing from `config/class.txt`

- `Avoid_Fee`
- `Cancel_High_Way_First`
- `Close_Cruise_Broadcast`
- `Nav_To_Company`
- `Nav_To_Home`
- `Open_Cruise_Broadcast`
- `Query_Destination_Weather`
- `Radio_Am`
- `Radio_Fm`
- `Set_Meeting_Place`

### Class config entries missing from tool schemas

- None
