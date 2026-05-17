"""
Mock 决策提供者
提供离线模式下的决策逻辑，通过策略模式注入到 DecisionEngine
"""
from typing import Dict, Any, List, Optional, Set
import random

from src.logic.quest_manager import QuestManager


class MockDecisionProvider:
    """
    模拟 LLM 决策提供者
    实现与真实 LLM 相同的接口，用于离线测试和演示
    """
    
    def __init__(self, profile: Optional[Dict[str, Any]] = None):
        self.profile = profile or {}
        self.quest_manager = QuestManager()
    
    def set_profile(self, profile: Dict[str, Any]):
        """设置 NPC 配置信息"""
        self.profile = profile or {}
        self.quest_manager.set_quests(self.profile.get("quests", []))
    
    def decide(self, prompt: str, state: Dict[str, Any]) -> List[Dict]:
        """
        模拟 LLM 决策（返回 tool call 格式）
        """
        _ = prompt
        
        event = state.get("event", "")
        distance = state.get("distance", state.get("distance_to_player", 999))
        player_message = state.get("player_message", "")
        persona = self.profile.get("persona", {})
        knowledge = self.profile.get("knowledge", {})

        if not event and distance < 120:
            event = "player_near"

        if event == "player_near":
            return self._handle_player_near(distance, persona)

        if event == "dialogue" and player_message:
            return self._handle_dialogue(player_message, state, knowledge)

        return []
    
    def _handle_player_near(self, distance: float, persona: Dict[str, Any]) -> List[Dict]:
        """处理玩家靠近事件"""
        if distance < 150:
            greeting = persona.get("greeting")
            greetings = [greeting] if greeting else [
                "欢迎来到这里。",
                "你好，有什么需要吗？",
                "见到你很高兴。",
            ]
            return [
                {"tool": "emote", "arguments": {"emotion": "wave", "duration": 1000}},
                {"tool": "dialogue", "arguments": {"message": random.choice(greetings), "emotion": "happy"}}
            ]
        else:
            return [{"tool": "emote", "arguments": {"emotion": "nod", "duration": 500}}]
    
    def _handle_dialogue(
        self,
        player_message: str,
        state: Dict[str, Any],
        knowledge: Dict[str, Any]
    ) -> List[Dict]:
        """处理对话事件"""
        lowered = player_message.lower()

        # 委托给 QuestManager 处理任务相关逻辑
        complete_result = self.quest_manager.try_complete_quests(
            state, ["完成", "交任务", "任务", "finish", "complete"]
        )
        if complete_result:
            return complete_result

        start_result = self.quest_manager.try_start_quests(
            state, ["任务", "帮忙", "工作", "quest", "help"]
        )
        if start_result:
            return start_result

        topics = knowledge.get("topics", [])
        if topics and any(token in lowered for token in ("哪里", "发生", "村", "forest", "village")):
            return [
                {
                    "tool": "dialogue",
                    "arguments": {
                        "message": f"我主要知道这些事：{'、'.join(topics[:3])}。",
                        "emotion": "thinking",
                    },
                }
            ]

        responses = [
            f"你说的是 '{player_message}'，让我想想。",
            "这个问题我可以和你聊聊。",
            "我会结合现在的情况回答你。",
            "这件事得看眼下发生了什么。",
        ]
        return [
            {"tool": "dialogue", "arguments": {"message": random.choice(responses), "emotion": "thinking"}}
        ]
    
    def _find_available_quest(
        self, quests: List[Dict], active_ids: Set[str], completed_ids: Set[str]
    ) -> Optional[Dict]:
        """查找可接取的任务"""
        return self.quest_manager.find_available_quest(active_ids, completed_ids)
    
    def _find_ready_quest(self, quests: List[Dict], ready_ids: Set[str]) -> Optional[Dict]:
        """查找可完成的任务"""
        return self.quest_manager.find_ready_quest(ready_ids)
    
    def _handle_complete_quest(self, quest: Dict) -> List[Dict]:
        """处理任务完成"""
        return [
            self.quest_manager.build_reward_dialogue(quest),
            self.quest_manager.build_complete_quest_action(quest),
        ]
    
    def _handle_start_quest(self, quest: Dict) -> List[Dict]:
        """处理任务接取"""
        return [
            {
                "tool": "dialogue",
                "arguments": {
                    "message": quest.get("description", "我这里有件事想请你帮忙。"),
                    "emotion": "neutral",
                },
            },
            self.quest_manager.build_start_quest_action(quest),
        ]