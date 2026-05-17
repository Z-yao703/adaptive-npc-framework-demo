class ShortTermMemory:
    """最近对话缓冲区"""
    def __init__(self, max_size=10):
        self.max_size = max_size
        self.history = []  # 格式：[{"role": "user" or "assistant", "content": "..."}]

    def add_user_message(self, content: str):
        self.history.append({"role": "user", "content": content})
        self._trim()

    def add_assistant_message(self, content: str):
        self.history.append({"role": "assistant", "content": content})
        self._trim()

    def get_history(self):
        return self.history

    def clear(self):
        self.history = []

    def _trim(self):
        if len(self.history) > self.max_size:
            self.history = self.history[-self.max_size:]