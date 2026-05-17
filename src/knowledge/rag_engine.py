"""
RAG 记忆引擎
基于检索增强生成的记忆管理
"""
from typing import List, Dict, Any
import re


class RAGEngine:
    """
    RAG 记忆引擎（简化版）
    
    功能：
    - 存储对话/事件记忆
    - 检索相关记忆
    - 上下文注入
    """
    
    def __init__(self):
        self.memories: List[Dict[str, Any]] = []
        self.max_memories: int = 100
    
    def load_memories(self, memory_config: Dict[str, Any]):
        """从配置加载记忆"""
        if isinstance(memory_config, dict):
            facts = memory_config.get("facts", [])
            for fact in facts:
                self.add_memory(fact, "fact")
        elif isinstance(memory_config, list):
            for item in memory_config:
                self.add_memory(item, "unknown")
    
    def add_memory(self, content: str, memory_type: str = "event"):
        """添加记忆"""
        memory = {
            "content": content,
            "type": memory_type,
            "importance": 1.0
        }
        
        self.memories.append(memory)
        
        # 限制记忆数量
        if len(self.memories) > self.max_memories:
            self.memories = self.memories[-self.max_memories:]
    
    def retrieve(self, query: str, top_k: int = 5) -> str:
        """
        检索相关记忆
        
        简化实现：关键词匹配
        实际项目可接入向量数据库
        """
        if not self.memories:
            return ""
        
        query_keywords = set(re.findall(r'\w+', query.lower()))
        scored = []
        
        for memory in self.memories:
            content = memory.get("content", "")
            memory_keywords = set(re.findall(r'\w+', content.lower()))
            
            # 计算交集
            overlap = query_keywords & memory_keywords
            score = len(overlap) / max(len(query_keywords), 1)
            
            # 重要性加权
            importance = memory.get("importance", 1.0)
            scored.append((score * importance, memory))
        
        # 排序并取 top_k
        scored.sort(reverse=True, key=lambda x: x[0])
        top_memories = [m for _, m in scored[:top_k]]
        
        # 格式化为上下文
        if not top_memories:
            return ""
        
        context_parts = ["相关记忆："]
        for m in top_memories:
            context_parts.append(f"- {m['content']}")
        
        return "\n".join(context_parts)
    
    def clear(self):
        """清空记忆"""
        self.memories = []
    
    def get_all(self) -> List[str]:
        """获取所有记忆内容"""
        return [m["content"] for m in self.memories]
