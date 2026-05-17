#!/usr/bin/env python3
"""
Adaptive NPC Framework - Main Entry Point
智能NPC框架 - 主入口

全双工事件驱动架构：
- ws_handler: 接收消息 -> 推入队列 -> 立即返回
- npc_loop: 消费队列 -> framework.run() -> game_adapter 推送结果
"""
from dotenv import load_dotenv
load_dotenv()

import os
import threading
import time
import uvicorn
from src.server.app import create_app, framework
from src.memory.database_io import DatabaseIO
from src.server.runtime.npc_manager import NPCManager
from src.server.runtime.game_adapter import game_adapter
from src.communication.ws_handler import set_npc_manager, set_default_agent
from src.server.runtime.registry_loader import RegistryLoader
from src.utils.logging import log_info, log_warn


# ==================== 配置区域 ====================
DEFAULT_NPC_CONFIG_PATH = "configs/default_npc.json"


def load_default_configs(db: DatabaseIO):
    """从 configs/ 目录加载默认 NPC 配置"""
    if not os.path.exists(DEFAULT_NPC_CONFIG_PATH):
        log_warn("未找到默认配置: {}", DEFAULT_NPC_CONFIG_PATH)
        return

    existing = db.load_agent("default_npc")
    if existing:
        log_info("默认 NPC 已存在: {}", existing.get("name", "default_npc"))
        return

    import json
    with open(DEFAULT_NPC_CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    db.save_agent("default_npc", config)
    log_info("默认 NPC 已加载: {}", config.get("name", "default_npc"))


def load_registry_npcs(registry: RegistryLoader, db: DatabaseIO):
    """从注册表加载所有 NPC 并初始化"""
    agent_ids = registry.get_all_agents()
    if not agent_ids:
        log_warn("Registry 中没有注册的 NPC")
        return

    log_info("开始加载 {} 个 NPC...", len(agent_ids))

    for agent_id in agent_ids:
        config = registry.load_config(agent_id)
        if not config:
            config = db.load_agent(agent_id)

        if config:
            framework.init_agent(agent_id, config)
            log_info("{}: {}", agent_id, config.get("name", agent_id))
        else:
            log_warn("{}: 配置未找到，跳过", agent_id)

    default_agent = registry.get_default_agent()
    set_default_agent(default_agent)
    log_info("默认 NPC: {}", default_agent)


# ==================== 启动服务 ====================

if __name__ == "__main__":
    # 初始化数据库
    db = DatabaseIO()
    load_default_configs(db)

    # 创建 RegistryLoader 并加载所有 NPC
    registry = RegistryLoader()
    load_registry_npcs(registry, db)

    # 创建 FastAPI 应用
    app = create_app()

    # 创建 NPCManager
    npc_manager = NPCManager(framework)
    set_npc_manager(npc_manager)

    # ============================================================
    # npc_loop - 运行在独立线程中
    # 【架构】使用 queue.Queue 作为事件总线，实现全双工解耦
    # 注意：事件循环由 ws_handler 在连接时设置
    # ============================================================
    def npc_loop():
        """
        后台决策循环（独立线程）
        
        职责：
        1. 从消息队列消费玩家消息
        2. 调用 framework.run() 处理
        3. 通过 game_adapter 推送结果
        """
        print("[npc_loop] 启动，等待 WebSocket 连接设置事件循环...")
        
        while True:
            try:
                results = npc_manager.tick()
                if results:
                    game_adapter.apply_actions(results)
            except Exception as e:
                print(f"[npc_loop] 异常: {e}")
            
            # 降低 CPU 占用，无消息时休眠
            time.sleep(0.1)

    threading.Thread(target=npc_loop, daemon=True, name="npc_loop").start()
    
    print("=" * 50)
    log_info("Adaptive NPC Framework 启动中...")
    print("=" * 50)
    log_info("架构: 全双工事件驱动")
    log_info("使用说明书: http://localhost:8000/docs")
    log_info("最小接入样例: http://localhost:8000/mygame")
    print("=" * 50)
    
    # 启动服务
    uvicorn.run(app, host="0.0.0.0", port=8000)
