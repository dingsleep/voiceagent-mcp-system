import unittest
from unittest.mock import patch

from voice_agent_mcp.agent import DialogueAgent
from voice_agent_mcp.live_tools import build_live_registry, plan_driving_route, search_nearby_places
from voice_agent_mcp.nlu_backends import RemoteNluBackend, RuleNluBackend


class LiveToolsTest(unittest.TestCase):
    def test_weather_normalizes_amap_mcp_response(self):
        registry = build_live_registry(
            weather_fetcher=lambda city, requested_date: {
                "\u57ce\u5e02": city,
                "\u5929\u6c14": "\u6674",
                "\u6e29\u5ea6": "26",
                "\u98ce\u5411": "\u5317",
                "\u98ce\u529b": "1-3",
            },
            place_searcher=lambda destination, city: {"pois": []},
        )

        result = registry.call("weather.query", {"city": "\u5317\u4eac", "date": "\u660e\u5929"})

        self.assertEqual(result["provider"], "amap-mcp")
        self.assertEqual(result["tool"], "maps_weather")
        self.assertEqual(result["weather"], "\u6674")
        self.assertEqual(result["date"], "\u660e\u5929")

    def test_music_requires_explicit_playback_consent(self):
        registry = build_live_registry(
            weather_fetcher=lambda city, requested_date: {},
            place_searcher=lambda destination, city: {"pois": []},
        )

        result = registry.call("music.play", {"artist": "\u5468\u6770\u4f26"})

        self.assertEqual(result["action"], "consent_required")
        self.assertEqual(result["artist"], "\u5468\u6770\u4f26")

    def test_agent_exposes_live_tool_trace(self):
        registry = build_live_registry(
            weather_fetcher=lambda city, requested_date: {
                "\u57ce\u5e02": city,
                "\u5929\u6c14": "\u6674",
                "\u6e29\u5ea6": "26",
            },
            place_searcher=lambda destination, city: {"pois": []},
        )
        final = DialogueAgent(tools=registry, nlu_backend=RuleNluBackend()).handle_as_dicts(
            "\u5317\u4eac\u5929\u6c14"
        )[-1]

        self.assertEqual(final["metadata"]["tool_trace"]["provider"], "amap-mcp")
        self.assertEqual(final["metadata"]["tool_trace"]["tool"], "maps_weather")

    def test_music_consent_result_is_rendered_without_a_song_field(self):
        registry = build_live_registry(
            weather_fetcher=lambda city, requested_date: {},
            place_searcher=lambda destination, city: {"pois": []},
        )
        frames = DialogueAgent(tools=registry, nlu_backend=RuleNluBackend()).handle_as_dicts(
            "\u64ad\u653e\u5468\u6770\u4f26\u7684\u6b4c"
        )
        final = frames[-1]

        self.assertEqual(final["function"], "music.play")
        self.assertEqual(final["metadata"]["tool_result"]["action"], "consent_required")
        self.assertIn("\u9009\u62e9", "".join(frame["content"] for frame in frames))

    def test_music_choice_is_resolved_from_conversation_memory(self):
        registry = build_live_registry(
            weather_fetcher=lambda city, requested_date: {},
            place_searcher=lambda destination, city: {"pois": []},
        )
        agent = DialogueAgent(tools=registry, nlu_backend=RuleNluBackend())
        agent.handle_as_dicts("\u64ad\u653e\u5468\u6770\u4f26\u7684\u6b4c", sender_id="music-choice")

        final = agent.handle_as_dicts("\u7ad9\u5185\u6f14\u793a\u97f3\u9891\u64ad\u653e", sender_id="music-choice")[-1]

        self.assertEqual(final["function"], "music.play")
        self.assertEqual(final["metadata"]["route"], "music_consent")
        self.assertEqual(final["metadata"]["tool_result"]["action"], "demo_audio_play")
        self.assertEqual(final["slots"]["artist"], "\u5468\u6770\u4f26")

    def test_music_song_title_is_preserved_for_provider_search(self):
        registry = build_live_registry(
            weather_fetcher=lambda city, requested_date: {},
            place_searcher=lambda destination, city: {"pois": []},
        )
        agent = DialogueAgent(tools=registry, nlu_backend=RuleNluBackend())
        first = agent.handle_as_dicts("\u64ad\u653e\u5468\u6770\u4f26\u7684\u6674\u5929", sender_id="song-title")[-1]
        selected = agent.handle_as_dicts("\u7f51\u6613\u4e91\u97f3\u4e50\u641c\u7d22", sender_id="song-title")[-1]

        self.assertEqual(first["slots"], {"artist": "\u5468\u6770\u4f26", "song": "\u6674\u5929"})
        self.assertEqual(first["metadata"]["tool_result"]["query"], "\u5468\u6770\u4f26 \u6674\u5929")
        self.assertEqual(selected["metadata"]["tool_result"]["platform"], "netease-music")
        self.assertEqual(selected["slots"], {"artist": "\u5468\u6770\u4f26", "song": "\u6674\u5929"})

    def test_music_slots_follow_an_explicit_artist_and_song(self):
        registry = build_live_registry(
            weather_fetcher=lambda city, requested_date: {},
            place_searcher=lambda destination, city: {"pois": []},
        )
        agent = DialogueAgent(tools=registry, nlu_backend=RuleNluBackend())
        final = agent.handle_as_dicts("\u64ad\u653e\u859b\u4e4b\u8c26\u7684\u6f14\u5458", sender_id="explicit-song")[-1]

        self.assertEqual(final["slots"], {"artist": "\u859b\u4e4b\u8c26", "song": "\u6f14\u5458"})

    def test_task_route_is_not_blocked_by_a_false_reject_result(self):
        class RejectAll:
            def evaluate(self, query, trace_id):
                from voice_agent_mcp.reject_backends import RejectDecision

                return RejectDecision(False, 0.1, 0, "test-reject")

        registry = build_live_registry(
            weather_fetcher=lambda city, requested_date: {},
            place_searcher=lambda destination, city: {"pois": []},
        )
        agent = DialogueAgent(tools=registry, nlu_backend=RuleNluBackend(), reject_backend=RejectAll())
        final = agent.handle_as_dicts("\u5bfc\u822a\u5230\u5317\u4eac\u7ad9", sender_id="route-override")[-1]

        self.assertEqual(final["intent"], "map_route")
        self.assertTrue(final["metadata"]["reject_trace"]["task_route_override"])

    def test_explicit_cockpit_command_bypasses_remote_nlu(self):
        class UnexpectedNluCall:
            def parse(self, query, trace_id, context=None):
                raise AssertionError("cockpit command should use dialogue state")

            def describe(self):
                return {"name": "unexpected"}

        final = DialogueAgent(nlu_backend=UnexpectedNluCall()).handle_as_dicts(
            "\u6253\u5f00\u7a7a\u8c03", sender_id="cockpit-direct"
        )[-1]

        self.assertEqual(final["intent"], "cockpit_control")
        self.assertEqual(final["metadata"]["nlu_backend"], "dialogue-state")
        self.assertEqual(final["metadata"]["decision_policy"]["strategy"], "dialogue_state")

    @patch("voice_agent_mcp.live_tools.maps_direction_driving")
    @patch("voice_agent_mcp.live_tools.maps_geo")
    def test_driving_route_resolves_endpoints_and_keeps_polyline(self, geo, driving):
        geo.side_effect = [
            {"return": [{"location": "116.30,39.98"}]},
            {"return": [{"location": "116.43,39.90"}]},
        ]
        driving.return_value = {
            "route": {
                "paths": [
                    {
                        "distance": "12300",
                        "duration": "1800",
                        "steps": [{"polyline": "116.30,39.98;116.43,39.90"}],
                    }
                ]
            }
        }

        route = plan_driving_route("\u4e2d\u5173\u6751", "\u5317\u4eac\u7ad9")

        self.assertEqual(route["distance_meters"], 12300)
        self.assertEqual(route["duration_seconds"], 1800)
        self.assertEqual(route["polyline"], ["116.30,39.98;116.43,39.90"])
        driving.assert_called_once_with("116.30,39.98", "116.43,39.90")
        geo.assert_any_call("\u4e2d\u5173\u6751", "\u5317\u4eac")

    @patch("voice_agent_mcp.live_tools.maps_direction_driving")
    @patch("voice_agent_mcp.live_tools.maps_geo")
    def test_driving_route_composes_real_legs_through_waypoint(self, geo, driving):
        geo.side_effect = [
            {"return": [{"location": "116.30,39.98"}]},
            {"return": [{"location": "116.43,39.90"}]},
            {"return": [{"location": "116.36,39.92"}]},
        ]
        driving.side_effect = [
            {"route": {"paths": [{"distance": "3000", "duration": "600", "steps": [{"polyline": "116.30,39.98;116.36,39.92"}]}]}},
            {"route": {"paths": [{"distance": "5000", "duration": "900", "steps": [{"polyline": "116.36,39.92;116.43,39.90"}]}]}},
        ]

        route = plan_driving_route("\u4e2d\u5173\u6751", "\u5317\u4eac\u7ad9", via=["\u5929\u5b89\u95e8"])

        self.assertEqual(route["distance_meters"], 8000)
        self.assertEqual(route["duration_seconds"], 1500)
        self.assertEqual(route["legs"], 2)
        self.assertEqual(route["via"], [{"name": "\u5929\u5b89\u95e8", "location": "116.36,39.92"}])
        self.assertEqual(driving.call_count, 2)

    def test_navigation_waypoint_edit_uses_dialogue_state_and_preserves_route(self):
        agent = DialogueAgent(nlu_backend=RuleNluBackend())
        agent.handle_as_dicts(
            "\u5bfc\u822a\u5230\u5f90\u5dde\u9ad8\u94c1\u7ad9\uff0c\u4ece\u5f90\u5dde\u706b\u8f66\u7ad9\u51fa\u53d1",
            sender_id="via-edit",
        )

        final = agent.handle_as_dicts("\u8def\u7ebf\u52a0\u4e00\u4e2a\u4e91\u9f99\u6e56", sender_id="via-edit")[-1]

        self.assertEqual(final["metadata"]["nlu_backend"], "not_used")
        self.assertEqual(final["metadata"]["decision_policy"]["reason"], "navigation_via_resolved")
        self.assertEqual(final["metadata"]["navigation_request"], {
            "provider": "dialogue-state",
            "action": "route_request",
            "origin": "\u5f90\u5dde\u706b\u8f66\u7ad9",
            "destination": "\u5f90\u5dde\u9ad8\u94c1\u7ad9",
            "via": ["\u4e91\u9f99\u6e56"],
        })

    def test_navigation_accepts_natural_origin_and_waypoint_phrases(self):
        agent = DialogueAgent(nlu_backend=RuleNluBackend())
        agent.handle_as_dicts("\u5bfc\u822a\u5230\u5f90\u5dde\u4e1c\u7ad9", sender_id="natural-via")
        origin = agent.handle_as_dicts("\u6211\u4ece\u5f90\u5dde\u7ad9\u51fa\u53d1", sender_id="natural-via")[-1]
        via = agent.handle_as_dicts("\u8def\u4e0a\u8981\u7ecf\u8fc7\u4e91\u9f99\u6e56", sender_id="natural-via")[-1]

        self.assertEqual(origin["slots"]["origin"], "\u5f90\u5dde\u7ad9")
        self.assertEqual(via["metadata"]["navigation_request"]["via"], ["\u4e91\u9f99\u6e56"])

    def test_combined_navigation_request_keeps_origin_and_destination(self):
        registry = build_live_registry(
            weather_fetcher=lambda city, requested_date: {},
            place_searcher=lambda destination, city: {"pois": [{"name": destination, "location": "117.20,34.20"}]},
        )
        final = DialogueAgent(tools=registry, nlu_backend=RuleNluBackend()).handle_as_dicts(
            "\u5bfc\u822a\u5230\u5f90\u5dde\u9ad8\u94c1\u7ad9\uff0c\u4ece\u5f90\u5dde\u706b\u8f66\u7ad9\u51fa\u53d1",
            sender_id="combined-navigation",
        )[-1]

        self.assertEqual(final["slots"], {"origin": "\u5f90\u5dde\u706b\u8f66\u7ad9", "destination": "\u5f90\u5dde\u9ad8\u94c1\u7ad9"})
        self.assertEqual(final["metadata"]["navigation_request"]["action"], "route_request")

    def test_origin_follow_up_uses_previous_destination(self):
        registry = build_live_registry(
            weather_fetcher=lambda city, requested_date: {},
            place_searcher=lambda destination, city: {"pois": [{"name": destination, "location": "117.20,34.20"}]},
        )
        agent = DialogueAgent(tools=registry, nlu_backend=RuleNluBackend())
        agent.handle_as_dicts("\u5bfc\u822a\u5230\u5f90\u5dde\u9ad8\u94c1\u7ad9", sender_id="origin-follow-up")
        final = agent.handle_as_dicts("\u51fa\u53d1\u5730\u4e3a\u5f90\u5dde\u706b\u8f66\u7ad9", sender_id="origin-follow-up")[-1]

        self.assertEqual(final["metadata"]["navigation_request"]["destination"], "\u5f90\u5dde\u9ad8\u94c1\u7ad9")
        self.assertEqual(final["metadata"]["navigation_request"]["origin"], "\u5f90\u5dde\u706b\u8f66\u7ad9")

    def test_current_location_plus_place_is_normalized_as_navigation_origin(self):
        registry = build_live_registry(
            weather_fetcher=lambda city, requested_date: {},
            place_searcher=lambda destination, city: {"pois": [{"name": destination, "location": "115.48,38.87"}]},
        )
        agent = DialogueAgent(tools=registry, nlu_backend=RuleNluBackend())

        agent.handle_as_dicts("导航到河北保定", sender_id="current-place-origin")
        final = agent.handle_as_dicts("当前位置徐州火车站", sender_id="current-place-origin")[-1]

        self.assertEqual(final["intent"], "map_route")
        self.assertEqual(final["slots"], {"origin": "徐州火车站", "destination": "河北保定"})
        self.assertEqual(final["metadata"]["navigation_request"]["action"], "route_request")
        self.assertEqual(final["metadata"]["conversation_context"]["awaiting"], "origin")
        self.assertEqual(final["metadata"]["decision_policy"]["strategy"], "dialogue_state")

    def test_navigation_context_accepts_bare_place_as_origin_without_remote_nlu(self):
        calls = []

        def transport(endpoint, payload, timeout_seconds):
            calls.append(payload)
            destination = "\u4fdd\u5b9a" if not payload.get("context") else "\u5f90\u5dde\u706b\u8f66\u7ad9"
            return {"intent": "navigation", "function": "Go_POI", "slots": {"POI": destination}}

        registry = build_live_registry(
            weather_fetcher=lambda city, requested_date: {},
            place_searcher=lambda destination, city: {"pois": [{"name": destination, "location": "115.48,38.87"}]},
        )
        agent = DialogueAgent(tools=registry, nlu_backend=RemoteNluBackend("http://nlu.example/v1", transport=transport))

        agent.handle_as_dicts("导航到保定", sender_id="model-origin-context")
        final = agent.handle_as_dicts("徐州火车站", sender_id="model-origin-context")[-1]

        self.assertEqual(len(calls), 1)
        self.assertEqual(final["slots"], {"origin": "徐州火车站", "destination": "保定"})
        self.assertEqual(final["metadata"]["navigation_request"]["action"], "route_request")
        self.assertEqual(final["metadata"]["decision_policy"]["strategy"], "dialogue_state")

    def test_explicit_new_task_does_not_forward_stale_navigation_context(self):
        calls = []

        def transport(endpoint, payload, timeout_seconds):
            calls.append(payload)
            if len(calls) == 1:
                return {"intent": "navigation", "function": "Go_POI", "slots": {"POI": "\u4fdd\u5b9a"}}
            return {"intent": "weather", "function": "Query_Weather", "slots": {"City": "\u5317\u4eac"}}

        registry = build_live_registry(
            weather_fetcher=lambda city, requested_date: {"\u57ce\u5e02": city, "\u5929\u6c14": "\u6674", "\u6e29\u5ea6": "26"},
            place_searcher=lambda destination, city: {"pois": [{"name": destination, "location": "115.48,38.87"}]},
        )
        agent = DialogueAgent(tools=registry, nlu_backend=RemoteNluBackend("http://nlu.example/v1", transport=transport))

        agent.handle_as_dicts("导航到保定", sender_id="new-task-context")
        final = agent.handle_as_dicts("北京天气", sender_id="new-task-context")[-1]

        self.assertNotIn("context", calls[1])
        self.assertEqual(final["metadata"]["conversation_context"], {})

    def test_nearby_charging_search_requires_explicit_location_choice(self):
        registry = build_live_registry(
            weather_fetcher=lambda city, requested_date: {},
            place_searcher=lambda destination, city: {"pois": []},
        )
        final = DialogueAgent(tools=registry, nlu_backend=RuleNluBackend()).handle_as_dicts(
            "\u9644\u8fd1\u5145\u7535\u7ad9", sender_id="nearby-charging"
        )[-1]

        self.assertEqual(final["intent"], "nearby_search")
        self.assertEqual(final["function"], "map.nearby")
        self.assertEqual(final["metadata"]["tool_result"]["action"], "location_required")
        self.assertEqual(final["metadata"]["tool_result"]["category"], "charging_station")

    def test_cockpit_simulator_keeps_state_across_multiple_commands(self):
        registry = build_live_registry(
            weather_fetcher=lambda city, requested_date: {},
            place_searcher=lambda destination, city: {"pois": []},
        )
        agent = DialogueAgent(tools=registry, nlu_backend=RuleNluBackend())

        opened = agent.handle_as_dicts("\u6253\u5f00\u7a7a\u8c03", sender_id="cockpit-state")[-1]
        adjusted = agent.handle_as_dicts("\u7a7a\u8c03\u6e29\u5ea6\u8c03\u523024\u5ea6", sender_id="cockpit-state")[-1]
        ventilation = agent.handle_as_dicts("\u6253\u5f00\u4e3b\u9a7e\u5ea7\u6905\u901a\u98ce", sender_id="cockpit-state")[-1]

        self.assertEqual(opened["function"], "cockpit.control")
        self.assertTrue(opened["metadata"]["tool_result"]["simulation"])
        self.assertTrue(adjusted["metadata"]["tool_result"]["state"]["air_condition"]["on"])
        self.assertEqual(adjusted["metadata"]["tool_result"]["state"]["air_condition"]["temperature"], 24)
        self.assertTrue(ventilation["metadata"]["tool_result"]["state"]["seat_ventilation"])

    def test_cockpit_state_is_isolated_by_sender_and_follow_up_uses_history(self):
        registry = build_live_registry(
            weather_fetcher=lambda city, requested_date: {},
            place_searcher=lambda destination, city: {"pois": []},
        )
        agent = DialogueAgent(tools=registry, nlu_backend=RuleNluBackend())

        agent.handle_as_dicts("打开空调", sender_id="cockpit-a")
        lowered = agent.handle_as_dicts("温度再低一点", sender_id="cockpit-a")[-1]
        other = agent.handle_as_dicts("打开车窗", sender_id="cockpit-b")[-1]

        self.assertEqual(lowered["metadata"]["tool_trace"]["context_source"], "history")
        self.assertEqual(lowered["metadata"]["tool_result"]["state"]["air_condition"]["temperature"], 23)
        self.assertTrue(lowered["metadata"]["tool_result"]["state"]["air_condition"]["on"])
        self.assertFalse(other["metadata"]["tool_result"]["state"]["air_condition"]["on"])
        self.assertEqual(other["metadata"]["tool_result"]["state"]["windows"], "open")

    def test_temperature_adjustment_requires_air_condition_to_be_on(self):
        registry = build_live_registry(
            weather_fetcher=lambda city, requested_date: {},
            place_searcher=lambda destination, city: {"pois": []},
        )
        agent = DialogueAgent(tools=registry, nlu_backend=RuleNluBackend())

        implicit = agent.handle_as_dicts("温度再低一点", sender_id="air-condition-guard")[-1]
        explicit = agent.handle_as_dicts("空调温度调到20度", sender_id="air-condition-guard")[-1]
        opened = agent.handle_as_dicts("打开空调", sender_id="air-condition-guard")[-1]
        adjusted = agent.handle_as_dicts("温度再低一点", sender_id="air-condition-guard")[-1]

        self.assertEqual(implicit["metadata"]["tool_result"]["action"], "activation_required")
        self.assertEqual(explicit["metadata"]["tool_result"]["action"], "activation_required")
        self.assertEqual(explicit["metadata"]["tool_result"]["state"]["air_condition"]["temperature"], 24)
        self.assertTrue(opened["metadata"]["tool_result"]["state"]["air_condition"]["on"])
        self.assertEqual(adjusted["metadata"]["tool_result"]["state"]["air_condition"]["temperature"], 23)

    def test_opening_trunk_requires_confirmation_and_can_be_cancelled(self):
        registry = build_live_registry(
            weather_fetcher=lambda city, requested_date: {},
            place_searcher=lambda destination, city: {"pois": []},
        )
        agent = DialogueAgent(tools=registry, nlu_backend=RuleNluBackend())

        pending = agent.handle_as_dicts("打开后备箱", sender_id="cockpit-confirm")[-1]
        cancelled = agent.handle_as_dicts("取消", sender_id="cockpit-confirm")[-1]
        pending_again = agent.handle_as_dicts("打开后备箱", sender_id="cockpit-confirm")[-1]
        confirmed = agent.handle_as_dicts("确认执行", sender_id="cockpit-confirm")[-1]

        self.assertEqual(pending["intent"], "cockpit_confirmation")
        self.assertEqual(pending["metadata"]["tool_result"]["action"], "await_confirmation")
        self.assertEqual(cancelled["intent"], "cockpit_cancelled")
        self.assertEqual(pending_again["intent"], "cockpit_confirmation")
        self.assertEqual(confirmed["metadata"]["tool_trace"]["context_source"], "confirmation")
        self.assertEqual(confirmed["metadata"]["tool_result"]["state"]["trunk"], "open")

    @patch("voice_agent_mcp.live_tools.maps_around_search")
    def test_nearby_search_returns_selectable_pois_with_locations(self, around):
        around.return_value = {
            "pois": [
                {"name": "\u6d4b\u8bd5\u5145\u7535\u7ad9", "address": "\u671d\u9633\u533a", "location": "116.48,39.92"},
                {"name": "\u6d4b\u8bd5\u5145\u7535\u7ad9 B", "address": "\u4e1c\u57ce\u533a", "location": "116.42,39.91"},
            ]
        }

        result = search_nearby_places(
            "\u5f53\u524d\u4f4d\u7f6e", "charging_station", origin_location="116.40,39.90"
        )

        self.assertEqual(result["tool"], "maps_around_search")
        self.assertEqual(result["keyword"], "\u5145\u7535\u7ad9")
        self.assertEqual(result["pois"][0]["location"], "116.48,39.92")
        around.assert_called_once_with("116.40,39.90", radius="3000", keywords="\u5145\u7535\u7ad9")


if __name__ == "__main__":
    unittest.main()
