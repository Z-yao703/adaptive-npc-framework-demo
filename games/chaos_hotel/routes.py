"""
混沌旅馆游戏 API 路由
定义 /api/game/start 和 /api/game/answer 接口
"""
from fastapi import APIRouter, Request
from games.chaos_hotel.game_session import GameSession
from src.memory.database_io import DatabaseIO

# 游戏会话存储（内存缓存，key=session_id）
# 同时持久化到 SQLite，由 DatabaseIO 管理
sessions = {}

# 数据库实例（延迟初始化，避免循环导入）
_db = None

def get_db() -> DatabaseIO:
    """延迟获取数据库实例"""
    global _db
    if _db is None:
        _db = DatabaseIO()
    return _db

router = APIRouter(prefix="/api/game", tags=["game"])


@router.post("/start")
async def start_game(request: Request):
    """
    启动新游戏：生成剧本、注入 NPC 秘密

    请求体：{"agent_ids": ["npc_1777163256169", "npc_1777166761367", "npc_1778492083422"], "player_id": "player_001"}
    """
    # 从 app state 获取 framework
    framework = request.app.state.framework

    body = await request.json()
    agent_ids = body.get("agent_ids", [])
    player_id = body.get("player_id", "player_001")

    if len(agent_ids) < 3:
        return {"error": "需要3个NPC ID"}, 400

    # 确保所有 NPC 已初始化
    for nid in agent_ids:
        if not framework.has_agent(nid):
            return {"error": f"NPC {nid} 未初始化，请先调用 /api/agent/{{id}}/init"}, 400

    # 从数据库读取玩家真实金币
    db = get_db()
    player_data = db.get_or_create_player(player_id)
    player_gold = player_data.get("gold", 100)

    # 创建游戏会话
    session = GameSession()
    public_info = session.start_game(agent_ids, framework, player_gold)

    # 内存缓存
    sessions[session.session_id] = session

    # 持久化到数据库
    db.save_game_session(
        session_id=session.session_id,
        title=session.title,
        story=session.story,
        roles=session.roles,
        questions=session.questions,
        progress=session.progress,
        suspicion=session.suspicion.get(),
        game_ended=session.game_ended,
        victory=session.victory,
        retry_count=session.retry_count,
        player_gold=session.player_gold
    )
    print(f"[GameRoute] 会话已持久化到数据库: {session.session_id}")

    print(f"[GameRoute] 新游戏启动: {session.session_id}, 剧本={session.title}, "
          f"story长度={len(session.story)}, roles数={len(session.roles)}, "
          f"questions数={len(session.questions)}")
    print(f"[GameRoute]   story内容: {session.story[:100]}...")
    print(f"[GameRoute]   roles keys: {list(session.roles.keys())}")
    return public_info


@router.post("/answer")
async def submit_answer(request: Request):
    """
    提交答案判定

    请求体：{
        "session_id": "uuid",
        "question_id": 1,
        "selected_option": "A"
    }
    """
    body = await request.json()
    session_id = body.get("session_id")
    question_id = body.get("question_id")
    selected_option = body.get("selected_option")

    if not session_id:
        return {"error": "缺少 session_id"}, 400

    # 先从内存缓存查找
    session = sessions.get(session_id)

    # 内存没有则从数据库加载
    if session is None:
        db = get_db()
        db_session = db.load_game_session(session_id)
        if db_session is None:
            return {"error": "无效的会话ID"}, 400
        # 重建 GameSession 对象
        session = GameSession(session_id=session_id)
        session.title = db_session["title"]
        session.story = db_session["story"]
        session.roles = db_session["roles"]
        session.questions = db_session["questions"]
        session.progress = db_session["progress"]
        session.retry_count = db_session.get("retry_count", {})
        session.player_gold = db_session.get("player_gold", 100)
        session.suspicion.reset()
        session.game_ended = db_session["game_ended"]
        session.victory = db_session["victory"]
        sessions[session_id] = session
        print(f"[GameRoute] 从数据库加载会话: {session_id}")

    result = session.check_answer(question_id, selected_option)

    # 更新数据库
    db = get_db()
    db.update_game_progress(
        session_id=session_id,
        progress=session.progress,
        suspicion=session.suspicion.get(),
        game_ended=session.game_ended,
        victory=session.victory,
        retry_count=session.retry_count,
        player_gold=session.player_gold
    )

    return result


@router.post("/retry")
async def submit_retry(request: Request):
    """
    重新回答题目：扣除20金币，重置题目状态

    请求体：{
        "session_id": "uuid",
        "question_id": 1,
        "player_id": "player_001"
    }
    """
    body = await request.json()
    session_id = body.get("session_id")
    question_id = body.get("question_id")
    player_id = body.get("player_id", "player_001")

    if not session_id:
        return {"error": "缺少 session_id"}, 400

    session = sessions.get(session_id)

    if session is None:
        db = get_db()
        db_session = db.load_game_session(session_id)
        if db_session is None:
            return {"error": "无效的会话ID"}, 400
        session = GameSession(session_id=session_id)
        session.title = db_session["title"]
        session.story = db_session["story"]
        session.roles = db_session["roles"]
        session.questions = db_session["questions"]
        session.progress = db_session["progress"]
        session.retry_count = db_session.get("retry_count", {})
        session.player_gold = db_session.get("player_gold", 100)
        session.suspicion.reset()
        session.game_ended = db_session["game_ended"]
        session.victory = db_session["victory"]
        sessions[session_id] = session

    result = session.retry_question(question_id, player_id)

    db = get_db()
    db.update_game_progress(
        session_id=session_id,
        progress=session.progress,
        suspicion=session.suspicion.get(),
        game_ended=session.game_ended,
        victory=session.victory,
        retry_count=session.retry_count,
        player_gold=session.player_gold
    )

    return result


@router.get("/summary")
async def get_summary(session_id: str):
    """
    获取游戏结局摘要（用于前端显示）
    """
    if not session_id:
        return {"error": "缺少 session_id"}, 400

    # 先从内存查找
    session = sessions.get(session_id)

    if session is None:
        # 从数据库加载
        db = get_db()
        db_session = db.load_game_session(session_id)
        if db_session is None:
            return {"error": "无效的会话ID"}, 400
        return db_session

    return {
        "session_id": session.session_id,
        "title": session.title,
        "story": session.story,
        "roles": session.roles,
        "questions": session.questions,
        "progress": session.progress,
        "suspicion": session.suspicion.get(),
        "game_over": session.game_ended,
        "victory": session.victory
    }


@router.get("/history")
async def get_history():
    """获取最近的游戏历史"""
    db = get_db()
    return db.list_game_sessions(limit=20)


@router.post("/replay")
async def replay_game(request: Request):
    """
    重玩指定剧本（不调用LLM，直接从数据库读取并随机注入）

    请求体：{
        "session_id": "uuid",
        "agent_ids": ["npc_id1", "npc_id2", "npc_id3"],
        "player_id": "player_001"
    }
    """
    framework = request.app.state.framework
    body = await request.json()
    session_id = body.get("session_id")
    agent_ids = body.get("agent_ids", [])
    player_id = body.get("player_id", "player_001")

    if not session_id:
        return {"error": "缺少 session_id"}, 400

    if len(agent_ids) < 3:
        return {"error": "需要3个NPC ID"}, 400

    # 确保所有 NPC 已初始化
    for nid in agent_ids:
        if not framework.has_agent(nid):
            return {"error": f"NPC {nid} 未初始化，请先调用 /api/agent/{{id}}/init"}, 400

    # 从数据库读取玩家真实金币
    db = get_db()
    player_data = db.get_or_create_player(player_id)
    player_gold = player_data.get("gold", 100)

    # 创建会话并执行重玩注入
    session = GameSession()
    result = session.replay_game(agent_ids, framework, session_id, player_gold)

    if "error" in result:
        return result, 400

    # 内存缓存
    sessions[session.session_id] = session

    # 更新数据库（重置进度和怀疑度）
    db.update_game_progress(
        session_id=session_id,
        progress={},
        suspicion=0,
        game_ended=False,
        victory=False
    )

    print(f"[GameRoute] 重玩剧本: {session_id}, 剧本={session.title}")
    return result


@router.delete("/{session_id}")
async def delete_game(session_id: str):
    """删除指定剧本"""
    db = get_db()
    db.delete_game_session(session_id)

    if session_id in sessions:
        del sessions[session_id]

    GameSession.remove_session(session_id)

    return {"status": "success", "message": "剧本已删除"}


# ==================== 玩家 API 路由 ====================

player_router = APIRouter(prefix="/api/player", tags=["player"])


@player_router.get("/{player_id}")
async def get_player(player_id: str):
    """获取玩家信息（金币 + 背包）"""
    db = get_db()
    return db.get_or_create_player(player_id)


@player_router.post("/{player_id}/buy")
async def buy_item(player_id: str, request: Request):
    """
    购买物品

    请求体：{"item_name": "牛油果冷豆腐", "item_type": "food", "price": 15}
    """
    body = await request.json()
    item_name = body.get("item_name")
    item_type = body.get("item_type")
    price = body.get("price")

    if not item_name or not item_type or price is None:
        return {"error": "缺少 item_name/item_type/price"}, 400

    db = get_db()

    result = db.deduct_player_gold(player_id, price)
    if not result["success"]:
        return result

    db.add_player_item(player_id, item_name, item_type)

    return {
        "success": True,
        "gold": result["gold"],
        "item_name": item_name,
        "item_type": item_type
    }


@player_router.post("/{player_id}/add_item")
async def add_player_item_route(player_id: str, request: Request):
    """
    直接添加物品到玩家背包（累加模式，用于暗号/任务奖励增量）

    请求体：{"item_name": "玫瑰", "item_type": "quest", "count": 1}
    """
    body = await request.json()
    item_name = body.get("item_name")
    item_type = body.get("item_type", "quest")
    count = body.get("count", 1)

    if not item_name:
        return {"error": "缺少 item_name"}, 400

    db = get_db()
    db.add_player_item(player_id, item_name, item_type, count)
    return {"success": True, "item_name": item_name, "item_type": item_type, "count": count}


@player_router.put("/{player_id}/set_item")
async def set_player_item_route(player_id: str, request: Request):
    """
    设置玩家背包物品的绝对数量（前端状态同步用）
    当 count 为 0 时删除该物品记录

    请求体：{"item_name": "玫瑰", "item_type": "quest", "count": 3}
    """
    body = await request.json()
    item_name = body.get("item_name")
    item_type = body.get("item_type", "quest")
    count = body.get("count", 0)

    if not item_name:
        return {"error": "缺少 item_name"}, 400

    db = get_db()
    db.set_player_item(player_id, item_name, item_type, count)
    return {"success": True, "item_name": item_name, "item_type": item_type, "count": count}


@player_router.post("/{player_id}/remove_item")
async def remove_player_item_route(player_id: str, request: Request):
    """
    从玩家背包扣除物品

    请求体：{"item_name": "玫瑰", "item_type": "quest", "count": 1}
    """
    body = await request.json()
    item_name = body.get("item_name")
    item_type = body.get("item_type", "quest")
    count = body.get("count", 1)

    if not item_name:
        return {"error": "缺少 item_name"}, 400

    db = get_db()
    ok = db.remove_player_item(player_id, item_name, item_type, count)
    return {"success": ok, "item_name": item_name, "item_type": item_type, "count": count}


@player_router.put("/{player_id}/gold")
async def update_gold(player_id: str, request: Request):
    """
    更新玩家金币

    请求体：{"gold": 80}
    """
    body = await request.json()
    gold = body.get("gold")

    if gold is None:
        return {"error": "缺少 gold"}, 400

    db = get_db()
    db.update_player_gold(player_id, gold)
    return {"success": True, "gold": gold}


@player_router.post("/{player_id}/sell")
async def sell_item(player_id: str, request: Request):
    """
    售卖物品给 NPC（玩家出售，NPC 购买）

    请求体：{"item_name": "牛乳可可饮", "item_type": "food", "price": 15, "tip": 5}
    """
    body = await request.json()
    item_name = body.get("item_name")
    item_type = body.get("item_type")
    price = body.get("price")
    tip = body.get("tip", 0)

    if not item_name or not item_type or price is None:
        return {"error": "缺少 item_name/item_type/price"}, 400

    db = get_db()

    # 1. 从背包移除物品
    ok = db.remove_player_item(player_id, item_name, item_type)
    if not ok:
        return {"error": f"你没有 {item_name} 可以出售"}, 400

    # 2. 增加金币（售价 + 附加费）
    total_price = price + tip
    current_gold = db.get_player_gold(player_id)
    new_gold = current_gold + total_price
    db.update_player_gold(player_id, new_gold)

    return {
        "success": True,
        "gold": new_gold,
        "item_name": item_name,
        "item_type": item_type,
        "price": price,
        "tip": tip,
        "total": total_price
    }
