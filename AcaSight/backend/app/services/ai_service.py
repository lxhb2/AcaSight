"""
AI 服务
支持多模型：OpenAI, DeepSeek, Claude, Ollama
动态读取 ai_config.json 配置，不使用硬编码环境变量
"""

from typing import AsyncGenerator, List, Dict, Optional
import json
import os
import httpx
from app.config import settings
from app.services.crypto import decrypt_key
import structlog

logger = structlog.get_logger()

CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'ai_config.json')


def load_ai_config() -> dict:
    """从 ai_config.json 加载配置"""
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


class AIService:
    """AI 服务管理器 - 动态加载配置"""
    
    def __init__(self):
        self._config = load_ai_config()
    
    def reload_config(self):
        """重新加载配置"""
        self._config = load_ai_config()
    
    def _get_provider_config(self, provider: Optional[str] = None) -> tuple[str, dict]:
        """获取提供商名称和配置（自动解密 api_key）"""
        if provider is None:
            provider = self._config.get('default_provider', 'ollama')
        pconf = dict(self._config.get('providers', {}).get(provider, {}))
        # 透明解密 API Key（加密存储只在磁盘生效，内存中按需解密）
        encrypted = pconf.get('api_key', '')
        if encrypted:
            pconf['api_key'] = decrypt_key(encrypted)
        return provider, pconf
    
    # 每个 provider 的默认模型
    PROVIDER_DEFAULT_MODELS = {
        'ollama': 'qwen3.5:4b',
        'openai': 'gpt-4o',
        'deepseek': 'deepseek-chat',
        'siliconflow': 'Qwen/Qwen2.5-7B-Instruct',
        'minimax': 'abab6.5s-chat',
        'glm': 'glm-4-flash',
        'claude': 'claude-3-5-sonnet-20241022',
    }

    async def chat(
        self,
        messages: List[Dict[str, str]],
        provider: Optional[str] = None,
        model: Optional[str] = None,
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """AI 对话 - 文本生成（无工具调用），动态路由到具体提供商"""
        provider, pconf = self._get_provider_config(provider)
        base_url = pconf.get('base_url', '')
        api_key = pconf.get('api_key', '')
        
        if not model:
            model = pconf.get('model') or self.PROVIDER_DEFAULT_MODELS.get(provider, 'gpt-4o')
        
        if provider == 'ollama':
            base_url = base_url or 'http://localhost:11434'
            async for chunk in _chat_ollama(messages, model, base_url, stream, temperature, max_tokens):
                yield chunk
        elif provider in ('openai', 'deepseek', 'siliconflow', 'minimax', 'glm'):
            if not api_key:
                yield f"[错误] {provider} API Key 未配置。请在设置中配置。"
                return
            if not base_url:
                base_url = {'openai': 'https://api.openai.com/v1', 'deepseek': 'https://api.deepseek.com/v1',
                            'siliconflow': 'https://api.siliconflow.cn/v1', 'minimax': 'https://api.minimax.chat/v1',
                            'glm': 'https://open.bigmodel.cn/api/paas/v4'}.get(provider, '')
            async for chunk in _chat_openai(messages, model, base_url, api_key, stream, temperature, max_tokens):
                yield chunk
        elif provider == 'claude':
            if not api_key:
                yield f"[错误] Claude API Key 未配置。请在设置中配置。"
                return
            async for chunk in _chat_claude(messages, model, api_key, stream, temperature, max_tokens):
                yield chunk
        else:
            yield f"[错误] 未知提供商: {provider}"

    async def chat_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict],
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: Optional[int] = 4096,
    ) -> Dict:
        """AI 对话带工具调用（Function Calling）
        
        发送消息和工具定义给模型，返回结构化的工具调用和文本响应。
        适用于 OpenAI 兼容的 API（OpenAI / DeepSeek / 硅基流动 / MiniMax / GLM）。
        
        Args:
            messages: 对话消息列表
            tools: OpenAI 格式的工具定义 [{"type":"function","function":{...}}]
            provider: AI 提供商
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大生成长度
            
        Returns:
            {"content": str, "tool_calls": [{"name": str, "arguments": dict}]}
        """
        provider, pconf = self._get_provider_config(provider)
        base_url = pconf.get('base_url', '')
        api_key = pconf.get('api_key', '')
        
        if not model:
            model = pconf.get('model') or self.PROVIDER_DEFAULT_MODELS.get(provider, 'gpt-4o')
        
        # 目前仅 OpenAI 兼容 API 支持 function calling
        if provider in ('openai', 'deepseek', 'siliconflow', 'minimax', 'glm'):
            if not api_key:
                return {"content": f"[错误] {provider} API Key 未配置。", "tool_calls": []}
            if not base_url:
                provider_urls = {
                    'openai': 'https://api.openai.com/v1',
                    'deepseek': 'https://api.deepseek.com/v1',
                    'siliconflow': 'https://api.siliconflow.cn/v1',
                    'minimax': 'https://api.minimax.chat/v1',
                    'glm': 'https://open.bigmodel.cn/api/paas/v4',
                }
                base_url = provider_urls.get(provider, '')
            return await _chat_openai_with_tools(messages, model, base_url, api_key, tools, temperature, max_tokens)
        elif provider == 'ollama':
            # Ollama 也支持 tools
            base_url = base_url or 'http://localhost:11434'
            return await _chat_ollama_with_tools(messages, model, base_url, tools, temperature, max_tokens)
        elif provider == 'claude':
            # Claude 通过 tool_use 格式支持
            if not api_key:
                return {"content": "[错误] Claude API Key 未配置。", "tool_calls": []}
            return await _chat_claude_with_tools(messages, model, api_key, tools, temperature, max_tokens)
        else:
            return {"content": f"[错误] 不支持的提供商: {provider}", "tool_calls": []}

    async def get_available_providers_with_tools(self) -> List[str]:
        """返回支持 function calling 的 provider 列表
        
        优先返回有 API Key 且启用的云端 provider，
        Ollama 仅作为最后兜底。
        """
        cloud_providers = ['siliconflow', 'deepseek', 'openai', 'minimax', 'glm', 'claude']
        local_providers = ['ollama']
        
        available = []
        for name in cloud_providers:
            pconf = self._config.get('providers', {}).get(name, {})
            if not pconf.get('enabled', False):
                continue
            encrypted = pconf.get('api_key', '')
            # 尝试解密判断密钥是否有效
            if encrypted and decrypt_key(encrypted):
                available.append(name)
        
        # Ollama 作为兜底
        if not available:
            for name in local_providers:
                pconf = self._config.get('providers', {}).get(name, {})
                if pconf.get('enabled', False):
                    available.append(name)
        
        return available or [self._config.get('default_provider', 'ollama')]
    
    async def generate_summary(self, text: str, max_length: int = 500) -> str:
        messages = [
            {"role": "system", "content": "你是一个学术助手。请为以下论文生成简洁的摘要，突出研究问题、方法、主要发现和意义。"},
            {"role": "user", "content": f"请为以下论文生成摘要（不超过 {max_length} 字）：\n\n{text[:8000]}"}
        ]
        response = ""
        async for chunk in self.chat(messages, temperature=0.3):
            response += chunk
        return response
    
    async def translate(self, text: str, target_language: str = "zh") -> str:
        lang_names = {"zh": "中文", "en": "英文", "ja": "日文", "de": "德文", "fr": "法文"}
        messages = [
            {"role": "system", "content": f"你是一个专业翻译。请将以下学术文本翻译成{lang_names.get(target_language, target_language)}，保持学术术语的准确性。"},
            {"role": "user", "content": text[:4000]}
        ]
        response = ""
        async for chunk in self.chat(messages, temperature=0.3):
            response += chunk
        return response
    
    async def deep_read_paper(self, text: str, title: str) -> str:
        prompt = f"""请对以下学术文献进行深度精读分析，文献标题：《{title}》
文献内容（节选）：{text[:3000]}
请按以下结构输出分析报告：
## 核心论点（3-5条核心观点）
## 研究方法（使用了哪些研究方法）
## 主要结论
## 创新点
## 局限性
## 关键词（5-8个）"""
        messages = [
            {"role": "system", "content": "你是专业学术文献分析专家。"},
            {"role": "user", "content": prompt}
        ]
        response = ""
        async for chunk in self.chat(messages, temperature=0.3):
            response += chunk
        return response
    
    async def generate_literature_review(self, papers: List[Dict], topic: str, extra_instruction: str = "") -> str:
        refs_text = ""
        for i, p in enumerate(papers, 1):
            title = p.get("title", "")
            authors = p.get("authors", [])
            author_str = ", ".join(authors[:3]) if isinstance(authors, list) else str(authors)
            year = p.get("year", "")
            abstract = (p.get("abstract", "") or "")[:300]
            refs_text += f"\n[{i}] {author_str}. {title} ({year})\n摘要: {abstract}\n"
        messages = [
            {"role": "system", "content": "你是学术文献综述专家。请根据以下文献撰写文献综述。"},
            {"role": "user", "content": f"主题: {topic}\n\n文献列表:\n{refs_text}\n\n请撰写文献综述，分析各研究的关系、差异和趋势。"}
        ]
        response = ""
        async for chunk in self.chat(messages, temperature=0.7):
            response += chunk
        return response
    
    async def find_research_gaps(self, papers: List[Dict]) -> str:
        papers_text = ""
        for i, p in enumerate(papers, 1):
            papers_text += f"\n{i}. {p.get('title', '')} - {p.get('abstract', '')[:300]}\n"
        messages = [
            {"role": "system", "content": "你是一个学术研究专家。请分析以下文献，识别研究空白和未来的研究方向。"},
            {"role": "user", "content": f"请分析以下文献，识别研究空白：\n\n{papers_text}"}
        ]
        response = ""
        async for chunk in self.chat(messages, temperature=0.7):
            response += chunk
        return response
    
    def get_available_providers(self) -> List[Dict]:
        providers = []
        for name, pconf in self._config.get('providers', {}).items():
            providers.append({
                'name': name,
                'available': pconf.get('enabled', False),
                'models': self._get_default_models(name),
                'model': pconf.get('model', ''),
                'enabled': pconf.get('enabled', False),
            })
        return providers
    
    def _get_default_models(self, provider: str) -> List[str]:
        defaults = {
            'ollama': ['llama3', 'qwen2', 'deepseek-coder', 'mistral', 'gemma'],
            'openai': ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo'],
            'deepseek': ['deepseek-chat', 'deepseek-coder', 'deepseek-reasoner'],
            'siliconflow': ['Qwen/Qwen2.5-72B-Instruct', 'deepseek-ai/DeepSeek-V3', 'Pro/Qwen/Qwen2.5-Coder-7B-Instruct', 'Qwen/Qwen2.5-7B-Instruct', 'THUDM/glm-4-9b-chat'],
            'minimax': ['abab6.5s-chat', 'abab7-chat-preview'],
            'glm': ['glm-4-flash', 'glm-4-plus', 'glm-4-air', 'glm-4-long'],
            'claude': ['claude-3-opus-20240229', 'claude-3-sonnet-20240229', 'claude-3-haiku-20240307', 'claude-3.5-sonnet-20241022'],
        }
        return defaults.get(provider, [])


# ==================== 底层对话函数 ====================


async def _chat_ollama(
    messages: List[Dict], model: Optional[str], base_url: str,
    stream: bool, temperature: float, max_tokens: Optional[int]
) -> AsyncGenerator[str, None]:
    """
    Ollama 对话 — 使用 /api/generate 端点（Ollama 0.22.0 的 /api/chat 有 hang 问题）
    将 messages 格式转换为 prompt 文本
    """
    import aiohttp

    # 构建 prompt：将 messages 列表转换为纯文本
    prompt_parts = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if role == "system":
            prompt_parts.append(f"System: {content}")
        elif role == "assistant":
            prompt_parts.append(f"Assistant: {content}")
        else:
            prompt_parts.append(f"User: {content}")
    prompt = "\n\n".join(prompt_parts) + "\n\nAssistant:"

    payload = {
        "model": model or "llama2",
        "prompt": prompt,
        "stream": stream,
        "options": {"temperature": temperature},
    }
    if max_tokens:
        payload["options"]["num_predict"] = max_tokens

    timeout = aiohttp.ClientTimeout(total=300)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        if stream:
            async with session.post(f"{base_url}/api/generate", json=payload) as resp:
                if resp.status >= 400:
                    text = await resp.text()
                    yield f"[Ollama 错误 ({resp.status})] {text[:200]}"
                    return
                buffer = b""
                async for chunk in resp.content.iter_chunks():
                    data_chunk, _ = chunk
                    if not data_chunk:
                        break
                    buffer += data_chunk
                    while b"\n" in buffer:
                        line, buffer = buffer.split(b"\n", 1)
                        line = line.strip()
                        if line:
                            try:
                                data = json.loads(line)
                                if data.get("done"):
                                    return
                                if "response" in data:
                                    yield data["response"]
                            except json.JSONDecodeError:
                                continue
        else:
            async with session.post(f"{base_url}/api/generate", json=payload) as resp:
                if resp.status >= 400:
                    text = await resp.text()
                    yield f"[Ollama 错误 ({resp.status})] {text[:200]}"
                    return
                data = await resp.json()
                if "response" in data:
                    yield data["response"]
                else:
                    yield str(data)


async def _chat_openai(
    messages: List[Dict], model: Optional[str], base_url: str, api_key: str,
    stream: bool, temperature: float, max_tokens: Optional[int]
) -> AsyncGenerator[str, None]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model or "gpt-4o",
        "messages": messages,
        "temperature": temperature,
        "stream": stream,
    }
    if max_tokens:
        payload["max_tokens"] = max_tokens
    async with httpx.AsyncClient(timeout=120) as client:
        if stream:
            async with client.stream("POST", f"{base_url}/chat/completions", headers=headers, json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            d = json.loads(data)
                            c = d["choices"][0]["delta"].get("content", "")
                            if c:
                                yield c
                        except:
                            pass
        else:
            resp = await client.post(f"{base_url}/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            yield resp.json()["choices"][0]["message"]["content"]


async def _chat_claude(
    messages: List[Dict], model: Optional[str], api_key: str,
    stream: bool, temperature: float, max_tokens: Optional[int]
) -> AsyncGenerator[str, None]:
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    # Claude requires 'system' as separate field
    system_msg = ""
    filtered = []
    for m in messages:
        if m["role"] == "system":
            system_msg = m["content"]
        else:
            filtered.append({"role": m["role"], "content": m["content"]})
    payload = {
        "model": model or "claude-3-sonnet-20240229",
        "messages": filtered,
        "temperature": temperature,
        "max_tokens": max_tokens or 4096,
        "stream": stream,
    }
    if system_msg:
        payload["system"] = system_msg
    async with httpx.AsyncClient(timeout=120) as client:
        if stream:
            payload["stream"] = True
            async with client.stream("POST", "https://api.anthropic.com/v1/messages", headers=headers, json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            if data.get("type") == "content_block_delta":
                                yield data["delta"]["text"]
                        except:
                            pass
        else:
            resp = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
            resp.raise_for_status()
            yield resp.json()["content"][0]["text"]


# ==================== Function Calling 对话函数 ====================


async def _chat_openai_with_tools(
    messages: List[Dict], model: str, base_url: str, api_key: str,
    tools: List[Dict], temperature: float, max_tokens: int
) -> Dict:
    """OpenAI 兼容 API 的 function calling 调用
    
    Returns:
        {"content": str, "tool_calls": [{"name": str, "arguments": dict}]}
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "tools": tools,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(f"{base_url}/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            
            choice = data["choices"][0]
            message = choice.get("message", {})
            
            content = message.get("content", "") or ""
            raw_tool_calls = message.get("tool_calls", [])
            
            tool_calls = []
            for tc in raw_tool_calls:
                try:
                    args = json.loads(tc["function"]["arguments"])
                except (json.JSONDecodeError, KeyError):
                    args = {}
                tool_calls.append({
                    "id": tc.get("id", ""),
                    "name": tc["function"]["name"],
                    "arguments": args,
                })
            
            return {
                "content": content,
                "tool_calls": tool_calls,
                "finish_reason": choice.get("finish_reason", "stop"),
            }
    except httpx.HTTPStatusError as e:
        logger.error(f"OpenAI tools call failed: {e.response.status_code} {e.response.text[:200]}")
        return {"content": f"[API 错误: {e.response.status_code}]", "tool_calls": [], "error": str(e)}
    except Exception as e:
        logger.error(f"OpenAI tools call exception: {e}")
        return {"content": f"[请求失败: {str(e)}]", "tool_calls": [], "error": str(e)}


async def _chat_ollama_with_tools(
    messages: List[Dict], model: str, base_url: str,
    tools: List[Dict], temperature: float, max_tokens: int
) -> Dict:
    """Ollama 的 function calling 调用"""
    # 转换 tools 格式为 Ollama 格式
    ollama_tools = []
    for t in tools:
        if t.get("type") == "function":
            func = t.get("function", {})
            ollama_tools.append({
                "type": "function",
                "function": {
                    "name": func.get("name", ""),
                    "description": func.get("description", ""),
                    "parameters": func.get("parameters", {}),
                }
            })
    
    payload = {
        "model": model,
        "messages": messages,
        "tools": ollama_tools,
        "stream": False,
        "options": {"temperature": temperature, "num_predict": max_tokens},
    }
    try:
        async with httpx.AsyncClient(timeout=180) as client:
            resp = await client.post(f"{base_url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
            
            msg = data.get("message", {})
            content = msg.get("content", "") or ""
            raw_tool_calls = msg.get("tool_calls", [])
            
            tool_calls = []
            for tc in raw_tool_calls:
                func = tc.get("function", {})
                try:
                    args = json.loads(func.get("arguments", "{}")) if isinstance(func.get("arguments"), str) else func.get("arguments", {})
                except (json.JSONDecodeError, TypeError):
                    args = {}
                tool_calls.append({
                    "id": tc.get("id", ""),
                    "name": func.get("name", ""),
                    "arguments": args,
                })
            
            return {
                "content": content,
                "tool_calls": tool_calls,
                "finish_reason": data.get("done_reason", "stop"),
            }
    except Exception as e:
        logger.error(f"Ollama tools call failed: {e}")
        return {"content": f"[错误: {str(e)}]", "tool_calls": [], "error": str(e)}


async def _chat_claude_with_tools(
    messages: List[Dict], model: str, api_key: str,
    tools: List[Dict], temperature: float, max_tokens: int
) -> Dict:
    """Claude 的 function calling 调用（通过 tool_use）"""
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    
    # Claude 需要将 system 消息分离
    system_msg = ""
    filtered = []
    for m in messages:
        if m["role"] == "system":
            system_msg = m["content"]
        else:
            filtered.append({"role": m["role"], "content": m["content"]})
    
    # 转换 tools 格式为 Claude 格式
    claude_tools = []
    for t in tools:
        if t.get("type") == "function":
            func = t.get("function", {})
            claude_tools.append({
                "name": func.get("name", ""),
                "description": func.get("description", ""),
                "input_schema": func.get("parameters", {}),
            })
    
    payload = {
        "model": model,
        "messages": filtered,
        "tools": claude_tools,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if system_msg:
        payload["system"] = system_msg
    
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            
            content = ""
            tool_calls = []
            
            for block in data.get("content", []):
                if block.get("type") == "text":
                    content += block.get("text", "")
                elif block.get("type") == "tool_use":
                    tool_calls.append({
                        "id": block.get("id", ""),
                        "name": block.get("name", ""),
                        "arguments": block.get("input", {}),
                    })
            
            return {
                "content": content,
                "tool_calls": tool_calls,
                "finish_reason": data.get("stop_reason", "end_turn"),
            }
    except Exception as e:
        logger.error(f"Claude tools call failed: {e}")
        return {"content": f"[错误: {str(e)}]", "tool_calls": [], "error": str(e)}


ai_service = AIService()
