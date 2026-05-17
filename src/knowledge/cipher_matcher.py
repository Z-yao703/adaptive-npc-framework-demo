"""
暗号向量匹配器 (Cipher Matcher)

使用 sentence-transformers 做 Embedding 语义匹配，
将玩家输入与 NPC 掌握的暗号-物品映射进行余弦相似度匹配。

设计原则：
- 模型只需加载一次（类级别缓存）
- 暗号向量化只做一次（初始化时）
- 匹配阈值可配置
- 支持每个 NPC 只匹配其 allowed_categories 中的暗号

使用示例：
    matcher = get_cipher_matcher()
    result = matcher.match("我想卖掉这瓶牛乳可可饮品", ["香香的花", "牙膏味的草"])
    # {"matched_cipher": "牙膏味的草", "score": 0.85, "item": "薄荷叶", "action": "give_item"}
"""

from __future__ import annotations

import numpy as np
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING
import threading
if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

# 全局单例
_matcher_instance: Optional["CipherMatcher"] = None
_init_lock = threading.Lock()

# 暗号-物品-动作映射表（全局常量）
CIPHER_MAP: Dict[str, Dict[str, Any]] = {
    "香香的花": {
        "item": "玫瑰",
        "action": "give_item",
        "reply_template": "这些玫瑰刚剪下来，拿好。"
    },
    "牙膏味的草": {
        "item": "薄荷叶",
        "action": "give_item",
        "reply_template": "薄荷叶给你，小心别弄皱了。"
    },
    "胖胖的陆地生物": {
        "item": "猪肉",
        "action": "give_item",
        "reply_template": "新鲜的猪肉，接着！"
    },
    "会吐泡泡的水中生物": {
        "item": "黑鱼",
        "action": "give_item",
        "reply_template": "黑鱼给你，游得很欢呢。"
    },
    "做奇奇怪怪的菜": {
        "item": None,
        "action": "start_quest",
        "quest_id": "cook_food",
        "reply_template": "嘿嘿，你终于知道了暗号？想赚金币就帮我做一道菜吧！"
    },
}

# 暗号→类别映射（用于按 NPC 的 allowed_categories 过滤）
CIPHER_CATEGORY_MAP: Dict[str, str] = {
    "香香的花": "植物",
    "牙膏味的草": "植物",
    "胖胖的陆地生物": "动物",
    "会吐泡泡的水中生物": "动物",
    "做奇奇怪怪的菜": "任务",
}

# 所有暗号列表（用于构建 embedding 向量库）
ALL_CIPHERS = list(CIPHER_MAP.keys())

# 默认匹配阈值（余弦相似度，范围 0-1）
DEFAULT_SIMILARITY_THRESHOLD = 0.75


class CipherMatcher:
    """
    暗号向量匹配引擎

    使用 sentence-transformers 将玩家输入与预设暗号进行语义匹配。
    支持：
    - 近似说法匹配（如"香香的花～" → "香香的花"）
    - 按 NPC 专有知识类别过滤暗号范围
    - 自动返回暗号对应的物品和动作
    """

    def __init__(self, model_name: str = "BAAI/bge-small-zh-v1.5"):
        self.model_name = model_name
        self.model: Optional["SentenceTransformer"] = None
        self.cipher_embeddings: Optional[np.ndarray] = None
        self.cipher_labels: List[str] = []
        self.similarity_threshold = DEFAULT_SIMILARITY_THRESHOLD
        self._initialized = False
        self._init_lock = threading.Lock()

    def initialize(self) -> None:
        """加载模型并构建暗号向量库（首次调用时执行）"""
        if self._initialized:
            return

        with self._init_lock:
            if self._initialized:
                return

            from sentence_transformers import SentenceTransformer

            print(f"[CipherMatcher] Loading model: {self.model_name} ...")
            self.model = SentenceTransformer(self.model_name)
            print(f"[CipherMatcher] Model loaded. Building cipher embeddings...")

            self.cipher_labels = ALL_CIPHERS
            self.cipher_embeddings = self.model.encode(
                ALL_CIPHERS,
                normalize_embeddings=True  # L2 归一化，之后用点积即余弦相似度
            )
            self._initialized = True
            print(f"[CipherMatcher] Ready. {len(self.cipher_labels)} ciphers indexed.")

    def match(
        self,
        player_text: str,
        allowed_categories: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        对玩家输入做暗号匹配

        Args:
            player_text: 玩家输入文本
            allowed_categories: NPC 允许的知识类别（如 ["植物"]），用于过滤暗号范围。
                               为 None 时匹配全部暗号。

        Returns:
            None: 未命中任何暗号
            Dict: {
                "matched_cipher": str,   # 匹配到的暗号原文
                "similarity": float,     # 余弦相似度 (0-1)
                "item": str | None,      # 对应物品名
                "action": str,           # 触发动作 (give_item | start_quest)
                "quest_id": str | None,  # 任务ID (仅 start_quest 时有值)
                "reply_template": str,   # 预设回复模板
            }
        """
        if not self._initialized:
            self.initialize()

        assert self.model is not None
        assert self.cipher_embeddings is not None

        if not player_text or not player_text.strip():
            return None

        # 编码玩家输入
        try:
            query_embedding = self.model.encode(
                [player_text],
                normalize_embeddings=True
            )
        except Exception as e:
            print(f"[CipherMatcher] Encoding error: {e}")
            return None

        # 计算相似度
        similarities = np.dot(query_embedding, self.cipher_embeddings.T)[0]

        # 按允许类别过滤
        candidate_indices = []
        for i, cipher in enumerate(self.cipher_labels):
            if allowed_categories is None:
                candidate_indices.append(i)
            else:
                cat = CIPHER_CATEGORY_MAP.get(cipher, "")
                if cat in allowed_categories:
                    candidate_indices.append(i)

        if not candidate_indices:
            return None

        # 找最高分
        best_idx = max(candidate_indices, key=lambda i: similarities[i])
        best_score = float(similarities[best_idx])

        if best_score < self.similarity_threshold:
            return None

        matched_cipher = self.cipher_labels[best_idx]
        cipher_info = CIPHER_MAP.get(matched_cipher, {})
        if not cipher_info:
            return None

        return {
            "matched_cipher": matched_cipher,
            "similarity": best_score,
            "item": cipher_info.get("item"),
            "action": cipher_info.get("action", "give_item"),
            "quest_id": cipher_info.get("quest_id"),
            "reply_template": cipher_info.get("reply_template", ""),
        }

    def set_threshold(self, threshold: float) -> None:
        """动态调整匹配阈值"""
        self.similarity_threshold = max(0.0, min(1.0, threshold))


def get_cipher_matcher(model_name: str = "BAAI/bge-small-zh-v1.5") -> CipherMatcher:
    """
    获取全局 CipherMatcher 单例

    首次调用时会自动下载/加载模型（约 100MB，仅一次）。
    """
    global _matcher_instance
    if _matcher_instance is None:
        with _init_lock:
            if _matcher_instance is None:
                _matcher_instance = CipherMatcher(model_name=model_name)
                _matcher_instance.initialize()
    return _matcher_instance


# ── 便捷函数：按 NPC profile 直接匹配 ──

def match_cipher_for_npc(
    player_text: str,
    allowed_categories: List[str],
    threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> Optional[Dict[str, Any]]:
    """
    便捷函数：为指定 NPC 做暗号匹配

    Args:
        player_text: 玩家输入
        allowed_categories: NPC 的 allowed_categories（如 ["植物"]）
        threshold: 匹配阈值

    Returns:
        match result dict 或 None
    """
    matcher = get_cipher_matcher()
    matcher.set_threshold(threshold)
    return matcher.match(player_text, allowed_categories)
