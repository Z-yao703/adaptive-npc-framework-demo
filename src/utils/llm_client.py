# LLM API 调用封装
import os
from volcenginesdkarkruntime import Ark

DEFAULT_MODEL = "doubao-seed-2-0-lite-260215"

class ArkClient:
    def __init__(self, model: str = DEFAULT_MODEL):
        self.client = Ark(
            api_key=os.getenv('ARK_API_KEY'),
        )
        self.model = model

    def generate_text(self, prompt: str, system_prompt: str = None, history: list = None) -> str:
        """
        生成文本响应

        Args:
            prompt: 用户输入（user role）
            system_prompt: 系统提示（system role），可选
            history: 对话历史 [{role, content}]，可选

        Returns:
            LLM 文本回复
        """
        messages = []

        # 系统消息
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # 对话历史
        if history:
            for msg in history:
                messages.append({"role": msg["role"], "content": msg["content"]})

        # 当前用户消息
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
        )
        return response.choices[0].message.content  # 直接返回第一个回复 # type: ignore
    
class LLMClient:
    """支持多轮对话的 LLM 客户端"""
    def __init__(self, config: dict):
        self.provider = config.get("provider", "ark")
        self.model = config.get("model", DEFAULT_MODEL)
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens", 200)
        
        if self.provider == "ark":
            self.client = ArkClient(model=self.model)
        else:
            self.client = None

    def generate_response(self, system_prompt: str, history: list, user_input: str, knowledge_context: str = "") -> str:
        if self.provider == "ark":
            full_prompt = system_prompt + "\n"
            if knowledge_context:
                full_prompt += f"相关知识：{knowledge_context}\n"
            for msg in history:
                role = "玩家" if msg["role"] == "user" else "你"
                full_prompt += f"{role}：{msg['content']}\n"
            full_prompt += f"玩家：{user_input}\n你："
            
            response = self.client.generate_text(full_prompt) # type: ignore
            return response
        else:
            return "[模拟回复] 你好，我是NPC。"