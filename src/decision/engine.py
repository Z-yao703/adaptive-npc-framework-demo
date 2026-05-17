"""
决策引擎
基于 LLM 决策 + 意图判断 + 动作约束
"""
from typing import Dict, Any, List, Optional, Set, Union, Callable
from src.protocol import (
    ActionType, npc_say, npc_emote, move_to,
    follow, start_trade, give_item, take_item,
    start_quest, update_quest, complete_quest, give_gold, error, ok
)  # 标准动作模板
from src.decision.intent_types import PlayerIntent
from src.decision.tool_caller import ToolCaller  # ToolCaller，它负责管理"工具"
from src.decision.intent_classifier import IntentClassifier
from src.decision.intent_handlers import IntentHandler
from src.decision.mock_provider import MockDecisionProvider
from src.logic.quest_manager import QuestManager


class DecisionEngine:
    """
    NPC 决策引擎
    - 接收 Prompt + 游戏状态
    - 意图判断与分类处理
    - 调用 LLM 生成决策
    - 约束动作在定义范围内
    - 返回符合 protocol.py 的标准 Action
    """
    
    def __init__(self, llm_client: Optional[Any] = None, npc_id: str = "default"):
        self.llm_client = llm_client
        self.npc_id = npc_id
        self.actions: List[Dict[str, Any]] = []
        self.action_registry: Set[str] = set()
        self.tool_caller: Optional[ToolCaller] = None
        self.profile: Dict[str, Any] = {}  # NPC 配置信息
        
        # 意图识别组件
        self.intent_classifier = IntentClassifier(llm_client)
        self.intent_handler: Optional[IntentHandler] = None
        
        # Mock 决策提供者（策略模式）
        self.mock_decision_provider = MockDecisionProvider()

        # 任务管理器
        self.quest_manager = QuestManager()
        
        self._register_actions()

    # 从配置文件加载 NPC 能做的动作，然后初始化工具调用器tool_caller
    def set_actions(self, actions: List[Dict[str, Any]]):
        """设置可用动作列表（从配置加载），并同步注册到 ToolCaller"""
        normalized = []
        for action in actions:
            if isinstance(action, dict):
                if "name" not in action:
                    action["name"] = action.get("type", "unknown")
                normalized.append(action)
        self.actions = normalized
        self._init_tool_caller()
        # 同步 quests 到任务管理器
        self.quest_manager.set_quests(self.profile.get("quests", []))
    # 保存 NPC 的人格设定（性格、对话、知识等）
    def set_profile(self, profile: Dict[str, Any]):
        """Store normalized NPC config for scene-aware fallback decisions."""
        self.profile = profile or {}
        self.quest_manager.set_quests(self.profile.get("quests", []))
        # 更新意图处理器的profile（使用专门的 set_profile 方法）
        if self.intent_handler:
            self.intent_handler.set_profile(profile or {})
        # 更新 mock 决策提供者的 profile
        self.mock_decision_provider.set_profile(profile or {})

    def _init_tool_caller(self):
        """初始化 ToolCaller（复用已注册的内置工具，只追加配置中的动作）"""
        # 如果已有 ToolCaller 实例，复用它（保留内置工具的 handler）
        if not self.tool_caller:
            self.tool_caller = ToolCaller()

        # 将配置中的动作注册为工具（如果内置工具中没有，则注册为无 handler 的工具）
        for action in self.actions:
            name = action.get("name", "")
            desc = action.get("description", "")
            params = action.get("parameters", {})
            if name and name not in self.tool_caller.tools:
                self.tool_caller.register(name=name, description=desc, parameters=params)
    
    def set_npc_id(self, npc_id: str):
        """设置 NPC ID"""
        self.npc_id = npc_id
        # 更新意图处理器的npc_id
        if self.intent_handler:
            self.intent_handler.npc_id = npc_id
    
    def _register_actions(self):
        """注册内置动作类型（用于验证）"""
        self.action_registry = {
            "dialogue", "move_to", "trade", "give_item", "take_item",
            "start_quest", "complete_quest", "emote", "follow"
        }
        self._init_action_converters()
    
    def _init_action_converters(self):
        """初始化动作转换注册表（注册表模式）"""
        self._action_converters: Dict[str, Callable[[Dict], Dict]] = {
            "dialogue": self._convert_dialogue,
            "move_to": self._convert_move_to,
            "emote": self._convert_emote,
            "follow": self._convert_follow,
            "trade": self._convert_trade,
            "give_item": self._convert_give_item,
            "take_item": self._convert_take_item,
            "start_quest": self._convert_start_quest,
            "update_quest": self._convert_update_quest,
            "complete_quest": self._convert_complete_quest,
            "give_gold": self._convert_give_gold,
            "error": self._convert_error,
        }
    
    def _convert_dialogue(self, raw: Dict) -> Dict:
        return npc_say(
            self.npc_id,
            raw.get("message", ""),
            raw.get("emotion", "neutral")
        )
    
    def _convert_move_to(self, raw: Dict) -> Dict:
        target = raw.get("target", {})
        if isinstance(target, dict):
            x, y = target.get("x", 0), target.get("y", 0)
        else:
            x, y = 0, 0
        return move_to(self.npc_id, x, y, raw.get("speed", 80))
    
    def _convert_emote(self, raw: Dict) -> Dict:
        return npc_emote(self.npc_id, raw.get("emotion", "wave"), raw.get("duration", 2000))
    
    def _convert_follow(self, raw: Dict) -> Dict:
        return follow(self.npc_id, raw.get("target", "player"), raw.get("distance", 50))
    
    def _convert_trade(self, raw: Dict) -> Dict:
        result = start_trade(self.npc_id, raw.get("items", []))
        result["params"]["tip"] = raw.get("tip", 0)
        result["params"]["message"] = raw.get("message", "")
        return result
    
    def _convert_give_item(self, raw: Dict) -> Dict:
        return give_item(self.npc_id, raw.get("item", ""), raw.get("quantity", 1))
    
    def _convert_take_item(self, raw: Dict) -> Dict:
        return take_item(self.npc_id, raw.get("item", ""), raw.get("quantity", 1))
    
    def _convert_start_quest(self, raw: Dict) -> Dict:
        return start_quest(
            self.npc_id, 
            raw.get("quest_id", ""), 
            raw.get("title", ""), 
            raw.get("description", "")
        )
    
    def _convert_update_quest(self, raw: Dict) -> Dict:
        return update_quest(
            self.npc_id,
            raw.get("quest_id", ""),
            raw.get("stage", 1),
            raw.get("title", ""),
            raw.get("description", ""),
            raw.get("progress", 0.0),
            raw.get("rewards", [])
        )
    
    def _convert_complete_quest(self, raw: Dict) -> Dict:
        return complete_quest(self.npc_id, raw.get("quest_id", ""),raw.get("description", ""), raw.get("rewards", []))
    
    def _convert_give_gold(self, raw: Dict) -> Dict:
        return give_gold(self.npc_id, raw.get("amount", 0), raw.get("reason", ""))
    
    def _convert_error(self, raw: Dict) -> Dict:
        return error(raw.get("message", "Unknown error"), self.npc_id)
    # 决策主入口：玩家输入 → 意图判断 → 分类处理 → 工具调用 → 格式转换 → 游戏验证 → 返回结果
    def decide(self, prompt: str, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        决策入口（增强版）
        1. 注入 NPC 专有类别信息（供暗号匹配使用）
        2. 意图判断（含 Embedding 暗号匹配）
        3. 根据意图分类处理
        4. 转换为标准协议格式
        5. 验证动作合法性
        """
        player_message = state.get("player_message", "")
        
        # 注入 NPC 的 allowed_categories（供 CipherMatcher 过滤暗号范围）
        persona = self.profile.get("persona", {})
        allowed_categories = persona.get("allowed_categories", [])
        if allowed_categories:
            state["npc_allowed_categories"] = allowed_categories
        
        # 初始化意图处理器（延迟初始化，确保profile已设置）
        if self.intent_handler is None:
            self.intent_handler = IntentHandler(
                llm_client=self.llm_client,
                profile=self.profile,
                npc_id=self.npc_id
            )
        
        # 步骤1：意图判断（含 Embedding 向量暗号匹配）
        intent = self.intent_classifier.classify(player_message, state)
        print(f"[Intent] 玩家意图: {intent.value}, 消息: {player_message[:50] if player_message else 'N/A'}...")
        
        # 【关键修复】如果意图为 UNKNOWN（空消息），直接返回空动作
        if intent == PlayerIntent.UNKNOWN:
            print("[Intent] 消息为空，跳过处理")
            return ok([])
        
        # 步骤2：根据意图分类处理
        # CIPHER_DETECTED 直接调用 intent_handler.handle() 处理
        raw_tool_calls = self.intent_handler.handle(intent, player_message, state, prompt)
        
        # 后续流程保持不变
        raw_actions = self._handle_tool_calls(raw_tool_calls, state)
        protocol_actions = self._to_protocol(raw_actions)
        protocol_actions = self._validate_game_logic(protocol_actions, state)
        valid_actions = [a for a in protocol_actions if self._validate_action(a)]
        
        if not valid_actions:
            valid_actions = [npc_say(self.npc_id, "......", "neutral")]

        return ok(valid_actions)
    
    def _to_protocol(self, raw_actions: Union[List[Dict], Dict]) -> List[Dict]:
        """
        将原始动作转换为协议标准格式（使用注册表模式）
        """
        if isinstance(raw_actions, dict):
            raw_actions = [raw_actions]
        
        protocol_actions = []
        for raw in raw_actions:
            action_type = raw.get("type", "dialogue")
            converter = self._action_converters.get(action_type)
            
            if converter:
                converted = converter(raw)
                if action_type in ("give_gold", "update_quest", "complete_quest"):
                    print(f"[Protocol] 转换 {action_type}: raw={raw} -> protocol={converted}")
                protocol_actions.append(converted)
            else:
                print(f"[Protocol] 无转换器: {action_type}, 原样传递")
                protocol_actions.append(raw)
        
        return protocol_actions
    
    def _format_actions(self) -> str:
        """格式化动作定义为文本"""
        lines = []
        for action in self.actions:
            name = action.get("name", "unknown")
            desc = action.get("description", "")
            params = action.get("parameters", {})
            lines.append(f"- {name}: {desc} (参数: {list(params.keys())})")
        return "\n".join(lines) if lines else "无自定义动作"
    
    def _llm_decide(self, prompt: str, state: Dict[str, Any]) -> List[Dict]:
        """
        使用真实 LLM 进行决策（返回 tool call 格式 JSON）
        """
        import json
        import re

        if not self.llm_client:
            return self.mock_decision_provider.decide(prompt, state)

        player_message = state.get("player_message", "")
        event = state.get("event", "")

        # 获取工具定义（用于注入 prompt）
        tool_schemas = self.tool_caller.get_tool_schemas() if self.tool_caller else []
        tools_desc = json.dumps(tool_schemas, ensure_ascii=False, indent=2) if tool_schemas else self._format_actions()

        # 强制 LLM 输出 tool call 格式
        system_prompt = f"""你是NPC决策系统。

【重要规则】
1. 必须通过调用工具完成行为，不要直接生成动作
2. 只能返回 JSON 数组，不要有任何其他解释文字
3. 每个工具调用格式：{{"tool": "工具名", "arguments": {{...}}}}
4. give_item 仅用于暗号匹配场景（由系统自动触发，你不需要手动调用）
5. take_item 用于收取玩家物品（如任务提交时收走材料）
6. start_trade 用于接受玩家售卖请求，开启交易面板
7. 你不能决定奖励内容，只能决定调用哪个工具
8. 涉及任务完成时，请合理判断玩家是否已完成任务
9. 如果你收到了系统注入的暗号匹配结果，直接按指示执行对应的工具调用，不要再做其他判断

【可用工具列表】
{tools_desc}

【返回格式示例】
[
  {{"tool": "dialogue", "arguments": {{"message": "你好旅行者", "emotion": "happy"}}}}
]
"""

        user_input = f"事件: {event}\n玩家说: {player_message}\n\n上下文:\n{prompt}"

        response = ""
        try:
            response = self.llm_client.generate_response(
                system_prompt=system_prompt,
                history=[],
                user_input=user_input
            )

            # 尝试从 markdown 代码块中提取 JSON
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
            if json_match:
                response = json_match.group(1)

            # 尝试直接解析
            tool_calls = json.loads(response.strip())
            if isinstance(tool_calls, dict):
                tool_calls = [tool_calls]

            return tool_calls

        except Exception as e:
            print(f"LLM 解析失败: {e}")
            print(f"LLM 响应内容: {response}")
            return [{"tool": "dialogue", "arguments": {"message": "……", "emotion": "neutral"}}]

    def _handle_tool_calls(self, tool_calls: List[Dict], state: Dict[str, Any]) -> List[Dict]:
        """
        处理工具调用：通过 ToolCaller 执行，获取标准 Action
        支持多 action 返回（如 complete_quest 返回 take_item + give_item）
        """
        if not tool_calls:
            return []

        raw_actions = []

        for call in tool_calls:
            tool_name = call.get("tool", "")
            args = call.get("arguments", {})

            # 强制执行 schema 约束（二次约束 LLM 输出）
            args = self._enforce_constraints(tool_name, args)

            if self.tool_caller and tool_name in self.tool_caller.tools:
                result = self.tool_caller.call(tool_name, args, state)

                if result.get("success"):
                    action = result["action"]
                    print(f"[ToolExec] {tool_name} 执行成功 -> action类型: {action.get('type') if isinstance(action, dict) else type(action).__name__}")

                    # ✅ 支持多 action（关键）
                    if isinstance(action, list):
                        raw_actions.extend(action)
                    else:
                        raw_actions.append(action)
                else:
                    print(f"[ToolExec] {tool_name} 执行失败: {result.get('error', 'tool error')}")
                    raw_actions.append({
                        "type": "error",
                        "message": result.get("error", "tool error")
                    })
            else:
                print(f"[ToolExec] 未知工具: {tool_name}, tool_caller存在={self.tool_caller is not None}, 在tools中={tool_name in self.tool_caller.tools if self.tool_caller else 'N/A'}")
                raw_actions.append({
                    "type": "error",
                    "message": f"Unknown tool: {tool_name}"
                })

        return raw_actions

    def _validate_action(self, action: Dict[str, Any]) -> bool:
        """验证动作是否合法"""
        if not action:
            return False
        
        action_type = action.get("type")
        if not action_type:
            return False
        
        # 检查是否为标准协议动作
        valid_types = {
            ActionType.NPC_SAY, ActionType.NPC_EMOTE,
            ActionType.MOVE_TO, ActionType.NPC_STOP, ActionType.FOLLOW,
            ActionType.START_TRADE, ActionType.GIVE_ITEM, ActionType.TAKE_ITEM,
            ActionType.START_QUEST, ActionType.UPDATE_QUEST, ActionType.COMPLETE_QUEST,
            ActionType.GIVE_GOLD,
            ActionType.ERROR, ActionType.CONFIG_UPDATE
        }
        
        if action_type in valid_types:
            return True
        
        # 检查是否为已注册动作
        if action_type in self.action_registry:
            return True
        
        # 检查是否为配置中定义的自定义动作
        for defined in self.actions:
            if defined.get("name") == action_type:
                return True
        
        return False

    def _get_allowed_items(self, action_name: str) -> List[str]:
        """
        从 schema 中读取允许的 item 枚举值
        支持新格式（dict 带 enum）和旧格式（字符串）
        """
        for action in self.actions:
            if action.get("name") == action_name:
                params = action.get("parameters", {})
                item_def = params.get("item", {})

                # 新格式：dict 带 enum
                if isinstance(item_def, dict):
                    return item_def.get("enum", [])

                # 兼容旧格式（字符串）
                if isinstance(item_def, str):
                    return [item_def] if item_def else []

        return []

    def _get_param_schema(self, action_name: str, param_name: str) -> Dict[str, Any]:
        """
        获取指定动作的指定参数的 schema 定义
        用于读取 min / max / enum 等约束
        """
        for action in self.actions:
            if action.get("name") == action_name:
                params = action.get("parameters", {})
                val = params.get(param_name)

                if isinstance(val, dict):
                    return val

        return {}

    def _enforce_constraints(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用 schema 强约束 LLM 输出
        确保 item 在允许范围内，quantity 在 min/max 范围内
        """
        # give_item / take_item 的 item 约束
        if tool_name in ("give_item", "take_item"):
            allowed_items = self._get_allowed_items(tool_name)

            if allowed_items:
                if args.get("item") not in allowed_items:
                    args["item"] = allowed_items[0]

            # 数量限制
            quantity_def = self._get_param_schema(tool_name, "quantity")
            if quantity_def:
                min_q = quantity_def.get("min", 1)
                max_q = quantity_def.get("max", 99)
                qty = int(args.get("quantity", min_q))
                args["quantity"] = max(min_q, min(qty, max_q))

        return args

    def _validate_game_logic(self, actions: List[Dict], state: Dict[str, Any]) -> List[Dict]:
        """
        游戏逻辑验证（后验证模式）
        在 LLM 生成动作后，根据真实游戏状态验证并修正
        """
        validated = []

        inventory = state.get("player_inventory", [])
        quests = state.get("player_quests", [])

        for action in actions:
            action_type = action.get("type")

            # ===== 任务完成校验 =====
            if action_type == "COMPLETE_QUEST":
                quest_id = action.get("params", {}).get("quest_id", "")
                print(f"[Validate] COMPLETE_QUEST 验证: quest_id={quest_id}")

                if self.quest_manager.is_multi_stage_quest(quest_id):
                    current_stage = self.quest_manager.get_current_stage(quest_id, quests)
                    quest = self.quest_manager.get_quest_by_id(quest_id)
                    total_stages = len(quest.get("stages", [])) if quest else 0
                    print(f"[Validate] 多阶段任务: current_stage={current_stage}, total_stages={total_stages}")
                    if current_stage < total_stages:
                        print(f"[Validate] 拒绝: 阶段未完成 ({current_stage} < {total_stages})")
                        validated.append({
                            "type": "NPC_SAY",
                            "params": {
                                "text": "你还没有完成任务要求呢。",
                                "emotion": "neutral"
                            }
                        })
                        continue
                    print(f"[Validate] 通过: 所有阶段已完成")
                elif not self.quest_manager.can_complete_quest(quest_id, inventory, quests):
                    print(f"[Validate] 拒绝: can_complete_quest返回False")
                    validated.append({
                        "type": "NPC_SAY",
                        "params": {
                            "text": "你还没有完成任务要求呢。",
                            "emotion": "neutral"
                        }
                    })
                    continue
                else:
                    print(f"[Validate] 通过: can_complete_quest返回True")

            validated.append(action)

        return validated

    def _can_complete_quest(self, quest_id: str, inventory: list, quests: list) -> bool:
        """任务完成验证，委托给 QuestManager"""
        return self.quest_manager.can_complete_quest(quest_id, inventory, quests)
