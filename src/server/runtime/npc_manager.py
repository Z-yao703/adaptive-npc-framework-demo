"""
NPC 管理器 - 后台决策循环
实现事件驱动的消息消费模型
"""
from typing import Dict, Any, List, Tuple
from src.server.framework import AdaptiveNPCFramework
from src.server.runtime.state_store import state_store


class NPCManager:
    """
    NPC 管理器
    
    职责：
    1. 管理活跃的 NPC Agent
    2. 从消息队列消费玩家消息
    3. 调用 framework.run() 处理消息
    """
    
    def __init__(self, framework: AdaptiveNPCFramework):
        self.framework = framework
        self.active_agents = set()

    def register_agent(self, agent_id: str):
        """注册一个活跃的 Agent"""
        self.active_agents.add(agent_id)

    def tick(self) -> List[Tuple[str, Dict[str, Any]]]:
        """
        后台 tick 循环（由 npc_loop 调用）
        
        消费模式：
        1. 从每个 Agent 的消息队列中获取消息
        2. 如果有消息，调用 framework.run() 处理
        3. 检测威胁坏人内容，增加警惕性
        4. 返回结果列表（由 game_adapter 发送）
        """
        results = []

        for agent_id in list(self.active_agents):
            pending_msg = state_store.pop_message(agent_id)
            
            if pending_msg:
                state = state_store.get(agent_id)
                state["player_message"] = pending_msg  # type: ignore
                
                print(f"[NPCManager] 处理消息: agent={agent_id}, msg={pending_msg[:30]}...")
                
                try:
                    result = self.framework.run(agent_id, state)
                    if result:
                        suspicion_value = self._check_threat_to_villain(agent_id, pending_msg)
                        if suspicion_value is not None:
                            if "actions" not in result:
                                result["actions"] = []
                            result["actions"].append({
                                "type": "UPDATE_SUSPICION",
                                "params": {"value": suspicion_value}
                            })
                        results.append((agent_id, result))
                except Exception as e:
                    print(f"[NPCManager] error for {agent_id}: {e}")

        return results

    def _check_threat_to_villain(self, agent_id: str, message: str):
        """检测玩家是否在威胁坏人，若是则增加警惕性"""
        try:
            from games.chaos_hotel.game_session import GameSession
            session = GameSession.get_session_by_npc_id(agent_id)
            if not session or session.game_ended:
                return None

            role = session.npc_role_mapping.get(agent_id, {})
            if role.get("alignment") != "villain":
                return None

            threat_keywords = [
                "凶手", "杀人", "你做的", "我知道是你", "报警", "逃不掉",
                "承认", "坦白", "真相", "你杀", "罪犯", "逮捕", "凶手是你",
                "你干的", "别装了", "露出马脚", "怀疑你", "就是你"
            ]
            if any(kw in message for kw in threat_keywords):
                session.suspicion.add(10)
                current = session.suspicion.get()
                print(f"[NPCManager] 检测到威胁坏人({agent_id})，警惕度+10，当前: {current}")
                if session.suspicion.is_game_over():
                    session.game_ended = True
                    session.victory = False
                    print(f"[NPCManager] 警惕度已满，游戏失败！")
                return current

        except Exception as e:
            print(f"[NPCManager] 威胁检测异常: {e}")

        return None
    
    def get_pending_count(self, agent_id: str) -> int:
        """获取指定 Agent 待处理的消息数量"""
        return state_store.get_queue_size(agent_id)
