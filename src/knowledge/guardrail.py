"""
安全护栏
过滤不当内容，确保 NPC 行为安全
"""
from typing import List, Dict, Any


class Guardrail:
    """
    内容安全护栏
    
    检查：
    - 禁止词过滤
    - 敏感信息检测
    - 动作安全性验证
    """
    
    def __init__(self):
        self.blocked_words: List[str] = [
            # 添加项目特定的禁止词
        ]
        
        self.allowed_actions: List[str] = [
            "dialogue", "move_to", "trade", "give_item", "take_item",
            "start_quest", "complete_quest", "emote", "follow"
        ]
    
    def check_message(self, message: str) -> Dict[str, Any]:
        """
        检查消息安全性
        
        返回：
        {
            "safe": bool,
            "sanitized": str,
            "reason": str
        }
        """
        if not message:
            return {"safe": True, "sanitized": "", "reason": ""}
        
        sanitized = message
        
        # 检查禁止词
        for word in self.blocked_words:
            if word.lower() in sanitized.lower():
                sanitized = sanitized.replace(word, "*" * len(word))
        
        # 基本过滤
        sanitized = sanitized.strip()
        
        return {
            "safe": True,
            "sanitized": sanitized,
            "reason": ""
        }
    
    def check_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        检查动作安全性
        
        返回：
        {
            "allowed": bool,
            "action": Dict,
            "reason": str
        }
        """
        action_type = action.get("type")
        
        if not action_type:
            return {"allowed": False, "action": None, "reason": "Missing action type"}
        
        if action_type not in self.allowed_actions:
            return {"allowed": False, "action": None, "reason": f"Action '{action_type}' not allowed"}
        
        return {"allowed": True, "action": action, "reason": ""}
    
    def sanitize_output(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """清理输出内容"""
        if action.get("message"):
            check = self.check_message(action["message"])
            action["message"] = check["sanitized"]
        
        return action
