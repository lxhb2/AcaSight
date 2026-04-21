"""
统一 LLM 客户端
支持 Ollama / SiliconFlow / LM Studio / 任何 OpenAI 兼容 API
自动检测网络，离线用本地模型，在线用云端 API
"""
import os
import sys
import json
import socket
from typing import List, Dict, Any, Optional

import requests


# ==================== 网络检测 ====================

def is_online(host: str = "8.8.8.8", port: int = 53, timeout: float = 2) -> bool:
    """检测是否有网络连接"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        sock.close()
        return True
    except Exception:
        return False


def check_ollama_available(base_url: str = "http://localhost:11434", timeout: float = 3) -> bool:
    """检测 Ollama 是否可用"""
    try:
        r = requests.get(f"{base_url}/api/tags", timeout=timeout)
        return r.status_code == 200
    except Exception:
        return False


def check_lmstudio_available(base_url: str = "http://localhost:1234", timeout: float = 3) -> bool:
    """检测 LM Studio 是否可用"""
    try:
        r = requests.get(f"{base_url}/v1/models", timeout=timeout)
        return r.status_code == 200
    except Exception:
        return False


# ==================== 配置加载 ====================

def _get_projects_dir() -> str:
    """获取项目根目录（projects/，而非 projects/src/）"""
    env_dir = os.getenv("PULSE_PROJECT_DIR")
    if env_dir:
        return env_dir
    # __file__ = .../projects/src/utils/llm_client.py → 往上 3 级
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_model_config() -> dict:
    """加载模型配置"""
    config_path = os.path.join(_get_projects_dir(), "config", "model_config.json")
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    # 默认配置
    return {
        "providers": {
            "online": {
                "provider": "ollama",
                "model": "qwen3.5:4b",
                "base_url": "http://localhost:11434",
                "api_key": "ollama",
                "temperature": 0.7,
                "timeout": 300
            }
        },
        "prompt_mode": "auto"
    }


def get_active_provider(force_mode: Optional[str] = None) -> Dict[str, Any]:
    """
    获取当前可用的 LLM 配置
    force_mode: "online" | "offline" | "ollama" | "lmstudio" | None(自动检测)
    """
    config = load_model_config()
    providers = config.get("providers", {})

    if force_mode == "online":
        return providers.get("online", list(providers.values())[0])

    if force_mode == "ollama":
        return providers.get("offline_ollama", providers.get("ollama", providers.get("online")))

    if force_mode == "lmstudio":
        return providers.get("offline_lmstudio", providers.get("lmstudio", providers.get("online")))

    # 自动检测
    if is_online():
        online_cfg = providers.get("online")
        if online_cfg and online_cfg.get("api_key"):
            return online_cfg

    # 尝试 Ollama
    ollama_cfg = providers.get("offline_ollama")
    if ollama_cfg and check_ollama_available(ollama_cfg.get("base_url", "http://localhost:11434")):
        return ollama_cfg

    # 尝试 LM Studio
    lmstudio_cfg = providers.get("offline_lmstudio")
    if lmstudio_cfg and check_lmstudio_available(lmstudio_cfg.get("base_url", "http://localhost:1234")):
        return lmstudio_cfg

    # 兜底
    return providers.get("offline_ollama", list(providers.values())[0])


# ==================== 统一 LLM 客户端 ====================

class LLMClient:
    """
    统一 LLM 客户端
    支持 Ollama 原生 API 和 OpenAI 兼容 API
    """

    def __init__(self, provider_config: Optional[Dict] = None,
                 force_mode: Optional[str] = None):
        if provider_config:
            self.config = provider_config
        else:
            self.config = get_active_provider(force_mode)

        self.provider = self.config.get("provider", "ollama")
        self.model = self.config.get("model", "qwen3.5:4b")
        self.base_url = self.config["base_url"].rstrip("/")
        self.temperature = self.config.get("temperature", 0.7)
        self.timeout = self.config.get("timeout", 300)
        self.api_key = self.config.get("api_key", "")

        # 判断 API 类型
        self._is_openai_compat = self.provider in ("siliconflow", "lmstudio", "openai")

        # 构建请求 URL
        if self._is_openai_compat:
            self._chat_url = f"{self.base_url}/chat/completions"
        else:
            self._chat_url = f"{self.base_url}/api/chat"

    @property
    def mode(self) -> str:
        """当前模式"""
        if self._is_openai_compat and self.provider != "lmstudio":
            return "online"
        return "offline"

    def chat(self, messages: List[Dict[str, str]],
             temperature: Optional[float] = None,
             stream: bool = False,
             **kwargs) -> Dict[str, Any]:
        """发送聊天请求"""
        temperature = temperature if temperature is not None else self.temperature

        if self._is_openai_compat:
            return self._chat_openai(messages, temperature, stream, **kwargs)
        else:
            return self._chat_ollama(messages, temperature, stream, **kwargs)

    def _chat_ollama(self, messages: List[Dict[str, str]],
                     temperature: float, stream: bool,
                     **kwargs) -> Dict[str, Any]:
        """Ollama 原生 API"""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
            **kwargs
        }
        resp = requests.post(self._chat_url, json=payload, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        # 转换为统一格式
        return {
            "message": {
                "role": "assistant",
                "content": data.get("message", {}).get("content", "")
            },
            "raw": data
        }

    def _chat_openai(self, messages: List[Dict[str, str]],
                     temperature: float, stream: bool,
                     **kwargs) -> Dict[str, Any]:
        """OpenAI 兼容 API"""
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
            **kwargs
        }
        resp = requests.post(self._chat_url, json=payload, headers=headers,
                             timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        # 转换为统一格式
        choices = data.get("choices", [])
        content = choices[0].get("message", {}).get("content", "") if choices else ""
        return {
            "message": {
                "role": "assistant",
                "content": content
            },
            "raw": data
        }

    def __repr__(self) -> str:
        return f"LLMClient(provider={self.provider}, model={self.model}, mode={self.mode})"


# ==================== 便捷函数 ====================

def create_client(force_mode: Optional[str] = None) -> LLMClient:
    """创建 LLM 客户端"""
    return LLMClient(force_mode=force_mode)


if __name__ == "__main__":
    # 测试
    print("网络检测:", "online" if is_online() else "offline")
    print("Ollama:", "available" if check_ollama_available() else "not available")
    print("LM Studio:", "available" if check_lmstudio_available() else "not available")

    provider = get_active_provider()
    print(f"当前 Provider: {provider.get('provider')} / {provider.get('model')}")

    client = create_client()
    print(f"客户端: {client}")

    # 快速测试
    resp = client.chat([{"role": "user", "content": "说OK"}])
    print(f"响应: {resp['message']['content']}")
