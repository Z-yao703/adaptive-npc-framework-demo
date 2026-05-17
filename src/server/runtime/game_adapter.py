"""
游戏适配器 - 跨线程 WebSocket 消息推送
"""
from typing import List, Tuple, Dict, Any
import asyncio
import threading


class GameAdapter:
    """
    游戏动作适配器
    
    职责：
    1. 接收 framework.run() 的结果
    2. 通过 WebSocket 推送给客户端
    
    跨线程处理：
    - npc_loop 运行在独立线程
    - WebSocket 需要在 asyncio 事件循环中发送
    - 使用 asyncio.run_coroutine_threadsafe() 实现跨线程调用
    """

    def __init__(self):
        self._main_loop: asyncio.AbstractEventLoop = None # type: ignore
        self._loop_lock = threading.Lock()

    def set_event_loop(self, loop: asyncio.AbstractEventLoop):
        """设置主事件循环"""
        with self._loop_lock:
            self._main_loop = loop
            print(f"[GameAdapter] 成功绑定事件循环: {id(loop)}")

    def apply_actions(self, results: List[Tuple[str, Dict[str, Any]]]):
        """
        应用动作结果（推送给客户端）
        
        Args:
            results: [(agent_id, action_result), ...]
        """
        if not results:
            return
        
        # 延迟导入避免循环依赖
        from src.communication.ws_handler import connections
        
        for agent_id, result in results:
            ws = connections.get(agent_id)
            if not ws:
                continue

            # ============================================================
            # 【防御性检查】确保事件循环存在且正在运行
            # ============================================================
            with self._loop_lock:
                loop = self._main_loop
            
            if loop and loop.is_running():
                try:
                    # 使用线程安全的方式投递
                    asyncio.run_coroutine_threadsafe(
                        ws.send_json(result), 
                        loop
                    )
                    print(f"[GameAdapter] 已投递消息到 {agent_id}")
                except Exception as e:
                    print(f"[GameAdapter] 跨线程发送失败: {e}")
            else:
                # 如果没有 Loop，记录清晰的日志
                print(f"[GameAdapter] 警告：尝试发送消息给 {agent_id}，但主线程事件循环尚未就绪或已关闭")


# 全局单例
game_adapter = GameAdapter()
