"""
Standardize game state exchanged through AgentBridge.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List


def normalize_game_state(raw_state: Dict[str, Any], agent_id: str = "") -> Dict[str, Any]:
    raw = deepcopy(raw_state or {})
    standard = _to_standard_state(raw, agent_id)
    flat = _flatten_standard_state(standard, raw)
    flat["standard_state"] = standard
    return flat


def _to_standard_state(raw: Dict[str, Any], agent_id: str) -> Dict[str, Any]:
    if any(key in raw for key in ("player", "npc", "dialogue", "quest", "world", "relationship")):
        player = raw.get("player", {})
        npc = raw.get("npc", {})
        dialogue = raw.get("dialogue", {})
        quest = raw.get("quest", {})
        world = raw.get("world", {})
        relationship = raw.get("relationship", {})
        return {
            "player": {
                "id": player.get("id", raw.get("player_id", "player")),
                "position": player.get("position", raw.get("player_position", {"x": 0, "y": 0})),
                "inventory": player.get("inventory", raw.get("player_inventory", [])),
                "level": player.get("level", raw.get("player_level")),
                "health": player.get("health", raw.get("player_health")),
            },
            "npc": {
                "id": npc.get("id", agent_id or raw.get("npc_id", "")),
                "position": npc.get("position", raw.get("npc_position", {"x": 0, "y": 0})),
            },
            "dialogue": {
                "event": dialogue.get("event", raw.get("event", "idle")),
                "player_text": dialogue.get("player_text", raw.get("player_message", "")),
                "history": dialogue.get("history", raw.get("dialogue_history", [])),
            },
            "quest": {
                "active": quest.get("active", raw.get("quest_active_ids", raw.get("player_quests", []))),
                "completed": quest.get("completed", raw.get("quest_completed_ids", [])),
                "ready_to_complete": quest.get("ready_to_complete", raw.get("quest_ready_to_complete_ids", [])),
            },
            "world": {
                "time_of_day": world.get("time_of_day", raw.get("time_of_day")),
                "weather": world.get("weather", raw.get("weather")),
            },
            "relationship": {
                "visits": relationship.get("visits", raw.get("relationship_visits", 0)),
            },
            "timestamp": raw.get("timestamp"),
        }

    return {
        "player": {
            "id": raw.get("player_id", "player"),
            "position": raw.get("player_position", {"x": 0, "y": 0}),
            "inventory": raw.get("player_inventory", []),
            "level": raw.get("player_level"),
            "health": raw.get("player_health"),
        },
        "npc": {
            "id": agent_id or raw.get("npc_id", ""),
            "position": raw.get("npc_position", {"x": 0, "y": 0}),
        },
        "dialogue": {
            "event": raw.get("event", "idle"),
            "player_text": raw.get("player_message", ""),
            "history": raw.get("dialogue_history", []),
        },
        "quest": {
            "active": raw.get("player_quests", []),
            "completed": raw.get("quest_completed_ids", []),
            "ready_to_complete": raw.get("quest_ready_to_complete_ids", []),
        },
        "world": {
            "time_of_day": raw.get("time_of_day"),
            "weather": raw.get("weather"),
        },
        "relationship": {
            "visits": raw.get("relationship_visits", 0),
        },
        "timestamp": raw.get("timestamp"),
    }


def _flatten_standard_state(state: Dict[str, Any], raw: Dict[str, Any] = None) -> Dict[str, Any]:
    player = state.get("player", {})
    npc = state.get("npc", {})
    dialogue = state.get("dialogue", {})
    quest = state.get("quest", {})
    world = state.get("world", {})
    relationship = state.get("relationship", {})

    player_position = player.get("position") or {"x": 0, "y": 0}
    npc_position = npc.get("position") or {"x": 0, "y": 0}

    flat = {
        "player_id": player.get("id", "player"),
        "player_position": player_position,
        "player_inventory": _normalize_inventory(player.get("inventory", [])),
        "player_level": player.get("level"),
        "player_health": player.get("health"),
        "npc_position": npc_position,
        "event": dialogue.get("event", "idle"),
        "player_message": dialogue.get("player_text", ""),
        "dialogue_history": dialogue.get("history", []),
        "player_quests": _normalize_active_quests(quest.get("active", [])),
        "quest_active_ids": _quest_ids(quest.get("active", [])),
        "quest_completed_ids": _quest_ids(quest.get("completed", [])),
        "quest_ready_to_complete_ids": _quest_ids(quest.get("ready_to_complete", [])),
        "quest_stages": quest.get("stages", {}),
        "time_of_day": world.get("time_of_day"),
        "weather": world.get("weather"),
        "relationship_visits": relationship.get("visits", 0),
        "timestamp": state.get("timestamp"),
    }
    flat["distance_to_player"] = _distance(player_position, npc_position)
    flat["tradeable_items"] = (raw or {}).get("tradeable_items", state.get("tradeable_items", []))
    return flat


def _normalize_inventory(inventory: Any) -> List[Any]:
    if not isinstance(inventory, list):
        return inventory if inventory else []
    return inventory


def _normalize_active_quests(active: Any) -> List[Any]:
    if not isinstance(active, list):
        return []
    return active


def _quest_ids(values: Any) -> List[str]:
    if not isinstance(values, list):
        return []

    result = []
    for value in values:
        if isinstance(value, str):
            result.append(value)
        elif isinstance(value, dict) and value.get("id"):
            result.append(value["id"])
    return result


def _distance(a: Dict[str, Any], b: Dict[str, Any]) -> float:
    try:
        dx = float(a.get("x", 0)) - float(b.get("x", 0))
        dy = float(a.get("y", 0)) - float(b.get("y", 0))
        return (dx * dx + dy * dy) ** 0.5
    except Exception:
        return 0.0
