"""
意图处理函数
根据意图类型执行不同的处理逻辑

【日常对话模块增强】
- 短期记忆存取：通过 ShortTermMemoryDB 存储/读取对话历史
- 性格化回复：通过 PersonalityResponse 生成符合人设的回复
- 历史上下文：将最近3轮对话注入到 LLM prompt 中
"""
import json
from typing import Dict, Any, List, Optional

from src.decision.intent_types import PlayerIntent
from src.memory.short_term_db import ShortTermMemoryDB, get_short_term_db
from src.utils.personality import PersonalityResponse, create_personality_response
from src.logic.quest_manager import QuestManager


class IntentHandler:
    """
    意图处理器
    根据意图类型调用相应的处理逻辑
    
    【日常对话处理流程】
    1. 识别为 CASUAL_CHAT 意图
    2. 获取玩家 ID 和 NPC ID
    3. 保存玩家发言到短期记忆
    4. 获取最近3轮对话历史作为上下文
    5. 使用性格回复生成器生成回复
    6. 保存 NPC 回复到短期记忆
    7. 返回 dialogue 工具调用
    """
    
    def __init__(self, llm_client: Optional[Any] = None, profile: Dict[str, Any] = None, npc_id: str = "default"): # type: ignore
        self.llm_client = llm_client
        self.profile = profile or {}
        self.npc_id = npc_id
        
        # 初始化短期记忆数据库（延迟初始化）
        self._short_term_db: Optional[ShortTermMemoryDB] = None
        
        # 初始化性格回复生成器（延迟初始化）
        self._personality_response: Optional[PersonalityResponse] = None

        # 任务管理器
        self.quest_manager = QuestManager()
        self.quest_manager.set_quests(self.profile.get("quests", []))
    
    @property
    def short_term_db(self) -> ShortTermMemoryDB:
        """延迟初始化短期记忆数据库"""
        if self._short_term_db is None:
            self._short_term_db = get_short_term_db()
        return self._short_term_db
    
    @property
    def personality_response(self) -> PersonalityResponse:
        """延迟初始化性格回复生成器"""
        if self._personality_response is None:
            self._personality_response = create_personality_response(self.profile)
        return self._personality_response
    
    def set_profile(self, profile: Dict[str, Any]):
        """设置/更新 NPC 配置（热更新）"""
        self.profile = profile or {}
        # 重置性格回复生成器
        self._personality_response = create_personality_response(self.profile)
        # 更新任务管理器
        self.quest_manager.set_quests(self.profile.get("quests", []))
    
    def set_npc_id(self, npc_id: str):
        """设置 NPC ID"""
        self.npc_id = npc_id
    
    def handle(
        self, 
        intent: PlayerIntent, 
        player_message: str, 
        state: Dict[str, Any],
        base_prompt: str
    ) -> List[Dict[str, Any]]:
        """
        根据意图类型执行不同的处理逻辑
        
        Args:
            intent: 判断出的意图类型
            player_message: 玩家原始消息
            state: 游戏状态
            base_prompt: 基础Prompt
        
        Returns:
            List[Dict]: 工具调用列表
        """
        # ============================================================
        # 【关键修复】所有意图都统一保存对话到数据库
        # ============================================================
        player_id = state.get('player_id', 'default_player')
        
        # 1. 保存玩家发言
        self.short_term_db.save_player_message(
            npc_id=self.npc_id,
            player_id=player_id,
            message=player_message
        )
        
        # 2. 根据意图类型调用处理方法
        tool_calls = []
        npc_response = ""
        
        if intent == PlayerIntent.CASUAL_CHAT:
            tool_calls = self._handle_casual_chat(player_message, state, base_prompt)
            # 从返回值提取 NPC 回复
            for call in tool_calls:
                if call.get("tool") == "dialogue":
                    npc_response = call.get("arguments", {}).get("message", "")
                    break
        
        elif intent == PlayerIntent.GAME_INFO_REQUEST:
            tool_calls = self._handle_game_info_request(player_message, state, base_prompt)
            # 从返回值提取 NPC 回复
            for call in tool_calls:
                if call.get("tool") == "dialogue":
                    npc_response = call.get("arguments", {}).get("message", "")
                    break
        
        elif intent == PlayerIntent.QUEST_RELATED:
            tool_calls = self._handle_quest_related(player_message, state, base_prompt)
            # 从返回值提取 NPC 回复
            for call in tool_calls:
                if call.get("tool") == "dialogue":
                    npc_response = call.get("arguments", {}).get("message", "")
                    break
        
        elif intent == PlayerIntent.TRADE_RELATED:
            tool_calls = self._handle_trade_related(player_message, state, base_prompt)
            # 从返回值提取 NPC 回复
            for call in tool_calls:
                if call.get("tool") == "dialogue":
                    npc_response = call.get("arguments", {}).get("message", "")
                    break
        
        elif intent == PlayerIntent.CIPHER_DETECTED:
            tool_calls = self._handle_cipher_detected(player_message, state, base_prompt)
            # 从返回值提取 NPC 回复
            for call in tool_calls:
                if call.get("tool") == "dialogue":
                    npc_response = call.get("arguments", {}).get("message", "")
                    break
        
        else:
            tool_calls = self._handle_default(player_message, state, base_prompt)
            # 从返回值提取 NPC 回复
            for call in tool_calls:
                if call.get("tool") == "dialogue":
                    npc_response = call.get("arguments", {}).get("message", "")
                    break
        
        # 3. 保存 NPC 回复
        if npc_response:
            self.short_term_db.save_npc_response(
                npc_id=self.npc_id,
                player_id=player_id,
                response=npc_response
            )
        
        return tool_calls
    
    def _handle_casual_chat(self, player_message: str, state: Dict[str, Any], base_prompt: str) -> List[Dict]:
        """
        处理日常交流意图
        
        【注意】对话保存已移至 handle() 方法统一处理
        
        Returns:
            List[Dict]: 包含 dialogue 工具调用的列表
        """
        # 获取玩家标识（用于获取历史上下文）
        player_id = state.get('player_id', 'default_player')
        
        # === 获取历史对话上下文 ===
        recent_chats = self.short_term_db.get_recent_chats(
            npc_id=self.npc_id,
            player_id=player_id,
            limit=3
        )
        history_context = self._format_history_context(recent_chats)
        
        # === 生成 NPC 回复 ===
        reply_result = self._generate_casual_reply(
            player_message=player_message,
            history_context=history_context,
            state=state
        )
        
        npc_response = reply_result.get('message', '……')
        emotion = reply_result.get('emotion', 'neutral')
        
        # === 返回 dialogue 工具调用 ===
        return [
            {
                "tool": "dialogue",
                "arguments": {
                    "message": npc_response,
                    "emotion": emotion
                }
            }
        ]
    
    def _generate_casual_reply(self, player_message: str, 
                                history_context: str,
                                state: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成日常对话回复
        
        策略：
        1. 有 LLM 时，使用 LLM 生成性格化回复
        2. 无 LLM 时，使用 PersonalityResponse 的预设库
        
        Returns:
            {"message": str, "emotion": str}
        """
        # 使用性格回复生成器
        personality = self.personality_response
        
        if self.llm_client:
            # === 在线模式：使用 LLM 生成回复 ===
            system_prompt = personality.get_llm_system_prompt(history_context)
            
            try:
                response = self.llm_client.generate_response(
                    system_prompt=system_prompt,
                    history=[],
                    user_input=f"玩家说：{player_message}\n\n请以 NPC 身份回复，保持性格人设。"
                )
                
                # 尝试解析回复
                import json
                import re
                
                # 尝试从 JSON 代码块中提取
                json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
                if json_match:
                    result = json.loads(json_match.group(1))
                    return {
                        "message": result.get('message', '……'),
                        "emotion": result.get('emotion', 'neutral')
                    }
                
                # 尝试直接解析 JSON
                json_match = re.search(r'\{[\s\S]*\}', response)
                if json_match:
                    result = json.loads(json_match.group())
                    return {
                        "message": result.get('message', response),
                        "emotion": result.get('emotion', 'neutral')
                    }
                
                # 如果解析失败，将整个响应作为消息返回
                return {
                    "message": response.strip() if response else '……',
                    "emotion": personality._detect_emotion(player_message)
                }
                
            except Exception as e:
                print(f"[IntentHandler] LLM 生成回复失败: {e}")
                # 回退到离线模式
                return personality.generate_casual_reply(player_message, history_context)
        else:
            # === 离线模式：使用预设库 ===
            return personality.generate_casual_reply(player_message, history_context)
    
    def _format_history_context(self, recent_chats: List[Dict]) -> str:
        """
        格式化历史对话为上下文字符串
        
        用于注入到 LLM prompt 中
        
        Args:
            recent_chats: 最近对话列表
        
        Returns:
            格式化后的上下文字符串
        """
        if not recent_chats:
            return "（暂无历史对话）"
        
        lines = []
        for chat in recent_chats:
            round_num = chat.get('round', '?')
            player_msg = chat.get('player_message', '')
            npc_resp = chat.get('npc_response', '')
            
            lines.append(f"第 {round_num} 轮 - 玩家：{player_msg}")
            if npc_resp:
                lines.append(f"         NPC：{npc_resp}")
        
        return "\n".join(lines)
    
    def _handle_game_info_request(self, player_message: str, state: Dict[str, Any], base_prompt: str) -> List[Dict]:
        """
        【待实现】处理游戏信息获取意图
        
        建议实现：
        - 检索知识库（RAG）获取相关信息
        - 结合NPC人设组织答案
        - 如果信息不足，可以回答"我不太清楚"或引导玩家
        """
        # 从profile中获取知识
        knowledge = self._retrieve_knowledge(player_message)
        
        enhanced_prompt = f"""{base_prompt}

【当前场景】玩家正在询问游戏相关信息。
【玩家问题】{player_message}
【可参考资料】{knowledge}

请基于上述资料，以NPC的身份回答玩家的问题。如果资料不足，请委婉表示不清楚，不要编造信息。"""
        
        return self._call_llm_for_tools(enhanced_prompt, state)
    
    def _handle_quest_related(self, player_message: str, state: Dict[str, Any], base_prompt: str) -> List[Dict]:
        """
        处理任务相关意图，委托给 QuestManager 进行任务查询
        """
        ready_ids = set(state.get("quest_ready_to_complete_ids", []))
        active_ids = set(state.get("quest_active_ids", []))
        completed_ids = set(state.get("quest_completed_ids", []))
        player_quests = state.get("player_quests", [])

        ready_quest = self.quest_manager.find_ready_quest(ready_ids)
        available_quest = self.quest_manager.find_available_quest(active_ids, completed_ids)

        quest_context = ""
        if ready_quest:
            quest_context = f"玩家有已完成待交付的任务：{ready_quest.get('title', '')}，请引导玩家说「交任务」来交付"
        elif available_quest:
            quest_context = f"玩家可以接取新任务：{available_quest.get('title', '')}"
        elif active_ids and player_quests:
            # 玩家有活跃多阶段任务，提供当前阶段指引
            active_quest_id = list(active_ids)[0]
            active_quest = self.quest_manager.get_quest_by_id(active_quest_id)
            if active_quest and self.quest_manager.is_multi_stage_quest(active_quest_id):
                current_stage = self.quest_manager.get_current_stage(active_quest_id, player_quests)
                stage_hint = self.quest_manager.get_stage_hint(active_quest_id, current_stage)
                stages = active_quest.get("stages", [])
                total_stages = len(stages)

                # 获取当前阶段所需物品
                stage_item = ""
                stage_goal = ""
                stage_reward = 0
                for s in stages:
                    if s.get("stage") == current_stage:
                        stage_item = s.get("required_item", "")
                        stage_goal = s.get("goal", "")
                        stage_reward = s.get("reward_gold", 0)
                        break

                # 检查玩家背包中是否已有阶段物品
                has_stage_item = self.quest_manager.check_stage_item(
                    active_quest_id, current_stage, state.get("player_inventory", [])
                )

                submit_guidance = ""
                if has_stage_item:
                    submit_guidance = (
                        f"玩家背包中已有「{stage_item}」，请提示玩家可以说「提交{stage_item}」来交付，"
                        f"然后使用 TAKE_ITEM 收走物品，再用 UPDATE_QUEST 推进阶段。"
                    )

                quest_context = (
                    f"玩家正在进行任务「{active_quest.get('title', '')}」，"
                    f"当前阶段 {current_stage}/{total_stages}。"
                    f"目标：{stage_goal}，所需物品：{stage_item}。"
                    f"提示：{stage_hint}。"
                    f"完成当前阶段奖励：{stage_reward} 金币。"
                    f"{submit_guidance}"
                    f"如果是最后阶段，完成时请使用 COMPLETE_QUEST 验收全部任务并发放 rewards 中的奖励。"
                )

        enhanced_prompt = f"""{base_prompt}

【当前场景】玩家正在询问任务相关事宜。
【玩家消息】{player_message}
【任务状态】{quest_context}
【背包物品】{state.get('player_inventory', [])}

请根据任务状态，判断玩家是想接取任务、提交物品完成任务阶段，还是询问进度。如果玩家背包中已有阶段所需物品且表达了提交意愿，使用 TAKE_ITEM 收走物品后用 UPDATE_QUEST 推进阶段。如果是最后阶段完成，使用 COMPLETE_QUEST。"""

        tool_calls = self._call_llm_for_tools(enhanced_prompt, state)
        print(f"[QuestHandler] LLM返回 {len(tool_calls)} 个tool_calls")

        tool_calls = self._auto_advance_quest_stage(tool_calls, active_ids, player_quests, state)
        print(f"[QuestHandler] 自动推进后共 {len(tool_calls)} 个tool_calls")
        for i, tc in enumerate(tool_calls):
            print(f"[QuestHandler]   [{i}] tool={tc.get('tool')}")

        return tool_calls

    def _auto_advance_quest_stage(
        self, tool_calls: List[Dict], active_ids: set, player_quests: List[Any], state: Dict[str, Any]
    ) -> List[Dict]:
        """
        自动推进任务阶段 + 自动注入阶段奖励

        【入口条件】检测到任意任务推进动作（take_item / update_quest / complete_quest）
                    OR 玩家背包已有当前阶段物品时也会触发
        【自动补全】确保缺失的 take_item / give_gold / update_quest / complete_quest 都被注入

        解决三个问题：
        1. LLM 不可靠地忘记调用 UPDATE_QUEST
        2. LLM 直接生成 UPDATE_QUEST 而忘记 TAKE_ITEM，导致阶段奖励 give_gold 被跳过
        3. LLM 只生成 dialogue 而没有任何任务工具调用时，阶段奖励被完全跳过
        """
        print(f"[QuestAuto] === 进入自动推进检查 ===")
        print(f"[QuestAuto] tool_calls数量={len(tool_calls)}, active_ids={active_ids}, player_quests数量={len(player_quests)}")
        for i, tc in enumerate(tool_calls):
            print(f"[QuestAuto]   [{i}] tool={tc.get('tool')}, args={tc.get('arguments')}")

        # 前置校验：必须有活跃任务
        if not active_ids:
            print(f"[QuestAuto] 跳过: active_ids为空(玩家无活跃任务)")
            return tool_calls
        if not player_quests:
            print(f"[QuestAuto] 跳过: player_quests为空")
            return tool_calls

        active_quest_id = list(active_ids)[0]
        print(f"[QuestAuto] 活跃任务ID: {active_quest_id}")
        active_quest = self.quest_manager.get_quest_by_id(active_quest_id)
        if not active_quest:
            print(f"[QuestAuto] 跳过: 未找到任务定义 {active_quest_id}")
            return tool_calls
        if not self.quest_manager.is_multi_stage_quest(active_quest_id):
            print(f"[QuestAuto] 跳过: {active_quest_id} 非多阶段任务")
            return tool_calls

        current_stage = self.quest_manager.get_current_stage(active_quest_id, player_quests)
        stages = active_quest.get("stages", [])
        total_stages = len(stages)
        print(f"[QuestAuto] 当前阶段: {current_stage}/{total_stages}")

        # 查找当前阶段定义
        current_stage_def = None
        for s in stages:
            if s.get("stage") == current_stage:
                current_stage_def = s
                break

        # 【关键修复】检测玩家背包是否已有阶段物品
        has_stage_item_in_inventory = False
        if current_stage_def:
            has_stage_item_in_inventory = self.quest_manager.check_stage_item(
                active_quest_id, current_stage, state.get("player_inventory", [])
            )
        print(f"[QuestAuto] 玩家背包有阶段物品: {has_stage_item_in_inventory}")

        has_take_item = any(call.get("tool") == "take_item" for call in tool_calls)
        has_update_quest = any(call.get("tool") == "update_quest" for call in tool_calls)
        has_complete_quest = any(call.get("tool") == "complete_quest" for call in tool_calls)

        print(f"[QuestAuto] LLM已生成: take_item={has_take_item}, update_quest={has_update_quest}, complete_quest={has_complete_quest}")

        # 【关键修复】入口条件：有任务推进动作 OR 背包已有阶段物品
        if not (has_take_item or has_update_quest or has_complete_quest or has_stage_item_in_inventory):
            print(f"[QuestAuto] 跳过: 无任务推进动作且背包无阶段物品")
            return tool_calls

        if has_stage_item_in_inventory and not (has_take_item or has_update_quest or has_complete_quest):
            print(f"[QuestAuto] >>> 检测到背包有阶段物品但LLM未生成任务工具，自动注入 <<<")

        # ================================================================
        # 【核心修复1】自动补全缺失的 TAKE_ITEM（收走当前阶段所需物品）
        # LLM 可能直接生成 UPDATE_QUEST 而忘记 TAKE_ITEM，导致物品未被消耗
        # ================================================================
        if not has_take_item and current_stage_def:
            required_item = current_stage_def.get("required_item", "")
            if required_item:
                tool_calls.append({
                    "tool": "take_item",
                    "arguments": {
                        "item": required_item,
                        "quantity": 1
                    }
                })
                has_take_item = True
                print(f"[QuestAuto] >>> 注入TAKE_ITEM: {required_item} (LLM未生成) <<<")

        # ================================================================
        # 【核心修复2】自动补全阶段金币奖励
        # 无论 LLM 是否生成 give_gold，只要任务阶段有 reward_gold 配置就注入
        # ================================================================
        if current_stage_def:
            reward_gold = current_stage_def.get("reward_gold", 0)
            print(f"[QuestAuto] 阶段{current_stage}奖励金币配置: {reward_gold}")
            if reward_gold > 0:
                has_give_gold = any(call.get("tool") == "give_gold" for call in tool_calls)
                print(f"[QuestAuto] LLM已生成give_gold: {has_give_gold}")
                if not has_give_gold:
                    tool_calls.append({
                        "tool": "give_gold",
                        "arguments": {
                            "amount": reward_gold,
                            "reason": f"完成「{active_quest.get('title', '')}」阶段{current_stage}奖励"
                        }
                    })
                    print(f"[QuestAuto] >>> 注入GIVE_GOLD: {reward_gold}金币 <<<")
        else:
            print(f"[QuestAuto] 警告: 未找到阶段{current_stage}的定义!")

        # ================================================================
        # 【核心修复3】自动补全阶段推进动作
        # 如果 LLM 已经生成了 update_quest/complete_quest，不重复注入
        # 否则自动注入正确的阶段推进动作
        # ================================================================
        if has_update_quest or has_complete_quest:
            print(f"[QuestAuto] LLM已处理阶段推进，跳过注入UPDATE_QUEST/COMPLETE_QUEST")
        else:
            next_stage = current_stage + 1
            if next_stage <= total_stages:
                tool_calls.append({
                    "tool": "update_quest",
                    "arguments": {
                        "quest_id": active_quest_id,
                        "stage": next_stage
                    }
                })
                print(f"[QuestAuto] 自动推进任务 {active_quest_id}: 阶段 {current_stage} → {next_stage}")
            else:
                tool_calls.append({
                    "tool": "complete_quest",
                    "arguments": {
                        "quest_id": active_quest_id,
                        "rewards": active_quest.get("rewards", [])
                    }
                })
                print(f"[QuestAuto] 自动完成任务 {active_quest_id}: 所有阶段已完成")

        return tool_calls
    
    def _handle_default(self, player_message: str, state: Dict[str, Any], base_prompt: str) -> List[Dict]:
        """
        默认处理（兜底）
        """
        return self._call_llm_for_tools(base_prompt, state)
    
    def _handle_cipher_detected(self, player_message: str, state: Dict[str, Any], base_prompt: str) -> List[Dict]:
        """
        处理暗号匹配命中（Embedding 向量匹配）
        
        直接从 state._cipher_match_result 中读取匹配结果，
        生成标准工具调用（give_item 或 start_quest）。
        完全绕过 LLM，确保暗号行为的确定性。
        """
        cipher_result = state.get("_cipher_match_result")
        if not cipher_result:
            return [{"tool": "dialogue", "arguments": {"message": "……", "emotion": "neutral"}}]
        
        matched_cipher = cipher_result.get("matched_cipher", "")
        action = cipher_result.get("action", "give_item")
        item = cipher_result.get("item")
        quest_id = cipher_result.get("quest_id")
        reply = cipher_result.get("reply_template", "拿好。")
        
        print(f"[CipherHandler] 暗号匹配: 「{matched_cipher}」, 动作: {action}, 物品: {item}")
        
        tool_calls = []
        
        # NPC 先说预设回复
        tool_calls.append({
            "tool": "dialogue",
            "arguments": {
                "message": reply,
                "emotion": "satisfied"
            }
        })
        
        # 根据动作类型生成工具调用
        if action == "give_item" and item:
            tool_calls.append({
                "tool": "give_item",
                "arguments": {
                    "item": item,
                    "quantity": 1
                }
            })
        elif action == "start_quest" and quest_id:
            # 查找任务定义获取完整信息
            quest = self.quest_manager.get_quest_by_id(quest_id)
            title = quest.get("title", quest_id) if quest else quest_id
            description = quest.get("description", "") if quest else ""
            tool_calls.append({
                "tool": "start_quest",
                "arguments": {
                    "quest_id": quest_id,
                    "title": title,
                    "description": description
                }
            })

            # 如果任务有阶段定义，自动追加第一阶段指引
            if quest and self.quest_manager.is_multi_stage_quest(quest_id):
                stages = quest.get("stages", [])
                if stages:
                    first_stage = stages[0]
                    stage_hint = self.quest_manager.get_stage_hint(quest_id, 1)
                    stage_goal = first_stage.get("goal", "")
                    stage_item = first_stage.get("required_item", "")
                    guidance_msg = (
                        f"第一阶段目标：{stage_goal}——{stage_hint}。"
                        f"去找对应NPC说暗号拿到「{stage_item}」，拿回来我再给你下一阶段的提示。"
                    )
                    tool_calls.append({
                        "tool": "dialogue",
                        "arguments": {
                            "message": guidance_msg,
                            "emotion": "thinking"
                        }
                    })
        
        return tool_calls
    
    def _handle_trade_related(self, player_message: str, state: Dict[str, Any], base_prompt: str) -> List[Dict]:
        """
        处理交易相关意图

        流程：
        1. 从 state 获取可交易物资列表（前端 observe() 携带）
        2. 关键词精确匹配 → LLM 语义匹配，找到玩家要卖的物品
        3. 结合 NPC persona 让 LLM 判断是否接受交易
        4. 接受 → start_trade 工具调用（物品信息+tip）
        5. 拒绝 → dialogue 工具调用（拒绝话术）
        """
        tradeable_items = state.get("tradeable_items", [])

        if not tradeable_items:
            return [{
                "tool": "dialogue",
                "arguments": {
                    "message": "抱歉，我现在没有在收东西呢...",
                    "emotion": "neutral"
                }
            }]

        # 匹配玩家要交易的物品
        matched_item = self._match_trade_item_vector(player_message, tradeable_items)

        if not matched_item:
            # 匹配失败，礼貌询问
            return [{
                "tool": "dialogue",
                "arguments": {
                    "message": "你想卖什么？我没太听明白…",
                    "emotion": "confused"
                }
            }]

        # 确保物品有必需的字段（防御性保护）
        if not matched_item.get("name"):
            matched_item["name"] = ""
        if not matched_item.get("type"):
            matched_item["type"] = "food"
        if not isinstance(matched_item.get("sellPrice"), (int, float)):
            matched_item["sellPrice"] = 0

        # 获取 NPC persona 核心信息
        persona = self.profile.get("persona", {})
        identity = persona.get("identity", "")
        speaking_style = persona.get("speaking_style", "casual")

        # 检查玩家是否实际拥有该物品
        player_inventory = state.get("player_inventory", [])
        owned_count = 0
        matched_name = matched_item.get("name", "")
        for inv_item in player_inventory:
            if isinstance(inv_item, dict):
                inv_name = inv_item.get("id") or inv_item.get("item_id", "")
                if inv_name == matched_name:
                    owned_count = inv_item.get("count", 0)
                    break

        # 构造完整的安全物品数据（确保字段齐全）
        safe_item = {
            "name": matched_item.get("name", ""),
            "sellPrice": matched_item.get("sellPrice", 0),
            "type": matched_item.get("type", "food")
        }
        print(f"[TradeHandler] safe_item: {json.dumps(safe_item, ensure_ascii=False)}, owned_count={owned_count}")

        # 玩家没有该物品 → 引导购买
        if owned_count <= 0:
            return [{
                "tool": "dialogue",
                "arguments": {
                    "message": f"你想买这个吗？可以去商店看看哦~",
                    "emotion": "neutral"
                }
            }]

        # 【核心重构】物品数据 100% 由代码控制，LLM 只负责生成 NPC 对话
        # 不再让 LLM 构造 start_trade（避免 items 格式错乱、tip 填文字等问题）
        tool_calls = []
        
        # LLM 只生成接受交易的对话文本
        dialogue_prompt = f"""{base_prompt}

【当前场景】玩家要出售「{matched_name}」（售价{safe_item['sellPrice']}金币）给NPC。
【玩家消息】{player_message}
【NPC身份】{identity}
【说话风格】{speaking_style}

请以NPC的身份，用一句符合人设的话接受这笔交易。（仅返回dialogue工具调用）"""
        
        llm_tool_calls = self._call_llm_for_tools(dialogue_prompt, state)
        tool_calls.extend(llm_tool_calls)

        # 直接构建 start_trade —— 完全确定性，不受 LLM 影响
        tool_calls.append({
            "tool": "start_trade",
            "arguments": {
                "items": [safe_item],
                "tip": 0,
                "message": ""
            }
        })
        print(f"[TradeHandler] 直接构建 start_trade items: {json.dumps([safe_item], ensure_ascii=False)}")

        return tool_calls

    def _match_trade_item_vector(self, player_message: str, tradeable_items: List[Dict]) -> Optional[Dict]:
        """
        从玩家消息中识别交易物品

        两层策略（纯交易系统，不依赖暗号匹配引擎）：
        1. 关键词精确匹配（快速路径，0延迟）
        2. LLM 语义匹配（准确路径）
        """
        if not tradeable_items:
            return None

        # 策略1：精确关键词匹配
        for item in tradeable_items:
            item_name = item.get("name", "")
            if item_name and item_name in player_message:
                print(f"[TradeMatch] 关键词精确匹配: {item_name}")
                return item

        # 策略2：LLM 语义匹配
        return self._match_trade_item_llm(player_message, tradeable_items)

    def _match_trade_item_llm(self, player_message: str, tradeable_items: List[Dict]) -> Optional[Dict]:
        """
        LLM 回退匹配（当向量匹配不可用时）
        """
        if not self.llm_client or len(tradeable_items) == 0:
            return None

        try:
            items_desc = "\n".join([
                f"- {item.get('name', '')} (类型: {item.get('type', '')}, 售价: {item.get('sellPrice', 0)}金币)"
                for item in tradeable_items
            ])

            response = self.llm_client.generate_response(
                system_prompt=f"""你是商品匹配器。根据玩家的话，从可交易物资列表中找出玩家想卖的物品。
只返回匹配到的物品名称（完全匹配列表中的名称），如果匹配不到返回 NONE。

可交易物资：
{items_desc}""",
                history=[],
                user_input=f"玩家说：{player_message}"
            )

            matched_name = response.strip().strip('"').strip("'")
            for item in tradeable_items:
                if item.get("name", "") == matched_name:
                    return item
        except Exception as e:
            print(f"[TradeMatch] LLM匹配失败: {e}")

        return None
    
    def _call_llm_for_tools(self, prompt: str, state: Dict[str, Any]) -> List[Dict]:
        """
        调用LLM生成工具调用
        
        返回格式：工具调用列表
        """
        import json
        import re
        
        if not self.llm_client:
            # 离线模式返回默认对话
            return [{"tool": "dialogue", "arguments": {"message": "……", "emotion": "neutral"}}]
        
        player_message = state.get("player_message", "")
        event = state.get("event", "")
        
        system_prompt = f"""你是NPC决策系统。

【重要规则】
1. 必须通过调用工具完成行为，不要直接生成动作
2. 只能返回 JSON 数组，不要有任何其他解释文字
3. 每个工具调用格式：{{"tool": "工具名", "arguments": {{...}}}}
4. give_item 仅由系统在暗号匹配时自动调用，你不需要调用
5. take_item 用于收取玩家物品（如任务提交时收走材料时使用）
6. start_trade 用于接受玩家售卖请求，开启交易面板（参数: items, tip, message）
7. update_quest 用于推进任务到下一阶段（参数: quest_id, stage）
8. complete_quest 用于整个任务完成时发放最终奖励
9. 任务阶段推进流程：玩家提交材料 → TAKE_ITEM 收走 → UPDATE_QUEST 推进阶段
10. 最后阶段完成时才使用 COMPLETE_QUEST（而不是每个阶段完成都用）
11. 每个阶段完成后在对话中提示下一阶段目标和暗号，鼓励玩家继续

【可用工具】
- dialogue: 让NPC说一段话 (参数: message, emotion)
- emote: 让NPC做出表情动作 (参数: emotion, duration)
- start_quest: 给玩家发布一个新任务 (参数: quest_id, title, description)
- start_trade: 发起交易，NPC接受玩家售卖请求 (参数: items, tip, message)
- update_quest: 推进任务到下一阶段 (参数: quest_id, stage)
- complete_quest: 验收玩家任务并发放奖励 (参数: quest_id, rewards)
- take_item: 从玩家背包收取物品 (参数: item, quantity)
- move_to: 让NPC移动到指定位置 (参数: target, speed)

【返回格式示例】
[
  {{"tool": "dialogue", "arguments": {{"message": "你好旅行者", "emotion": "happy"}}}},
  {{"tool": "emote", "arguments": {{"emotion": "wave", "duration": 1000}}}}
]
"""

        user_input = f"事件: {event}\n玩家说: {player_message}\n\n上下文:\n{prompt}"
        
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
            print(f"[Intent Handler] LLM调用失败: {e}")
            return [{"tool": "dialogue", "arguments": {"message": "……", "emotion": "neutral"}}]
    
    def _retrieve_knowledge(self, query: str) -> str:
        """
        从知识库检索相关信息
        
        简化实现：从profile中获取知识
        TODO: 后续接入RAG引擎
        """
        knowledge = self.profile.get("knowledge", {})
        topics = knowledge.get("topics", [])
        facts = knowledge.get("world_facts", [])
        
        # 简单关键词匹配
        relevant_facts = []
        query_lower = query.lower()
        
        for fact in facts:
            if any(word in query_lower for word in fact.lower().split()):
                relevant_facts.append(fact)
        
        if topics:
            relevant_facts.append(f"擅长话题：{'、'.join(topics[:5])}")
        
        return "\n".join(relevant_facts) if relevant_facts else "暂无相关资料"
