"""
记忆管理模块 - 统一协调器
协调短期对话记忆、长期关系摘要与知识检索，对外提供单一接口

分层设计：
- ShortTermMemoryDB  → 对话历史 SQLite 持久化（已有）
- LongTermMemory     → NPC 对玩家的关系摘要（新增，简化版键值对）
- RAGEngine          → 语义相关记忆关键词检索（已有）
- MemoryManager      → 对外统一协调器（本模块实现）

使用示例：
```python
mm = MemoryManager("npc_001")
mm.init_rag(rag_engine)

# 保存对话
mm.save_dialogue("player_1", "你好", "你好旅行者！")

# 记住关系事实
mm.remember("trust_level", "友好")

# 获取整合后的上下文
context = mm.get_context(filtered_state)
```
"""
from typing import Dict, Optional

from src.memory.short_term_db import ShortTermMemoryDB, get_short_term_db
from src.knowledge.rag_engine import RAGEngine


class LongTermMemory:
    """
    长期记忆（简化版）：存储 NPC 对玩家的关系摘要

    设计理念：
    - 不做复杂的 LLM 自动压缩/反思（保留给未来工作）
    - 以键值对存储关键事实，适配小型游戏性能约束

    存储示例：
    {"trust_level": "友好", "last_quest": "帮忙送信", "met_times": 3}
    """

    def __init__(self):
        self.facts: Dict[str, str] = {}

    def set_fact(self, key: str, value: str):
        """设置或更新一个关系事实"""
        self.facts[key] = value

    def get_fact(self, key: str) -> Optional[str]:
        """读取一个关系事实"""
        return self.facts.get(key)

    def get_all_facts(self) -> Dict[str, str]:
        """获取所有关系事实（用于持久化）"""
        return dict(self.facts)

    def load_facts(self, facts: Dict[str, str]):
        """从持久化数据批量加载事实"""
        self.facts = dict(facts)

    def to_context_string(self) -> str:
        """将长期记忆转为可注入 Prompt 的文本"""
        if not self.facts:
            return ""
        lines = ["[关于该玩家的长期记忆]"]
        for key, value in self.facts.items():
            lines.append(f"- {key}: {value}")
        return "\n".join(lines)

    def clear(self):
        """清除所有事实"""
        self.facts = {}


class MemoryManager:
    """
    记忆管理协调器（Facade 模式）

    职责：
    1. 短期记忆  → 委托 ShortTermMemoryDB（对话历史 CRUD）
    2. 长期记忆  → 委托 LongTermMemory（关系摘要存储）
    3. 知识检索  → 委托 RAGEngine（配置记忆关键词检索）
    4. 统一接口  → get_context() 供 Prompt 构建使用
    """

    def __init__(self, npc_id: str):
        self.npc_id = npc_id
        self.short_term: ShortTermMemoryDB = get_short_term_db()
        self.long_term: LongTermMemory = LongTermMemory()
        self.rag: Optional[RAGEngine] = None

    def init_rag(self, rag_engine: RAGEngine):
        """注入 RAG 引擎（由 framework.init_agent() 调用）"""
        self.rag = rag_engine

    # ── 短期记忆操作（对话历史）──

    def save_player_message(self, player_id: str, message: str) -> int:
        """保存玩家发言"""
        return self.short_term.save_player_message(
            npc_id=self.npc_id, player_id=player_id, message=message
        )

    def save_npc_response(self, player_id: str, response: str) -> int:
        """保存 NPC 回复"""
        return self.short_term.save_npc_response(
            npc_id=self.npc_id, player_id=player_id, response=response
        )

    def save_dialogue(self, player_id: str, player_msg: str,
                       npc_reply: str) -> tuple:
        """保存一轮完整对话（事务性）"""
        return self.short_term.save_dialogue_pair(
            npc_id=self.npc_id, player_id=player_id,
            player_message=player_msg, npc_response=npc_reply
        )

    def get_recent_dialogue(self, player_id: Optional[str] = None,
                             limit: int = 3) -> list:
        """获取最近 N 轮对话"""
        return self.short_term.get_recent_chats(
            npc_id=self.npc_id, player_id=player_id, limit=limit
        )

    def get_dialogue_for_display(self, player_id: Optional[str] = None,
                                  limit: int = 3) -> list:
        """获取前端展示用的对话历史（扁平化消息列表）"""
        return self.short_term.get_history_for_display(
            npc_id=self.npc_id, player_id=player_id, limit=limit
        )

    # ── 长期记忆操作（关系摘要）──

    def remember(self, key: str, value: str):
        """记住一个关于玩家的关键事实"""
        self.long_term.set_fact(key, value)

    def recall(self, key: str) -> Optional[str]:
        """回忆一个关于玩家的关键事实"""
        return self.long_term.get_fact(key)

    # ── 统一上下文构建 ──

    def get_context(self, state: dict) -> str:
        """
        构建记忆上下文，供 DialogueManager 注入 Prompt

        整合顺序：
        1. 长期记忆摘要（关系事实）
        2. RAG 检索结果（语义相关记忆）
        """
        parts = []

        # 长期记忆（关系摘要）
        long_term_text = self.long_term.to_context_string()
        if long_term_text:
            parts.append(long_term_text)

        # RAG 检索（语义相关记忆）
        if self.rag:
            rag_text = self.rag.retrieve(str(state))
            if rag_text:
                parts.append(rag_text)

        return "\n\n".join(parts)

    def clear(self, player_id: Optional[str] = None):
        """清除记忆（短期 + 长期）"""
        self.short_term.clear_npc_memory(self.npc_id, player_id)
        self.long_term.clear()

    def get_statistics(self) -> dict:
        """获取记忆统计"""
        return self.short_term.get_statistics(self.npc_id)
