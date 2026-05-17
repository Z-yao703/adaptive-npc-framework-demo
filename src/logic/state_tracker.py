"""
状态追踪器
追踪 NPC 和玩家的历史状态
"""
from typing import Dict, Any, List, Optional
from collections import deque
import time


class StateTracker:
    """
    状态追踪器
    
    功能：
    - 记录历史状态
    - 检测状态变化
    - 提供状态变化事件
    """
    
    def __init__(self, history_size: int = 50):
        self.history: deque = deque(maxlen=history_size)
        self.last_state: Optional[Dict[str, Any]] = None
        self.changes: Dict[str, Any] = {}
    
    def update(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """更新状态，返回变化"""
        self.changes = self._compute_changes(state)
        
        # 添加时间戳
        state_with_time = {
            **state,
            "_timestamp": int(time.time())
        }
        
        self.history.append(state_with_time)
        self.last_state = state
        
        return self.changes
    
    def _compute_changes(self, new_state: Dict[str, Any]) -> Dict[str, Any]:
        """计算状态变化"""
        if not self.last_state:
            return {"full_update": True, "state": new_state}
        
        changes = {}
        for key, value in new_state.items():
            if key not in self.last_state or self.last_state[key] != value:
                changes[key] = {
                    "old": self.last_state.get(key),
                    "new": value
                }
        
        # 检测删除的键
        for key in self.last_state:
            if key not in new_state:
                changes[key] = {
                    "old": self.last_state[key],
                    "new": None
                }
        
        return changes if changes else {"unchanged": True}
    
    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取历史状态"""
        return list(self.history)[-limit:]
    
    def get_change_summary(self) -> str:
        """获取变化摘要"""
        if not self.changes:
            return "状态无变化"
        
        parts = []
        for key, change in self.changes.items():
            if key.startswith("_"):
                continue
            old_val = change.get("old", "N/A")
            new_val = change.get("new", "N/A")
            parts.append(f"{key}: {old_val} → {new_val}")
        
        return "; ".join(parts) if parts else "无明显变化"
    
    def detect_event(self, event_type: str, state: Dict[str, Any]) -> bool:
        """检测特定事件"""
        if event_type == "player_approached":
            dist = state.get("distance_to_player", 999)
            return dist < 5 and (not self.last_state or 
                self.last_state.get("distance_to_player", 999) >= 5)
        
        if event_type == "player_entered":
            return "_was_empty" not in self.last_state if self.last_state else True
        
        return False
