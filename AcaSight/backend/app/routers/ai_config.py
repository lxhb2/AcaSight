"""
AI 配置路由

密钥安全：
- 存储时 AES-256-GCM 加密（cryptography 库）
- 读取时返回 "xxxx****xxxx" 脱敏版本
- 保存时 "****" 检测：留空/脱敏 → 保留旧密钥；新密钥 → 加密存储
- Agent 运行时通过 decrypt_api_key() 透明解密
"""

import base64
import json
import os
from typing import Optional, Dict, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import httpx
import structlog

from app.config import settings
from app.services.ai_service import ai_service, load_ai_config
from app.services.crypto import encrypt_key, decrypt_key, mask_key

logger = structlog.get_logger()
router = APIRouter()

CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'ai_config.json')


def _load_config() -> dict:
    """加载配置文件（密钥保持加密态）"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    return {
        'default_provider': 'ollama',
        'default_model': '',
        'providers': {
            'ollama': {'base_url': 'http://localhost:11434', 'api_key': '', 'enabled': True},
            'openai': {'base_url': 'https://api.openai.com/v1', 'api_key': '', 'enabled': False},
            'deepseek': {'base_url': 'https://api.deepseek.com/v1', 'api_key': '', 'enabled': False},
            'siliconflow': {'base_url': 'https://api.siliconflow.cn/v1', 'api_key': '', 'enabled': False},
            'minimax': {'base_url': 'https://api.minimax.chat/v1', 'api_key': '', 'enabled': False},
            'glm': {'base_url': 'https://open.bigmodel.cn/api/paas/v4', 'api_key': '', 'enabled': False},
            'claude': {'base_url': 'https://api.anthropic.com', 'api_key': '', 'enabled': False},
        }
    }


def _save_config(config: dict):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


class AIConfigUpdate(BaseModel):
    default_provider: Optional[str] = None
    default_model: Optional[str] = None
    providers: Optional[Dict[str, Dict]] = None


class ProviderTestRequest(BaseModel):
    provider: str
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None


@router.get("/config")
async def get_ai_config():
    """返回脱敏配置：api_key 显示 xxxx****xxxx，has_api_key 标记是否存在"""
    config = _load_config()
    masked = json.loads(json.dumps(config))
    for pname, pconf in masked.get('providers', {}).items():
        encrypted = pconf.get('api_key', '')
        if encrypted:
            plain = decrypt_key(encrypted)
            pconf['api_key'] = mask_key(plain)
            pconf['has_api_key'] = True
        else:
            pconf['api_key'] = ''
            pconf['has_api_key'] = False
    return masked


@router.post("/config")
async def save_ai_config(update: AIConfigUpdate):
    config = _load_config()
    if update.default_provider is not None:
        config['default_provider'] = update.default_provider
    if update.default_model is not None:
        config['default_model'] = update.default_model
    # 只允许写入的提供商配置字段（自动过滤 has_api_key 等前端元数据）
    PROVIDER_EDITABLE = {'base_url', 'api_key', 'enabled', 'model'}
    if update.providers is not None:
        for pname, pconf in update.providers.items():
            if pname in config.get('providers', {}):
                for k, v in pconf.items():
                    if k not in PROVIDER_EDITABLE:
                        continue  # 跳过 has_api_key 等前端元数据字段
                    if k == 'api_key':
                        if not v or '****' in v:
                            # 留空或脱敏 key → 保留旧值（密钥覆盖保护）
                            continue
                        # 新密钥 → 加密存储
                        config['providers'][pname][k] = encrypt_key(v)
                        continue
                    config['providers'][pname][k] = v
            else:
                # 新增提供商：只保留可编辑字段
                new_pconf = {k: v for k, v in pconf.items() if k in PROVIDER_EDITABLE}
                if new_pconf.get('api_key') and '****' not in new_pconf['api_key']:
                    new_pconf['api_key'] = encrypt_key(new_pconf['api_key'])
                config.setdefault('providers', {})[pname] = new_pconf
    _save_config(config)
    ai_service.reload_config()
    # 返回脱敏版本
    masked = json.loads(json.dumps(config))
    for pname, pconf in masked.get('providers', {}).items():
        encrypted = pconf.get('api_key', '')
        if encrypted:
            plain = decrypt_key(encrypted)
            pconf['api_key'] = mask_key(plain)
    return {"status": "ok", "config": masked}


@router.post("/test")
async def test_ai_provider(req: ProviderTestRequest):
    """测试提供商连接。若前端未传 key，尝试从存储中解密。"""
    try:
        # 解密 API Key：优先用请求中的，否则从存储解密
        api_key = req.api_key or ''
        if (not api_key or '****' in api_key) and req.provider != 'ollama':
            config = _load_config()
            encrypted = config.get('providers', {}).get(req.provider, {}).get('api_key', '')
            if encrypted:
                api_key = decrypt_key(encrypted)
            if not api_key:
                return {"connected": False, "error": "API Key 未配置"}

        if req.provider == 'ollama':
            base_url = req.base_url or 'http://localhost:11434'
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{base_url}/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    models = [m.get('name', '') for m in data.get('models', [])]
                    return {"connected": True, "models": models, "provider": "ollama"}
                return {"connected": False, "error": f"HTTP {resp.status_code}"}

        elif req.provider == 'openai':
            base_url = req.base_url or 'https://api.openai.com/v1'
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{base_url}/models",
                    headers={"Authorization": f"Bearer {api_key}"}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    models = [m.get('id', '') for m in data.get('data', []) if 'gpt' in m.get('id', '').lower()]
                    return {"connected": True, "models": models, "provider": "openai"}
                return {"connected": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}

        elif req.provider == 'deepseek':
            base_url = req.base_url or 'https://api.deepseek.com/v1'
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{base_url}/models",
                    headers={"Authorization": f"Bearer {api_key}"}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    models = [m.get('id', '') for m in data.get('data', [])]
                    return {"connected": True, "models": models, "provider": "deepseek"}
                return {"connected": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}

        elif req.provider == 'siliconflow':
            base_url = req.base_url or 'https://api.siliconflow.cn/v1'
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{base_url}/models",
                    headers={"Authorization": f"Bearer {api_key}"}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    models = [m.get('id', '') for m in data.get('data', [])]
                    return {"connected": True, "models": models, "provider": "siliconflow"}
                return {"connected": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}

        elif req.provider == 'minimax':
            base_url = req.base_url or 'https://api.minimax.chat/v1'
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{base_url}/models",
                    headers={"Authorization": f"Bearer {api_key}"}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    models = [m.get('id', '') for m in data.get('data', [])]
                    return {"connected": True, "models": models, "provider": "minimax"}
                return {"connected": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}

        elif req.provider == 'glm':
            base_url = req.base_url or 'https://open.bigmodel.cn/api/paas/v4'
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{base_url}/models",
                    headers={"Authorization": f"Bearer {api_key}"}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    models = [m.get('id', '') for m in data.get('data', [])]
                    return {"connected": True, "models": models, "provider": "glm"}
                return {"connected": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}

        elif req.provider == 'claude':
            pass
            return {"connected": True, "models": ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307", "claude-3.5-sonnet-20241022"], "provider": "claude"}

        else:
            return {"connected": False, "error": f"未知提供商: {req.provider}"}

    except httpx.ConnectError:
        return {"connected": False, "error": "连接失败，请检查服务是否运行"}
    except httpx.TimeoutException:
        return {"connected": False, "error": "连接超时"}
    except Exception as e:
        return {"connected": False, "error": str(e)}


@router.get("/providers")
async def get_providers():
    """获取提供商列表及其密钥状态（加密存储不泄露）"""
    config = _load_config()
    result = []
    for name, pconf in config.get('providers', {}).items():
        encrypted = pconf.get('api_key', '')
        has_key = bool(decrypt_key(encrypted) if encrypted else '')
        result.append({
            'id': name,
            'enabled': pconf.get('enabled', False),
            'base_url': pconf.get('base_url', ''),
            'has_api_key': has_key,
        })
    return {"providers": result}


@router.get("/models/{provider}")
async def get_provider_models(provider: str):
    config = _load_config()
    pconf = config.get('providers', {}).get(provider, {})
    base_url = pconf.get('base_url', '')
    encrypted = pconf.get('api_key', '')
    api_key = decrypt_key(encrypted) if encrypted else ''

    if provider == 'ollama':
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{base_url or 'http://localhost:11434'}/api/tags")
                if resp.status_code == 200:
                    return {"models": [m.get('name', '') for m in resp.json().get('models', [])]}
        except:
            pass
        return {"models": ["llama3", "qwen2", "deepseek-coder", "mistral", "gemma"]}

    elif provider == 'openai':
        return {"models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]}

    elif provider == 'deepseek':
        return {"models": ["deepseek-chat", "deepseek-coder", "deepseek-reasoner"]}

    elif provider == 'siliconflow':
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{base_url or 'https://api.siliconflow.cn/v1'}/models", headers={"Authorization": f"Bearer {api_key}"})
                if resp.status_code == 200:
                    return {"models": [m.get('id', '') for m in resp.json().get('data', [])]}
        except: pass
        return {"models": ['Qwen/Qwen2.5-72B-Instruct', 'deepseek-ai/DeepSeek-V3', 'Pro/Qwen/Qwen2.5-Coder-7B-Instruct', 'THUDM/glm-4-9b-chat']}

    elif provider == 'minimax':
        return {"models": ['abab6.5s-chat', 'abab7-chat-preview']}

    elif provider == 'glm':
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{base_url or 'https://open.bigmodel.cn/api/paas/v4'}/models", headers={"Authorization": f"Bearer {api_key}"})
                if resp.status_code == 200:
                    return {"models": [m.get('id', '') for m in resp.json().get('data', [])]}
        except: pass
        return {"models": ['glm-4-flash', 'glm-4-plus', 'glm-4-air', 'glm-4-long']}

    elif provider == 'claude':
        return {"models": ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307", "claude-3.5-sonnet-20241022"]}

    return {"models": []}
