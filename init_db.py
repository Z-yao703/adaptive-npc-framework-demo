#!/usr/bin/env python3
"""
数据库初始化脚本
运行此脚本初始化数据库并导入预设配置
"""
import json
import os
import sqlite3
from pathlib import Path

def init_database():
    # 确保目录存在
    os.makedirs("database", exist_ok=True)
    os.makedirs("configs", exist_ok=True)
    
    db_path = "database/agents.db"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # 创建表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS agents (
            id TEXT PRIMARY KEY,
            name TEXT,
            config TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    
    # 导入预设配置
    configs_dir = Path("configs")
    imported = 0
    
    for json_file in configs_dir.glob("*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                config = json.load(f)
            
            agent_id = config.get("id")
            if agent_id:
                config_json = json.dumps(config, ensure_ascii=False)
                name = config.get("name", agent_id)
                
                cur.execute("""
                    INSERT OR REPLACE INTO agents (id, name, config, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """, (agent_id, name, config_json))
                imported += 1
                print(f"  ✓ 导入: {name} ({agent_id})")
        except Exception as e:
            print(f"  ✗ 跳过 {json_file.name}: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ 初始化完成！共导入 {imported} 个 NPC 配置")
    return imported

if __name__ == "__main__":
    print("🔧 Adaptive NPC Framework - 数据库初始化")
    print("=" * 50)
    init_database()
