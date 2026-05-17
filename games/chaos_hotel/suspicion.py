"""
SuspicionManager - 怀疑度管理系统
为混沌旅馆推理游戏提供怀疑度追踪

规则：
- 怀疑度范围 0-100，以 5 为最小单位
- 答错 +15
- 达到 100 触发游戏失败
"""
import math


class SuspicionManager:
    MIN = 0
    MAX = 100
    STEP = 5

    def __init__(self):
        self._value = 0

    def add(self, amount: int):
        """增加怀疑度，自动向 STEP 取整并钳制到 [MIN, MAX]"""
        # 按 STEP 向上取整
        new_value = self._value + amount
        rounded = math.ceil(new_value / self.STEP) * self.STEP
        self._value = min(self.MAX, max(self.MIN, rounded))

    def sub(self, amount: int):
        """减少怀疑度"""
        new_value = self._value - amount
        rounded = math.floor(new_value / self.STEP) * self.STEP
        self._value = min(self.MAX, max(self.MIN, rounded))

    def get(self) -> int:
        return self._value

    def set(self, value: int):
        """直接设置怀疑度（用于从数据库恢复）"""
        self._value = min(self.MAX, max(self.MIN, value))

    def is_game_over(self) -> bool:
        """怀疑度 >= MAX 时游戏失败"""
        return self._value >= self.MAX

    def reset(self):
        self._value = 0
