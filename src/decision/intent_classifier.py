"""
意图分类器
负责判断玩家对话的意图类型

增强版：集成 Embedding 向量暗号匹配（CIPHER_DETECTED）
"""
from typing import Dict, Any, Optional
from src.decision.intent_types import PlayerIntent


class IntentClassifier:
    """
    意图分类器
    
    使用规则+LLM混合策略进行意图分类：
    1. 优先使用规则匹配（快速、确定性强）
    2. Embedding 向量匹配暗号（新增）
    3. 规则无法确定时，使用LLM分类（智能、准确）
    """
    
    def __init__(self, llm_client: Optional[Any] = None):
        self.llm_client = llm_client
        self._cipher_matcher = None  # 延迟加载
    
    @property
    def cipher_matcher(self):
        """延迟加载 CipherMatcher（避免循环导入 & 提前加载模型）"""
        if self._cipher_matcher is None:
            from src.knowledge.cipher_matcher import get_cipher_matcher
            self._cipher_matcher = get_cipher_matcher()
        return self._cipher_matcher
    
    def classify(self, player_message: str, state: Dict[str, Any]) -> PlayerIntent:
        """
        判断玩家对话意图
        
        Args:
            player_message: 玩家输入的消息
            state: 当前游戏状态（包含任务信息等）
        
        Returns:
            PlayerIntent: 意图类型枚举
        """
        if not player_message:
            return PlayerIntent.UNKNOWN
        
        # 策略1：基于关键词的快速规则判断（性能优先）
        intent = self._rule_based_detection(player_message)
        if intent != PlayerIntent.UNKNOWN:
            return intent
        
        # 策略1.5：状态感知的规则检测（多阶段任务物品提交场景）
        intent = self._state_aware_quest_detection(player_message, state)
        if intent != PlayerIntent.UNKNOWN:
            return intent
        
        # 策略2：Embedding 向量暗号匹配（新增）
        intent = self._cipher_detection(player_message, state)
        if intent != PlayerIntent.UNKNOWN:
            return intent
        
        # 策略3：使用LLM进行意图分类（准确性优先）
        if self.llm_client:
            return self._llm_classification(player_message, state)
        
        # 【关键修复】默认返回 UNKNOWN，而不是 CASUAL_CHAT
        return PlayerIntent.UNKNOWN
    
    def _state_aware_quest_detection(self, message: str, state: Dict[str, Any]) -> PlayerIntent:
        """
        状态感知的规则检测：多阶段任务物品提交场景
        
        问题场景：玩家说"给你玫瑰"给任务NPC，但关键词检测可能遗漏，
        LLM 也可能分类为 CASUAL_CHAT，导致阶段奖励永远不会触发。
        
        核心逻辑：
        - 如果玩家有活跃任务
        - 且消息中提到了背包中某个物品的名称
        → 很可能是在提交任务物品，判定为 QUEST_RELATED
        
        注意：不依赖 QuestManager（它需要加载 NPC 配置才有任务定义），
        直接从 state 中获取玩家数据判断。
        """
        try:
            active_ids = state.get("quest_active_ids", [])
            player_inventory = state.get("player_inventory", [])
            
            if not active_ids or not player_inventory:
                return PlayerIntent.UNKNOWN
            
            # 检查消息中是否提到了背包中任何物品的名称
            for inv_item in player_inventory:
                if isinstance(inv_item, dict):
                    item_name = inv_item.get("id") or inv_item.get("item_id", "")
                    if item_name and item_name in message:
                        print(f"[StateAware] 玩家提到背包物品「{item_name}」且有活跃任务，"
                              f"判定为QUEST_RELATED")
                        return PlayerIntent.QUEST_RELATED
            
        except Exception as e:
            print(f"[StateAware] 状态感知检测异常: {e}")
        
        return PlayerIntent.UNKNOWN

    def _cipher_detection(self, message: str, state: Dict[str, Any]) -> PlayerIntent:
        """
        使用 Embedding 向量匹配检测暗号（新增策略）
        
        从 state 中提取 NPC 的 allowed_categories 进行过滤匹配。
        """
        try:
            # 从 state 获取 NPC 的专有知识类别
            allowed_categories = state.get("npc_allowed_categories", None)
            
            # 如果不传类别，匹配全部暗号（兜底）
            result = self.cipher_matcher.match(message, allowed_categories)
            
            if result is not None:
                print(f"[CipherMatch] 命中暗号: {result['matched_cipher']} "
                      f"(相似度: {result['similarity']:.3f}, "
                      f"动作: {result['action']})")
                # 将匹配结果存入 state 供后续处理器使用
                state["_cipher_match_result"] = result
                return PlayerIntent.CIPHER_DETECTED
            
        except Exception as e:
            print(f"[CipherMatch] 匹配异常: {e}")
        
        return PlayerIntent.UNKNOWN
    
    def _rule_based_detection(self, message: str) -> PlayerIntent:
        """
        基于规则的意图检测（快速路径）
        
        优点：无需调用LLM，响应速度快
        适用：明显的关键词匹配场景
        """
        if not message:
            return PlayerIntent.UNKNOWN
            
        lowered = message.lower()
        
        # 交易/售卖关键词
        trade_keywords = [
            "卖", "出售", "交易", "买吗", "要不要",
            "购买", "卖给你", "卖你", "收吗", "收不收",
            "换金币", "卖掉", "出手", "sell", "trade"
        ]
        for kw in trade_keywords:
            if kw in lowered:
                return PlayerIntent.TRADE_RELATED
        
        # 任务相关关键词（含"给你"模式——玩家提交任务物品时常用）
        quest_keywords = [
            "任务", "quest", "帮忙", "help", "完成", "finish", 
            "提交", "交付", "奖励", "reward", "进度", "progress",
            "交任务", "接任务", "quest", "给你", "拿来了", "带来了",
            "拿到了", "找到了", "做好了", "搞定了"
        ]
        for kw in quest_keywords:
            if kw in lowered:
                return PlayerIntent.QUEST_RELATED
        
        # 游戏信息关键词
        info_keywords = [
            "怎么", "how", "哪里", "where", "什么", "what", 
            "为什么", "why", "介绍", "about", "背景", "故事",
            "村子", "village", "世界", "world", "游戏", "game",
            "如何", "怎样", "在哪"
        ]
        for kw in info_keywords:
            if kw in lowered:
                return PlayerIntent.GAME_INFO_REQUEST
        
        # 日常问候关键词
        chat_keywords = [
            "你好", "hello", "hi", "hey", "再见", "bye", 
            "谢谢", "thanks", "早上好", "晚上好", "good morning",
            "吃了吗", "天气", "最近", "怎么样"
        ]
        for kw in chat_keywords:
            if kw in lowered:
                return PlayerIntent.CASUAL_CHAT
        
        return PlayerIntent.UNKNOWN
    
    def _llm_classification(self, message: str, state: Dict[str, Any]) -> PlayerIntent:
        """
        使用LLM进行意图分类（精确路径）
        
        当规则无法确定时，调用LLM进行智能分类
        """
        system_prompt = """你是一个意图分类器。请分析玩家的输入，将其归类为以下五类之一：

1. CASUAL_CHAT - 日常交流：问候、闲聊、情感交流、无关紧要的对话
2. GAME_INFO_REQUEST - 游戏信息获取：询问游戏机制、世界观、NPC背景故事、地点等
3. QUEST_RELATED - 任务逻辑相关：任务接取、任务完成、询问任务进度、交付物品
4. TRADE_RELATED - 交易售卖相关：玩家想卖东西给NPC、询问NPC是否购买物品
5. CIPHER_DETECTED - 暗号匹配：怀疑触发了隐藏暗号（但需进一步验证）

只返回意图类型，不要有任何其他解释。格式：CASUAL_CHAT 或 GAME_INFO_REQUEST 或 QUEST_RELATED 或 TRADE_RELATED 或 CIPHER_DETECTED"""

        try:
            response = self.llm_client.generate_response( # type: ignore
                system_prompt=system_prompt,
                history=[],
                user_input=f"玩家说：{message}"
            )
            
            response_upper = response.strip().upper()
            
            if "TRADE" in response_upper:
                return PlayerIntent.TRADE_RELATED
            elif "CIPHER" in response_upper or "DETECT" in response_upper:
                return PlayerIntent.CIPHER_DETECTED
            elif "QUEST" in response_upper:
                return PlayerIntent.QUEST_RELATED
            elif "INFO" in response_upper or "GAME" in response_upper:
                return PlayerIntent.GAME_INFO_REQUEST
            elif "CASUAL" in response_upper or "CHAT" in response_upper:
                return PlayerIntent.CASUAL_CHAT
                
        except Exception as e:
            print(f"[Intent Classification Error] {e}")
        
        return PlayerIntent.CASUAL_CHAT  # 默认兜底
