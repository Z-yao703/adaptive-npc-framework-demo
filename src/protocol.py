"""
通信协议定义模块

此文件由 generate_protocols.py 自动生成
源文件: protocol.yaml
生成时间: 2026-05-01 15:50:22
版本: 2.0.0

本模块定义标准的 Action 协议，供前后端通信使用。

核心原则：
- 后端只做"决策"，返回标准 Action
- 前端只做"执行"，解析标准 Action
- 协议是唯一的契约，任何游戏都可接入

标准输出格式：
{
    "type": "ACTIONS",
    "actions": [
        {"type": "NPC_SAY", "params": {"npc_id": "...", "text": "..."}},
        {"type": "MOVE_TO", "params": {"npc_id": "...", "x": 100, "y": 200}}
    ]
}

标准输入格式：
{
    "type": "STATE_UPDATE",
    "state": {
        "player_position": {"x": 100, "y": 200},
        "player_inventory": ["apple", "apple"],
        "distance_to_npc": 50
    }
}
"""

from typing import Dict, Any, List, Optional


# ========================================
# 标准 Action 类型枚举
# ========================================
class ActionType:
    """标准 Action 类型常量"""
    # 对话类
    NPC_SAY = "NPC_SAY"  # NPC说话/显示对话气泡
    NPC_EMOTE = "NPC_EMOTE"  # NPC表情动作
    # 移动类
    MOVE_TO = "MOVE_TO"  # NPC移动到目标位置
    NPC_STOP = "NPC_STOP"  # NPC停止移动
    FOLLOW = "FOLLOW"  # NPC跟随目标
    # 交互类
    START_TRADE = "START_TRADE"  # 打开交易界面
    GIVE_ITEM = "GIVE_ITEM"  # NPC给予物品
    TAKE_ITEM = "TAKE_ITEM"  # NPC拿走物品
    # 任务类
    START_QUEST = "START_QUEST"  # 开始新任务
    UPDATE_QUEST = "UPDATE_QUEST"  # 更新任务进度
    COMPLETE_QUEST = "COMPLETE_QUEST"  # 完成任务
    GIVE_GOLD = "GIVE_GOLD"  # 给予金币
    # 系统类
    ERROR = "ERROR"  # 错误信息
    CONFIG_UPDATE = "CONFIG_UPDATE"  # 配置热更新

# ========================================
# Action 工厂函数
# ========================================

def action(type_: str, **params) -> Dict[str, Any]:
    """
    创建单个 Action
    
    Args:
        type_: Action 类型（如 NPC_SAY, MOVE_TO）
        **params: Action 参数
    
    Returns:
        标准 Action 字典
    """
    return {
        "type": type_,
        "params": params
    }


def pack_actions(actions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    打包多个 Action 为标准输出格式
    
    Args:
        actions: Action 列表
    
    Returns:
        标准 ACTIONS 消息
    """
    return {
        "type": "ACTIONS",
        "actions": actions
    }

# ========================================
# 标准 Action 构造函数（便捷封装）
# ========================================

def npc_say(npc_id: str, text: str, emotion: str = "neutral") -> Dict[str, Any]:
    """
    NPC说话/显示对话气泡
    
    Args:
            npc_id: NPC的唯一标识符
            text: NPC要说的文本内容
            emotion: NPC说话时的情绪（默认: neutral）
    
    Returns:
        NPC_SAY Action
    """
    return action(ActionType.NPC_SAY, npc_id=npc_id, text=text, emotion=emotion)


def npc_emote(npc_id: str, emotion: str, duration: float = 2000) -> Dict[str, Any]:
    """
    NPC表情动作
    
    Args:
            npc_id: NPC的唯一标识符
            emotion: 表情类型
            duration: 动作持续时间（毫秒）（默认: 2000）
    
    Returns:
        NPC_EMOTE Action
    """
    return action(ActionType.NPC_EMOTE, npc_id=npc_id, emotion=emotion, duration=duration)


def move_to(npc_id: str, x: float, y: float, speed: float = 3.0) -> Dict[str, Any]:
    """
    NPC移动到目标位置
    
    Args:
            npc_id: NPC的唯一标识符
            x: 目标位置的X坐标
            y: 目标位置的Y坐标
            speed: 移动速度（像素/帧）（默认: 3.0）
    
    Returns:
        MOVE_TO Action
    """
    return action(ActionType.MOVE_TO, npc_id=npc_id, x=x, y=y, speed=speed)


def npc_stop() -> Dict[str, Any]:
    """
    NPC停止移动
    
    Args:
    
    Returns:
        NPC_STOP Action
    """
    return action(ActionType.NPC_STOP)


def follow(npc_id: str, target_id: str, distance: float = 50.0) -> Dict[str, Any]:
    """
    NPC跟随目标
    
    Args:
            npc_id: NPC的唯一标识符
            target_id: 要跟随的目标标识（玩家或其他NPC）
            distance: 跟随距离（像素）（默认: 50.0）
    
    Returns:
        FOLLOW Action
    """
    return action(ActionType.FOLLOW, npc_id=npc_id, target_id=target_id, distance=distance)


def start_trade(npc_id: str, items: List = []) -> Dict[str, Any]:
    """
    打开交易界面
    
    Args:
        npc_id: NPC的唯一标识符
        items: 交易物品列表（默认: []）
    
    Returns:
        START_TRADE Action
    """
    return action(ActionType.START_TRADE, npc_id=npc_id, items=items)


def give_item(npc_id: str, item: str, quantity: int = 1) -> Dict[str, Any]:
    """
    NPC给予物品
    
    Args:
        npc_id: NPC的唯一标识符
        item: 物品ID
        quantity: 物品数量（默认: 1）
    
    Returns:
        GIVE_ITEM Action
    """
    return action(ActionType.GIVE_ITEM, npc_id=npc_id, item=item, quantity=quantity)


def take_item(npc_id: str, item: str, quantity: int = 1) -> Dict[str, Any]:
    """
    NPC拿走物品
    
    Args:
        npc_id: NPC的唯一标识符
        item: 物品ID
        quantity: 物品数量（默认: 1）
    
    Returns:
        TAKE_ITEM Action
    """
    return action(ActionType.TAKE_ITEM, npc_id=npc_id, item=item, quantity=quantity)


def start_quest(npc_id: str, quest_id: str, title: str, description: str, progress: float = 0.0, rewards: List = []) -> Dict[str, Any]:
    """
    开始新任务
    
    Args:
            npc_id: NPC的唯一标识符
            quest_id: 任务的唯一标识符
            title: 任务标题
            description: 任务描述
            progress: 任务进度（0-1的小数）（默认: 0.0）
            rewards: 任务奖励列表（默认: []）
    
    Returns:
        START_QUEST Action
    """
    return action(ActionType.START_QUEST, npc_id=npc_id, quest_id=quest_id, title=title, description=description, progress=progress, rewards=rewards)


def update_quest(npc_id: str, quest_id: str, stage: int = 1, title: str = "", description: str = "", progress: float = 0.0, rewards: List = []) -> Dict[str, Any]:
    """
    更新任务进度
    
    Args:
            npc_id: NPC的唯一标识符
            quest_id: 任务的唯一标识符
            stage: 当前阶段编号
            title: 任务标题
            description: 任务描述
            progress: 任务进度（0-1的小数）（默认: 0.0）
            rewards: 任务奖励列表（默认: []）
    
    Returns:
        UPDATE_QUEST Action
    """
    return action(ActionType.UPDATE_QUEST, npc_id=npc_id, quest_id=quest_id, stage=stage, title=title, description=description, progress=progress, rewards=rewards)


def complete_quest(npc_id: str, quest_id: str, title: str, description: str, progress: float = 0.0, rewards: List = []) -> Dict[str, Any]:
    """
    完成任务
    
    Args:
            npc_id: NPC的唯一标识符
            quest_id: 任务的唯一标识符
            title: 任务标题
            description: 任务描述
            progress: 任务进度（0-1的小数）（默认: 0.0）
            rewards: 任务奖励列表（默认: []）
    
    Returns:
        COMPLETE_QUEST Action
    """
    return action(ActionType.COMPLETE_QUEST, npc_id=npc_id, quest_id=quest_id, title=title, description=description, progress=progress, rewards=rewards)


def give_gold(npc_id: str, amount: int = 0, reason: str = "") -> Dict[str, Any]:
    """
    给予金币
    
    Args:
            npc_id: NPC的唯一标识符
            amount: 金币数量
            reason: 给予原因
    
    Returns:
        GIVE_GOLD Action
    """
    return action(ActionType.GIVE_GOLD, npc_id=npc_id, amount=amount, reason=reason)


def config_update() -> Dict[str, Any]:
    """
    配置热更新
    
    Args:
    
    Returns:
        CONFIG_UPDATE Action
    """
    return action(ActionType.CONFIG_UPDATE)


# ========================================
# 便捷函数：构建完整响应
# ========================================

def error(message: str, npc_id: Optional[str] = None) -> Dict[str, Any]:
    """
    生成 ERROR Action
    
    Args:
        message: 错误信息
        npc_id: NPC 标识（可选）
    
    Returns:
        ERROR Action
    """
    params = {"message": message}
    if npc_id:
        params["npc_id"] = npc_id
    return action(ActionType.ERROR, **params)


def ok(actions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    构建成功响应
    
    Args:
        actions: Action 列表
    
    Returns:
        标准 ACTIONS 消息
    """
    return pack_actions(actions)


def fail(message: str, npc_id: Optional[str] = None) -> Dict[str, Any]:
    """
    构建失败响应
    
    Args:
        message: 错误信息
        npc_id: NPC 标识
    
    Returns:
        包含 ERROR Action 的标准消息
    """
    return pack_actions([error(message, npc_id)])