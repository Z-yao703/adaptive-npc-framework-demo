"""
配置加载器
支持 JSON 文件和 SQLite 数据库
"""
import json
import os
from typing import Dict, Any, Optional


class ConfigLoader:
    """
    配置加载器
    
    优先级：
    1. 数据库（生产环境）
    2. JSON 文件（开发/备份）
    """
    
    def __init__(self, db_path: str = "database/agents.db"):
        self.db_path = db_path
        self._ensure_database()
    
    # TODO: ==================== 需要调整此函数 ====================
    # 当前逻辑：从数据库或JSON文件加载NPC配置
    # 需要调整：
    # 1. 加载NPC配置后，检查是否包含 world_id
    # 2. 如果需要，可以根据 world_id 加载对应的世界背景信息
    # 3. 但根据需求，世界背景信息不需要在加载时合并，只需要保存引用
    # 所以此函数可能不需要大改，只需要确保能正确加载新的字段结构

    
    def _ensure_database(self):
        """确保数据库目录存在"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    def load(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        加载 agent 配置
        
        优先从数据库加载，fallback 到 JSON
        """
        # 尝试数据库
        config = self._load_from_db(agent_id)
        if config:
            return config
        
        # Fallback 到 JSON
        return self._load_from_json(agent_id)
    
    def _load_from_db(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """从 SQLite 数据库加载"""
        try:
            import sqlite3
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            
            cur.execute("SELECT config FROM agents WHERE id = ?", (agent_id,))
            row = cur.fetchone()
            conn.close()
            
            if row:
                return json.loads(row["config"])
        except Exception as e:
            print(f"DB load error: {e}")
        
        return None
    
    def _load_from_json(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """从 JSON 文件加载（备用）"""
        json_path = f"configs/{agent_id}.json"
        
        if not os.path.exists(json_path):
            return None
        
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"JSON load error: {e}")
            return None
    
    def save(self, agent_id: str, config: Dict[str, Any]):
        """保存配置到数据库"""
        import sqlite3
        
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        # 创建表（如果不存在）
        cur.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                id TEXT PRIMARY KEY,
                name TEXT,
                config TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 插入或更新
        config_json = json.dumps(config, ensure_ascii=False)
        name = config.get("name", agent_id)
        
        cur.execute("""
            INSERT OR REPLACE INTO agents (id, name, config)
            VALUES (?, ?, ?)
        """, (agent_id, name, config_json))
        
        conn.commit()
        conn.close()
    
    def delete(self, agent_id: str):
        """删除配置"""
        import sqlite3
        
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("DELETE FROM agents WHERE id = ?", (agent_id,))
        conn.commit()
        conn.close()
    
    def list_all(self) -> list:
        """列出所有 agent"""
        try:
            import sqlite3
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("SELECT id, name FROM agents ORDER BY updated_at DESC")
            rows = cur.fetchall()
            conn.close()
            
            return [{"id": r[0], "name": r[1]} for r in rows]
        except:
            return []
    
    def export_json(self, agent_id: str, path: str):
        """导出到 JSON 文件"""
        config = self.load(agent_id)
        if config:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
    
    def import_json(self, path: str):
        """从 JSON 文件导入"""
        with open(path, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        agent_id = config.get("id")
        if agent_id:
            self.save(agent_id, config)
            return agent_id
        return None
    
    # ==================== 世界背景加载（新增） ====================
    # TODO: 根据需求，世界背景不需要单独加载
    # NPC配置中包含了 world_id 和 allowed_categories
    # 世界背景信息保存在单独的JSON文件中
    # 当需要访问世界背景信息时，根据 world_id 加载对应的JSON文件
    
    def load_world(self, world_id: str) -> Optional[Dict[str, Any]]:
        """
        加载世界背景配置
        从 configs/world_{world_id}.json 读取
        
        Args:
            world_id: 世界背景ID
            
        Returns:
            世界背景配置字典，如果不存在则返回None
        """
        json_path = f"configs/{world_id}.json"
        
        if not os.path.exists(json_path):
            return None
        
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"World config load error: {e}")
            return None
    
    def load_world_knowledge(self, world_id: str, allowed_categories: list) -> str:
        """
        根据 world_id 和 allowed_categories 加载世界知识
        返回格式化的知识文本，用于注入到NPC的Prompt中
        
        Args:
            world_id: 世界背景ID
            allowed_categories: 允许访问的知识类别列表
            
        Returns:
            格式化的知识文本
        """
        world_config = self.load_world(world_id)
        if not world_config:
            return ""
        
        sections = []
        
        # 添加世界描述（数组转字符串）
        descriptions = world_config.get("description", [])
        if descriptions:
            desc_text = "\n".join(f"- {d}" for d in descriptions)
            sections.append(f"【世界简介】\n{desc_text}")
        
        # 添加通用知识
        if world_config.get("general_info"):
            sections.append(f"【世界通用知识】\n{world_config['general_info']}")
        
        # 添加允许的专有知识类别
        categories = world_config.get("categories", [])
        for cat in categories:
            if cat["name"] in allowed_categories:
                items = "\n".join(f"- {item}" for item in cat["items"])
                sections.append(f"【{cat['name']}】\n{items}")
        
        return "\n\n".join(sections)
