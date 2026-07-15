from .arbitration import arbitrate
from .chat_backends import ChatBackend, RuleChatBackend
from .frames import Frame, stream_text
from .memory import MemoryStore, Turn
from dataclasses import replace
import re
import time
import uuid

from .nlu_backends import NLUBackend, RuleNluBackend, build_nlu_backend
from .reject_backends import RejectBackend, RuleRejectBackend
from .rewrite import rewrite_query
from .tools import ToolRegistry, default_registry


def _pending_music_choice(query: str, history: list[Turn]) -> tuple[str, str, str, str] | None:
    """Resolve an explicit playback choice against the most recent music turn."""
    last_music = next((turn for turn in reversed(history) if turn.intent == "music_play"), None)
    if not last_music:
        return None

    normalized = query.strip().lower()
    artist = last_music.slots.get("artist") or "\u5f53\u524d\u6b4c\u624b"
    song = last_music.slots.get("song", "")
    if "\u7f51\u6613\u4e91" in normalized:
        return artist, song, "third_party_search", "netease-music"
    if any(word in normalized for word in ("\u7b2c\u4e09\u65b9\u641c\u7d22", "qq\u97f3\u4e50", "\u540c\u610f\u5e76\u641c\u7d22")):
        return artist, song, "third_party_search", "qq-music"
    if any(word in normalized for word in ("\u7ad9\u5185\u6f14\u793a", "\u6f14\u793a\u97f3\u9891", "\u7ad9\u5185\u64ad\u653e")):
        return artist, song, "demo_audio_play", "local-demo"
    return None


def _enrich_music_slots(query: str, slots: dict) -> dict:
    """Use an explicit "artist's song" request to correct incomplete NLU slots."""
    merged = dict(slots)
    explicit = re.search(
        r"(?:\u64ad\u653e|\u653e\u4e00\u9996|\u6765\u4e00\u9996)\s*(.+?)\s*\u7684\s*([^\uff0c\u3002\uff01\uff1f!?]+)",
        query,
    )
    if not explicit:
        return merged

    artist = explicit.group(1).strip()
    song = explicit.group(2).strip().removesuffix("\u7684\u6b4c").removesuffix("\u6b4c")
    if artist:
        merged["artist"] = artist
    if song:
        merged["song"] = song
    return merged


def _combined_navigation_request(query: str) -> tuple[str, str] | None:
    """Extract ``navigate to B, from A`` without relying on a fixed city list."""
    matched = re.search(
        r"(?:\u5bfc\u822a\u5230|\u5bfc\u822a\u53bb|\u53bb)\s*(.+?)\s*[\uff0c,]\s*(?:\u4ece|\u51fa\u53d1\u5730|\u8d77\u70b9)\s*(.+?)(?:\u51fa\u53d1)?$",
        query,
    )
    if not matched:
        return None
    destination = matched.group(1).strip()
    origin = matched.group(2).strip().removesuffix("\u51fa\u53d1")
    return (origin, destination) if origin and destination else None


def _nearby_category(query: str) -> str:
    if "\u9644\u8fd1" not in query:
        return ""
    if "\u5145\u7535" in query:
        return "charging_station"
    if any(word in query for word in ("\u505c\u8f66", "\u6cca\u8f66")):
        return "parking_lot"
    return ""


def _cockpit_slots(query: str) -> dict:
    """Normalize demonstrable cockpit controls before dispatching to the simulator."""
    compact = query.replace(" ", "")
    closed = any(word in compact for word in ("\u5173\u95ed", "\u5173\u4e0a", "\u5173\u6389"))
    opened = any(word in compact for word in ("\u6253\u5f00", "\u5f00\u542f", "\u5f00\u4e00\u4e0b"))

    if "\u540e\u5907\u7bb1" in compact:
        return {"target": "trunk", "operation": "power", "value": not closed}
    if any(word in compact for word in ("\u8f66\u7a97", "\u7a97\u6237")):
        return {"target": "windows", "operation": "power", "value": not closed}
    if "\u5ea7\u6905" in compact and "\u901a\u98ce" in compact:
        return {"target": "seat_ventilation", "operation": "power", "value": not closed}
    if "\u65e0\u7ebf\u5145\u7535" in compact:
        return {"target": "wireless_charging", "operation": "power", "value": not closed}
    if "\u6c1b\u56f4\u706f" in compact:
        color = next((name for name in ("\u84dd\u8272", "\u7d2b\u8272", "\u7ea2\u8272", "\u7eff\u8272", "\u6a59\u8272") if name in compact), "")
        if color:
            return {"target": "ambient_light", "operation": "color", "value": color}
        return {"target": "ambient_light", "operation": "power", "value": not closed}
    if "\u7a7a\u8c03" in compact:
        temperature = re.search(r"(?<!\d)(1[6-9]|2\d|3[0-2])\s*(?:\u5ea6|\u2103)?", compact)
        if temperature:
            return {"target": "air_condition", "operation": "temperature", "value": int(temperature.group(1))}
        if any(word in compact for word in ("\u8c03\u4f4e", "\u964d\u4f4e")):
            return {"target": "air_condition", "operation": "temperature_delta", "value": -1}
        if any(word in compact for word in ("\u8c03\u9ad8", "\u5347\u9ad8")):
            return {"target": "air_condition", "operation": "temperature_delta", "value": 1}
        if "\u81ea\u52a8\u6a21\u5f0f" in compact:
            return {"target": "air_condition", "operation": "mode", "value": "auto"}
        if opened or closed:
            return {"target": "air_condition", "operation": "power", "value": not closed}
    return {}


def _cockpit_follow_up_slots(query: str, history: list[Turn]) -> dict:
    """Resolve a short cockpit follow-up only against the last executed control."""
    last = history[-1] if history else None
    if not last or last.intent != "cockpit_control":
        return {}

    compact = query.replace(" ", "")
    target = last.slots.get("target")
    if target == "air_condition":
        if any(word in compact for word in ("\u518d\u4f4e\u4e00\u70b9", "\u4f4e\u4e00\u70b9", "\u518d\u51b7\u4e00\u70b9")):
            return {"target": target, "operation": "temperature_delta", "value": -1}
        if any(word in compact for word in ("\u518d\u9ad8\u4e00\u70b9", "\u9ad8\u4e00\u70b9", "\u518d\u70ed\u4e00\u70b9")):
            return {"target": target, "operation": "temperature_delta", "value": 1}

    if any(word in compact for word in ("\u5173\u6389", "\u5173\u95ed", "\u5173\u4e0a")) and any(
        word in compact for word in ("\u5b83", "\u8fd9\u4e2a", "\u90a3\u4e2a")
    ):
        return {"target": target, "operation": "power", "value": False}
    return {}


def _cockpit_confirmation(query: str, history: list[Turn]) -> tuple[str, dict] | None:
    """Resolve an explicit confirmation or cancellation for a pending cockpit action."""
    last = history[-1] if history else None
    if not last or last.intent != "cockpit_confirmation":
        return None

    compact = query.replace(" ", "")
    if any(word in compact for word in ("\u53d6\u6d88", "\u7b97\u4e86", "\u4e0d\u7528\u4e86", "\u4e0d\u6267\u884c")):
        return "cancelled", dict(last.slots)
    if any(word in compact for word in ("\u786e\u8ba4", "\u786e\u5b9a\u6267\u884c", "\u6267\u884c\u5427")):
        return "confirmed", dict(last.slots)
    return None


def _requires_cockpit_confirmation(slots: dict) -> bool:
    """Model a deliberate safety gate for the most visible physical-like action."""
    return slots.get("target") == "trunk" and slots.get("value") is True


def _implicit_air_condition_adjustment(query: str) -> bool:
    """Recognize a concise temperature follow-up without mistaking weather queries."""
    compact = query.replace(" ", "")
    return any(word in compact for word in ("\u518d\u4f4e\u4e00\u70b9", "\u518d\u9ad8\u4e00\u70b9", "\u518d\u51b7\u4e00\u70b9", "\u518d\u70ed\u4e00\u70b9"))


def _starts_new_task(query: str) -> bool:
    """Prevent an active task from biasing an explicit, unrelated new request."""
    return any(
        marker in query
        for marker in (
            "\u5929\u6c14",
            "\u64ad\u653e",
            "\u653e\u4e00\u9996",
            "\u6765\u4e00\u9996",
            "\u5bfc\u822a",
            "\u8def\u7ebf",
            "\u9644\u8fd1",
        )
    ) or bool(_cockpit_slots(query))


def _navigation_context(history: list[Turn]) -> dict:
    """Derive the active navigation task from compact, structured turn memory."""
    last_route = next((turn for turn in reversed(history) if turn.intent == "map_route"), None)
    if not last_route:
        return {}
    destination = last_route.slots.get("destination", "")
    if not destination:
        return {}
    context = {
        "task": "navigation",
        "destination": destination,
        "via": list(last_route.slots.get("via", [])),
    }
    if origin := last_route.slots.get("origin"):
        context["origin"] = origin
        context["awaiting"] = "route_modification"
    else:
        context["awaiting"] = "origin"
    return context


def _navigation_follow_up(query: str, history: list[Turn]) -> dict | None:
    """Continue a manual origin/destination exchange from the recent task memory."""
    navigation_context = _navigation_context(history)
    origin_match = re.fullmatch(
        r"(?:\u6211\u4ece|\u5f53\u524d\u4f4d\u7f6e|\u5f53\u524d\u7684\u4f4d\u7f6e|\u6211\u5728|\u4ece|\u51fa\u53d1\u5730|\u8d77\u70b9)\s*(?:\u4e3a|\u662f)?\s*(.+?)(?:\u51fa\u53d1)?",
        query.strip(),
    )
    if origin_match:
        origin = origin_match.group(1).strip().removesuffix("\u51fa\u53d1")
        destination = navigation_context.get("destination", "") or next(
            (turn.slots.get("destination", "") for turn in reversed(history) if turn.intent == "map_route"), ""
        )
        if not origin:
            return None
        return {"origin": origin, "destination": destination, "via": navigation_context.get("via", [])}
    if navigation_context.get("awaiting") == "origin" and not _starts_new_task(query):
        origin = query.strip()
        if re.fullmatch(r"[\u4e00-\u9fffA-Za-z0-9\s-]{2,40}", origin):
            return {
                "origin": origin,
                "destination": navigation_context["destination"],
                "via": navigation_context.get("via", []),
            }
    last = history[-1] if history else None
    if last and last.intent == "navigation_origin" and last.slots.get("origin"):
        destination = query.strip()
        return {"origin": last.slots["origin"], "destination": destination, "via": last.slots.get("via", [])} if destination else None
    return None


def _navigation_via_follow_up(query: str, history: list[Turn]) -> dict | None:
    """Add one waypoint to the active route without sending a deterministic edit to FC."""
    context = _navigation_context(history)
    if not context:
        return None
    matched = re.fullmatch(
        r"(?:\u8def\u7ebf|\u8def\u4e0a(?:\u8981)?)?(?:\u52a0(?:\u4e0a|\u4e00\u4e2a)?|\u6dfb\u52a0|\u7ecf\u8fc7|\u9014\u7ecf|\u5148\u53bb|\u987a\u8def\u53bb)\s*(.+?)",
        query.strip(),
    )
    if not matched:
        return None
    waypoint = re.split(r"(?:\u518d\u53bb|\u7136\u540e\u53bb)", matched.group(1), maxsplit=1)[0].strip()
    if not waypoint:
        return None
    via = list(context.get("via", []))
    if waypoint not in via:
        via.append(waypoint)
    return {
        "origin": context.get("origin", ""),
        "destination": context["destination"],
        "via": via,
        "waypoint": waypoint,
    }


class DialogueAgent:
    def __init__(
        self,
        memory: MemoryStore | None = None,
        tools: ToolRegistry | None = None,
        nlu_backend: NLUBackend | None = None,
        reject_backend: RejectBackend | None = None,
        chat_backend: ChatBackend | None = None,
    ):
        self.memory = memory or MemoryStore()
        self.tools = tools or default_registry()
        self.nlu_backend = nlu_backend or build_nlu_backend()
        self.reject_backend = reject_backend or RuleRejectBackend()
        self.chat_backend = chat_backend or RuleChatBackend()

    def handle(self, query: str, sender_id: str = "demo", trace_id: str | None = None) -> list[Frame]:
        started = time.perf_counter()
        trace_id = trace_id or uuid.uuid4().hex
        history = self.memory.get(sender_id)
        rewritten = rewrite_query(query, history)
        navigation_context = _navigation_context(history)
        nlu_context = {} if navigation_context and _starts_new_task(rewritten) else navigation_context
        confirmation = _cockpit_confirmation(rewritten, history)
        if confirmation:
            return self._resolve_cockpit_confirmation(
                rewritten, sender_id, trace_id, started, confirmation
            )

        explicit_cockpit_slots = _cockpit_slots(rewritten)
        cockpit_slots = explicit_cockpit_slots or _cockpit_follow_up_slots(rewritten, history)
        cockpit_context = "history" if cockpit_slots and not explicit_cockpit_slots else "explicit"
        if _implicit_air_condition_adjustment(rewritten) and not cockpit_slots:
            return self._air_condition_activation_required(rewritten, sender_id, trace_id, started)
        route = arbitrate(rewritten)
        if _nearby_category(rewritten) or cockpit_slots or nlu_context:
            route = "task"
        metadata = {
            "trace_id": trace_id,
            "route": route,
            "nlu_backend": "not_used",
            "conversation_context": nlu_context,
        }

        music_choice = _pending_music_choice(rewritten, history)
        if music_choice:
            artist, song, action, platform = music_choice
            target = f"{artist} {song}".strip()
            answer = (
                f"\u5df2\u4e3a\u4f60\u51c6\u5907 {target} \u7684\u7b2c\u4e09\u65b9\u97f3\u4e50\u641c\u7d22\u3002"
                if action == "third_party_search"
                else "\u6b63\u5728\u542f\u52a8\u7ad9\u5185\u6f14\u793a\u97f3\u9891\u3002"
            )
            tool_result = {
                "provider": "music-consent",
                "action": action,
                "artist": artist,
                "song": song,
                "query": target,
                "platform": platform,
            }
            metadata.update(
                {
                    "route": "music_consent",
                    "tool_trace": {
                        "function": "music.play",
                        "provider": "music-consent",
                        "action": action,
                        "platform": platform,
                        "latency_ms": 0,
                    },
                    "tool_result": tool_result,
                }
            )
            slots = {"artist": artist, **({"song": song} if song else {})}
            self.memory.append(sender_id, Turn(rewritten, answer, "music_play", slots))
            return list(
                stream_text(
                    answer,
                    intent="music_play",
                    function="music.play",
                    slots=slots,
                    metadata=self._finish(metadata, started),
                )
            )

        navigation_via = _navigation_via_follow_up(rewritten, history)
        if navigation_via:
            return self._resolve_navigation_via(rewritten, sender_id, started, metadata, navigation_via)

        navigation_follow_up = _navigation_follow_up(rewritten, history)
        if navigation_follow_up:
            origin = navigation_follow_up["origin"]
            destination = navigation_follow_up["destination"]
            via = navigation_follow_up["via"]
            if destination:
                via_copy = f"\uff0c\u9014\u7ecf{'\u3001'.join(via)}" if via else ""
                answer = f"\u5df2\u786e\u8ba4\u4ece{origin}\u5230{destination}{via_copy}\uff0c\u8def\u7ebf\u6b63\u5728\u751f\u6210\uff0c\u5b8c\u6210\u540e\u5c06\u5728\u53f3\u4fa7\u663e\u793a\u5730\u56fe\u3001\u8ddd\u79bb\u4e0e\u65f6\u95f4\u3002"
                action = "route_request"
                intent = "map_route"
                slots = {"origin": origin, "destination": destination, **({"via": via} if via else {})}
            else:
                answer = f"\u5df2\u786e\u8ba4\u51fa\u53d1\u5730\u4e3a{origin}\u3002\u8bf7\u544a\u77e5\u76ee\u7684\u5730\uff0c\u4ee5\u4fbf\u4e3a\u60a8\u89c4\u5212\u8def\u7ebf\u3002"
                action = "await_destination"
                intent = "navigation_origin"
                slots = {"origin": origin, **({"via": via} if via else {})}
            tool_result = {"provider": "dialogue-state", "action": action, **slots}
            metadata.update(
                {
                    "route": "navigation_state",
                    "decision_policy": {"strategy": "dialogue_state", "reason": "navigation_slot_resolved"},
                    "tool_trace": {"function": "map.route", "provider": "dialogue-state", "action": action, "latency_ms": 0},
                    "tool_result": tool_result,
                    "navigation_request": tool_result if action == "route_request" else {},
                }
            )
            self.memory.append(sender_id, Turn(rewritten, answer, intent, slots))
            return list(
                stream_text(
                    answer,
                    intent=intent,
                    function="map.route" if action == "route_request" else "",
                    slots=slots,
                    metadata=self._finish(metadata, started),
                )
            )

        try:
            reject = self.reject_backend.evaluate(rewritten, trace_id)
        except (OSError, RuntimeError, ValueError) as exc:
            reject = RuleRejectBackend().evaluate(rewritten, trace_id)
            reject = reject.__class__(
                allowed=reject.allowed,
                confidence=reject.confidence,
                latency_ms=reject.latency_ms,
                backend=reject.backend,
                fallback_reason=f"reject_error:{type(exc).__name__}",
            )
        metadata["reject_trace"] = {
            "backend": reject.backend,
            "allowed": reject.allowed,
            "confidence": reject.confidence,
            "latency_ms": reject.latency_ms,
            "fallback_reason": reject.fallback_reason,
        }

        if not reject.allowed and route != "task":
            answer = "抱歉，这个请求不在当前车载任务能力范围内。"
            self.memory.append(sender_id, Turn(rewritten, answer, "reject"))
            return list(stream_text(answer, intent="reject", metadata=self._finish(metadata, started)))

        if not reject.allowed:
            metadata["reject_trace"]["task_route_override"] = True

        if cockpit_slots:
            return self._execute_cockpit_control(
                rewritten, sender_id, started, metadata, cockpit_slots, cockpit_context
            )

        if route == "reject":
            answer = "抱歉，这个问题我还没理解，请换个说法。"
            self.memory.append(sender_id, Turn(rewritten, answer, "reject"))
            return list(stream_text(answer, intent="reject", metadata=self._finish(metadata, started)))

        if route == "chat":
            try:
                chat = self.chat_backend.reply(rewritten)
            except (OSError, RuntimeError, ValueError):
                chat = RuleChatBackend().reply(rewritten)
            answer = chat.text
            self.memory.append(sender_id, Turn(rewritten, answer, "chat"))
            metadata["chat_trace"] = chat.trace
            return list(stream_text(answer, intent="chat", metadata=self._finish(metadata, started)))

        try:
            decision = self.nlu_backend.parse(rewritten, trace_id, context=nlu_context)
        except (OSError, RuntimeError, ValueError) as exc:
            decision = RuleNluBackend().parse(rewritten, trace_id)
            decision = decision.__class__(
                result=decision.result,
                backend=decision.backend,
                latency_ms=decision.latency_ms,
                fallback_reason=f"remote_error:{type(exc).__name__}",
            )

        nlu = decision.result
        if not self.tools.has(nlu.function):
            fallback = RuleNluBackend().parse(rewritten, trace_id)
            decision = fallback.__class__(
                result=fallback.result,
                backend=fallback.backend,
                latency_ms=decision.latency_ms + fallback.latency_ms,
                fallback_reason=f"unsupported_function:{nlu.function}",
            )
            nlu = decision.result

        combined_navigation = _combined_navigation_request(rewritten)
        nearby_category = _nearby_category(rewritten)
        if nlu.function == "music.play":
            nlu = replace(nlu, slots=_enrich_music_slots(rewritten, nlu.slots))
        if nearby_category:
            nlu = replace(nlu, intent="nearby_search", function="map.nearby", slots={"category": nearby_category})
        if nlu.function == "map.route" and combined_navigation:
            origin, destination = combined_navigation
            nlu = replace(nlu, slots={**nlu.slots, "origin": origin, "destination": destination})

        navigation_origin_resolved = False
        if (
            nlu_context.get("awaiting") == "origin"
            and nlu.function == "map.route"
            and nlu_context.get("destination")
        ):
            inferred_origin = nlu.slots.get("origin") or nlu.slots.get("destination")
            if inferred_origin:
                nlu = replace(
                    nlu,
                    slots={
                        "origin": inferred_origin,
                        "destination": nlu_context["destination"],
                        **({"via": nlu_context["via"]} if nlu_context.get("via") else {}),
                    },
                )
                navigation_origin_resolved = True

        if nlu.function == "cockpit.control" and _requires_cockpit_confirmation(nlu.slots):
            return self._await_cockpit_confirmation(
                rewritten, sender_id, started, metadata, cockpit_context, nlu.slots, decision
            )

        tool_started = time.perf_counter()
        tool_slots = {**nlu.slots, "_session_id": sender_id} if nlu.function == "cockpit.control" else nlu.slots
        tool_result = self.tools.call(nlu.function, tool_slots)
        tool_trace = {
            "function": nlu.function,
            "latency_ms": round((time.perf_counter() - tool_started) * 1000),
        }
        for key in ("provider", "tool", "action", "platform", "simulation", "state_scope"):
            if key in tool_result:
                tool_trace[key] = tool_result[key]
        if nlu.function == "cockpit.control":
            tool_trace["context_source"] = cockpit_context
        answer = self._nlg(nlu.function, tool_result)
        navigation_request = {}
        if nlu.function == "map.route" and (combined_navigation or navigation_origin_resolved) and "error" not in tool_result:
            origin, destination = nlu.slots["origin"], nlu.slots["destination"]
            via = nlu.slots.get("via", [])
            via_copy = f"\uff0c\u9014\u7ecf{'\u3001'.join(via)}" if via else ""
            answer = f"\u5df2\u786e\u8ba4\u4ece{origin}\u5230{destination}{via_copy}\uff0c\u8def\u7ebf\u6b63\u5728\u751f\u6210\uff0c\u5b8c\u6210\u540e\u5c06\u5728\u53f3\u4fa7\u663e\u793a\u5730\u56fe\u3001\u8ddd\u79bb\u4e0e\u65f6\u95f4\u3002"
            navigation_request = {
                "provider": "dialogue-state",
                "action": "route_request",
                "origin": origin,
                "destination": destination,
                **({"via": via} if via else {}),
            }
        self.memory.append(sender_id, Turn(rewritten, answer, nlu.intent, nlu.slots))
        metadata.update(
            {
                "nlu_backend": decision.backend,
                "nlu_latency_ms": decision.latency_ms,
                "fallback_reason": decision.fallback_reason,
                "nlu_trace": decision.trace,
                "decision_policy": decision.trace.get(
                    "decision_policy",
                    {"strategy": "rule_fallback" if decision.backend == "rule" else "nlu_backend"},
                ),
                "tool_trace": tool_trace,
                "tool_result": tool_result,
                "navigation_request": navigation_request,
            }
        )
        return list(
            stream_text(
                answer,
                intent=nlu.intent,
                function=nlu.function,
                slots=nlu.slots,
                metadata=self._finish(metadata, started),
            )
        )

    def _resolve_navigation_via(
        self,
        query: str,
        sender_id: str,
        started: float,
        metadata: dict,
        navigation_via: dict,
    ) -> list[Frame]:
        origin = navigation_via["origin"]
        destination = navigation_via["destination"]
        via = navigation_via["via"]
        waypoint = navigation_via["waypoint"]
        slots = {"destination": destination, "via": via, **({"origin": origin} if origin else {})}
        if origin:
            action = "route_request"
            answer = f"\u5df2\u5c06{waypoint}\u52a0\u5165\u9014\u7ecf\u70b9\uff0c\u6b63\u5728\u91cd\u65b0\u89c4\u5212\u4ece{origin}\u5230{destination}\u7684\u9a7e\u8f66\u8def\u7ebf\u3002"
        else:
            action = "await_origin"
            answer = f"\u5df2\u5c06{waypoint}\u52a0\u5165\u9014\u7ecf\u70b9\u3002\u8bf7\u544a\u77e5\u51fa\u53d1\u5730\uff0c\u6211\u5c06\u4e3a\u60a8\u89c4\u5212\u7ecf\u7531{'\u3001'.join(via)}\u7684\u9a7e\u8f66\u8def\u7ebf\u3002"
        tool_result = {"provider": "dialogue-state", "action": action, **slots}
        metadata.update(
            {
                "route": "navigation_state",
                "decision_policy": {"strategy": "dialogue_state", "reason": "navigation_via_resolved"},
                "tool_trace": {"function": "map.route", "provider": "dialogue-state", "action": action, "latency_ms": 0},
                "tool_result": tool_result,
                "navigation_request": tool_result if action == "route_request" else {},
            }
        )
        self.memory.append(sender_id, Turn(query, answer, "map_route", slots))
        return list(
            stream_text(
                answer,
                intent="map_route",
                function="map.route",
                slots=slots,
                metadata=self._finish(metadata, started),
            )
        )

    def _execute_cockpit_control(
        self,
        query: str,
        sender_id: str,
        started: float,
        metadata: dict,
        slots: dict,
        cockpit_context: str,
    ) -> list[Frame]:
        if _requires_cockpit_confirmation(slots):
            return self._await_cockpit_confirmation(
                query, sender_id, started, metadata, cockpit_context, slots
            )

        tool_started = time.perf_counter()
        tool_result = self.tools.call("cockpit.control", {**slots, "_session_id": sender_id})
        tool_trace = {
            "function": "cockpit.control",
            "latency_ms": round((time.perf_counter() - tool_started) * 1000),
            "context_source": cockpit_context,
        }
        for key in ("provider", "tool", "action", "simulation", "state_scope"):
            if key in tool_result:
                tool_trace[key] = tool_result[key]
        answer = self._nlg("cockpit.control", tool_result)
        self.memory.append(sender_id, Turn(query, answer, "cockpit_control", slots))
        metadata.update(
            {
                "route": "cockpit_state",
                "nlu_backend": "dialogue-state",
                "nlu_latency_ms": 0,
                "fallback_reason": "",
                "nlu_trace": {},
                "decision_policy": {
                    "strategy": "dialogue_state",
                    "reason": "cockpit_slots_resolved",
                },
                "tool_trace": tool_trace,
                "tool_result": tool_result,
            }
        )
        return list(
            stream_text(
                answer,
                intent="cockpit_control",
                function="cockpit.control",
                slots=slots,
                metadata=self._finish(metadata, started),
            )
        )

    def _await_cockpit_confirmation(
        self,
        query: str,
        sender_id: str,
        started: float,
        metadata: dict,
        cockpit_context: str,
        slots: dict,
        decision: object | None = None,
    ) -> list[Frame]:
        answer = "\u8fd9\u662f\u4e00\u6b21\u5ea7\u8231\u6a21\u62df\u64cd\u4f5c\uff1a\u786e\u8ba4\u6253\u5f00\u540e\u5907\u7bb1\u5417\uff1f\u8bf7\u8f93\u5165\u201c\u786e\u8ba4\u6267\u884c\u201d\u6216\u201c\u53d6\u6d88\u201d\u3002"
        tool_result = {
            "provider": "dialogue-state",
            "action": "await_confirmation",
            "simulation": True,
            "state_scope": "session",
            "target": slots.get("target"),
        }
        self.memory.append(sender_id, Turn(query, answer, "cockpit_confirmation", slots))
        metadata.update(
            {
                "route": "cockpit_state",
                "nlu_backend": decision.backend if decision else "dialogue-state",
                "nlu_latency_ms": decision.latency_ms if decision else 0,
                "fallback_reason": decision.fallback_reason if decision else "",
                "nlu_trace": decision.trace if decision else {},
                "decision_policy": {
                    "strategy": "dialogue_state",
                    "reason": "cockpit_confirmation_required",
                },
                "tool_trace": {
                    "function": "cockpit.control",
                    "provider": "dialogue-state",
                    "action": "await_confirmation",
                    "simulation": True,
                    "state_scope": "session",
                    "context_source": cockpit_context,
                    "latency_ms": 0,
                },
                "tool_result": tool_result,
            }
        )
        return list(
            stream_text(
                answer,
                intent="cockpit_confirmation",
                function="cockpit.control",
                slots=slots,
                metadata=self._finish(metadata, started),
            )
        )

    def _air_condition_activation_required(
        self, query: str, sender_id: str, trace_id: str, started: float
    ) -> list[Frame]:
        answer = "\u7a7a\u8c03\u5c1a\u672a\u5f00\u542f\uff0c\u65e0\u6cd5\u8c03\u6574\u6e29\u5ea6\u3002\u8bf7\u5148\u8bf4\u201c\u6253\u5f00\u7a7a\u8c03\u201d\u3002"
        slots = {"target": "air_condition", "operation": "temperature_delta"}
        tool_result = {
            "provider": "dialogue-state",
            "action": "activation_required",
            "simulation": True,
            "state_scope": "session",
            "target": "air_condition",
        }
        self.memory.append(sender_id, Turn(query, answer, "cockpit_activation_required", slots))
        metadata = {
            "trace_id": trace_id,
            "route": "cockpit_state_guard",
            "nlu_backend": "dialogue-state",
            "tool_trace": {
                "function": "cockpit.control",
                "provider": "dialogue-state",
                "action": "activation_required",
                "simulation": True,
                "state_scope": "session",
                "latency_ms": 0,
            },
            "tool_result": tool_result,
        }
        return list(
            stream_text(
                answer,
                intent="cockpit_activation_required",
                function="cockpit.control",
                slots=slots,
                metadata=self._finish(metadata, started),
            )
        )

    def _resolve_cockpit_confirmation(
        self,
        query: str,
        sender_id: str,
        trace_id: str,
        started: float,
        confirmation: tuple[str, dict],
    ) -> list[Frame]:
        action, slots = confirmation
        metadata = {
            "trace_id": trace_id,
            "route": "cockpit_confirmation",
            "nlu_backend": "session-memory",
        }
        if action == "cancelled":
            answer = "\u5df2\u53d6\u6d88\u5ea7\u8231\u6a21\u62df\u64cd\u4f5c\uff0c\u5f53\u524d\u4f1a\u8bdd\u7684\u72b6\u6001\u672a\u53d8\u66f4\u3002"
            tool_result = {
                "provider": "dialogue-state",
                "action": "cancelled",
                "simulation": True,
                "state_scope": "session",
                "target": slots.get("target"),
            }
            intent = "cockpit_cancelled"
        else:
            tool_started = time.perf_counter()
            tool_result = self.tools.call("cockpit.control", {**slots, "_session_id": sender_id})
            answer = self._nlg("cockpit.control", tool_result)
            intent = "cockpit_control"
            metadata["tool_latency_ms"] = round((time.perf_counter() - tool_started) * 1000)

        self.memory.append(sender_id, Turn(query, answer, intent, slots))
        metadata.update(
            {
                "tool_trace": {
                    "function": "cockpit.control",
                    "provider": tool_result.get("provider"),
                    "tool": tool_result.get("tool"),
                    "action": tool_result.get("action", action),
                    "simulation": True,
                    "state_scope": tool_result.get("state_scope", "session"),
                    "context_source": "confirmation",
                    "latency_ms": metadata.pop("tool_latency_ms", 0),
                },
                "tool_result": tool_result,
            }
        )
        return list(
            stream_text(
                answer,
                intent=intent,
                function="cockpit.control",
                slots=slots,
                metadata=self._finish(metadata, started),
            )
        )

    def handle_as_dicts(self, query: str, sender_id: str = "demo", trace_id: str | None = None) -> list[dict]:
        return [frame.to_dict() for frame in self.handle(query, sender_id, trace_id)]

    def status(self) -> dict:
        return {"status": "healthy", "nlu": self.nlu_backend.describe(), "tools": len(self.tools.list_tools())}

    @staticmethod
    def _finish(metadata: dict, started: float) -> dict:
        return {**metadata, "total_latency_ms": round((time.perf_counter() - started) * 1000)}

    def _chat(self, query: str) -> str:
        if "笑话" in query:
            return "可以。为什么程序员喜欢安静？因为一有噪声，就想 debug。"
        return "我是一个任务型对话 Agent Demo，可以查天气、放音乐、规划路线，也能做简单闲聊。"

    def _nlg(self, function: str, result: dict) -> str:
        if function == "cockpit.control" and result.get("action") == "activation_required":
            return "\u7a7a\u8c03\u5c1a\u672a\u5f00\u542f\uff0c\u672a\u8c03\u6574\u6e29\u5ea6\u3002\u8bf7\u5148\u8bf4\u201c\u6253\u5f00\u7a7a\u8c03\u201d\u3002"
        if "error" in result:
            if function == "map.route":
                return "地图服务暂时不可用，请稍后重试或改用手动起终点规划。"
            return "工具暂时不可用，我稍后再试。"
        if function == "weather.query":
            return f"{result['city']}{result['date']}天气{result['weather']}，气温{result['temperature']}。"
        if function == "music.play":
            if result.get("action") == "consent_required":
                artist = result.get("artist") or "当前歌手"
                return f"已识别{artist}的音乐请求，请选择第三方搜索或站内演示音频播放。"
            return f"正在为你播放{result['artist']}的《{result['song']}》。"
        if function == "map.nearby":
            keyword = result.get("keyword", "\u5468\u8fb9\u670d\u52a1")
            return f"\u53ef\u4ee5\u4e3a\u4f60\u641c\u7d22\u9644\u8fd1{keyword}\u3002\u8bf7\u9009\u62e9\u4f7f\u7528\u5f53\u524d\u4f4d\u7f6e\uff0c\u6216\u624b\u52a8\u8f93\u5165\u4e00\u4e2a\u5730\u70b9\u3002"
        if function == "cockpit.control":
            return f"\u5df2\u5728\u5ea7\u8231\u6a21\u62df\u5668\u4e2d\u6267\u884c\uff1a{result.get('summary', '\u5ea7\u8231\u52a8\u4f5c')}\u3002\u53f3\u4fa7\u53ef\u67e5\u770b\u72b6\u6001\u53d8\u5316\u4e0e\u610f\u56fe\u8bc6\u522b Trace\u3002"
        if function == "map.route":
            destination = result.get("destination", "目的地")
            poi = next(iter(result.get("pois", [])), {})
            resolved_name = poi.get("name") or destination
            return f"已找到{resolved_name}。请使用当前位置，或输入出发地后为你规划驾车路线。"
        return "任务已处理完成。"
