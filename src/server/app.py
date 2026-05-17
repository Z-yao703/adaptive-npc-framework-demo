"""
Adaptive NPC Framework - FastAPI 应用
包含所有 Web 服务路由和 WebSocket 处理
"""
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import json
import os
import sys
from pathlib import Path
from typing import Dict

# 获取项目根目录（相对于 app.py 的位置）
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# 添加 games/ 到 Python path，使游戏模块可导入
GAMES_DIR = str(PROJECT_ROOT / "games")
if GAMES_DIR not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 导入核心模块
from src.server.framework import AdaptiveNPCFramework
from src.communication.ws_handler import handle_ws, push_update, connections, get_default_agent
from src.memory.database_io import DatabaseIO
from src.server.runtime.config_schema import normalize_agent_config
from src.server.runtime.state_protocol import normalize_game_state

# 导入游戏路由
from games.chaos_hotel.routes import router as game_router
from games.chaos_hotel.routes import player_router

# 全局框架实例
framework = AdaptiveNPCFramework()
db = DatabaseIO()


def create_app() -> FastAPI:
    """
    创建 FastAPI 应用
    
    设计原则：
    - 所有 Web 服务逻辑集中在此
    - 不涉及核心框架逻辑
    """
    app = FastAPI(
        title="Adaptive NPC Framework API",
        description="智能NPC框架后端服务",
        version="1.0.0",
        docs_url=None,
        openapi_url=None
    )
    
    # ==================== 中间件 ====================
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 生产环境应限制
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 托管最小接入样例
    if (PROJECT_ROOT / "mygame").is_dir():
        app.mount("/mygame", StaticFiles(directory=str(PROJECT_ROOT / "mygame"), html=True), name="mygame")

    # 托管 AgentBridge SDK
    @app.get("/bridge/agent_bridge.js")
    async def get_bridge():
        """
        智能 NPC 框架 SDK 导出接口
        确保游戏端可以通过固定 URL 访问到最新的 SDK
        """
        bridge_path = PROJECT_ROOT / "bridge" / "agent_bridge.js"
        return FileResponse(str(bridge_path), media_type="application/javascript")

    # 托管 NPC 渲染模块
    @app.get("/bridge/npc-render.js")
    async def get_npc_render():
        """
        NPC 渲染模块导出接口
        提供独立的 NPC 渲染功能，简化游戏接入
        """
        render_path = PROJECT_ROOT / "bridge" / "npc-render.js"
        if render_path.exists():
            return FileResponse(str(render_path), media_type="application/javascript")
        return {"error": "npc-render.js not found"}, 404

    # ==================== WebSocket 端点 ====================

    @app.websocket("/ws")
    async def websocket_endpoint_default(ws: WebSocket):
        """
        游戏客户端 WebSocket 连接（无 agent_id，自动使用默认 NPC）

        协议：
        - INIT: 客户端初始化确认
        - STATE_UPDATE: 游戏状态更新，返回 NPC 决策
        - PING: 心跳检测
        """
        await handle_ws(ws, None, framework)

    @app.websocket("/ws/{agent_id}")
    async def websocket_endpoint(ws: WebSocket, agent_id: str):
        """
        游戏客户端 WebSocket 连接（指定 agent_id）

        协议：
        - INIT: 客户端初始化确认
        - STATE_UPDATE: 游戏状态更新，返回 NPC 决策
        - PING: 心跳检测
        """
        await handle_ws(ws, agent_id, framework)
    
    # ==================== Agent 管理 API ====================
    
    @app.get("/api/agent/list")
    async def list_agents() -> Dict:
        """获取所有 NPC 列表"""
        agents = []
        for item in db.list_agents():
            config = db.load_agent(item["id"]) or {}
            normalized = normalize_agent_config(config)
            agents.append({
                "id": item["id"],
                "name": normalized.get("meta", {}).get("name", item["id"]),
                "updated_at": item["updated_at"],
            })
        return {"agents": agents}
    
    @app.get("/api/agent/{agent_id}")
    async def get_agent(agent_id: str):
        """获取单个 NPC 配置"""
        config = db.load_agent(agent_id)
        if config:
            return normalize_agent_config(config)
        return {"error": "Agent not found"}, 404
    
    @app.post("/api/agent/save")
    async def save_agent(config: dict):
        """
        保存 NPC 配置到数据库
        
        同时推送到运行中的 NPC 实现热更新
        """
        normalized_config = normalize_agent_config(config)
        agent_id = normalized_config.get("id")
        if not agent_id:
            return {"error": "Agent ID is required"}, 400
        
        # 保存到数据库
        db.save_agent(agent_id, normalized_config)

        # 如果 NPC 已经在运行，直接刷新后端内存中的配置
        if framework.has_agent(agent_id):
            framework.update_agent_config(agent_id, normalized_config)
        
        # 同时保存 JSON 备份
        os.makedirs("configs", exist_ok=True)
        with open(f"configs/{agent_id}.json", "w", encoding="utf-8") as f:
            json.dump(normalized_config, f, ensure_ascii=False, indent=2)
        
        # 推送到运行中的 NPC（热更新）
        if agent_id in connections:
            await push_update(agent_id, {
                "type": "CONFIG_UPDATE",
                "config": normalized_config
            })
        
        return {"status": "ok", "agent_id": agent_id}
    
    @app.delete("/api/agent/{agent_id}")
    async def delete_agent(agent_id: str):
        """删除 NPC"""
        db.delete_agent(agent_id)
        
        # 删除 JSON 备份
        json_path = f"configs/{agent_id}.json"
        if os.path.exists(json_path):
            os.remove(json_path)
        
        return {"status": "ok"}
    
    @app.post("/api/agent/{agent_id}/init")
    async def init_agent(agent_id: str):
        """
        初始化 NPC（运行时加载配置）
        
        用于游戏开始时动态加载 NPC
        """
        config = db.load_agent(agent_id)
        if not config:
            return {"error": "Agent not found"}, 404
        
        framework.init_agent(agent_id, normalize_agent_config(config))
        return {"status": "initialized", "agent_id": agent_id}
    
    @app.post("/api/agent/{agent_id}/process")
    async def process_state(agent_id: str, state: dict):
        """
        处理游戏状态，返回 NPC 决策
        
        用于无需 WebSocket 的同步调用场景
        """
        action = framework.run(agent_id, normalize_game_state(state, agent_id))
        return {"action": action}
    
    # ==================== 世界背景管理 API ====================

    @app.get("/api/world/list")
    async def list_worlds() -> Dict:
        """
        获取所有世界背景列表
        扫描 configs/ 目录下的 world_*.json 文件
        """
        worlds = []
        configs_dir = PROJECT_ROOT / "configs"
        
        if configs_dir.exists():
            for json_file in configs_dir.glob("world_*.json"):
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        config = json.load(f)
                        worlds.append({
                            "id": config.get("id", json_file.stem),
                            "name": config.get("name", json_file.stem),
                            "updated_at": os.path.getmtime(json_file)
                        })
                except Exception as e:
                    print(f"Error loading {json_file}: {e}")
        
        return {"worlds": worlds}

    @app.get("/api/world/{world_id}")
    async def get_world(world_id: str):
        """
        获取单个世界背景配置
        从 configs/world_{world_id}.json 读取
        """
        config_path = PROJECT_ROOT / "configs" / f"{world_id}.json"
        
        if not config_path.exists():
            return {"error": "World not found"}, 404
        
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                return config
        except Exception as e:
            return {"error": str(e)}, 500

    @app.post("/api/world/save")
    async def save_world(config: dict):
        """
        保存世界背景配置到JSON文件
        保存到 configs/world_{id}.json
        """
        world_id = config.get("id")
        if not world_id:
            return {"error": "World ID is required"}, 400
        
        configs_dir = PROJECT_ROOT / "configs"
        configs_dir.mkdir(exist_ok=True)
        
        config_path = configs_dir / f"{world_id}.json"
        
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            return {"status": "ok", "world_id": world_id}
        except Exception as e:
            return {"error": str(e)}, 500

    @app.delete("/api/world/{world_id}")
    async def delete_world(world_id: str):
        """
        删除世界背景JSON文件
        """
        config_path = PROJECT_ROOT / "configs" / f"{world_id}.json"
        
        if not config_path.exists():
            return {"error": "World not found"}, 404
        
        try:
            os.remove(config_path)
            return {"status": "ok"}
        except Exception as e:
            return {"error": str(e)}, 500
    
    # ==================== 短期记忆 API ====================
    
    @app.get("/api/short_term_memory/{npc_id}")
    async def get_short_term_memory(npc_id: str, limit: int = 3, player_id: str = None):  # type: ignore
        """
        获取 NPC 的短期对话记忆
        
        用于前端对话历史展示
        
        Args:
            npc_id: NPC 标识符
            limit: 返回轮数（默认3轮）
            player_id: 玩家标识符（可选，为空则返回所有玩家的对话）
        
        Returns:
            {"npc_id": str, "history": [...], "display_messages": [...]}
        """
        from src.memory.short_term_db import get_short_term_db
        
        db = get_short_term_db()
        
        # 获取对话历史
        history = db.get_recent_chats(npc_id, player_id, limit)
        
        # 获取用于前端显示的消息列表
        display_messages = db.get_history_for_display(npc_id, player_id, limit)
        
        # 获取统计信息
        stats = db.get_statistics(npc_id)
        
        return {
            "npc_id": npc_id,
            "history": history,
            "display_messages": display_messages,
            "stats": stats
        }
    
    @app.delete("/api/short_term_memory/{npc_id}")
    async def clear_short_term_memory(npc_id: str, player_id: str = None): # type: ignore
        """
        清除 NPC 的短期记忆
        
        Args:
            npc_id: NPC 标识符
            player_id: 玩家标识符（可选，为空则清除所有玩家的对话）
        """
        from src.memory.short_term_db import get_short_term_db
        
        db = get_short_term_db()
        db.clear_npc_memory(npc_id, player_id)
        
        return {"status": "ok", "message": f"已清除 {npc_id} 的对话记忆"}
    
    # ==================== 使用说明文档 ====================
    
    @app.get("/docs")
    async def usage_manual():
        """
        软件使用说明书
        
        返回 USAGE_MANUAL.md 的内容，替代默认的 Swagger API 文档
        """
        manual_path = PROJECT_ROOT / "USAGE_MANUAL.md"
        if not manual_path.exists():
            from fastapi.responses import HTMLResponse
            return HTMLResponse("<h1>使用说明书未找到</h1><p>请确保 USAGE_MANUAL.md 文件存在于项目根目录。</p>", status_code=404)
        
        content = manual_path.read_text(encoding="utf-8")
        
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Adaptive NPC Framework - 使用说明书</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif;
            max-width: 960px;
            margin: 0 auto;
            padding: 40px 20px;
            line-height: 1.8;
            color: #24292e;
            background: #fff;
        }}
        pre {{
            background: #f6f8fa;
            border: 1px solid #e1e4e8;
            border-radius: 6px;
            padding: 16px;
            overflow-x: auto;
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 13px;
            line-height: 1.5;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        code {{
            background: #f6f8fa;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 13px;
        }}
        pre code {{
            background: none;
            padding: 0;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 16px 0;
        }}
        th, td {{
            border: 1px solid #e1e4e8;
            padding: 8px 12px;
            text-align: left;
        }}
        th {{
            background: #f6f8fa;
            font-weight: 600;
        }}
        h1, h2, h3, h4 {{
            color: #1a1a1a;
            margin-top: 24px;
            margin-bottom: 12px;
        }}
        h1 {{ font-size: 2em; border-bottom: 1px solid #e1e4e8; padding-bottom: 8px; }}
        h2 {{ font-size: 1.5em; border-bottom: 1px solid #e1e4e8; padding-bottom: 6px; }}
        p {{ margin: 8px 0; }}
        strong {{ color: #1a1a1a; }}
    </style>
</head>
<body>
<pre>{content}</pre>
</body>
</html>"""
        from fastapi.responses import HTMLResponse
        return HTMLResponse(html)
    
    # ==================== 健康检查 ====================
    
    @app.get("/api/health")
    async def health_check() -> Dict:
        """健康检查"""
        return {
            "status": "healthy",
            "connections": len(connections),
            "agents": len(framework.agents)
        }
    
    # ==================== 注册游戏路由 ====================
    app.include_router(game_router)
    app.include_router(player_router)
    
    # 将 framework 存入 app.state，供游戏路由访问
    app.state.framework = framework
    
    return app


# 兼容旧版：如果直接运行此文件
if __name__ == "__main__":
    import uvicorn
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8000)
