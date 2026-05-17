"""
Adaptive NPC Framework - 核心框架
提供统一的 NPC 管理接口

设计原则：
- 不涉及 Web 协议（HTTP/WebSocket）
- 纯业务逻辑，可独立测试
- 可被任何应用导入使用
"""
from typing import Dict, Any, Optional, List

from src.communication.dialogue_manager import DialogueManager
from src.decision.engine import DecisionEngine
from src.config.loader import ConfigLoader
from src.knowledge.rag_engine import RAGEngine
from src.logic.state_tracker import StateTracker
from src.memory.manager import MemoryManager
from src.server.runtime.config_schema import normalize_agent_config
from src.utils.llm_client import LLMClient


class AdaptiveNPCFramework:
    """
    智能 NPC 框架核心类
    
    架构：
    1. ConfigLoader - 配置加载
    2. DialogueManager - 对话/人设管理
    3. DecisionEngine - LLM 决策引擎
    4. MemoryManager - 分层记忆管理（短期+长期+RAG）
    5. StateTracker - 状态追踪
    
    使用示例：
    ```python
    from src.server.framework import AdaptiveNPCFramework
    
    framework = AdaptiveNPCFramework()
    
    # 初始化 NPC
    config = {
        "id": "village_chief",
        "name": "老村长",
        "personality": "慈祥但固执",
        "sensors": ["player_inventory"],
        "actions": [{"name": "dialogue", ...}]
    }
    framework.init_agent("village_chief", config)
    
    # 处理游戏状态
    state = {
        "player_inventory": ["apple", "apple", "apple"],
        "distance_to_npc": 50
    }
    result = framework.run("village_chief", state)
    # 返回：{"type": "ACTIONS", "actions": [{"type": "NPC_SAY", "params": {...}}]}
    ```
    """
    
    def __init__(self):
        self.config_loader = ConfigLoader()
        self.agents: Dict[str, Dict[str, Any]] = {}
        self.dialogue_managers: Dict[str, DialogueManager] = {}
        self.decision_engines: Dict[str, DecisionEngine] = {}
        self.rag_engines: Dict[str, RAGEngine] = {}
        self.memory_managers: Dict[str, MemoryManager] = {}
        self.state_trackers: Dict[str, StateTracker] = {}
    
    def init_agent(self, agent_id: str, config: Dict[str, Any]):
        """
        初始化单个 NPC Agent
        
        配置结构：
        {
            "id": "npc_001",
            "name": "老村长",
            "personality": "慈祥但有点固执",
            "sensors": ["player_position", "player_inventory"],
            "actions": [
                {"name": "dialogue", "parameters": {...}},
                {"name": "give_item", "parameters": {...}}
            ],
            "memory": {"facts": []}
        }
        
        Args:
            agent_id: NPC 唯一标识符
            config: NPC 配置字典
        """
        config = normalize_agent_config(config)

        # 注入世界知识到 NPC 配置（暗号规则、物品映射等）
        persona = config.get("persona", {})
        world_id = persona.get("world_id", "")
        if world_id:
            world_knowledge = self.config_loader.load_world_knowledge(
                world_id,
                persona.get("allowed_categories", [])
            )
            if world_knowledge:
                # 将世界知识附加到 personality 文本
                current_personality = config.get("personality", "")
                config["personality"] = current_personality + "\n\n" + world_knowledge
                print(f"[Framework] World knowledge injected for {agent_id}")

        # 创建组件实例
        dialogue_manager = DialogueManager()
        # 接入真实 LLM（需在项目根目录 .env 文件中配置 ARK_API_KEY）
        llm_client = LLMClient({})
        decision_engine = DecisionEngine(llm_client=llm_client)
        
        # 配置组件
        personality = config.get("personality", "一个普通的 NPC")
        dialogue_manager.set_name(config.get("meta", {}).get("name", agent_id))
        dialogue_manager.set_greeting(config.get("persona", {}).get("greeting", ""))
        dialogue_manager.set_profile(config)
        dialogue_manager.set_personality(personality)

        # 转换新版 actions（字符串数组 → DecisionEngine 期望的对象数组）
        actions = self._normalize_actions(config.get("actions", []))
        decision_engine.set_actions(actions)
        decision_engine.set_profile(config)
        
        # 存储 agent 和组件
        self.agents[agent_id] = config
        self.dialogue_managers[agent_id] = dialogue_manager
        self.decision_engines[agent_id] = decision_engine
        
        # 记忆管理器（统一协调短期/长期/RAG 记忆）
        memory_mgr = MemoryManager(agent_id)
        self.memory_managers[agent_id] = memory_mgr
        
        # RAG 记忆引擎（如果配置了初始记忆数据）
        if "memory" in config:
            rag = RAGEngine()
            rag.load_memories(config["memory"])
            memory_mgr.init_rag(rag)
            self.rag_engines[agent_id] = rag  # 兼容保留
        
        # 状态追踪器
        self.state_trackers[agent_id] = StateTracker()
        
        print(f"[OK] Agent initialized: {agent_id}")
    
    def update_agent_config(self, agent_id: str, config: Dict[str, Any]):
        """
        热更新 NPC 配置（无需重启）
        
        Args:
            agent_id: NPC 唯一标识符
            config: 新的配置字典
        """
        config = normalize_agent_config(config)
        self.agents[agent_id] = config
        
        # 更新对话管理器
        if agent_id in self.dialogue_managers:
            personality = config.get("personality", "")
            self.dialogue_managers[agent_id].set_name(config.get("meta", {}).get("name", agent_id))
            self.dialogue_managers[agent_id].set_greeting(config.get("persona", {}).get("greeting", ""))
            self.dialogue_managers[agent_id].set_profile(config)
            self.dialogue_managers[agent_id].set_personality(personality)
        
        # 更新决策引擎
        if agent_id in self.decision_engines:
            actions = self._normalize_actions(config.get("actions", []))
            self.decision_engines[agent_id].set_actions(actions)
            self.decision_engines[agent_id].set_profile(config)
        
        print(f"[UPDATE] Agent config updated: {agent_id}")
    
    def run(self, agent_id: str, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        主处理流程
        
        流程：
        1. 感知阶段 - 根据 sensors 过滤环境数据
        2. 理解阶段 - 构建 Prompt，检索记忆
        3. 决策阶段 - LLM 决策（返回 Intent）
        4. 适配阶段 - Intent → 标准 Action
        
        Args:
            agent_id: NPC 唯一标识符
            state: 游戏状态（包含玩家位置、背包、天气等）
        
        Returns:
            标准 ACTIONS 消息，如：
            {"type": "ACTIONS", "actions": [{"type": "NPC_SAY", "params": {...}}]}
        """
        # 检查 agent 是否存在
        if agent_id not in self.agents:
            from src.protocol import fail
            return fail(f"Agent {agent_id} not found")
        
        config = self.agents[agent_id]
        
        # 1. 感知阶段 - 根据配置的 sensors 过滤状态数据
        sensors_config = config.get("sensors", {})
        sensors = self._normalize_sensors(sensors_config)
        filtered_state = self._filter_state(state, sensors)
        
        # 2. 状态追踪
        tracker = self.state_trackers.get(agent_id)
        if tracker:
            tracker.update(filtered_state)
        
        # 3. 检索相关记忆（通过 MemoryManager 统一获取）
        memory_context = ""
        if agent_id in self.memory_managers:
            memory_context = self.memory_managers[agent_id].get_context(
                filtered_state
            )
        
        # 4. 构建 Prompt
        dm = self.dialogue_managers[agent_id]
        dm.set_memory(memory_context)
        prompt = dm.build_prompt(filtered_state)
        
        # 5. LLM 决策（DecisionEngine 直接返回标准协议格式）
        de = self.decision_engines[agent_id]
        de.set_npc_id(agent_id)  # 确保使用正确的 NPC ID
        result = de.decide(prompt, filtered_state)
        
        # 直接返回标准 ACTIONS 消息
        return result
    
    def _filter_state(self, state: Dict[str, Any], sensors: list) -> Dict[str, Any]:
        """
        根据配置的 sensors 过滤状态数据
        
        这实现了"感知"机制：NPC 只能看到配置中允许的数据
        
        Args:
            state: 完整的游戏状态
            sensors: NPC 配置的感知器列表
        
        Returns:
            过滤后的状态
        """
        always_available = {
            "event",
            "player_message",
            "timestamp",
            "standard_state",
            "quest_active_ids",
            "quest_completed_ids",
            "quest_ready_to_complete_ids",
            "player_quests",
            "tradeable_items",
            "player_inventory",
        }

        if not sensors:
            return state

        filtered = {}
        for key in sensors:
            if key in state:
                filtered[key] = state[key]

        for key in always_available:
            if key in state:
                filtered[key] = state[key]

        return filtered

    def _normalize_actions(self, actions: List[Any]) -> List[Dict[str, Any]]:
        """
        转换新版 actions 格式（字符串数组 → DecisionEngine 期望的对象数组）

        新版格式：["GIVE_ITEM", "MOVE_TO", ...]
        旧版格式：[{"name": "dialogue", "parameters": {...}}, ...]
        """
        if not actions:
            return []

        ACTION_TEMPLATES = {
            "GIVE_ITEM": {"name": "GIVE_ITEM", "description": "给予物品", "parameters": {"item": {"type": "string"}}},
            "MOVE_TO": {"name": "MOVE_TO", "description": "移动到目标", "parameters": {"target": {"type": "string"}}},
            "NPC_EMOTE": {"name": "NPC_EMOTE", "description": "表情动作", "parameters": {"emotion": {"type": "string"}}},
            "NPC_SAY": {"name": "NPC_SAY", "description": "说话", "parameters": {"message": {"type": "string"}}},
            "NPC_STOP": {"name": "NPC_STOP", "description": "停止移动", "parameters": {}},
            "START_QUEST": {"name": "START_QUEST", "description": "开始任务", "parameters": {"quest_id": {"type": "string"}}},
            "TAKE_ITEM": {"name": "TAKE_ITEM", "description": "拿走物品", "parameters": {"item": {"type": "string"}}},
            "UPDATE_QUEST": {"name": "UPDATE_QUEST", "description": "更新任务进度", "parameters": {"quest_id": {"type": "string"}}},
        }

        # 内置必须动作（不在 JSON 配置中也能自动注入）
        BUILTIN_REQUIRED = [
            {"name": "start_trade", "description": "发起交易：NPC接受玩家售卖请求，打开交易面板", "parameters": {
                "items": {"type": "array"},
                "tip": {"type": "number"},
                "message": {"type": "string"}
            }},
        ]

        normalized = []
        seen_names = set()
        for action in actions:
            if isinstance(action, dict):
                if "name" not in action:
                    action["name"] = action.get("type", "unknown")
                normalized.append(action)
                seen_names.add(action["name"].lower())
            elif isinstance(action, str):
                tmpl = ACTION_TEMPLATES.get(action, {"name": action, "description": action, "parameters": {}})
                normalized.append(tmpl)
                seen_names.add(tmpl["name"].lower())

        # 自动注入未在 JSON actions 中声明的内置必需动作
        for builtin in BUILTIN_REQUIRED:
            if builtin["name"].lower() not in seen_names:
                normalized.append(builtin)

        return normalized

    def _normalize_sensors(self, sensors_config: Dict[str, Any]) -> List[str]:
        """
        将 v2 sensors 对象格式转为 _filter_state 期望的字符串数组

        格式：{"detect_player": true, "database_binding": "world_db"}
        """
        if not sensors_config or not isinstance(sensors_config, dict):
            return []

        sensors = []
        if sensors_config.get("detect_player", False):
            sensors.extend(["player_id", "player_position", "distance_to_player"])

        # database_binding 不影响状态过滤，仅用于权限控制
        return sensors

    def get_agent_info(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """获取 agent 信息"""
        return self.agents.get(agent_id)
    
    def list_agents(self) -> list:
        """列出所有已初始化的 agents"""
        return list(self.agents.keys())
    
    def has_agent(self, agent_id: str) -> bool:
        """检查 agent 是否存在"""
        return agent_id in self.agents
