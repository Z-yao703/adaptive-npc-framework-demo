"""
工具调用器（Tool Caller）
负责注册工具、解析 LLM 函数调用、执行工具并返回标准 Action

设计原则：
1. ToolCaller 不依赖具体游戏实现（只返回语义 Action）
2. handler 必须返回标准 Action 数据，格式：{"action": {...}}
3. engine.py 不包含业务逻辑，只做调度
"""

from typing import Dict, Any, Callable, Optional
from dataclasses import dataclass


@dataclass
class ToolDefinition:
    """工具定义"""
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Optional[Callable] = None


class ToolCaller:
    """
    工具调用器

    职责：
    - 注册工具（能力声明）
    - 执行工具 handler（系统规则）
    - 返回标准 Action（给 engine → protocol → 前端执行）

    禁止：
    - 直接操作游戏对象（如 inventory、player）
    - 包含具体游戏业务逻辑（应由 handler 返回语义数据）
    """

    def __init__(self):
        self.tools: Dict[str, ToolDefinition] = {}
        self._register_builtin_tools()

    def _register_builtin_tools(self):
        """注册内置工具（带 handler，返回标准 Action）"""

        def give_reward_handler(args: Dict[str, Any]) -> Dict[str, Any]:
            """
            根据任务给予奖励（系统规则）
            注意：这里只是"系统规则"，不依赖具体游戏实现
            返回语义 Action，由前端/游戏层执行具体逻辑
            """
            quest_id = args.get("quest_id", "")

            # 奖励表（未来应来自配置或数据库）
            reward_table = {
                "apple_quest": {"item": "铜币", "quantity": 10},
                "default": {"item": "铜币", "quantity": 1}
            }

            reward = reward_table.get(quest_id, reward_table["default"])

            return {
                "action": {
                    "type": "give_item",
                    "item": reward["item"],
                    "quantity": reward["quantity"]
                }
            }

        def dialogue_handler(args: Dict[str, Any]) -> Dict[str, Any]:
            """
            处理对话（返回标准 dialogue action）
            """
            return {
                "action": {
                    "type": "dialogue",
                    "message": args.get("message", ""),
                    "emotion": args.get("emotion", "neutral")
                }
            }

        def move_to_handler(args: Dict[str, Any]) -> Dict[str, Any]:
            """
            处理移动（返回标准 move_to action）
            """
            return {
                "action": {
                    "type": "move_to",
                    "target": args.get("target", {"x": 0, "y": 0}),
                    "speed": args.get("speed", 80)
                }
            }

        def emote_handler(args: Dict[str, Any]) -> Dict[str, Any]:
            """
            处理表情动作
            """
            return {
                "action": {
                    "type": "emote",
                    "emotion": args.get("emotion", "wave"),
                    "duration": args.get("duration", 2000)
                }
            }

        def start_quest_handler(args: Dict[str, Any]) -> Dict[str, Any]:
            """
            处理任务发布
            """
            return {
                "action": {
                    "type": "start_quest",
                    "quest_id": args.get("quest_id", ""),
                    "title": args.get("title", ""),
                    "description": args.get("description", "")
                }
            }

        def complete_quest_handler(args: Dict[str, Any]) -> Dict[str, Any]:
            """
            任务完成动作。
            奖励由配置或运行时上下文提供。
            """
            return {
                "action": {
                    "type": "complete_quest",
                    "quest_id": args.get("quest_id", ""),
                    "rewards": args.get("rewards", [])
                }
            }

        def take_item_handler(args: Dict[str, Any]) -> Dict[str, Any]:
            """
            处理收取物品
            """
            return {
                "action": {
                    "type": "take_item",
                    "item": args.get("item", ""),
                    "quantity": args.get("quantity", 1)
                }
            }

        def give_item_handler(args: Dict[str, Any]) -> Dict[str, Any]:
            """
            处理 NPC 直接给予物品（仅暗号触发场景使用）
            """
            return {
                "action": {
                    "type": "give_item",
                    "item": args.get("item", ""),
                    "quantity": args.get("quantity", 1)
                }
            }

        def give_gold_handler(args: Dict[str, Any]) -> Dict[str, Any]:
            """
            处理 NPC 给予金币（任务阶段奖励等）
            """
            return {
                "action": {
                    "type": "give_gold",
                    "amount": args.get("amount", 0),
                    "reason": args.get("reason", "")
                }
            }

        def update_quest_handler(args: Dict[str, Any]) -> Dict[str, Any]:
            """
            处理任务阶段更新
            """
            return {
                "action": {
                    "type": "update_quest",
                    "quest_id": args.get("quest_id", ""),
                    "stage": args.get("stage", 1)
                }
            }

        # 注册工具（注意：give_item 仅用于暗号场景）
        self.register(
            name="give_reward",
            description="根据任务给予玩家奖励（系统自动决定物品和数量）",
            parameters={
                "quest_id": {"type": "string", "description": "任务ID"}
            },
            handler=give_reward_handler
        )

        self.register(
            name="give_item",
            description="NPC直接给予玩家物品（仅在暗号匹配时使用，系统会自动调用此工具）",
            parameters={
                "item": {"type": "string", "description": "物品名称"},
                "quantity": {"type": "number", "description": "数量"}
            },
            handler=give_item_handler
        )

        self.register(
            name="give_gold",
            description="给予玩家金币（用于任务阶段奖励等）",
            parameters={
                "amount": {"type": "number", "description": "金币数量"},
                "reason": {"type": "string", "description": "给予原因"}
            },
            handler=give_gold_handler
        )

        self.register(
            name="update_quest",
            description="更新任务进度到下一阶段",
            parameters={
                "quest_id": {"type": "string", "description": "任务ID"},
                "stage": {"type": "number", "description": "当前阶段编号"}
            },
            handler=update_quest_handler
        )

        self.register(
            name="dialogue",
            description="让NPC说一段话",
            parameters={
                "message": {"type": "string", "description": "要说的内容"},
                "emotion": {"type": "string", "description": "情感状态 (neutral/happy/sad/angry/thinking/satisfied)"}
            },
            handler=dialogue_handler
        )

        self.register(
            name="move_to",
            description="让NPC移动到指定位置",
            parameters={
                "target": {"type": "object", "description": "目标坐标 {x, y}"},
                "speed": {"type": "number", "description": "移动速度"}
            },
            handler=move_to_handler
        )

        self.register(
            name="emote",
            description="让NPC做出表情动作",
            parameters={
                "emotion": {"type": "string", "description": "表情类型 (wave/nod/happy/angry等)"},
                "duration": {"type": "number", "description": "持续时间(ms)"}
            },
            handler=emote_handler
        )

        self.register(
            name="start_quest",
            description="给玩家发布一个新任务",
            parameters={
                "quest_id": {"type": "string", "description": "任务ID"},
                "title": {"type": "string", "description": "任务标题"},
                "description": {"type": "string", "description": "任务描述"}
            },
            handler=start_quest_handler
        )

        self.register(
            name="complete_quest",
            description="验收玩家任务并发放奖励",
            parameters={
                "quest_id": {"type": "string", "description": "任务ID"},
                "rewards": {"type": "array", "description": "奖励列表"}
            },
            handler=complete_quest_handler
        )

        self.register(
            name="take_item",
            description="从玩家背包收取物品",
            parameters={
                "item": {"type": "string", "description": "物品ID"},
                "quantity": {"type": "number", "description": "数量"}
            },
            handler=take_item_handler
        )

        # ========== start_trade handler ==========
        def start_trade_handler(args: Dict[str, Any]) -> Dict[str, Any]:
            """
            处理交易发起（NPC 接受玩家的售卖请求）
            返回 trade action，携带匹配到的物品信息 + tip
            """
            items = args.get("items", [])
            tip = args.get("tip", 0)
            message = args.get("message", "")
            return {
                "action": {
                    "type": "trade",
                    "npc_id": args.get("npc_id", ""),
                    "items": items,
                    "tip": tip,
                    "message": message
                }
            }

        self.register(
            name="start_trade",
            description="发起交易：NPC接受玩家售卖请求，打开交易面板。携带匹配到的物品列表（每项含name/sellPrice/type）、tip金额、以及NPC消息",
            parameters={
                "items": {
                    "type": "array",
                    "description": "匹配到的可交易物品列表，每项包含 name(物品名)/sellPrice(售价)/type(分类:food/supply)"
                },
                "tip": {
                    "type": "number",
                    "description": "NPC自主决定的附加费金额（通常0或5）"
                },
                "message": {
                    "type": "string",
                    "description": "NPC接受交易时说的话"
                }
            },
            handler=start_trade_handler
        )

    def register(self, name: str, description: str, parameters: Dict, handler: Optional[Callable] = None):
        """注册工具"""
        self.tools[name] = ToolDefinition(
            name=name,
            description=description,
            parameters=parameters,
            handler=handler
        )

    def call(self, tool_name: str, arguments: Dict[str, Any], game_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用工具

        参数：
        - tool_name: 工具名
        - arguments: LLM 传来的参数
        - game_context: 游戏状态上下文

        返回：
        - {"success": True, "action": {...}}  # 成功，返回标准 Action
        - {"success": False, "error": "..."}  # 失败
        """
        if tool_name not in self.tools:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}

        tool = self.tools[tool_name]

        try:
            if tool.handler:
                # 合并游戏上下文，调用 handler
                full_args = {**game_context, **arguments}
                result = tool.handler(full_args)

                # 强制要求返回 action
                if not isinstance(result, dict) or "action" not in result:
                    return {"success": False, "error": "Tool must return {'action': ...}"}

                return {"success": True, "action": result["action"]}
            else:
                return {"success": False, "error": "No handler defined for tool"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_tool_schemas(self) -> list:
        """获取工具定义（用于注入 LLM prompt），支持完整 JSON Schema"""
        schemas = []
        for tool in self.tools.values():
            properties = {}

            for key, val in tool.parameters.items():
                # 如果是新 schema（dict）
                if isinstance(val, dict):
                    prop = {
                        "type": val.get("type", "string"),
                        "description": val.get("description", "")
                    }

                    # 支持 enum
                    if "enum" in val:
                        prop["enum"] = val["enum"]

                    # 支持 number 约束
                    if val.get("type") == "number":
                        if "min" in val:
                            prop["minimum"] = val["min"]
                        if "max" in val:
                            prop["maximum"] = val["max"]

                    properties[key] = prop

                else:
                    continue

            schemas.append({
                "name": tool.name,
                "description": tool.description,
                "parameters": {
                    "type": "object",
                    "properties": properties
                }
            })
        return schemas
