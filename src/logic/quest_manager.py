"""
任务处理范式（Quest Manager）

提供可复用的任务生命周期管理：
- 查询可接取/可完成的任务
- 验证任务完成条件
- 生成任务接取/完成的标准动作

设计原则：
- 纯业务逻辑，不依赖具体游戏实现
- 游戏开发者可通过 bridge 文件调用，也可替换/扩展具体验证逻辑
- 与 config_schema 中 quest 配置数据（id/title/description/completion_check/rewards）配合使用
- 复用 QuestValidator 进行条件验证
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from src.logic.quest_validator import QuestValidator


class QuestManager:
    """任务处理范式：查询 / 验证 / 动作生成"""

    def __init__(self, quests: Optional[List[Dict[str, Any]]] = None):
        self.quests: List[Dict[str, Any]] = quests or []
        self.validator = QuestValidator()

    def set_quests(self, quests: List[Dict[str, Any]]) -> None:
        """设置任务列表（热更新），同时注册到 QuestValidator"""
        self.quests = quests or []
        for quest in self.quests:
            qid = quest.get("id")
            if qid:
                self.validator.register_quest(
                    qid,
                    self._quest_to_validator_conditions(quest),
                )

    def _quest_to_validator_conditions(self, quest: Dict[str, Any]) -> List[Dict[str, Any]]:
        """将 v2 quest 配置转为 QuestValidator 条件格式"""
        conditions = []
        completion_check = quest.get("completion_check", {})
        for item_req in completion_check.get("inventory_contains", []):
            conditions.append({
                "type": "item_collected",
                "params": {
                    "item_id": item_req.get("item_id", ""),
                    "count": item_req.get("count", 1),
                },
            })
        return conditions

    # ── 查询 ──────────────────────────────────────────────

    def find_available_quest(
        self, active_ids: Set[str], completed_ids: Set[str]
    ) -> Optional[Dict[str, Any]]:
        """
        查找第一个可接取的任务（未激活且未完成）
        """
        return next(
            (
                quest for quest in self.quests
                if quest.get("id")
                and quest.get("id") not in active_ids
                and quest.get("id") not in completed_ids
            ),
            None,
        )

    def find_ready_quest(self, ready_ids: Set[str]) -> Optional[Dict[str, Any]]:
        """
        查找第一个待交付的任务
        """
        return next(
            (quest for quest in self.quests if quest.get("id") in ready_ids),
            None,
        )

    def get_quest_by_id(self, quest_id: str) -> Optional[Dict[str, Any]]:
        """按 ID 查找任务"""
        return next(
            (quest for quest in self.quests if quest.get("id") == quest_id),
            None,
        )

    # ── 验证 ──────────────────────────────────────────────

    def can_complete_quest(
        self, quest_id: str, inventory: List[Any], quests: List[Any]
    ) -> bool:
        """
        验证玩家是否满足任务完成条件

        优先使用 QuestValidator（如果已注册），回退到直接检查 inventory_contains
        """
        # 优先使用 QuestValidator
        if quest_id in self.validator.quest_definitions:
            result = self.validator.validate(quest_id, {"player_inventory": inventory})
            return result.get("completed", False)

        # 回退：直接检查 completion_check.inventory_contains
        quest = self.get_quest_by_id(quest_id)
        if not quest:
            quest = next((q for q in quests if q.get("id") == quest_id), None)
            if not quest:
                return False

        completion_check = quest.get("completion_check", {})
        requirements = completion_check.get("inventory_contains", [])

        for req in requirements:
            item_id = req.get("item_id", "")
            need = req.get("count", 1)
            owned = self._count_inventory_item(inventory, item_id)
            if owned < need:
                return False

        return True

    def _count_inventory_item(self, inventory: List[Any], item_id: str) -> int:
        """统计背包中指定物品的数量"""
        total = 0
        for item in inventory:
            if not isinstance(item, dict):
                continue
            iid = item.get("id") or item.get("item_id", "")
            if iid == item_id:
                total += item.get("count", 1)
        return total

    # ── 动作生成 ──────────────────────────────────────────

    def build_start_quest_action(self, quest: Dict[str, Any]) -> Dict[str, Any]:
        """生成 start_quest 工具调用"""
        return {
            "tool": "start_quest",
            "arguments": {
                "quest_id": quest.get("id", ""),
                "title": quest.get("title", ""),
                "description": quest.get("description", ""),
            },
        }

    def build_complete_quest_action(self, quest: Dict[str, Any]) -> Dict[str, Any]:
        """生成 complete_quest 工具调用"""
        return {
            "tool": "complete_quest",
            "arguments": {
                "quest_id": quest.get("id", ""),
                "rewards": quest.get("rewards", []),
            },
        }

    def build_reward_dialogue(
        self, quest: Dict[str, Any], default_message: str = "做得不错，这件事已经办好了。"
    ) -> Dict[str, Any]:
        """生成任务完成的对话提示"""
        return {
            "tool": "dialogue",
            "arguments": {
                "message": quest.get("reward_text", default_message),
                "emotion": "satisfied",
            },
        }

    # ── 完整流程 ──────────────────────────────────────────

    def get_current_stage(self, quest_id: str, player_quests: List[Any]) -> int:
        """
        从玩家任务列表中获取指定任务的当前阶段
        
        Args:
            quest_id: 任务ID
            player_quests: 玩家活跃任务列表
        
        Returns:
            当前阶段编号（从1开始），0表示未开始或未找到
        """
        for q in player_quests:
            if isinstance(q, dict) and q.get("id") == quest_id:
                return q.get("stage", 1)
            elif isinstance(q, str) and q == quest_id:
                return 1  # 简单字符串格式默认阶段1
        return 0

    def check_stage_item(self, quest_id: str, stage: int, inventory: List[Any]) -> bool:
        """
        检查当前阶段所需物品是否在背包中
        
        Args:
            quest_id: 任务ID
            stage: 当前阶段编号
            inventory: 玩家背包
        
        Returns:
            True 如果所需物品在背包中
        """
        quest = self.get_quest_by_id(quest_id)
        if not quest:
            return False
        
        stages = quest.get("stages", [])
        if not stages:
            return False
        
        # 查找对应阶段
        stage_def = None
        for s in stages:
            if s.get("stage") == stage:
                stage_def = s
                break
        
        if not stage_def:
            return False
        
        required_item = stage_def.get("required_item", "")
        if not required_item:
            return False
        
        # 检查背包中是否有该物品
        return self._count_inventory_item(inventory, required_item) > 0

    def get_stage_hint(self, quest_id: str, stage: int) -> str:
        """
        获取指定阶段的提示信息
        
        Args:
            quest_id: 任务ID
            stage: 当前阶段编号
        
        Returns:
            提示文本
        """
        quest = self.get_quest_by_id(quest_id)
        if not quest:
            return ""
        
        stages = quest.get("stages", [])
        for s in stages:
            if s.get("stage") == stage:
                return s.get("hint", "")
        return ""

    def is_multi_stage_quest(self, quest_id: str) -> bool:
        """
        判断任务是否为多阶段任务
        
        Returns:
            True 如果任务定义了 stages 字段
        """
        quest = self.get_quest_by_id(quest_id)
        if not quest:
            return False
        return bool(quest.get("stages"))

    def try_complete_quests(
        self,
        state: Dict[str, Any],
        message_tokens: List[str],
    ) -> Optional[List[Dict[str, Any]]]:
        """
        尝试完成任务：如果玩家消息包含交付关键词且有可交付任务，返回完整动作序列

        返回格式如：
        [
            {"tool": "dialogue", "arguments": {"message": "...", "emotion": "satisfied"}},
            {"tool": "complete_quest", "arguments": {"quest_id": "...", "rewards": [...]}}
        ]
        """
        ready_ids = set(state.get("quest_ready_to_complete_ids", []))
        ready_quest = self.find_ready_quest(ready_ids)
        if not ready_quest:
            return None

        lowered = state.get("player_message", "").lower()
        if not any(token in lowered for token in message_tokens):
            return None

        return [
            self.build_reward_dialogue(ready_quest),
            self.build_complete_quest_action(ready_quest),
        ]

    def try_start_quests(
        self,
        state: Dict[str, Any],
        message_tokens: List[str],
    ) -> Optional[List[Dict[str, Any]]]:
        """
        尝试接取任务：如果玩家消息包含任务关键词且有可接取任务，返回完整动作序列
        """
        active_ids = set(state.get("quest_active_ids", []))
        completed_ids = set(state.get("quest_completed_ids", []))
        available_quest = self.find_available_quest(active_ids, completed_ids)
        if not available_quest:
            return None

        lowered = state.get("player_message", "").lower()
        if not any(token in lowered for token in message_tokens):
            return None

        return [
            {
                "tool": "dialogue",
                "arguments": {
                    "message": available_quest.get("description", "我这里有件事想请你帮忙。"),
                    "emotion": "neutral",
                },
            },
            self.build_start_quest_action(available_quest),
        ]
