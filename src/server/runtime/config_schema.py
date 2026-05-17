"""
一个 配置标准化/规范化模块
"""

from __future__ import annotations
from copy import deepcopy
from typing import Any, Dict, List


# 默认传感器配置
DEFAULT_SENSORS = {
    "detect_player": True,
    "database_binding": "none",
}
# 默认可用动作列表 - 8种预设动作
DEFAULT_ACTIONS = [
    "GIVE_ITEM",
    "MOVE_TO",
    "NPC_EMOTE",
    "NPC_SAY",
    "NPC_STOP",
    "START_QUEST",
    "TAKE_ITEM",
    "UPDATE_QUEST",
    "GIVE_GOLD",
]


def normalize_agent_config(raw_config: Dict[str, Any]) -> Dict[str, Any]:
    raw = deepcopy(raw_config or {})
    normalized = _normalize_v2(raw)

    # 运行时衍生字段
    normalized["personality"] = _build_personality_text(normalized)

    # 确保 sensors 和 actions 是正确格式
    normalized["sensors"] = _fix_sensors_format(normalized.get("sensors", DEFAULT_SENSORS))
    normalized["actions"] = _fix_actions_format(normalized.get("actions", DEFAULT_ACTIONS))

    return normalized

# 处理 v2 格式配置 - v2 规范化（处理字段缺失的默认值）
def _normalize_v2(config: Dict[str, Any]) -> Dict[str, Any]:
    meta = config.get("meta", {})
    presentation = config.get("presentation", {})
    persona = config.get("persona", {})
    knowledge = config.get("knowledge", {})

    normalized = {
        "id": config.get("id", ""),
        "version": str(config.get("version", "2.0")),
        "meta": {
            "name": meta.get("name", ""),
            "role": meta.get("role", "villager"),
            "tags": list(meta.get("tags", [])),
        },
        "presentation": {
            "sprite": presentation.get("sprite", ""),
            "render_cfg": _normalize_render_cfg(presentation.get("render_cfg", {})),
        },
        "persona": {
            "identity": persona.get("identity", ""),
            "world_id": persona.get("world_id", ""),
            "allowed_categories": list(persona.get("allowed_categories", [])),
            "speaking_style": persona.get("speaking_style", "plain"),
            "greeting": persona.get("greeting", ""),
            "taboos": list(persona.get("taboos", [])),
        },
        "knowledge": {
            "world_facts": list(knowledge.get("world_facts", [])),
            "topics": list(knowledge.get("topics", [])),
        },
        # 新版简化字段
        "sensors": config.get("sensors", DEFAULT_SENSORS),
        "actions": list(config.get("actions", DEFAULT_ACTIONS)),
        # 其他字段
        "quests": [_normalize_quest(quest) for quest in config.get("quests", [])],
    }
    return normalized

def _fix_sensors_format(sensors: Any) -> Dict[str, Any]:
    """修复 sensors 格式，确保是正确的 v2 格式"""
    if isinstance(sensors, dict) and "detect_player" in sensors:
        return {
            "detect_player": bool(sensors.get("detect_player", True)),
            "database_binding": sensors.get("database_binding", "none"),
        }
    return DEFAULT_SENSORS
def _fix_actions_format(actions: Any) -> List[str]:
    """修复 actions 格式，确保是字符串列表"""
    if not actions:
        return DEFAULT_ACTIONS
    if isinstance(actions, list) and all(isinstance(a, str) for a in actions):
        return actions
    return DEFAULT_ACTIONS

# 标准化精灵动画配置 - 渲染配置处理（确保包含完整的 8 个方向动画帧定义）
def _normalize_render_cfg(render_cfg: Dict[str, Any]) -> Dict[str, Any]:
    cfg = render_cfg or {}
    animations = cfg.get("animations", {})
    default_idle = list(animations.get("idle", [0, 1]))
    default_walk = list(animations.get("walk", [8, 12]))

    return {
        "frameWidth": int(cfg.get("frameWidth", 48)),
        "frameHeight": int(cfg.get("frameHeight", 64)),
        "scale": int(cfg.get("scale", 2)),
        "animations": {
            "idle_down": list(animations.get("idle_down", default_idle)),
            "idle_left": list(animations.get("idle_left", default_idle)),
            "idle_right": list(animations.get("idle_right", default_idle)),
            "idle_up": list(animations.get("idle_up", default_idle)),
            "walk_down": list(animations.get("walk_down", default_walk)),
            "walk_left": list(animations.get("walk_left", default_walk)),
            "walk_right": list(animations.get("walk_right", default_walk)),
            "walk_up": list(animations.get("walk_up", default_walk)),
        },
    }

 # 标准化任务配置 - 任务配置处理
def _normalize_quest(quest: Dict[str, Any]) -> Dict[str, Any]:
    completion = quest.get("completion_check", {})
    rewards = quest.get("rewards", [])
    return {
        "id": quest.get("id", ""),
        "title": quest.get("title", ""),
        "description": quest.get("description", ""),
        "start_if": quest.get("start_if", {}),
        "completion_check": {
            "inventory_contains": list(completion.get("inventory_contains", [])),
        },
        "reward_text": quest.get("reward_text", ""),
        "rewards": list(rewards),
        "stages": list(quest.get("stages", [])),
    }

# 构建用于 LLM 的 personality 文本 -人设文本构建
def _build_personality_text(config: Dict[str, Any]) -> str:
    persona = config["persona"]
    meta = config["meta"]
    knowledge = config["knowledge"]

    lines = [
        f"Name: {meta['name'] or config['id']}",
        f"Role: {meta['role']}",
        f"Identity: {persona['identity']}".strip(),
        f"Speaking style: {persona['speaking_style']}",
    ]

    if knowledge["topics"]:
        lines.append("Topics: " + ", ".join(knowledge["topics"]))
    if persona["taboos"]:
        lines.append("Taboos: " + ", ".join(persona["taboos"]))

    # 添加世界知识（从 world config 注入）
    world_id = persona.get("world_id")
    if world_id:
        world_knowledge = _load_world_knowledge(world_id, persona.get("allowed_categories", []))
        if world_knowledge:
            lines.append("")
            lines.append(world_knowledge)

    return "\n".join(line for line in lines if line and not line.endswith(": "))


def _load_world_knowledge(world_id: str, allowed_categories: list) -> str:
    """从世界配置文件中加载知识并格式化为文本"""
    import json
    import os

    json_path = f"configs/{world_id}.json"
    if not os.path.exists(json_path):
        return ""

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            world_config = json.load(f)
    except Exception:
        return ""

    sections = []

    # 世界描述（关键事实）
    descriptions = world_config.get("description", [])
    if descriptions:
        desc_text = "\n".join(f"- {d}" for d in descriptions)
        sections.append(f"【世界关键事实】\n{desc_text}")

    # 通用背景
    general_info = world_config.get("general_info", "")
    if general_info:
        sections.append(f"【通用背景】\n{general_info}")

    # 专有知识（仅 allowed_categories 中的类别）
    categories = world_config.get("categories", [])
    for cat in categories:
        cat_name = cat.get("name", "")
        if cat_name in allowed_categories:
            items_text = "\n".join(f"- {item}" for item in cat.get("items", []))
            sections.append(f"【{cat_name}专有知识 - 你必须严格遵守】\n{items_text}")

    return "\n\n".join(sections) if sections else ""
