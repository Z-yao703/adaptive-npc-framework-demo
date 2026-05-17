"""
WebSocket transport for game clients.
全双工事件驱动架构：
- 上行：ws_handler 接收消息 -> 推入队列 -> 立即返回
- 下行：game_adapter 从队列消费结果 -> 主动推送给客户端
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Optional
import asyncio

from fastapi import WebSocket

from src.server.runtime.state_store import state_store
from src.server.runtime.state_protocol import normalize_game_state
from src.utils.logging import log_info, log_warn

if TYPE_CHECKING:
    from src.server.framework import AdaptiveNPCFramework


# ============================================================
# 全局连接管理器 - agent_id 到 WebSocket 对象的映射
# ============================================================
connections: Dict[str, WebSocket] = {}
_npc_manager = None
_default_agent_id: Optional[str] = None


def set_npc_manager(manager) -> None:
    global _npc_manager
    _npc_manager = manager


def set_default_agent(agent_id: str) -> None:
    global _default_agent_id
    _default_agent_id = agent_id


def get_default_agent() -> str:
    return _default_agent_id or "default_npc"


async def handle_ws(
    ws: WebSocket,
    agent_id: Optional[str],
    framework: "AdaptiveNPCFramework",
) -> None:
    """
    WebSocket 连接处理（全双工模式）
    
    职责：
    1. 管理连接生命周期
    2. 接收玩家消息 -> 推入队列（不处理）
    3. 不原地等待 AI 结果（由 game_adapter 推送）
    """
    if agent_id is None:
        agent_id = get_default_agent()
        log_info("未指定 agent_id，自动使用 {}", agent_id)

    await ws.accept()
    connections[agent_id] = ws
    log_info("WebSocket 连接已建立: agent_id={}", agent_id)

    # ============================================================
    # 【防御性】只在事件循环未设置时才设置
    # ============================================================
    try:
        from src.server.runtime.game_adapter import game_adapter
        if game_adapter._main_loop is None:
            loop = asyncio.get_running_loop()
            game_adapter.set_event_loop(loop)
            print(f"[WS] 已设置事件循环: {id(loop)}")
        else:
            print(f"[WS] 事件循环已存在，跳过设置")
    except Exception as e:
        print(f"[WS] 设置事件循环失败: {e}")

    # 初始化 NPC（如果尚未初始化）
    if agent_id not in framework.agents:
        config = framework.config_loader.load(agent_id)
        if config:
            framework.init_agent(agent_id, config)
            log_info("已加载配置: {}", agent_id)
        else:
            framework.init_agent(
                agent_id,
                {
                    "id": agent_id,
                    "name": "NPC",
                    "personality": "一个普通的 NPC",
                    "sensors": [],
                    "actions": [
                        {
                            "name": "dialogue",
                            "parameters": {"message": "", "emotion": "neutral"},
                        }
                    ],
                },
            )
            log_warn("未找到配置，已创建临时默认配置: {}", agent_id)

    await ws.send_json(
        {
            "type": "INIT_ACK",
            "agent_id": agent_id,
            "status": "connected",
        }
    )

    try:
        while True:
            data = await ws.receive_json()
            msg_type = data.get("type")

            if msg_type == "STATE_UPDATE":
                raw_state = data.get("state", {})
                player_msg = raw_state.get("player_message", "")
                
                # ============================================================
                # 【关键修改】只负责更新状态和推送消息入队
                # 不再调用 framework.run()，由 npc_loop 后台处理
                # ============================================================
                
                # 1. 更新基础状态（位置、环境等）
                state_store.update(
                    agent_id,
                    normalize_game_state(raw_state, agent_id),
                )
                
                # 2. 注册到 npc_manager（确保 npc_loop 能处理）
                if _npc_manager:
                    _npc_manager.register_agent(agent_id)
                
                # 3. 如果有对话消息，推入事件队列
                if player_msg and player_msg.strip():
                    print(f"[WS] 收到 STATE_UPDATE, player_message={player_msg[:50]}...")
                    state_store.push_message(agent_id, player_msg)
                    print(f"[WS] 消息已入队，交给后台线程处理: {player_msg[:30]}...")
                            
            elif msg_type == "PING":
                await ws.send_json({"type": "PONG"})
                
    except Exception as exc:
        print(f"WebSocket error for {agent_id}: {exc}")
    finally:
        connections.pop(agent_id, None)
        log_info("WebSocket 连接已断开: {}", agent_id)
        if _npc_manager:
            _npc_manager.active_agents.discard(agent_id)  # 清理活跃集合


async def push_update(agent_id: str, payload: dict) -> bool:
    """通过全局连接推送消息给客户端"""
    if agent_id in connections:
        await connections[agent_id].send_json(payload)
        log_info("已推送更新到 {}: {}", agent_id, payload.get("type"))
        return True

    log_warn("{} 未连接，无法推送", agent_id)
    return False


async def broadcast(payload: dict) -> None:
    """广播消息给所有连接"""
    for ws in connections.values():
        try:
            await ws.send_json(payload)
        except Exception:
            pass

    log_info("广播消息: {}", payload.get("type"))
