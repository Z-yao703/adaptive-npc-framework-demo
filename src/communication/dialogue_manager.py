"""
Build structured prompts for dialogue-first NPCs.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class DialogueManager:
    def __init__(self):
        self.personality: str = ""
        self.memory_context: str = ""
        self.system_prompt_template: str = ""
        self.greeting: str = ""
        self.npc_name: str = "NPC"
        self.profile: Dict[str, Any] = {}

    def set_personality(self, personality: str) -> None:
        self.personality = personality
        self._build_system_prompt()

    def set_name(self, name: str) -> None:
        self.npc_name = name or "NPC"

    def set_greeting(self, greeting: str) -> None:
        self.greeting = greeting or ""

    def set_profile(self, profile: Dict[str, Any]) -> None:
        self.profile = profile or {}
        self._build_system_prompt()

    def _build_system_prompt(self) -> None:
        persona = self.profile.get("persona", {})
        knowledge = self.profile.get("knowledge", {})
        dialogue_policy = self.profile.get("dialogue_policy", {})

        topics = ", ".join(knowledge.get("topics", [])) or "general village life"
        taboos = ", ".join(persona.get("taboos", [])) or "stay in character"
        fallback = dialogue_policy.get("fallback_reply", "这件事我得再想想。")
        max_sentences = dialogue_policy.get("max_reply_sentences", 2)

        # 提取 world_facts（包含本局阵营和秘密）
        world_facts = knowledge.get("world_facts", [])
        world_facts_text = ""
        if world_facts:
            world_facts_text = "你知道的关于这个世界的事实：\n"
            for fact in world_facts:
                world_facts_text += f"- {fact}\n"
            world_facts_text += "\n"

        # 暗号速查表（注入 system prompt，作为兜底）
        cipher_table = self._build_cipher_table(persona)

        self.system_prompt_template = (
            f"You are the game NPC '{self.npc_name}'.\n"
            f"Personality profile:\n{self.personality}\n\n"
            f"{world_facts_text}"
            f"{cipher_table}"
            f"Dialogue topics: {topics}\n"
            f"Taboos: {taboos}\n"
            f"Fallback reply: {fallback}\n"
            f"Maximum reply sentences: {max_sentences}\n\n"
            "You must stay in character, respond to the current scene, "
            "and only choose actions allowed by the scene policy."
        )
    
    def _build_cipher_table(self, persona: Dict[str, Any]) -> str:
        """
        根据 NPC 的 allowed_categories 构建暗号速查表
        
        这是 Embedding 匹配的兜底：如果 Embedding 匹配失败，
        LLM 仍可从 system prompt 中的速查表进行判断。
        """
        from src.knowledge.cipher_matcher import CIPHER_MAP, CIPHER_CATEGORY_MAP
        
        allowed = persona.get("allowed_categories", [])
        if not allowed:
            return ""
        
        relevant_entries = []
        for cipher, info in CIPHER_MAP.items():
            cat = CIPHER_CATEGORY_MAP.get(cipher, "")
            if cat in allowed:
                if info.get("action") == "give_item":
                    relevant_entries.append(
                        f'当玩家说出「{cipher}」→ 调用 give_item("{info["item"]}")'
                    )
                elif info.get("action") == "start_quest":
                    relevant_entries.append(
                        f'当玩家说出「{cipher}」→ 调用 start_quest("{info.get("quest_id")}")'
                    )
        
        if not relevant_entries:
            return ""
        
        lines = ["【暗号速查表 - 注意：暗号匹配由系统自动完成，以下仅供参考】"]
        for entry in relevant_entries:
            lines.append(f"- {entry}")
        lines.append("")
        
        return "\n".join(lines) + "\n"

    def set_memory(self, context: str) -> None:
        self.memory_context = context

    def build_prompt(self, state: Dict[str, Any]) -> str:
        standard = state.get("standard_state", {})
        dialogue = standard.get("dialogue", {})
        quest = standard.get("quest", {})
        world = standard.get("world", {})
        scenes = self.profile.get("dialogue_policy", {}).get("scenes", {})

        event = state.get("event", dialogue.get("event", "idle"))
        scene_policy = scenes.get(event, {})

        sections = [
            self.system_prompt_template,
            f"Current scene: {event}",
            f"Scene goal: {scene_policy.get('goal', 'React naturally to the player.')}",
            "Allowed actions: "
            + ", ".join(scene_policy.get("allowed_actions", ["NPC_SAY"])),
            "",
            "Current state:",
            self._format_state(state),
        ]

        if state.get("player_message"):
            sections.append(f"Player said: {state['player_message']}")

        active_quests = quest.get("active", [])
        ready_quests = quest.get("ready_to_complete", [])
        if active_quests:
            sections.append(f"Active quests: {active_quests}")
        if ready_quests:
            sections.append(f"Ready to complete quests: {ready_quests}")

        if world.get("time_of_day") or world.get("weather"):
            sections.append(
                f"World context: time={world.get('time_of_day')}, weather={world.get('weather')}"
            )

        if self.memory_context:
            sections.append(f"Memory context: {self.memory_context}")

        sections.append("Choose the best action sequence for this moment.")
        return "\n".join(section for section in sections if section)

    def _format_state(self, state: Dict[str, Any]) -> str:
        lines = []

        if "player_position" in state:
            lines.append(f"player_position={state['player_position']}")
        if "npc_position" in state:
            lines.append(f"npc_position={state['npc_position']}")
        if "distance_to_player" in state:
            lines.append(f"distance_to_player={round(float(state['distance_to_player']), 2)}")
        if "player_inventory" in state:
            lines.append(f"player_inventory={state['player_inventory']}")
        if "player_quests" in state:
            lines.append(f"player_quests={state['player_quests']}")
        if "quest_completed_ids" in state:
            lines.append(f"quest_completed_ids={state['quest_completed_ids']}")
        if "quest_ready_to_complete_ids" in state:
            lines.append(f"quest_ready_to_complete_ids={state['quest_ready_to_complete_ids']}")
        if "relationship_visits" in state:
            lines.append(f"relationship_visits={state['relationship_visits']}")
        if "time_of_day" in state:
            lines.append(f"time_of_day={state['time_of_day']}")
        if "weather" in state:
            lines.append(f"weather={state['weather']}")

        return "\n".join(lines) if lines else "no special state"

    def build_dialogue(self, message: str, emotion: Optional[str] = None) -> Dict[str, Any]:
        result = {
            "type": "dialogue",
            "message": message,
        }
        if emotion:
            result["emotion"] = emotion
        return result

    def generate_greeting(self) -> str:
        if self.greeting:
            return self.greeting
        return "你好。"
