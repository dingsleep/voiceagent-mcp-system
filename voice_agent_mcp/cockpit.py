"""Stateful, explicitly simulated cockpit actuator for the local demo."""

from __future__ import annotations

from copy import deepcopy


class CockpitSimulator:
    """Keep a small observable vehicle state without claiming real vehicle control."""

    def __init__(self) -> None:
        self._sessions: dict[str, dict] = {}

    @staticmethod
    def _initial_state() -> dict:
        return {
            "air_condition": {"on": False, "temperature": 24, "mode": "manual"},
            "windows": "closed",
            "seat_ventilation": False,
            "trunk": "closed",
            "ambient_light": {"on": False, "color": "cyan"},
            "wireless_charging": False,
        }

    def execute(self, slots: dict) -> dict:
        session_id = str(slots.get("_session_id") or "default")
        state = self._sessions.setdefault(session_id, self._initial_state())
        target = slots.get("target", "")
        operation = slots.get("operation", "")
        value = slots.get("value")
        activation_required = (
            target == "air_condition"
            and operation in {"temperature", "temperature_delta", "mode"}
            and not state["air_condition"]["on"]
        )
        summary = (
            "\u7a7a\u8c03\u5c1a\u672a\u5f00\u542f\uff0c\u672a\u8c03\u6574\u6e29\u5ea6"
            if activation_required
            else self._apply(state, target, operation, value)
        )
        return {
            "provider": "cockpit-simulator",
            "tool": "cockpit.control",
            "simulation": True,
            "state_scope": "session",
            **({"action": "activation_required"} if activation_required else {}),
            "target": target,
            "operation": operation,
            "summary": summary,
            "state": deepcopy(state),
        }

    @staticmethod
    def _apply(state: dict, target: str, operation: str, value: object) -> str:
        if target == "air_condition":
            air = state["air_condition"]
            if operation == "power":
                air["on"] = bool(value)
                return "\u7a7a\u8c03\u5df2\u5f00\u542f" if air["on"] else "\u7a7a\u8c03\u5df2\u5173\u95ed"
            if operation == "temperature":
                air["temperature"] = max(16, min(32, int(value)))
                return f"\u7a7a\u8c03\u6e29\u5ea6\u5df2\u8bbe\u4e3a {air['temperature']} \u5ea6"
            if operation == "temperature_delta":
                air["temperature"] = max(16, min(32, air["temperature"] + int(value)))
                return f"\u7a7a\u8c03\u6e29\u5ea6\u5df2\u8c03\u6574\u4e3a {air['temperature']} \u5ea6"
            if operation == "mode":
                air["mode"] = str(value)
                return "\u7a7a\u8c03\u5df2\u5207\u6362\u81ea\u52a8\u6a21\u5f0f" if value == "auto" else "\u7a7a\u8c03\u5df2\u5207\u6362\u624b\u52a8\u6a21\u5f0f"

        if target == "windows":
            state["windows"] = "open" if bool(value) else "closed"
            return "\u8f66\u7a97\u5df2\u6253\u5f00" if bool(value) else "\u8f66\u7a97\u5df2\u5173\u95ed"

        if target == "seat_ventilation":
            state["seat_ventilation"] = bool(value)
            return "\u4e3b\u9a7e\u5ea7\u6905\u901a\u98ce\u5df2\u6253\u5f00" if bool(value) else "\u4e3b\u9a7e\u5ea7\u6905\u901a\u98ce\u5df2\u5173\u95ed"

        if target == "trunk":
            state["trunk"] = "open" if bool(value) else "closed"
            return "\u540e\u5907\u7bb1\u5df2\u6253\u5f00" if bool(value) else "\u540e\u5907\u7bb1\u5df2\u5173\u95ed"

        if target == "ambient_light":
            light = state["ambient_light"]
            if operation == "power":
                light["on"] = bool(value)
                return "\u6c1b\u56f4\u706f\u5df2\u6253\u5f00" if bool(value) else "\u6c1b\u56f4\u706f\u5df2\u5173\u95ed"
            if operation == "color":
                light["on"] = True
                light["color"] = str(value)
                return f"\u6c1b\u56f4\u706f\u5df2\u5207\u6362\u4e3a{value}"

        if target == "wireless_charging":
            state["wireless_charging"] = bool(value)
            return "\u65e0\u7ebf\u5145\u7535\u5df2\u6253\u5f00" if bool(value) else "\u65e0\u7ebf\u5145\u7535\u5df2\u5173\u95ed"

        return "\u6682\u4e0d\u652f\u6301\u8be5\u5ea7\u8231\u52a8\u4f5c"
