"""
短期记忆数据库模块
负责管理 NPC 与玩家的日常对话历史

设计原则：
1. 每个 NPC 的记忆完全隔离（通过 npc_id）
2. 只存储日常对话类型（is_casual_chat = 1）
3. 自动维护对话轮数
4. 查询时按轮数降序返回最近 N 轮
"""
import sqlite3
import os
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class DialogueEntry:
    """单条对话记录"""
    id: int
    npc_id: str
    player_id: str
    round_num: int
    player_message: Optional[str]
    npc_response: Optional[str]
    timestamp: str
    is_casual_chat: bool


class ShortTermMemoryDB:
    """
    短期记忆数据库
    
    数据库结构：
    - id: 自增主键
    - npc_id: NPC 标识（用于隔离不同 NPC 的记忆）
    - player_id: 玩家标识
    - round_num: 对话轮数（每轮包含玩家发言 + NPC 回复）
    - player_message: 玩家发言内容
    - npc_response: NPC 回复内容
    - timestamp: 时间戳
    - is_casual_chat: 是否日常对话（1=是，0=否）
    """
    
    def __init__(self, db_path: str = "database/short_term_memory.db"):
        self.db_path = db_path
        self._ensure_dir()
        self._init_table()
    
    def _ensure_dir(self):
        """确保数据库目录存在"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    def _init_table(self):
        """初始化表结构"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS short_term_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                npc_id TEXT NOT NULL,
                player_id TEXT NOT NULL,
                round_num INTEGER NOT NULL,
                player_message TEXT,
                npc_response TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_casual_chat INTEGER DEFAULT 1
            )
        """)
        # 创建索引优化查询
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_npc_casual_round 
            ON short_term_memory(npc_id, is_casual_chat, round_num DESC)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_npc_timestamp 
            ON short_term_memory(npc_id, timestamp DESC)
        """)
        conn.commit()
        conn.close()
    
    def _get_next_round(self, npc_id: str, player_id: str = None) -> int: # type: ignore
        """获取下一个对话轮数（按 NPC + 玩家组合）"""
        conn = sqlite3.connect(self.db_path)
        if player_id:
            cur = conn.execute(
                "SELECT MAX(round_num) FROM short_term_memory WHERE npc_id = ? AND player_id = ? AND is_casual_chat = 1",
                (npc_id, player_id)
            )
        else:
            cur = conn.execute(
                "SELECT MAX(round_num) FROM short_term_memory WHERE npc_id = ? AND is_casual_chat = 1",
                (npc_id,)
            )
        result = cur.fetchone()[0]
        conn.close()
        return (result or 0) + 1
    
    def save_player_message(self, npc_id: str, player_id: str, message: str) -> int:
        """
        保存玩家发言（只存消息，等待 NPC 回复）
        
        Returns:
            entry_id: 记录 ID
        """
        round_num = self._get_next_round(npc_id, player_id)
        
        conn = sqlite3.connect(self.db_path)
        cur = conn.execute("""
            INSERT INTO short_term_memory 
            (npc_id, player_id, round_num, player_message, is_casual_chat)
            VALUES (?, ?, ?, ?, 1)
        """, (npc_id, player_id, round_num, message))
        conn.commit()
        entry_id = cur.lastrowid
        conn.close()
        
        return entry_id # type: ignore
    
    def save_npc_response(self, npc_id: str, player_id: str, response: str) -> int:
        """
        保存 NPC 回复（更新最后一轮的回复）
        
        查找同一 NPC、玩家最近的玩家发言记录，更新其 NPC 回复
        """
        conn = sqlite3.connect(self.db_path)
        
        # 找到最近的玩家发言记录
        cur = conn.execute("""
            SELECT id, round_num FROM short_term_memory 
            WHERE npc_id = ? AND player_id = ? AND player_message IS NOT NULL 
            AND npc_response IS NULL AND is_casual_chat = 1
            ORDER BY id DESC LIMIT 1
        """, (npc_id, player_id))
        
        row = cur.fetchone()
        
        if row:
            entry_id = row[0]
            # 更新 NPC 回复
            conn.execute("""
                UPDATE short_term_memory 
                SET npc_response = ?
                WHERE id = ?
            """, (response, entry_id))
            conn.commit()
            conn.close()
            return entry_id
        else:
            # 如果没有找到匹配的记录，创建一个新记录
            # 这可能发生在首次对话时
            round_num = self._get_next_round(npc_id)
            cur = conn.execute("""
                INSERT INTO short_term_memory 
                (npc_id, player_id, round_num, npc_response, is_casual_chat)
                VALUES (?, ?, ?, ?, 1)
            """, (npc_id, player_id, round_num, response))
            conn.commit()
            entry_id = cur.lastrowid
            conn.close()
            return entry_id # type: ignore
    
    def save_dialogue_pair(self, npc_id: str, player_id: str, 
                          player_message: str, npc_response: str) -> tuple:
        """
        保存一对完整的对话（玩家发言 + NPC 回复）
        
        使用单个事务确保数据一致性
        
        Returns:
            (player_entry_id, npc_entry_id)
        """
        conn = sqlite3.connect(self.db_path)
        
        try:
            # 获取下一个轮数（按 NPC + 玩家组合）
            cur = conn.execute(
                "SELECT MAX(round_num) FROM short_term_memory WHERE npc_id = ? AND player_id = ? AND is_casual_chat = 1",
                (npc_id, player_id)
            )
            result = cur.fetchone()[0]
            round_num = (result or 0) + 1
            
            # 插入玩家消息记录
            cur = conn.execute("""
                INSERT INTO short_term_memory 
                (npc_id, player_id, round_num, player_message, npc_response, is_casual_chat)
                VALUES (?, ?, ?, ?, ?, 1)
            """, (npc_id, player_id, round_num, player_message, npc_response))
            
            player_entry_id = cur.lastrowid
            
            conn.commit()
            return (player_entry_id, player_entry_id)  # 同一个记录
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def get_recent_chats(self, npc_id: str, player_id: str = None,  # type: ignore
                         limit: int = 3) -> List[Dict]:
        """
        获取最近 N 轮对话历史
        
        Args:
            npc_id: NPC 标识
            player_id: 玩家标识（可选，为空则返回该 NPC 与所有玩家的对话）
            limit: 返回轮数
        
        Returns:
            List[Dict]: 每轮对话的问答对列表
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        if player_id:
            cur = conn.execute("""
                SELECT round_num, player_id, player_message, npc_response, timestamp
                FROM short_term_memory 
                WHERE npc_id = ? AND player_id = ? AND is_casual_chat = 1
                AND player_message IS NOT NULL
                ORDER BY round_num DESC
                LIMIT ?
            """, (npc_id, player_id, limit))
        else:
            cur = conn.execute("""
                SELECT round_num, player_id, player_message, npc_response, timestamp
                FROM short_term_memory 
                WHERE npc_id = ? AND is_casual_chat = 1
                AND player_message IS NOT NULL
                ORDER BY round_num DESC
                LIMIT ?
            """, (npc_id, limit))
        
        rows = cur.fetchall()
        conn.close()
        
        # 格式化为问答对
        results = []
        for row in rows:
            results.append({
                'round': row['round_num'],
                'player_id': row['player_id'],
                'player_message': row['player_message'],
                'npc_response': row['npc_response'],
                'timestamp': row['timestamp']
            })
        
        return results
    
    def get_history_for_display(self, npc_id: str, player_id: str = None,  # type: ignore
                               limit: int = 3) -> List[Dict]:
        """
        获取用于前端显示的对话历史格式
        
        返回扁平化的消息列表，每条消息包含 speaker 和 content
        按时间正序排列（旧的在前，新的在后）
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        if player_id:
            cur = conn.execute("""
                SELECT round_num, player_id, player_message, npc_response, timestamp
                FROM short_term_memory 
                WHERE npc_id = ? AND player_id = ? AND is_casual_chat = 1
                AND player_message IS NOT NULL
                ORDER BY round_num ASC
                LIMIT ?
            """, (npc_id, player_id, limit))
        else:
            cur = conn.execute("""
                SELECT round_num, player_id, player_message, npc_response, timestamp
                FROM short_term_memory 
                WHERE npc_id = ? AND is_casual_chat = 1
                AND player_message IS NOT NULL
                ORDER BY round_num ASC
                LIMIT ?
            """, (npc_id, limit))
        
        rows = cur.fetchall()
        conn.close()
        
        # 构建扁平化消息列表（按时间正序）
        messages = []
        for row in rows:
            messages.append({
                'speaker': '玩家',
                'content': row['player_message']
            })
            if row['npc_response']:
                messages.append({
                    'speaker': 'NPC',
                    'content': row['npc_response']
                })
        
        return messages
    
    def clear_npc_memory(self, npc_id: str, player_id: str = None): # type: ignore
        """清除指定 NPC 的记忆（可选按玩家）"""
        conn = sqlite3.connect(self.db_path)
        if player_id:
            conn.execute(
                "DELETE FROM short_term_memory WHERE npc_id = ? AND player_id = ?",
                (npc_id, player_id)
            )
        else:
            conn.execute(
                "DELETE FROM short_term_memory WHERE npc_id = ?",
                (npc_id,)
            )
        conn.commit()
        conn.close()
    
    def get_statistics(self, npc_id: str) -> Dict:
        """获取 NPC 的记忆统计"""
        conn = sqlite3.connect(self.db_path)
        
        cur = conn.execute("""
            SELECT COUNT(*) as total, 
                   COUNT(DISTINCT player_id) as unique_players,
                   MAX(round_num) as max_round
            FROM short_term_memory 
            WHERE npc_id = ? AND is_casual_chat = 1
        """, (npc_id,))
        
        row = cur.fetchone()
        conn.close()
        
        return {
            'npc_id': npc_id,
            'total_entries': row[0] or 0,
            'unique_players': row[1] or 0,
            'max_round': row[2] or 0
        }


# 全局单例（延迟初始化）
_short_term_db: Optional[ShortTermMemoryDB] = None


def get_short_term_db() -> ShortTermMemoryDB:
    """获取全局短期记忆数据库实例"""
    global _short_term_db
    if _short_term_db is None:
        _short_term_db = ShortTermMemoryDB()
    return _short_term_db
