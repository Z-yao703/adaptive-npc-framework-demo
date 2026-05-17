"""
Registry-based NPC config loading.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from src.utils.logging import log_error, log_info, log_warn

REGISTRY_PATH = "configs/npc_registry.json"
CONFIGS_DIR = "configs"


class RegistryLoader:
    def __init__(self, registry_path: str = REGISTRY_PATH):
        self.registry_path = registry_path
        self.registry: Dict[str, Any] = {}
        self._load_registry()

    def _load_registry(self) -> None:
        if not os.path.exists(self.registry_path):
            log_warn("Registry 文件不存在: {}", self.registry_path)
            self.registry = self._empty_registry()
            return

        try:
            with open(self.registry_path, "r", encoding="utf-8") as file:
                self.registry = json.load(file)
            log_info("Registry 已加载: {} 个 NPC", len(self.registry.get("agents", [])))
        except Exception as exc:
            log_error("Registry 加载失败: {}", exc)
            self.registry = self._empty_registry()

    def _empty_registry(self) -> Dict[str, Any]:
        return {
            "version": "1.0",
            "description": "NPC Registry",
            "default_agent": "default_npc",
            "agents": [],
        }

    def get_all_agents(self) -> List[str]:
        return self.registry.get("agents", [])

    def get_default_agent(self) -> str:
        default_agent = self.registry.get("default_agent")
        if default_agent:
            return default_agent

        agents = self.get_all_agents()
        if agents:
            return agents[0]

        return "default_npc"

    def load_config(self, agent_id: str) -> Optional[Dict[str, Any]]:
        direct_path = os.path.join(CONFIGS_DIR, f"{agent_id}.json")
        if os.path.exists(direct_path):
            return self._load_json(agent_id, direct_path)

        dir_path = os.path.join(CONFIGS_DIR, agent_id, "config.json")
        if os.path.exists(dir_path):
            return self._load_json(agent_id, dir_path)

        log_warn("未找到配置: {}", agent_id)
        return None

    def _load_json(self, agent_id: str, path: str) -> Optional[Dict[str, Any]]:
        try:
            with open(path, "r", encoding="utf-8") as file:
                return json.load(file)
        except Exception as exc:
            log_error("配置加载失败 {}: {}", agent_id, exc)
            return None

    def reload(self) -> None:
        self._load_registry()

    def save_registry(self) -> None:
        try:
            os.makedirs(os.path.dirname(self.registry_path), exist_ok=True)
            with open(self.registry_path, "w", encoding="utf-8") as file:
                json.dump(self.registry, file, ensure_ascii=False, indent=4)
            log_info("Registry 已保存: {}", self.registry_path)
        except Exception as exc:
            log_error("Registry 保存失败: {}", exc)
