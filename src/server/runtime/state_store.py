"""
状态存储模块 - 支持线程安全的消息队列
"""
import queue
import threading
from typing import Dict, Any, Optional


class StateStore:
    """
    全局状态缓存 + 消息队列（线程安全）
    
    设计：
    1. _states: 存储 NPC 的长期状态（位置、环境等）
    2. _message_queues: 每个 Agent 的消息队列，用于事件驱动
    """
    def __init__(self):
        self._states: Dict[str, Dict[str, Any]] = {}
        self._message_queues: Dict[str, queue.Queue] = {}
        self._lock = threading.Lock()

    def update(self, agent_id: str, state: Dict[str, Any]):
        """更新 NPC 的长期状态"""
        with self._lock:
            self._states[agent_id] = state

    def get(self, agent_id: str) -> Dict[str, Dict[str, Any]]:
        """获取 NPC 的长期状态"""
        with self._lock:
            return self._states.get(agent_id, {})

    def get_all(self) -> Dict[str, Dict[str, Any]]:
        """获取所有 NPC 状态"""
        with self._lock:
            return dict(self._states)

    # ============================================================
    # 消息队列操作（实现事件化）
    # ============================================================
    
    def push_message(self, agent_id: str, message: str) -> bool:
        """
        玩家消息入队（事件化）
        
        Args:
            agent_id: NPC ID
            message: 玩家发送的消息内容
            
        Returns:
            True if message was queued, False otherwise
        """
        with self._lock:
            if agent_id not in self._message_queues:
                self._message_queues[agent_id] = queue.Queue()
            self._message_queues[agent_id].put(message)
            return True

    def pop_message(self, agent_id: str) -> Optional[str]:
        """
        NPC 消费消息（消费后即从队列移除）
        
        Args:
            agent_id: NPC ID
            
        Returns:
            消息内容，如果没有消息则返回 None
        """
        with self._lock:
            q = self._message_queues.get(agent_id)
            if q and not q.empty():
                try:
                    return q.get_nowait()  # 非阻塞获取
                except queue.Empty:
                    return None
        return None

    def has_pending_messages(self, agent_id: str) -> bool:
        """检查是否有待处理的消息"""
        with self._lock:
            q = self._message_queues.get(agent_id)
            return q is not None and not q.empty()

    def get_queue_size(self, agent_id: str) -> int:
        """获取队列中的消息数量"""
        with self._lock:
            q = self._message_queues.get(agent_id)
            if q:
                return q.qsize()
        return 0


# 全局单例
state_store = StateStore()
