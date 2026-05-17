"""
NPC 性格回复工具模块

根据 NPC 性格配置生成符合人设的回复

设计原则：
1. 完全解耦于具体游戏实现
2. 通过 LLM 生成性格化回复
3. 支持离线降级（使用预设回复库）
4. 不修改任何游戏状态
"""
from typing import Dict, Any, Optional, List
import random


class PersonalityResponse:
    """
    性格化回复生成器
    
    根据 NPC 的性格配置（persona、identity、speaking_style 等）
    生成符合人设的自然对话回复
    """
    
    def __init__(self, profile: Dict[str, Any]):
        """
        初始化性格回复生成器
        
        Args:
            profile: NPC 配置字典，应包含 persona 字段
        """
        self.profile = profile
        self.persona = profile.get('persona', {})
        self.identity = self.persona.get('identity', '')
        self.personality = self.persona.get('personality', '')
        self.speaking_style = self.persona.get('speaking_style', 'normal')
        self.taboos = self.persona.get('taboos', [])
        self.meta = profile.get('meta', {})
        self.npc_name = self.meta.get('name', 'NPC')
        
        # 离线模式下的预设回复库
        self._greeting_responses = self._build_greeting_responses()
        self._emotion_keywords = self._build_emotion_keywords()
    
    def _build_greeting_responses(self) -> Dict[str, List[str]]:
        """构建预设回复库"""
        return {
            'friendly': [
                "嘿！你好啊！见到你真开心！",
                "哇，你来了！今天过得怎么样？",
                "嗨！欢迎欢迎！",
            ],
            'normal': [
                "你好。",
                "嗯？有什么事吗？",
                "你好，有什么事？",
            ],
            'formal': [
                "您好，旅行者。",
                "幸会，不知有何贵干？",
                "您好，请问有何吩咐？",
            ],
            'elder': [
                "哦，是年轻人啊……",
                "孩子，你来了……",
                "唔，是远道而来的旅人……",
            ],
            'humorous': [
                "哟，又见面了！今天太阳打西边出来了？",
                "哈！我就知道你会来的！",
                "哟吼！惊喜不惊喜？",
            ],
            'shy': [
                "啊……你、你好……",
                "呃……是、是游客吗？",
                "你、你好……（小声）",
            ],
            'angry': [
                "哼，又是你！",
                "有什么事快说！",
                "别烦我！",
            ],
            'cool': [
                "……来了。",
                "嗯。",
                "……",
            ],
        }
    
    def _build_emotion_keywords(self) -> Dict[str, List[str]]:
        """构建情绪关键词映射"""
        return {
            'happy': ['谢谢', '感谢', '好棒', '太棒了', '开心', '哈哈', '不错', '厉害'],
            'sad': ['难过', '伤心', '郁闷', '烦躁', '痛苦', '糟糕', '烦'],
            'angry': ['讨厌', '生气', '愤怒', '滚', '烦', '讨厌'],
            'surprised': ['什么', '真的', '不会吧', '天哪', '哇'],
            'friendly': ['你好', '嗨', '哈喽', '早上好', '晚上好', 'hi', 'hello'],
        }
    
    def generate_casual_reply(self, player_message: str, 
                              context: str = "",
                              history: List[Dict] = None) -> Dict[str, Any]:
        """
        生成日常对话回复（主入口）
        
        Args:
            player_message: 玩家消息
            context: 上下文描述
            history: 最近对话历史列表
        
        Returns:
            {"message": str, "emotion": str}
        """
        # 检测消息情绪
        emotion = self._detect_emotion(player_message)
        
        # 根据情绪选择回复
        reply = self._generate_reply(player_message, emotion, context, history)
        
        return {
            "message": reply,
            "emotion": emotion
        }
    
    def _detect_emotion(self, message: str) -> str:
        """根据消息内容检测情绪"""
        if not message:
            return 'neutral'
        
        message_lower = message.lower()
        
        # 优先检测强情绪
        for emotion, keywords in self._emotion_keywords.items():
            if emotion == 'neutral':
                continue
            for kw in keywords:
                if kw in message_lower:
                    return emotion
        
        return 'neutral'
    
    def _generate_reply(self, message: str, emotion: str, 
                       context: str, history: List[Dict]) -> str:
        """
        生成回复内容
        
        策略：
        1. 根据说话风格选择预设回复
        2. 根据情绪调整回复
        3. 如果有上下文，融入上下文
        """
        style = self.speaking_style.lower() if self.speaking_style else 'normal'
        
        # 获取该风格的回复库
        responses = self._greeting_responses.get(style, self._greeting_responses['normal'])
        
        # 根据情绪调整
        if emotion == 'happy':
            return random.choice([
                f"哈哈，听到你这么说我也开心！",
                f"太好了！{self.npc_name}也很高兴！",
                f"嗯嗯，继续继续！"
            ])
        elif emotion == 'sad':
            return random.choice([
                "别难过，一切都会好起来的。",
                "我理解你的感受……",
                "嗯……有时候是这样的。"
            ])
        elif emotion == 'surprised':
            return random.choice([
                "真的吗？",
                "这倒是没想到……",
                "哦？说来听听。"
            ])
        
        # 根据上下文选择回复
        if self._is_greeting(message):
            return self._generate_greeting()
        
        # 根据上下文生成回复
        if context and history:
            return self._generate_contextual_reply(message, context, history)
        
        # 默认回复
        return random.choice(responses)
    
    def _is_greeting(self, message: str) -> bool:
        """判断是否为问候语"""
        greetings = ['你好', '嗨', 'hi', 'hello', '早上好', '晚上好', 
                    'hey', 'yo', '哟', '在吗', '在不在']
        message_lower = message.lower()
        return any(g in message_lower for g in greetings)
    
    def _generate_greeting(self) -> str:
        """生成问候语"""
        style = self.speaking_style.lower() if self.speaking_style else 'normal'
        responses = self._greeting_responses.get(style, self._greeting_responses['normal'])
        
        base = random.choice(responses)
        
        # 融入 NPC 特色
        if '嘿咻' in self.identity:
            return f"嘿咻！{base}"
        
        return base
    
    def _generate_contextual_reply(self, message: str, 
                                  context: str, 
                                  history: List[Dict]) -> str:
        """
        基于上下文生成回复
        
        这个方法主要用于离线模式
        在线模式会由 LLM 处理
        """
        # 检查是否在询问天气
        if any(kw in message for kw in ['天气', '气候', '冷', '热']):
            return random.choice([
                "今天的天气还不错呢。",
                "天气啊……挺好的。",
                "嗯，天气挺宜人的。"
            ])
        
        # 检查是否在询问状态
        if any(kw in message for kw in ['怎么样', '如何', '还好']):
            return random.choice([
                "还不错，谢谢关心。",
                "一般般啦……",
                "还行，你呢？"
            ])
        
        # 检查是否在道别
        if any(kw in message for kw in ['再见', '拜拜', '走了', 'bye']):
            return random.choice([
                "再见！有空再来玩啊！",
                "拜拜！",
                "路上小心！"
            ])
        
        # 检查是否在道谢
        if any(kw in message for kw in ['谢谢', '感谢', '谢']):
            return random.choice([
                "不客气！",
                "没什么！",
                "小事一桩！"
            ])
        
        # 默认闲聊回复
        casual_replies = [
            f"你说的「{message[:10]}...」，让我想想。",
            "嗯……这个问题有意思。",
            "我明白你的意思了。",
            "继续说，我在听。",
            "是吗？"
        ]
        
        return random.choice(casual_replies)
    
    def build_personality_prompt(self) -> str:
        """
        构建性格描述片段（用于 LLM 调用）
        
        Returns:
            包含 NPC 性格信息的字符串
        """
        parts = [
            f"【NPC名称】{self.npc_name}",
            f"【身份设定】{self.identity}" if self.identity else "",
            f"【性格描述】{self.personality}" if self.personality else "",
            f"【说话风格】{self.speaking_style}" if self.speaking_style else "",
            f"【禁忌话题】{', '.join(self.taboos)}" if self.taboos else "【禁忌话题】无"
        ]
        
        return "\n".join([p for p in parts if p])
    
    def get_llm_system_prompt(self, history_context: str = "") -> str:
        """
        获取用于 LLM 调用的完整 system prompt
        
        Args:
            history_context: 历史对话上下文
        
        Returns:
            完整的 system prompt
        """
        prompt = f"""你是游戏中的 NPC「{self.npc_name}」。

{self.build_personality_prompt()}

【当前场景】
玩家正在与你进行日常对话。

【对话历史】
{history_context if history_context else "（暂无历史对话）"}

【重要规则】
1. 必须保持 NPC 的人设和性格
2. 回复要自然，符合日常交流场景
3. 每条回复不超过 2 句话
4. 根据说话风格调整用词
5. 遇到禁忌话题要委婉转移

请以 NPC「{self.npc_name}」的身份回复玩家。"""
        
        return prompt


# 全局工厂函数
def create_personality_response(profile: Dict[str, Any]) -> PersonalityResponse:
    """
    创建性格回复生成器的工厂函数
    
    这是推荐的使用方式
    """
    return PersonalityResponse(profile)
