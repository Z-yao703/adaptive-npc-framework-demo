"""
任务验证器
验证玩家是否满足任务完成条件
"""
from typing import Dict, Any, List


class QuestValidator:
    """
    任务验证器
    
    验证条件类型：
    - item_collected: 收集指定物品
    - item_delivered: 交付物品给 NPC
    - enemy_defeated: 击败敌人
    - location_visited: 访问地点
    - quest_completed: 完成前置任务
    """
    
    def __init__(self):
        self.quest_definitions: Dict[str, Dict] = {}
    
    def register_quest(self, quest_id: str, conditions: List[Dict]):
        """注册任务定义"""
        self.quest_definitions[quest_id] = {
            "id": quest_id,
            "conditions": conditions
        }
    
    def validate(self, quest_id: str, player_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证任务完成条件
        
        返回：
        {
            "completed": bool,
            "progress": float,  # 0.0 - 1.0
            "details": [...]
        }
        """
        if quest_id not in self.quest_definitions:
            return {"completed": False, "progress": 0, "error": "Quest not found"}
        
        quest = self.quest_definitions[quest_id]
        conditions = quest["conditions"]
        
        results = []
        completed_count = 0
        
        for condition in conditions:
            cond_type = condition.get("type")
            params = condition.get("params", {})
            
            result = self._check_condition(cond_type, params, player_state)
            results.append(result)
            
            if result["met"]:
                completed_count += 1
        
        progress = completed_count / len(conditions) if conditions else 1.0
        
        return {
            "completed": progress >= 1.0,
            "progress": progress,
            "details": results
        }
    
    def _check_condition(self, cond_type: str, params: Dict, state: Dict) -> Dict:
        """检查单个条件"""
        if cond_type == "item_collected":
            item_id = params.get("item_id")
            count = params.get("count", 1)
            inventory = state.get("player_inventory", [])
            
            # 简单计数
            item_count = inventory.count(item_id) if isinstance(inventory, list) else 0
            met = item_count >= count
            
            return {
                "type": cond_type,
                "met": met,
                "current": item_count,
                "required": count,
                "description": f"收集 {count} 个 {item_id}"
            }
        
        if cond_type == "location_visited":
            location = params.get("location")
            visited = state.get("locations_visited", [])
            met = location in visited
            
            return {
                "type": cond_type,
                "met": met,
                "description": f"访问 {location}"
            }
        
        if cond_type == "quest_completed":
            quest_id = params.get("quest_id")
            completed = state.get("quests_completed", [])
            met = quest_id in completed
            
            return {
                "type": cond_type,
                "met": met,
                "description": f"完成前置任务 {quest_id}"
            }
        
        # 默认返回未满足
        return {
            "type": cond_type,
            "met": False,
            "description": f"未知条件: {cond_type}"
        }
