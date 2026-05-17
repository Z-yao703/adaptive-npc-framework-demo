"""
意图类型定义
"""
from enum import Enum


class PlayerIntent(Enum):
    """玩家对话意图类型"""
    CASUAL_CHAT = "casual_chat"           # 日常交流
    GAME_INFO_REQUEST = "game_info"       # 游戏信息获取
    QUEST_RELATED = "quest_related"       # 任务逻辑相关
    CIPHER_DETECTED = "cipher_detected"   # 暗号匹配命中（Embedding 向量匹配）
    TRADE_RELATED = "trade_related"       # 交易/售卖相关
    UNKNOWN = "unknown"                   # 未知/其他
