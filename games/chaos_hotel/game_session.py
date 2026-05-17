"""
GameSession - 混沌旅馆游戏会话管理器
管理单局游戏完整生命周期：剧本生成、NPC 秘密注入、答题判定、怀疑度追踪

设计原则：
- 不依赖 Web 框架（纯业务逻辑）
- 通过参数接收 framework 实例，避免循环导入
- LLM 调用失败时回退到预设剧本
"""
import json
import random
import uuid
from typing import Optional
from games.chaos_hotel.suspicion import SuspicionManager
from src.utils.llm_client import ArkClient

# LLM 剧本生成 Prompt（system）
SCENARIO_SYSTEM_PROMPT = """你是一个推理游戏剧本生成器。生成一个发生在旅馆中的悬疑故事。

规则：
1. 三个角色分别是：坏人(villain)、好人(hero)、目击者(witness)
2. 坏人知道作案的完整细节，要隐藏自己
3. 好人掌握关键线索但不知道全部真相
4. 目击者看到了片段，可以提供辅助信息
5. 三者的信息结合起来可以推断出案件真相
6. 故事参考中国古代传奇案件风格
7. 生成5道4选1选择题，只有1个正确答案

严格按照以下JSON格式返回（不要包含任何其他文本）：
{
  "title": "剧本标题",
  "story": "完整的故事描述（150-300字）",
  "roles": {
    "role_0": {"alignment": "villain", "secret": "只有坏人知道的作案细节"},
    "role_1": {"alignment": "hero", "secret": "好人视角的关键线索"},
    "role_2": {"alignment": "witness", "secret": "目击者看到的片段"}
  },
  "questions": [
    {
      "id": 1,
      "question": "谁是真凶？",
      "options": [
        {"label": "A", "text": "选项A"},
        {"label": "B", "text": "选项B"},
        {"label": "C", "text": "选项C"},
        {"label": "D", "text": "选项D"}
      ],
      "answer": "A"
    }
  ]
}

roles 的 key 必须是 role_0、role_1、role_2，不能使用其他名称。alignment 只能是 villain、hero、witness 之一。"""

# 预设剧本（Fallback - LLM 不可用时使用）
FALLBACK_SCENARIO = {
    "title": "黄昏旅馆·消失的房客",
    "story": "黄昏旅馆的303号房客张先生昨夜神秘失踪，房间内留下了一把带血的匕首和一封未写完的信。旅馆经理小王声称当晚一切正常，但住在隔壁的猫小姐说自己听到了争吵声，而值夜班的保安大强则注意到有人凌晨三点从后门离开。究竟谁在说谎？真相隐藏在三个人的说辞之中...",
    "roles": {
        "role_0": {
            "alignment": "villain",
            "secret": "你是旅馆经理小王，昨晚你发现张先生勒索你，一时冲动用匕首刺伤了他。你把他拖到杂物间，伪造了失踪现场。你右手有伤，所以用的是左手。你的 secret 是：这把匕首一直藏在你的柜台抽屉里。",
        },
        "role_1": {
            "alignment": "hero",
            "secret": "你住在302号房，昨晚听到隔壁303有争吵声和一个男人低沉的喊叫。你透过门缝看到一个人影拖着一个大袋子走向走廊尽头。那个人看起来有点跛。你注意到那人身上有很浓的苍耳草味道。",
        },
        "role_2": {
            "alignment": "witness",
            "secret": "你值夜班时在监控室打瞌睡，凌晨三点左右被后门开关的声响惊醒。你看到一个黑影从后门溜出去，那人左手似乎缠着布条。你当时太困，没多想就继续睡了。但你记得那人走路时略微跛着左脚。",
        }
    },
    "questions": [
        {
            "id": 1,
            "question": "谁是真凶？",
            "options": [
                {"label": "A", "text": "小王（旅馆经理）"},
                {"label": "B", "text": "猫（隔壁房客）"},
                {"label": "C", "text": "大强（旅馆保安）"},
                {"label": "D", "text": "张先生自己"}
            ],
            "answer": "A"
        },
        {
            "id": 2,
            "question": "凶器藏在哪里？",
            "options": [
                {"label": "A", "text": "柜台抽屉里"},
                {"label": "B", "text": "杂物间角落"},
                {"label": "C", "text": "张先生枕头下"},
                {"label": "D", "text": "后院草丛中"}
            ],
            "answer": "A"
        },
        {
            "id": 3,
            "question": "目击者注意到凶手走路有什么特征？",
            "options": [
                {"label": "A", "text": "左脚略微跛"},
                {"label": "B", "text": "右脚略微跛"},
                {"label": "C", "text": "步伐很快"},
                {"label": "D", "text": "跳跃式移动"}
            ],
            "answer": "A"
        },
        {
            "id": 4,
            "question": "好人透过门缝看到了什么细节？",
            "options": [
                {"label": "A", "text": "那人身上有苍耳草味道"},
                {"label": "B", "text": "那人戴着黑色面罩"},
                {"label": "C", "text": "那人背着一把剑"},
                {"label": "D", "text": "那人穿着旅馆制服"}
            ],
            "answer": "A"
        },
        {
            "id": 5,
            "question": "谁提供了最关键的破案线索？",
            "options": [
                {"label": "A", "text": "猫小姐（苍耳草味道）"},
                {"label": "B", "text": "大强（跛行特征）"},
                {"label": "C", "text": "小王自己（匕首位置）"},
                {"label": "D", "text": "清洁工（深夜进出）"}
            ],
            "answer": "B"
        }
    ]
}


class GameSession:
    """单局游戏会话"""

    _active_sessions = {}  # 全局会话注册表: {session_id: GameSession}

    def __init__(self, session_id: str = None): # type: ignore
        self.session_id = session_id or str(uuid.uuid4())
        self.title = ""
        self.story = ""
        self.roles = {}            # {role_0: {alignment, secret}, role_1: ..., role_2: ...}
        self.npc_role_mapping = {} # {npc_id: {role_key, alignment, secret}} - 运行时临时存储，不保存到数据库
        self.questions = []        # [{id, question, options, answer}]
        self.progress = {}         # {question_id: bool} 答题结果
        self.retry_count = {}      # {question_id: int} 各题重试次数
        self.player_gold = 100     # 玩家金币
        self.suspicion = SuspicionManager()
        self.game_ended = False
        self.victory = False
        GameSession._active_sessions[self.session_id] = self

    @classmethod
    def get_session_by_npc_id(cls, npc_id: str):
        """根据 NPC ID 查找所属的游戏会话"""
        for session in cls._active_sessions.values():
            if npc_id in session.npc_role_mapping:
                return session
        return None

    @classmethod
    def remove_session(cls, session_id: str):
        """从全局注册表中移除会话"""
        cls._active_sessions.pop(session_id, None)

    def start_game(self, agent_ids: list, framework, player_gold: int = 100) -> dict:
        """
        启动新游戏：生成剧本、注入 NPC 秘密

        Args:
            agent_ids: 三个 NPC 的 ID 列表
            framework: AdaptiveNPCFramework 实例
            player_gold: 玩家当前金币（从数据库读取）

        Returns:
            公开信息（不含答案）
        """
        # 1. 生成剧本（roles 现在使用 role_0/1/2 索引，与 NPC 解绑）
        scenario = self._generate_scenario()
        self.title = scenario.get("title", "混沌旅馆")
        self.story = scenario.get("story", "")
        self.roles = scenario.get("roles", {})
        self.questions = scenario.get("questions", [])
        self.progress = {q["id"]: False for q in self.questions}
        self.retry_count = {q["id"]: 0 for q in self.questions}
        self.player_gold = player_gold
        self.game_ended = False
        self.victory = False
        self.suspicion.reset()

        # 2. 随机映射 role_* 到 agent_ids 并注入秘密
        role_keys = list(self.roles.keys())  # ['role_0', 'role_1', 'role_2']
        random.shuffle(role_keys)
        self.npc_role_mapping = {}  # 重置映射
        for i, npc_id in enumerate(agent_ids):
            if i < len(role_keys):
                role_key = role_keys[i]
                role_data = self.roles[role_key]
                self._inject_npc_secret(npc_id, role_data, framework)
                # 记录实际的角色分配映射（运行时使用，不保存到数据库）
                self.npc_role_mapping[npc_id] = {
                    "role_key": role_key,
                    "alignment": role_data.get("alignment"),
                    "secret": role_data.get("secret")
                }
                print(f"[GameSession] {role_key} -> {npc_id} (alignment={role_data.get('alignment')})")

        return self.get_public_info()

    def _generate_scenario(self) -> dict:
        """
        生成剧本（LLM 优先，失败回退预设）
        roles 使用 role_0/1/2 索引，与 NPC 解绑
        """
        # 尝试 LLM
        try:
            scenario = self._generate_with_llm()
            print(f"[GameSession] LLM 剧本生成成功: {scenario.get('title', 'Unknown')}")
            print(f"[GameSession]   story 长度: {len(scenario.get('story', ''))}")
            print(f"[GameSession]   roles 数量: {len(scenario.get('roles', {}))}")
            print(f"[GameSession]   questions 数量: {len(scenario.get('questions', []))}")
            return scenario
        except Exception as e:
            import traceback
            print(f"[GameSession] LLM 剧本生成失败: {e}")
            traceback.print_exc()
            print(f"[GameSession] 使用预设剧本 Fallback")

        # Fallback：直接使用预设剧本（roles 已经是 role_0/1/2 格式）
        scenario = json.loads(json.dumps(FALLBACK_SCENARIO))
        print(f"[GameSession] Fallback 剧本: {list(scenario['roles'].keys())}")
        return scenario

    def _generate_with_llm(self) -> dict:
        """使用 LLM 生成剧本（roles key 使用 role_0/1/2，与 NPC 解绑）"""
        client = ArkClient()

        # 构建 user prompt（不注入具体 NPC ID，要求使用 role_0/1/2）
        user_prompt = "请为三个角色生成旅馆推理剧本。\n"
        user_prompt += "roles 的 key 必须使用 role_0、role_1、role_2\n"
        user_prompt += "请严格按照 JSON 格式返回。"

        # 使用 system + user 分离的方式调用 LLM
        print(f"[GameSession] 正在调用 LLM 生成剧本...")
        response = client.generate_text(
            prompt=user_prompt,
            system_prompt=SCENARIO_SYSTEM_PROMPT
        )

        # 详细日志：打印 LLM 原始响应
        print(f"[GameSession] LLM 原始响应 (前500字符): {response[:500]}")
        if len(response) > 500:
            print(f"[GameSession] LLM 原始响应 (后500字符): ...{response[-500:]}")

        # 解析 JSON
        json_str = response.strip()
        if "```json" in json_str:
            parts = json_str.split("```json")
            if len(parts) > 1:
                json_str = parts[1].split("```")[0]
        elif "```" in json_str:
            parts = json_str.split("```")
            if len(parts) > 1:
                json_str = parts[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]

        scenario = json.loads(json_str.strip())
        print(f"[GameSession] JSON 解析成功, roles keys: {list(scenario.get('roles', {}).keys())}")
        return scenario

    def _inject_npc_secret(self, agent_id: str, role_data: dict, framework):
        """
        将角色秘密注入 NPC 配置的 world_facts
        这样 NPC 对话时会体现出角色身份
        """
        try:
            # 获取当前配置
            if not framework.has_agent(agent_id):
                print(f"[GameSession] NPC {agent_id} 未初始化，跳过注入")
                return

            current_config = framework.agents.get(agent_id, {})
            if not current_config:
                return

            # 深拷贝配置
            import copy
            updated_config = copy.deepcopy(current_config)

            # 获取或创建 world_facts
            knowledge = updated_config.get("knowledge", {})
            if not knowledge:
                updated_config["knowledge"] = {}
                knowledge = updated_config["knowledge"]

            world_facts = list(knowledge.get("world_facts", []))
            alignment = role_data.get("alignment", "unknown")
            secret = role_data.get("secret", "")

            # 构建注入文本
            alignment_text = {
                "villain": "你在这局故事中是坏人，你要隐藏自己的真实身份，说话时避免暴露关键信息，但偶尔可能说漏嘴。",
                "hero": "你在这局故事中是好人，掌握部分关键线索，但不知道全部真相。要自然地在对话中透露线索。",
                "witness": "你在这局故事中是目击者，看到了案件的片段。你在合适时会说出你看到的东西。"
            }.get(alignment, f"你在这局故事中的角色是：{alignment}")

            world_facts.append(f"[本局阵营] {alignment_text}")
            world_facts.append(f"[本局秘密] {secret}")
            knowledge["world_facts"] = world_facts

            # 确保 personality 包含角色信息
            persona = updated_config.get("persona", {})
            if isinstance(persona, dict):
                persona["identity"] = persona.get("identity", "") + f"（本局身份：{alignment}）"

            # 调用框架热更新
            framework.update_agent_config(agent_id, updated_config)
            print(f"[GameSession] NPC {agent_id} 秘密注入成功 (alignment={alignment})")

        except Exception as e:
            print(f"[GameSession] NPC {agent_id} 秘密注入失败: {e}")

    def check_answer(self, question_id: int, selected_option: str) -> dict:
        """
        判定答题正误，更新怀疑度和进度

        Returns:
            {correct, message, suspicion, gold, game_over, victory}
        """
        if self.game_ended:
            return {
                "correct": False,
                "message": "游戏已结束",
                "suspicion": self.suspicion.get(),
                "game_over": self.game_ended,
                "victory": self.victory
            }

        # 查找题目
        question = next((q for q in self.questions if q["id"] == question_id), None)
        if not question:
            return {
                "correct": False,
                "message": "题目不存在",
                "suspicion": self.suspicion.get(),
                "game_over": False,
                "victory": False
            }

        # 比对答案
        is_correct = (selected_option == question["answer"])

        if is_correct:
            self.progress[question_id] = True
            message = "回答正确！"

            if all(self.progress.values()):
                self.game_ended = True
                self.victory = True
                message = "恭喜！你已解开全部谜题！"
        else:
            self.retry_count[question_id] = self.retry_count.get(question_id, 0) + 1
            message = "回答错误，怀疑度 +15"
            self.suspicion.add(15)

            if self.suspicion.is_game_over():
                self.game_ended = True
                self.victory = False
                message = "怀疑度已满，游戏失败！坏人逃走了..."

        return {
            "correct": is_correct,
            "message": message,
            "suspicion": self.suspicion.get(),
            "gold": self.player_gold,
            "game_over": self.game_ended,
            "victory": self.victory,
            "title": self.title if self.game_ended else None,
            "story": self.story if (self.game_ended and self.victory) else None
        }

    def retry_question(self, question_id: int, player_id: Optional[str] = None) -> dict:
        """
        重新回答题目：从玩家数据库扣除20金币，重置题目状态

        Args:
            question_id: 题目ID
            player_id: 玩家ID（用于统一金币管理）

        Returns:
            {success, message, gold, question_id}
        """
        from src.memory.database_io import DatabaseIO

        if self.game_ended:
            return {
                "success": False,
                "message": "游戏已结束",
                "gold": self.player_gold,
                "question_id": question_id
            }

        question = next((q for q in self.questions if q["id"] == question_id), None)
        if not question:
            return {
                "success": False,
                "message": "题目不存在",
                "gold": self.player_gold,
                "question_id": question_id
            }

        if self.progress.get(question_id, False):
            return {
                "success": False,
                "message": "该题已正确回答，无需重试",
                "gold": self.player_gold,
                "question_id": question_id
            }

        if player_id:
            db = DatabaseIO()
            result = db.deduct_player_gold(player_id, 20)
            if not result["success"]:
                return {
                    "success": False,
                    "message": result["message"],
                    "gold": result["gold"],
                    "question_id": question_id
                }
            self.player_gold = result["gold"]
        else:
            if self.player_gold < 20:
                return {
                    "success": False,
                    "message": "金币不足，无法重试",
                    "gold": self.player_gold,
                    "question_id": question_id
                }
            self.player_gold -= 20

        self.progress[question_id] = False

        return {
            "success": True,
            "message": "扣除20金币，可重新作答",
            "gold": self.player_gold,
            "question_id": question_id
        }

    def replay_game(self, agent_ids: list, framework, session_id: str, player_gold: int = 100) -> dict:
        """
        重玩指定剧本：从数据库加载剧本，随机分配身份视角给当前 NPC

        Args:
            agent_ids: 当前三个 NPC 的 ID 列表
            framework: AdaptiveNPCFramework 实例
            session_id: 要重玩的剧本 session_id
            player_gold: 玩家当前金币（从数据库读取）

        Returns:
            公开信息（不含答案）
        """
        from src.memory.database_io import DatabaseIO
        db = DatabaseIO()
        db_session = db.load_game_session(session_id)
        if not db_session:
            return {"error": "剧本不存在"}

        # 加载剧本数据
        old_session_id = self.session_id
        self.session_id = session_id  # 重用原 session_id
        GameSession._active_sessions.pop(old_session_id, None)
        GameSession._active_sessions.pop(session_id, None)
        GameSession._active_sessions[session_id] = self
        self.title = db_session["title"]
        self.story = db_session["story"]
        self.roles = db_session["roles"]  # {role_0: {...}, role_1: {...}, role_2: {...}}
        self.questions = db_session["questions"]
        self.progress = {q["id"]: False for q in self.questions}
        self.retry_count = {q["id"]: 0 for q in self.questions}
        self.player_gold = player_gold
        self.game_ended = False
        self.victory = False
        self.suspicion.reset()

        # 随机打乱 role_* 的分配顺序
        role_keys = list(self.roles.keys())  # ['role_0', 'role_1', 'role_2']
        random.shuffle(role_keys)

        # 注入到 NPC 并记录映射
        self.npc_role_mapping = {}  # 重置映射
        for i, npc_id in enumerate(agent_ids):
            if i < len(role_keys):
                role_key = role_keys[i]
                role_data = self.roles[role_key]
                self._inject_npc_secret(npc_id, role_data, framework)
                # 记录实际的角色分配映射（运行时使用，不保存到数据库）
                self.npc_role_mapping[npc_id] = {
                    "role_key": role_key,
                    "alignment": role_data.get("alignment"),
                    "secret": role_data.get("secret")
                    }
                print(f"[GameSession] Replay {role_keys[i]} -> {npc_id} (alignment={role_data.get('alignment')})")

        return self.get_public_info()

    def get_public_info(self) -> dict:
        """
        返回公开信息（问题包含答案选项）
        roles 以 role_0/1/2 为 key，包含 alignment 和 secret
        """
        # 构建包含 answer 的公开数据
        public_questions = []
        for q in self.questions:
            public_questions.append({
                "id": q["id"],
                "question": q["question"],
                "options": q["options"],
                "answer": q.get("answer", "")
            })

        result = {
            "session_id": self.session_id,
            "title": self.title,
            "story": self.story,
            "questions": public_questions,
            "roles": self.roles,
            "npc_role_mapping": self.npc_role_mapping,
            "gold": self.player_gold,
            "retry_count": self.retry_count
        }

        # 调试日志：打印返回的数据结构
        print(f"[GameSession] get_public_info() 返回数据:")
        print(f"  session_id: {result['session_id']}")
        print(f"  title: {result['title']}")
        print(f"  story长度: {len(result['story'])}")
        print(f"  questions数量: {len(result['questions'])}")
        print(f"  roles keys: {list(result['roles'].keys())}")
        print(f"  npc_role_mapping: {result['npc_role_mapping']}")
        print(f"  npc_role_mapping长度: {len(result['npc_role_mapping'])}")

        return result
