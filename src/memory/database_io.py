"""
数据库 IO 封装
提供简洁的数据库操作接口
"""
import json
import os
import sqlite3
from typing import Dict, Any, List, Optional


class DatabaseIO:
    """SQLite 数据库操作封装"""
    
    def __init__(self, db_path: str = "database/agents.db"):
        self.db_path = db_path
        self._init_db()
        self._init_games_db()
        self._init_players_db()
    
    def _init_db(self):
        """初始化数据库表"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        
        # 创建 agents 表（如果不存在）
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                id TEXT PRIMARY KEY,
                name TEXT,
                config TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 检查并添加新字段（用于知识存储）
        self._migrate_db(conn)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                agent_id TEXT,
                content TEXT,
                embedding TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
    
    def _migrate_db(self, conn):
        """
        迁移数据库结构
        添加新字段到现有表
        """
        # 检查 agents 表是否有新字段
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(agents)")
        columns = [row[1] for row in cur.fetchall()]
        
        # 添加新字段（如果不存在）
        new_columns = [
            ("general_knowledge", "TEXT"),
            ("specific_knowledge", "TEXT"),
            ("knowledge_embedding", "TEXT")
        ]
        
        for col_name, col_type in new_columns:
            if col_name not in columns:
                try:
                    cur.execute(f"ALTER TABLE agents ADD COLUMN {col_name} {col_type}")
                    print(f"Added column {col_name} to agents table")
                except Exception as e:
                    print(f"Error adding column {col_name}: {e}")
        
        conn.commit()
    
    def save_agent(self, agent_id: str, config: Dict[str, Any], 
                   general_knowledge: str = None, specific_knowledge: str = None,  # type: ignore
                   knowledge_embedding: str = None): # type: ignore
        """
        保存 agent 配置
        
        Args:
            agent_id: NPC ID
            config: NPC 配置字典
            general_knowledge: NPC 通用知识（未来用于向量化）
            specific_knowledge: NPC 专属知识（未来用于向量化）
            knowledge_embedding: 知识向量（预留字段）
        """
        conn = sqlite3.connect(self.db_path)
        config_json = json.dumps(config, ensure_ascii=False)
        name = config.get("name", agent_id)
        
        # 检查是否包含新知识字段
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(agents)")
        columns = [row[1] for row in cur.fetchall()]
        
        if "general_knowledge" in columns:
            # 新表结构：包含知识字段
            conn.execute("""
                INSERT OR REPLACE INTO agents 
                (id, name, config, general_knowledge, specific_knowledge, knowledge_embedding, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (agent_id, name, config_json, general_knowledge, specific_knowledge, knowledge_embedding))
        else:
            # 旧表结构：不包含知识字段
            conn.execute("""
                INSERT OR REPLACE INTO agents (id, name, config, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (agent_id, name, config_json))
        
        conn.commit()
        conn.close()
    
    def load_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """加载 agent 配置"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        # 检查是否包含新知识字段
        cur.execute("PRAGMA table_info(agents)")
        columns = [row[1] for row in cur.fetchall()]
        
        if "general_knowledge" in columns:
            # 新表结构：包含知识字段
            cur.execute("""
                SELECT config, general_knowledge, specific_knowledge, knowledge_embedding 
                FROM agents WHERE id = ?
            """, (agent_id,))
        else:
            # 旧表结构：不包含知识字段
            cur.execute("SELECT config FROM agents WHERE id = ?", (agent_id,))
        
        row = cur.fetchone()
        conn.close()
        
        if row:
            config = json.loads(row["config"])
            
            # 如果表包含新知识字段，添加到配置中
            if "general_knowledge" in columns:
                config["general_knowledge"] = row["general_knowledge"]
                config["specific_knowledge"] = row["specific_knowledge"]
                config["knowledge_embedding"] = row["knowledge_embedding"]
            
            return config
        return None
    
    def delete_agent(self, agent_id: str):
        """删除 agent"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM agents WHERE id = ?", (agent_id,))
        conn.execute("DELETE FROM memories WHERE agent_id = ?", (agent_id,))
        conn.commit()
        conn.close()
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """列出所有 agents"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        cur.execute("SELECT id, name, updated_at FROM agents ORDER BY updated_at DESC")
        rows = cur.fetchall()
        conn.close()
        
        return [
            {"id": r["id"], "name": r["name"], "updated_at": r["updated_at"]}
            for r in rows
        ]
    
    def save_memory(self, agent_id: str, content: str, embedding: Optional[str] = None):
        """保存记忆"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO memories (agent_id, content, embedding)
            VALUES (?, ?, ?)
        """, (agent_id, content, embedding))
        conn.commit()
        conn.close()
    
    def get_memories(self, agent_id: str) -> List[str]:
        """获取记忆列表"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        cur.execute(
            "SELECT content FROM memories WHERE agent_id = ? ORDER BY created_at",
            (agent_id,)
        )
        rows = cur.fetchall()
        conn.close()
        
        return [r["content"] if r["content"] else "" for r in rows]
    
    # ==================== 预留接口：知识存储 ====================
    # TODO: 以下函数用于未来向量数据库存储
    # WARNING: 当前项目不完整，向量数据库逻辑暂未实现
    
    def save_agent_knowledge(self, agent_id: str, general_knowledge: str, 
                            specific_knowledge: str, embedding: str = None): # type: ignore
        """
        保存NPC知识到数据库
        预留接口，未来用于向量数据库存储
        
        Args:
            agent_id: NPC ID
            general_knowledge: 通用知识（JSON格式或纯文本）
            specific_knowledge: 专属知识（JSON格式）
            embedding: 知识向量化存储（预留）
        
        TODO: 实现向量化存储逻辑
        WARNING: 当前项目不完整，向量数据库逻辑暂未实现
        """
        # 加载现有配置
        config = self.load_agent(agent_id) or {}
        
        # 调用 save_agent 保存知识
        self.save_agent(agent_id, config, general_knowledge, specific_knowledge, embedding)
        
        print(f"Knowledge saved for agent {agent_id}")
    
    # ==================== 游戏会话持久化 ====================

    def _init_games_db(self):
        """初始化 games 数据库表"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS games (
                session_id TEXT PRIMARY KEY,
                title TEXT,
                story TEXT,
                roles TEXT,
                questions TEXT,
                progress TEXT,
                suspicion INTEGER DEFAULT 0,
                game_ended INTEGER DEFAULT 0,
                victory INTEGER DEFAULT 0,
                retry_count TEXT DEFAULT '{}',
                player_gold INTEGER DEFAULT 100,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self._migrate_games_db(conn)
        conn.commit()
        conn.close()

    def _migrate_games_db(self, conn):
        """迁移 games 表结构，添加新字段"""
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(games)")
        columns = [row[1] for row in cur.fetchall()]

        new_columns = [
            ("retry_count", "TEXT DEFAULT '{}'"),
            ("player_gold", "INTEGER DEFAULT 100")
        ]

        for col_name, col_type in new_columns:
            if col_name not in columns:
                try:
                    cur.execute(f"ALTER TABLE games ADD COLUMN {col_name} {col_type}")
                    print(f"[DatabaseIO] Added column {col_name} to games table")
                except Exception as e:
                    print(f"[DatabaseIO] Error adding column {col_name}: {e}")

    def save_game_session(self, session_id: str, title: str, story: str,
                           roles: dict, questions: list, progress: dict,
                           suspicion: int, game_ended: bool, victory: bool,
                           retry_count: Optional[dict] = None, player_gold: int = 100):
        """保存游戏会话到数据库"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT OR REPLACE INTO games
            (session_id, title, story, roles, questions, progress,
             suspicion, game_ended, victory, retry_count, player_gold, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            session_id, title, story,
            json.dumps(roles, ensure_ascii=False),
            json.dumps(questions, ensure_ascii=False),
            json.dumps(progress, ensure_ascii=False),
            suspicion,
            int(game_ended),
            int(victory),
            json.dumps(retry_count or {}, ensure_ascii=False),
            player_gold
        ))
        conn.commit()
        conn.close()

    def load_game_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """从数据库加载游戏会话"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM games WHERE session_id = ?", (session_id,))
        row = cur.fetchone()
        conn.close()

        if not row:
            return None

        return {
            "session_id": row["session_id"],
            "title": row["title"],
            "story": row["story"],
            "roles": json.loads(row["roles"]) if row["roles"] else {},
            "questions": json.loads(row["questions"]) if row["questions"] else [],
            "progress": json.loads(row["progress"]) if row["progress"] else {},
            "suspicion": row["suspicion"],
            "game_ended": bool(row["game_ended"]),
            "victory": bool(row["victory"]),
            "retry_count": json.loads(row["retry_count"]) if row["retry_count"] else {},
            "player_gold": row["player_gold"] if "player_gold" in row.keys() else 100
        }

    def update_game_progress(self, session_id: str, progress: dict,
                               suspicion: int, game_ended: bool, victory: bool,
                               retry_count: Optional[dict] = None, player_gold: Optional[int] = None):
        """更新游戏进度"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            UPDATE games SET progress=?, suspicion=?, game_ended=?,
            victory=?, retry_count=?, player_gold=?, updated_at=CURRENT_TIMESTAMP
            WHERE session_id=?
        """, (
            json.dumps(progress, ensure_ascii=False),
            suspicion,
            int(game_ended),
            int(victory),
            json.dumps(retry_count or {}, ensure_ascii=False),
            player_gold if player_gold is not None else 100,
            session_id
        ))
        conn.commit()
        conn.close()

    def list_game_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """列出最近的会话"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT session_id, title, suspicion, game_ended, victory, created_at
            FROM games ORDER BY created_at DESC LIMIT ?
        """, (limit,))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def delete_game_session(self, session_id: str):
        """从数据库删除游戏会话"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM games WHERE session_id = ?", (session_id,))
        conn.commit()
        conn.close()

    # ==================== 玩家数据持久化 ====================

    def _init_players_db(self):
        """初始化玩家数据库表"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS players (
                id TEXT PRIMARY KEY,
                gold INTEGER DEFAULT 100,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS player_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id TEXT NOT NULL,
                item_name TEXT NOT NULL,
                item_type TEXT NOT NULL,
                count INTEGER DEFAULT 0,
                FOREIGN KEY (player_id) REFERENCES players(id)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_inventory_player
            ON player_inventory(player_id)
        """)
        self._migrate_players_db(conn)
        conn.commit()
        conn.close()

    def _migrate_players_db(self, conn):
        """迁移 players 表结构"""
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(players)")
        columns = [row[1] for row in cur.fetchall()]
        if "gold" not in columns:
            try:
                cur.execute("ALTER TABLE players ADD COLUMN gold INTEGER DEFAULT 100")
                print("[DatabaseIO] Added column gold to players table")
            except Exception as e:
                print(f"[DatabaseIO] Error adding column gold: {e}")

    def get_or_create_player(self, player_id: str) -> Dict[str, Any]:
        """获取或创建玩家记录"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM players WHERE id = ?", (player_id,))
        row = cur.fetchone()

        if row:
            result = {
                "id": row["id"],
                "gold": row["gold"],
                "inventory": self.get_player_inventory(player_id)
            }
            conn.close()
            return result

        cur.execute(
            "INSERT INTO players (id, gold) VALUES (?, 100)",
            (player_id,)
        )
        conn.commit()
        conn.close()

        return {
            "id": player_id,
            "gold": 100,
            "inventory": {}
        }

    def get_player_gold(self, player_id: str) -> int:
        """获取玩家金币"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT gold FROM players WHERE id = ?", (player_id,))
        row = cur.fetchone()
        conn.close()
        return row[0] if row else 100

    def update_player_gold(self, player_id: str, gold: int) -> bool:
        """更新玩家金币"""
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT OR REPLACE INTO players (id, gold, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (player_id, gold)
        )
        conn.commit()
        conn.close()
        return True

    def deduct_player_gold(self, player_id: str, amount: int) -> Dict[str, Any]:
        """扣除玩家金币，返回操作结果"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT gold FROM players WHERE id = ?", (player_id,))
        row = cur.fetchone()

        current_gold = row[0] if row else 100

        if current_gold < amount:
            conn.close()
            return {"success": False, "message": "金币不足", "gold": current_gold}

        new_gold = current_gold - amount
        conn.execute(
            "INSERT OR REPLACE INTO players (id, gold, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (player_id, new_gold)
        )
        conn.commit()
        conn.close()
        return {"success": True, "message": f"扣除{amount}金币", "gold": new_gold}

    def get_player_inventory(self, player_id: str) -> Dict[str, int]:
        """获取玩家背包"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT item_name, item_type, count FROM player_inventory WHERE player_id = ? AND count > 0",
            (player_id,)
        )
        rows = cur.fetchall()
        conn.close()

        inventory = {}
        for name, item_type, count in rows:
            key = f"{item_type}:{name}"
            inventory[key] = {"name": name, "type": item_type, "count": count}
        return inventory

    def add_player_item(self, player_id: str, item_name: str, item_type: str, count: int = 1):
        """添加物品到玩家背包（累加模式，用于购买/奖励增量）"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT id, count FROM player_inventory WHERE player_id = ? AND item_name = ? AND item_type = ?",
            (player_id, item_name, item_type)
        )
        row = cur.fetchone()

        if row:
            new_count = row[1] + count
            conn.execute(
                "UPDATE player_inventory SET count = ? WHERE id = ?",
                (new_count, row[0])
            )
        else:
            conn.execute(
                "INSERT INTO player_inventory (player_id, item_name, item_type, count) VALUES (?, ?, ?, ?)",
                (player_id, item_name, item_type, count)
            )

        conn.commit()
        conn.close()

    def set_player_item(self, player_id: str, item_name: str, item_type: str, count: int):
        """
        设置玩家背包物品的绝对数量（用于前端状态同步）
        当 count 为 0 时删除该物品记录
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM player_inventory WHERE player_id = ? AND item_name = ? AND item_type = ?",
            (player_id, item_name, item_type)
        )
        row = cur.fetchone()

        if count <= 0:
            # 数量为 0 或负数：删除记录
            if row:
                conn.execute("DELETE FROM player_inventory WHERE id = ?", (row[0],))
        elif row:
            conn.execute(
                "UPDATE player_inventory SET count = ? WHERE id = ?",
                (count, row[0])
            )
        else:
            conn.execute(
                "INSERT INTO player_inventory (player_id, item_name, item_type, count) VALUES (?, ?, ?, ?)",
                (player_id, item_name, item_type, count)
            )

        conn.commit()
        conn.close()

    def remove_player_item(self, player_id: str, item_name: str, item_type: str, count: int = 1):
        """
        从玩家背包扣除指定数量的物品
        如果扣除后数量 <= 0，删除该物品记录
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT id, count FROM player_inventory WHERE player_id = ? AND item_name = ? AND item_type = ?",
            (player_id, item_name, item_type)
        )
        row = cur.fetchone()

        if not row:
            conn.close()
            return False

        new_count = row[1] - count
        if new_count <= 0:
            conn.execute("DELETE FROM player_inventory WHERE id = ?", (row[0],))
        else:
            conn.execute(
                "UPDATE player_inventory SET count = ? WHERE id = ?",
                (new_count, row[0])
            )

        conn.commit()
        conn.close()
        return True

    def load_agent_knowledge(self, agent_id: str) -> Dict[str, Any]:
        """
        加载NPC知识 from 数据库
        预留接口，未来用于向量数据库检索
        
        Returns:
            {"general_knowledge": str, "specific_knowledge": str, "knowledge_embedding": str}
        
        TODO: 实现向量化检索逻辑
        WARNING: 当前项目不完整，向量数据库逻辑暂未实现
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        # 检查是否包含新知识字段
        cur.execute("PRAGMA table_info(agents)")
        columns = [row[1] for row in cur.fetchall()]
        
        if "general_knowledge" in columns:
            cur.execute("""
                SELECT general_knowledge, specific_knowledge, knowledge_embedding 
                FROM agents WHERE id = ?
            """, (agent_id,))
            row = cur.fetchone()
            
            if row:
                return {
                    "general_knowledge": row["general_knowledge"],
                    "specific_knowledge": row["specific_knowledge"],
                    "knowledge_embedding": row["knowledge_embedding"]
                }
        
        conn.close()
        
        # 如果没有知识字段，返回空字典
        return {
            "general_knowledge": None,
            "specific_knowledge": None,
            "knowledge_embedding": None
        }
