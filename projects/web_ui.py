#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pulse Learning System - Web UI v2.1
修复：状态缓存键名错误、后台线程超时、流式响应 provider 判断、快速命令响应
"""
import os
import sys
import json
import time
import threading
from datetime import datetime

from flask import Flask, render_template_string, request, jsonify, session, Response

# 设置工作目录
PROJECTS_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECTS_DIR)
sys.path.insert(0, os.path.join(PROJECTS_DIR, "src"))

# 添加脉冲学习记忆系统路径
PULSE_LEARNING_DIR = r"D:\四季如歌\新建文件夹\脉冲学习"
sys.path.insert(0, PULSE_LEARNING_DIR)

# 初始化记忆桥接
try:
    from web_memory_bridge import get_bridge
    _memory_bridge = get_bridge()
    print("[Memory] 记忆系统已加载")
except Exception as e:
    _memory_bridge = None
    print(f"[Memory] 记忆系统加载失败: {e}")

app = Flask(__name__)
app.secret_key = 'pulse-learning-secret-key-2026'
app.config['JSON_AS_ASCII'] = False

# ==================== 状态缓存（后台5秒刷新，不阻塞主线程） ====================
_status_cache = {
    'online': False,
    'ollama': False,
    'lmstudio': False,
    'provider': 'unknown',
    'model': 'unknown',
    'last_update': 0,
    '_lock': threading.Lock(),
    '_running': False
}
_CACHE_TTL = 5  # 秒


def _refresh_status_cache():
    """后台刷新状态缓存（短超时，不阻塞）"""
    try:
        from utils.llm_client import is_online, check_ollama_available, check_lmstudio_available
        online = is_online(timeout=1)
    except Exception:
        online = False
    try:
        ollama = check_ollama_available(timeout=1)
    except Exception:
        ollama = False
    try:
        lmstudio = check_lmstudio_available(timeout=1)
    except Exception:
        lmstudio = False

    # 读取配置确定 provider 和 model
    try:
        from utils.llm_client import load_model_config
        config = load_model_config()
        providers = config.get("providers", {})
    except Exception:
        providers = {}

    if online:
        p = providers.get("online", {})
        if p and p.get("api_key"):
            provider_name = p.get("provider", "siliconflow")
            model = p.get("model", "unknown")
        elif lmstudio:
            p = providers.get("offline_lmstudio", {})
            provider_name = "lmstudio"
            model = p.get("model", "unknown")
        elif ollama:
            p = providers.get("offline_ollama", {})
            provider_name = "ollama"
            model = p.get("model", "unknown")
        else:
            provider_name = "offline"
            model = "none"
    elif lmstudio:
        p = providers.get("offline_lmstudio", {})
        provider_name = "lmstudio"
        model = p.get("model", "unknown")
    elif ollama:
        p = providers.get("offline_ollama", {})
        provider_name = "ollama"
        model = p.get("model", "unknown")
    else:
        provider_name = "offline"
        model = "none"

    with _status_cache['_lock']:
        _status_cache['online'] = online
        _status_cache['ollama'] = ollama
        _status_cache['lmstudio'] = lmstudio
        _status_cache['provider'] = provider_name
        _status_cache['model'] = model
        _status_cache['last_update'] = time.time()


def _start_status_bg_thread():
    """启动后台状态刷新线程"""
    if _status_cache['_running']:
        return
    _status_cache['_running'] = True

    def _bg():
        while _status_cache['_running']:
            try:
                _refresh_status_cache()
            except Exception:
                pass
            time.sleep(_CACHE_TTL)

    t = threading.Thread(target=_bg, daemon=True)
    t.start()


def _get_cached_status() -> dict:
    """获取缓存的状态（立即返回，不阻塞）"""
    with _status_cache['_lock']:
        return {
            'online': _status_cache['online'],
            'ollama': _status_cache['ollama'],
            'lmstudio': _status_cache['lmstudio'],
            'provider': _status_cache['provider'],
            'model': _status_cache['model'],
        }


# ==================== 会话初始化 ====================

def _init_session():
    if 'current_project' not in session:
        session['current_project'] = None
    if 'mode' not in session:
        session['mode'] = 'auto'
    if 'use_light' not in session:
        session['use_light'] = True
    if 'history' not in session:
        session['history'] = []


# ==================== 文件工具 ====================

def _read_file_safe(path: str) -> str:
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
    except Exception:
        pass
    return ""


def _write_file_safe(path: str, content: str) -> bool:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception:
        return False


# ==================== 项目/模块工具 ====================

def _get_pulse_dir() -> str:
    return r"D:\四季如歌\新建文件夹\脉冲学习"


def list_projects_fast() -> list:
    """快速列出项目（目录扫描，不调 LLM）"""
    pulse_dir = _get_pulse_dir()
    projects = []
    if os.path.exists(pulse_dir):
        for d in os.listdir(pulse_dir):
            if os.path.isdir(os.path.join(pulse_dir, d)):
                index_file = os.path.join(pulse_dir, d, "_index.md")
                if os.path.exists(index_file):
                    projects.append(d)
    return projects


def _list_project_files(project_name: str) -> list:
    """列出项目文件"""
    pulse_dir = _get_pulse_dir()
    project_dir = os.path.join(pulse_dir, project_name)
    files = []
    if os.path.exists(project_dir):
        for f in os.listdir(project_dir):
            if f.endswith('.md'):
                files.append(f)
        modules_dir = os.path.join(project_dir, 'modules')
        if os.path.exists(modules_dir):
            for f in os.listdir(modules_dir):
                if f.endswith('.md'):
                    files.append(f'modules/{f}')
    return files


def _check_and_execute_tool(message: str) -> dict:
    """
    检查用户消息是否需要执行工具，并执行
    返回: {'tool': 工具名, 'result': 结果} 或 None
    """
    message_lower = message.lower()
    
    # 工具1: 创建项目
    if any(kw in message_lower for kw in ['创建项目', '新项目', '开始项目', 'new project']):
        # 提取项目名称和描述
        import re
        project_name = None
        description = ""
        
        # 尝试提取 "创建项目 xxx" 或 "创建项目：xxx"
        match = re.search(r'创建项目[：:]?\s*(.+?)(?:，|,|。|\n|$)', message)
        if match:
            parts = match.group(1).split('，', 1)
            project_name = parts[0].strip()
            if len(parts) > 1:
                description = parts[1].strip()
        
        # 如果没提取到，尝试其他模式
        if not project_name:
            match = re.search(r'我想(?:开始|创建|学)[习]?\s*(.+?)(?:，|,|。|\n|$)', message)
            if match:
                project_name = match.group(1).strip()
        
        if project_name:
            try:
                from tools.pulse_tools import create_project
                result = create_project(project_name, description or f"{project_name} 学习项目")
                return {'tool': f'create_project("{project_name}")', 'result': result}
            except Exception as e:
                return {'tool': 'create_project', 'result': f'❌ 错误: {str(e)}'}
    
    # 工具2: 列出项目
    if any(kw in message_lower for kw in ['列出项目', '所有项目', '查看项目', 'list projects', '我的项目']):
        try:
            from tools.pulse_tools import list_projects
            result = list_projects()
            return {'tool': 'list_projects()', 'result': result}
        except Exception as e:
            return {'tool': 'list_projects', 'result': f'❌ 错误: {str(e)}'}
    
    # 工具3: 查看项目状态
    if any(kw in message_lower for kw in ['项目状态', '进度', 'status']):
        try:
            from tools.pulse_tools import get_project_status
            # 尝试提取项目名称
            import re
            match = re.search(r'(?:项目)?[：:]?\s*["\']?([^"\']+?)["\']?(?:的)?(?:状态|进度)', message)
            project_name = match.group(1).strip() if match else None
            
            result = get_project_status(project_name)
            return {'tool': f'get_project_status("{project_name or "current"}")', 'result': result}
        except Exception as e:
            return {'tool': 'get_project_status', 'result': f'❌ 错误: {str(e)}'}
    
    # 工具4: 创建模块
    if any(kw in message_lower for kw in ['创建模块', '新模块', '添加模块', 'new module']) or message.strip() in ['1', '2', '3', '4', '5']:
        try:
            from tools.pulse_tools import create_module, list_projects
            import re
            
            # 数字选择映射
            module_map = {
                '1': '网络基础',
                '2': 'Web安全入门', 
                '3': '信息收集',
                '4': '漏洞挖掘实战',
                '5': '漏洞报告编写'
            }
            
            msg_stripped = message.strip()
            if msg_stripped in module_map:
                module_name = module_map[msg_stripped]
            else:
                # 提取模块名
                match = re.search(r'(?:创建|添加)模块[：:]?\s*(.+?)(?:，|,|。|\n|$)', message)
                module_name = match.group(1).strip() if match else "新模块"
            
            # 获取当前活跃项目
            projects_result = list_projects()
            # 尝试从列表中提取第一个项目名
            import re as re_module
            project_match = re_module.search(r'## \d+\.\s*(.+?)\s+', projects_result)
            if project_match:
                project_name = project_match.group(1).strip()
            else:
                return {'tool': 'create_module', 'result': '❌ 错误: 没有找到任何项目，请先创建项目'}
            
            result = create_module(project_name=project_name, module_name=module_name, module_goal=f"学习{module_name}", estimated_time=30)
            return {'tool': f'create_module("{project_name}", "{module_name}")', 'result': result}
        except Exception as e:
            return {'tool': 'create_module', 'result': f'❌ 错误: {str(e)}'}
    
    # 工具5: 完成挑战
    if any(kw in message_lower for kw in ['完成挑战', '标记完成', 'done', 'complete']):
        try:
            from tools.pulse_tools import complete_challenge
            import re
            # 尝试提取项目名、模块ID、挑战ID
            result = complete_challenge()  # 使用默认参数
            return {'tool': 'complete_challenge()', 'result': result}
        except Exception as e:
            return {'tool': 'complete_challenge', 'result': f'❌ 错误: {str(e)}'}
    
    # 工具6: 查看徽章
    if any(kw in message_lower for kw in ['徽章', 'badge', '成就', '我的徽章']):
        try:
            from tools.badge_manager import get_badge_manager
            bm = get_badge_manager()
            result = bm.get_status_text()
            return {'tool': 'badge_manager.get_status_text()', 'result': result}
        except Exception as e:
            return {'tool': 'badge_manager', 'result': f'❌ 错误: {str(e)}'}
    
    # 工具7: 查看学习统计
    if any(kw in message_lower for kw in ['统计', 'stats', '学习统计', '我的统计', '进度统计']):
        try:
            from tools.pulse_tools import get_learning_stats
            # 检查是否有项目名称
            project_match = re.search(r'统计\s+(.+)', message)
            project_name = project_match.group(1).strip() if project_match else None
            result = get_learning_stats(project_name)
            return {'tool': 'get_learning_stats()', 'result': result}
        except Exception as e:
            return {'tool': 'get_learning_stats', 'result': f'❌ 错误: {str(e)}'}
    
    return None


def get_client_info() -> dict:
    """获取客户端状态信息（使用缓存）"""
    cached = _get_cached_status()
    force_mode = session.get('mode', 'auto')
    # 如果用户手动选了 provider，覆盖缓存的 provider/model
    if force_mode == 'online':
        cached['provider'] = 'siliconflow'
        try:
            from utils.llm_client import load_model_config
            cfg = load_model_config()
            cached['model'] = cfg.get("providers", {}).get("online", {}).get("model", "unknown")
        except Exception:
            cached['model'] = "unknown"
    elif force_mode == 'ollama':
        cached['provider'] = 'ollama'
        try:
            from utils.llm_client import load_model_config
            cfg = load_model_config()
            cached['model'] = cfg.get("providers", {}).get("offline_ollama", {}).get("model", "unknown")
        except Exception:
            cached['model'] = "unknown"
    elif force_mode == 'lmstudio':
        cached['provider'] = 'lmstudio'
        try:
            from utils.llm_client import load_model_config
            cfg = load_model_config()
            cached['model'] = cfg.get("providers", {}).get("offline_lmstudio", {}).get("model", "unknown")
        except Exception:
            cached['model'] = "unknown"

    cached['mode'] = force_mode
    cached['light'] = session.get('use_light', True)
    cached['current_project'] = session.get('current_project')
    return cached


# ==================== 流式聊天 ====================

def send_to_llm_stream(message: str):
    """流式发送消息到 LLM，逐字返回（旧接口，已弃用）"""
    return _do_llm_stream(
        message,
        session.get('mode', 'auto') if session.get('mode') != 'auto' else None,
        session.get('use_light', True),
        list(session.get('history', []))
    )


def _do_llm_stream(message: str, force_mode: str, use_light: bool, history: list = None):
    """流式发送消息到 LLM — 接收显式参数，不依赖 Flask session"""
    from utils.llm_client import create_client
    from utils.prompt_builder import (
        build_pulse_learning_system_prompt,
        build_pulse_learning_system_prompt_light
    )

    try:
        client = create_client(force_mode=force_mode if force_mode != 'auto' else None)
    except Exception as e:
        yield f"[LLM client error: {e}]"
        return

    try:
        if use_light:
            prompt = build_pulse_learning_system_prompt_light(language="中文")
        else:
            prompt = build_pulse_learning_system_prompt(language="中文")
    except Exception as e:
        yield f"[Prompt error: {e}]"
        return

    messages = [{"role": "system", "content": prompt}]
    # 优先使用新的记忆系统获取历史
    if _memory_bridge:
        try:
            history = _memory_bridge.get_chat_history_for_llm(limit=10)
            messages.extend(history)
        except Exception as e:
            print(f"[Memory] 获取历史失败: {e}")
    elif history:
        messages.extend(history)
    messages.append({"role": "user", "content": message})

    import requests as req

    full_content = ""
    
    # 工具调用检测 - 在发送给 LLM 之前先检查是否需要工具
    tool_result = _check_and_execute_tool(message)
    if tool_result:
        # 发送工具调用状态
        yield f"\n🔧 **执行工具**: {tool_result['tool']}\n\n"
        if tool_result['result']:
            # 将工具结果加入上下文
            messages.append({"role": "assistant", "content": f"我已执行工具: {tool_result['tool']}\n结果:\n{tool_result['result']}"})
            full_content += f"{tool_result['result']}\n\n"
    try:
        if client._is_openai_compat:
            # OpenAI 兼容 API 流式
            headers = {"Content-Type": "application/json"}
            if client.api_key and client.api_key not in ("ollama", "lm-studio", ""):
                headers["Authorization"] = f"Bearer {client.api_key}"
            payload = {
                "model": client.model,
                "messages": messages,
                "temperature": client.temperature,
                "stream": True,
                "max_tokens": 2048
            }
            resp = req.post(client._chat_url, json=payload, headers=headers,
                            stream=True, timeout=client.timeout)
            if resp.status_code != 200:
                yield f"[API error {resp.status_code}: {resp.text[:200]}]"
                return
            for line in resp.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            delta = data.get("choices", [{}])[0].get("delta", {})
                            chunk = delta.get("content", "")
                            if chunk:
                                full_content += chunk
                                yield chunk
                        except json.JSONDecodeError:
                            continue
        else:
            # Ollama 流式
            payload = {
                "model": client.model,
                "messages": messages,
                "temperature": client.temperature,
                "stream": True
            }
            resp = req.post(client._chat_url, json=payload, stream=True, timeout=client.timeout)
            resp.raise_for_status()
            for line in resp.iter_lines():
                if line:
                    try:
                        data = json.loads(line.decode('utf-8'))
                        chunk = data.get("message", {}).get("content", "")
                        if chunk:
                            full_content += chunk
                            yield chunk
                    except json.JSONDecodeError:
                        continue

    except Exception as e:
        # 如果流式失败，尝试非流式
        try:
            response = client.chat(messages=messages, temperature=client.temperature)
            full_content = response["message"]["content"]
            yield full_content
        except Exception as e2:
            yield f"\nLLM request failed: {str(e2)}"

    # 注意：不在此处保存历史（session 不可用），由调用方处理


def _save_chat_history(message: str, response: str):
    """在 request context 内保存聊天历史"""
    _init_session()
    session['history'] = session.get('history', [])
    session['history'].append({"role": "user", "content": message})
    session['history'].append({"role": "assistant", "content": response})
    if len(session['history']) > 20:
        session['history'] = session['history'][-20:]


def send_to_llm(message: str) -> str:
    """非流式发送（用于快速命令）"""
    from utils.llm_client import create_client
    from utils.prompt_builder import (
        build_pulse_learning_system_prompt,
        build_pulse_learning_system_prompt_light
    )

    client = create_client(force_mode=session.get('mode') if session.get('mode') != 'auto' else None)
    prompt = build_pulse_learning_system_prompt_light(language="中文") if session.get('use_light', True) \
        else build_pulse_learning_system_prompt(language="中文")
    messages = [{"role": "system", "content": prompt}]
    messages.extend(session.get('history', []))
    messages.append({"role": "user", "content": message})
    try:
        response = client.chat(messages=messages, temperature=client.temperature)
        content = response["message"]["content"]
        session['history'] = session.get('history', [])
        session['history'].append({"role": "user", "content": message})
        session['history'].append({"role": "assistant", "content": content})
        if len(session['history']) > 20:
            session['history'] = session['history'][-20:]
        return content
    except Exception as e:
        return f"❌ 错误: {str(e)}"


# ==================== HTML 模板 ====================

HTML_TEMPLATE = r'''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🎯 Pulse Learning System</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    min-height: 100vh; color: #e0e0e0;
}
.container { max-width: 900px; margin: 0 auto; padding: 20px; min-height: 100vh; display: flex; flex-direction: column; }
.status-bar {
    display: flex; justify-content: space-between; align-items: center;
    padding: 12px 20px; background: rgba(255,255,255,0.05);
    border-radius: 12px; margin-bottom: 15px;
    backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.1);
}
.status-left { display: flex; align-items: center; gap: 15px; }
.status-badge { padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; }
.badge-online { background: #10b981; color: #fff; }
.badge-offline { background: #ef4444; color: #fff; }
.badge-light { background: #6366f1; color: #fff; }
.badge-full { background: #ec4899; color: #fff; }
.model-info { font-size: 12px; color: #888; }
.project-badge { background: rgba(16,185,129,0.2); color: #10b981; padding: 4px 12px; border-radius: 20px; font-size: 12px; }
.chat-area {
    flex: 1; display: flex; flex-direction: column;
    background: rgba(255,255,255,0.03); border-radius: 16px;
    overflow: hidden; border: 1px solid rgba(255,255,255,0.08);
}
.chat-messages { flex: 1; padding: 20px; overflow-y: auto; min-height: 400px; max-height: 60vh; }
.message { margin-bottom: 16px; animation: fadeIn 0.3s ease; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
.message-user {
    background: linear-gradient(135deg, #3b82f6, #6366f1); color: white;
    padding: 12px 16px; border-radius: 16px 16px 4px 16px;
    max-width: 80%; margin-left: auto; word-wrap: break-word;
}
.message-assistant {
    background: rgba(255,255,255,0.08); padding: 12px 16px;
    border-radius: 16px 16px 16px 4px; max-width: 85%;
    word-wrap: break-word; line-height: 1.6;
}
.message-assistant pre { background: #1a1a2e; padding: 12px; border-radius: 8px; overflow-x: auto; margin: 8px 0; }
.message-assistant code { font-family: 'Fira Code', monospace; font-size: 13px; }
.message-assistant table { border-collapse: collapse; width: 100%; margin: 10px 0; }
.message-assistant th, .message-assistant td { border: 1px solid rgba(255,255,255,0.1); padding: 8px 12px; text-align: left; }
.message-assistant th { background: rgba(255,255,255,0.05); }
.tool-call { 
    background: linear-gradient(135deg, rgba(59,130,246,0.2), rgba(99,102,241,0.2)); 
    border: 1px solid rgba(99,102,241,0.4);
    border-radius: 12px; 
    padding: 12px 16px; 
    margin: 12px 0;
    font-size: 13px;
}
.tool-call-header { 
    display: flex; 
    align-items: center; 
    gap: 8px; 
    color: #818cf8; 
    font-weight: 600;
    margin-bottom: 8px;
}
.tool-call-content { 
    color: #c7c7c7; 
    white-space: pre-wrap;
    font-family: 'Fira Code', monospace;
    font-size: 12px;
}
.quick-actions {
    display: flex; gap: 8px; padding: 12px 20px;
    background: rgba(255,255,255,0.02); border-top: 1px solid rgba(255,255,255,0.05);
    flex-wrap: wrap;
}
.quick-btn {
    background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.1);
    color: #e0e0e0; padding: 6px 14px; border-radius: 20px;
    font-size: 12px; cursor: pointer; transition: all 0.2s;
}
.quick-btn:hover { background: rgba(255,255,255,0.15); transform: translateY(-1px); }
.quick-btn:active { transform: translateY(0); }
.input-area {
    display: flex; gap: 10px; padding: 16px 20px;
    background: rgba(255,255,255,0.03); border-top: 1px solid rgba(255,255,255,0.05);
}
.input-area input {
    flex: 1; background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.15); border-radius: 25px;
    padding: 12px 20px; color: white; font-size: 14px; outline: none;
    transition: border-color 0.2s;
}
.input-area input:focus { border-color: #3b82f6; }
.input-area input::placeholder { color: #666; }
.send-btn {
    background: linear-gradient(135deg, #3b82f6, #6366f1);
    border: none; border-radius: 25px; padding: 12px 24px;
    color: white; font-weight: 600; cursor: pointer; transition: transform 0.2s;
}
.send-btn:hover { transform: scale(1.05); }
.send-btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
.settings-panel {
    background: rgba(255,255,255,0.05); border-radius: 12px;
    padding: 12px 16px; margin-bottom: 15px;
    border: 1px solid rgba(255,255,255,0.08);
}
.settings-row { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.settings-label { font-size: 12px; color: #888; margin-right: 6px; }
.setting-btn {
    padding: 5px 12px; border-radius: 8px; font-size: 12px; cursor: pointer;
    border: 1px solid rgba(255,255,255,0.15); background: rgba(255,255,255,0.05);
    color: #e0e0e0; transition: all 0.15s;
}
.setting-btn:hover, .setting-btn.active { background: #3b82f6; color: white; border-color: #3b82f6; }
.welcome { text-align: center; padding: 40px 20px; color: #888; }
.welcome h2 { font-size: 24px; margin-bottom: 10px; }
.welcome p { margin: 5px 0; font-size: 14px; }
.header { text-align: center; padding: 15px; }
.header h1 {
    font-size: 28px;
    background: linear-gradient(135deg, #3b82f6, #ec4899);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 5px;
}
.header p { color: #666; font-size: 14px; }
.loading { display: inline-block; width: 20px; height: 20px;
    border: 2px solid rgba(255,255,255,0.1); border-top-color: #3b82f6;
    border-radius: 50%; animation: spin 0.8s linear infinite; vertical-align: middle;
}
@keyframes spin { to { transform: rotate(360deg); } }
.project-selector { display: flex; gap: 10px; align-items: center; margin-bottom: 15px; }
.project-selector select {
    flex: 1; background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.15); border-radius: 8px;
    padding: 10px; color: white; font-size: 14px;
}
.file-panel {
    background: rgba(255,255,255,0.03); border-radius: 12px;
    padding: 12px; margin-bottom: 15px;
    border: 1px solid rgba(255,255,255,0.08);
}
.file-panel-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.file-panel-title { font-size: 13px; color: #10b981; font-weight: 600; }
.file-item {
    display: flex; justify-content: space-between; align-items: center;
    padding: 6px 10px; margin: 4px 0; background: rgba(255,255,255,0.04);
    border-radius: 6px; font-size: 12px; cursor: pointer; transition: background 0.15s;
}
.file-item:hover { background: rgba(255,255,255,0.1); }
.file-item-name { color: #e0e0e0; }
.file-item-action { color: #3b82f6; font-size: 11px; }
.error-msg { color: #ef4444; font-size: 13px; }
/* Markdown rendering styles */
.message-assistant h1, .message-assistant h2, .message-assistant h3 {
    margin: 12px 0 8px 0;
    color: #e0e0e0;
}
.message-assistant h1 { font-size: 1.4em; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 8px; }
.message-assistant h2 { font-size: 1.2em; }
.message-assistant h3 { font-size: 1.1em; }
.message-assistant p { margin: 8px 0; }
.message-assistant ul, .message-assistant ol { margin: 8px 0; padding-left: 24px; }
.message-assistant li { margin: 4px 0; }
.message-assistant blockquote {
    border-left: 3px solid #3b82f6;
    margin: 8px 0;
    padding: 8px 16px;
    background: rgba(255,255,255,0.03);
    border-radius: 0 8px 8px 0;
}
.message-assistant code {
    background: rgba(255,255,255,0.1);
    padding: 2px 6px;
    border-radius: 4px;
    font-family: 'Fira Code', monospace;
    font-size: 0.9em;
}
.message-assistant pre.hljs {
    background: #1a1a2e;
    padding: 12px;
    border-radius: 8px;
    overflow-x: auto;
    margin: 8px 0;
}
.message-assistant pre.hljs code {
    background: transparent;
    padding: 0;
}
.message-assistant a { color: #3b82f6; text-decoration: none; }
.message-assistant a:hover { text-decoration: underline; }
.message-assistant hr { border: none; border-top: 1px solid rgba(255,255,255,0.1); margin: 16px 0; }
@media (max-width: 600px) {
    .container { padding: 10px; }
    .status-bar { flex-direction: column; gap: 10px; }
    .message-user, .message-assistant { max-width: 95%; }
}
</style>
<!-- markdown-it for rendering AI responses -->
<script src="https://cdn.jsdelivr.net/npm/markdown-it@14.1.1/dist/markdown-it.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/highlight.js@11.9.0/lib/core.min.js"></script>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/highlight.js@11.9.0/styles/github-dark.min.css">
</head>
<body>
<div class="container">
    <div class="header">
        <h1>🎯 Pulse Learning System</h1>
        <p>脉冲式学习 · 游戏化管理 · 即时反馈</p>
    </div>
    <div class="status-bar">
        <div class="status-left">
            <span class="status-badge badge-online" id="online-badge">检测中...</span>
            <span class="model-info" id="model-info">-</span>
        </div>
        <div class="status-right">
            <span class="status-badge badge-light" id="prompt-badge">精简模式</span>
            <span class="project-badge" id="project-badge">未选择项目</span>
        </div>
    </div>
    <div class="settings-panel">
        <div class="settings-row">
            <span class="settings-label">模型:</span>
            <button class="setting-btn" onclick="setMode('auto')" id="btn-auto">自动</button>
            <button class="setting-btn" onclick="setMode('online')" id="btn-online">🌐 云端</button>
            <button class="setting-btn" onclick="setMode('ollama')" id="btn-ollama">🦙 Ollama</button>
            <button class="setting-btn" onclick="setMode('lmstudio')" id="btn-lmstudio">📦 LM Studio</button>
            <span class="settings-label" style="margin-left:15px">提示词:</span>
            <button class="setting-btn" onclick="setPrompt('light')" id="btn-light">精简</button>
            <button class="setting-btn" onclick="setPrompt('full')" id="btn-full">完整</button>
        </div>
    </div>
    <div class="project-selector">
        <select id="project-select" onchange="selectProject(this.value)">
            <option value="">-- 选择项目 --</option>
        </select>
        <button class="setting-btn" onclick="refreshProjects()">🔄</button>
    </div>
    <div class="file-panel" id="file-panel" style="display:none">
        <div class="file-panel-header">
            <span class="file-panel-title">📁 项目文件</span>
            <button class="quick-btn" onclick="refreshFiles()" style="font-size:11px">刷新</button>
        </div>
        <div id="file-list"></div>
    </div>
    <div class="chat-area">
        <div class="chat-messages" id="chat-messages">
            <div class="welcome">
                <h2>👋 欢迎使用脉冲学习系统</h2>
                <p>告诉我你想学习什么，我来帮你拆解目标、生成挑战！</p>
                <p style="margin-top:15px">
                    <button class="quick-btn" onclick="quickAction('new')">🚀 新建项目</button>
                    <button class="quick-btn" onclick="quickAction('list')">📋 查看项目</button>
                    <button class="quick-btn" onclick="quickAction('help')">❓ 帮助</button>
                </p>
            </div>
        </div>
        <div class="quick-actions">
            <button class="quick-btn" onclick="quickAction('module')">📚 新建模块</button>
            <button class="quick-btn" onclick="quickAction('status')">📊 项目状态</button>
            <button class="quick-btn" onclick="quickAction('complete')">✅ 完成挑战</button>
            <button class="quick-btn" onclick="quickAction('files')">📁 浏览文件</button>
            <button class="quick-btn" onclick="clearHistory()">🗑️ 清除</button>
        </div>
        <div class="input-area">
            <input type="text" id="message-input" placeholder="输入你的学习目标..."
                   onkeypress="if(event.key==='Enter'&&!sending)sendMessage()">
            <button class="send-btn" id="send-btn" onclick="sendMessage()">发送</button>
        </div>
    </div>
</div>
<script>
let sending = false;

function refreshStatus() {
    fetch('/api/status').then(r=>r.json()).then(data=>{
        const ob = document.getElementById('online-badge');
        if(data.online){ ob.textContent='🟢 在线'; ob.className='status-badge badge-online'; }
        else { ob.textContent='🔴 离线'; ob.className='status-badge badge-offline'; }
        document.getElementById('model-info').textContent=`${data.provider} / ${data.model}`;
        const pb = document.getElementById('prompt-badge');
        if(data.light){ pb.textContent='精简模式'; pb.className='status-badge badge-light'; }
        else { pb.textContent='完整模式'; pb.className='status-badge badge-full'; }
        document.getElementById('project-badge').textContent=data.current_project||'未选择项目';
        ['auto','online','ollama','lmstudio'].forEach(m=>{
            const b=document.getElementById('btn-'+m);
            if(b) b.classList.toggle('active',data.mode===m);
        });
        const bl=document.getElementById('btn-light'), bf=document.getElementById('btn-full');
        if(bl) bl.classList.toggle('active',data.light);
        if(bf) bf.classList.toggle('active',!data.light);
    }).catch(()=>{});
}

function refreshProjects() {
    fetch('/api/projects').then(r=>r.json()).then(data=>{
        const s=document.getElementById('project-select');
        s.innerHTML='<option value="">-- 选择项目 --</option>';
        data.projects.forEach(p=>{ const o=document.createElement('option'); o.value=p; o.textContent=p; s.appendChild(o); });
        if(data.current) s.value=data.current;
    }).catch(()=>{});
}

function selectProject(name) {
    fetch('/api/project/select',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:name})})
    .then(()=>{ refreshStatus(); refreshProjects(); if(name) refreshFiles(); }).catch(()=>{});
}

function refreshFiles() {
    const proj = document.getElementById('project-select').value;
    if(!proj) return;
    fetch('/api/files?project='+encodeURIComponent(proj)).then(r=>r.json()).then(data=>{
        const panel=document.getElementById('file-panel');
        const list=document.getElementById('file-list');
        if(data.files && data.files.length>0){
            panel.style.display='block';
            list.innerHTML='';
            data.files.forEach(f=>{
                const d=document.createElement('div');
                d.className='file-item';
                d.innerHTML=`<span class="file-item-name">${f.name}</span><span class="file-item-action">查看</span>`;
                d.onclick=()=>quickAction('查看文件 '+f.name);
                list.appendChild(d);
            });
        } else { panel.style.display='none'; }
    }).catch(()=>{});
}

// Initialize markdown-it
const md = window.markdownit({
    html: true,
    linkify: true,
    typographer: true,
    highlight: function(str, lang) {
        if (lang && hljs.getLanguage(lang)) {
            try {
                return '<pre class="hljs"><code>' + hljs.highlight(str, { language: lang }).value + '</code></pre>';
            } catch (__) {}
        }
        return '<pre class="hljs"><code>' + md.utils.escapeHtml(str) + '</code></pre>';
    }
});

function addMessage(role, content, isMarkdown = false) {
    const c=document.getElementById('chat-messages');
    const d=document.createElement('div');
    d.className='message message-'+role;
    // Render markdown for assistant messages
    if (role === 'assistant' && isMarkdown) {
        d.innerHTML = md.render(content);
    } else {
        d.innerHTML = content;
    }
    c.appendChild(d);
    c.scrollTop=c.scrollHeight;
    return d;
}

function sendMessage() {
    if(sending) return;
    const input=document.getElementById('message-input');
    const msg=input.value.trim();
    if(!msg) return;
    input.value='';
    sending=true;
    document.getElementById('send-btn').disabled=true;

    addMessage('user', msg);
    const assistantDiv=addMessage('assistant','<span class="loading"></span>');
    
    // 工具调用显示区域
    let toolCallDiv = null;

    // 使用 fetch + ReadableStream 替代 EventSource（避免缓存和重连问题）
    fetch('/api/chat/stream',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({message:msg})
    }).then(response=>{
        if(!response.ok) throw new Error('HTTP '+response.status);
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullContent = '';
        let gotContent = false;

        function read() {
            reader.read().then(({done, value})=>{
                if(done) {
                    sending=false;
                    document.getElementById('send-btn').disabled=false;
                    return;
                }
                const text = decoder.decode(value, {stream:true});
                // 解析 SSE 格式
                const lines = text.split('\n');
                for(const line of lines) {
                    if(line.startsWith('data: ')) {
                        const dataStr = line.substring(6);
                        if(dataStr.trim() === '[DONE]') {
                            sending=false;
                            document.getElementById('send-btn').disabled=false;
                            // 保存对话历史
                            if(fullContent) {
                                fetch('/api/save_history',{
                                    method:'POST',
                                    headers:{'Content-Type':'application/json'},
                                    body:JSON.stringify({user:msg, assistant:fullContent})
                                }).catch(()=>{});
                            }
                            return;
                        }
                        try {
                            const d = JSON.parse(dataStr);
                            if(d.content) {
                                // 检测工具调用标记
                                const toolMatch = d.content.match(/🔧 \*\*执行工具\*\*: (.+?)\n\n/);
                                if (toolMatch && !toolCallDiv) {
                                    // 创建工具调用显示区域
                                    toolCallDiv = document.createElement('div');
                                    toolCallDiv.className = 'tool-call';
                                    toolCallDiv.innerHTML = '<div class="tool-call-header">🔧 正在执行工具...</div>';
                                    assistantDiv.parentNode.insertBefore(toolCallDiv, assistantDiv);
                                    if(!gotContent){ assistantDiv.innerHTML=''; }
                                    gotContent=true;
                                    // 从内容中移除工具调用标记
                                    d.content = d.content.replace(/🔧 \*\*执行工具\*\*: (.+?)\n\n/, '');
                                }
                                
                                if(!gotContent){ assistantDiv.innerHTML=''; gotContent=true; }
                                fullContent += d.content;
                                // Render markdown in real-time
                                assistantDiv.innerHTML = md.render(fullContent);
                                const c=document.getElementById('chat-messages');
                                c.scrollTop=c.scrollHeight;
                            }
                            if(d.error) {
                                assistantDiv.innerHTML='<span class="error-msg">❌ '+d.error+'</span>';
                                sending=false;
                                document.getElementById('send-btn').disabled=false;
                                return;
                            }
                        } catch(err) { /* skip */ }
                    }
                }
                read(); // 继续读取
            }).catch(err=>{
                if(!gotContent) {
                    assistantDiv.innerHTML='<span class="error-msg">❌ 连接中断</span>';
                }
                sending=false;
                document.getElementById('send-btn').disabled=false;
                // 保存已收到的内容
                if(fullContent) {
                    fetch('/api/save_history',{
                        method:'POST',
                        headers:{'Content-Type':'application/json'},
                        body:JSON.stringify({user:msg, assistant:fullContent})
                    }).catch(()=>{});
                }
            });
        }
        read();
    }).catch(err=>{
        assistantDiv.innerHTML='<span class="error-msg">❌ 请求失败: '+err.message+'</span>';
        sending=false;
        document.getElementById('send-btn').disabled=false;
    });
}

function quickAction(action) {
    if(sending) return;
    const actions = {
        'new':'我想开始一个新的学习项目',
        'list':'列出我所有的学习项目',
        'help':'帮助',
        'module':'我想创建一个新的学习模块',
        'status':'查看当前项目的状态',
        'complete':'完成当前的挑战',
        'files':'浏览项目文件'
    };
    const msg = actions[action] || action;
    document.getElementById('message-input').value = msg;
    sendMessage();
}

function clearHistory() {
    fetch('/api/clear',{method:'POST'}).then(()=>{
        document.getElementById('chat-messages').innerHTML='<div class="welcome"><h2>👋 对话已清除</h2><p>继续你的学习之旅吧！</p></div>';
    }).catch(()=>{});
}

function setMode(mode) {
    fetch('/api/mode',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mode:mode})}).then(()=>refreshStatus()).catch(()=>{});
}

function setPrompt(type) {
    fetch('/api/prompt',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({type:type})}).then(()=>refreshStatus()).catch(()=>{});
}

// 初始化
refreshStatus();
refreshProjects();
// 定时刷新状态（不频繁）
setInterval(refreshStatus, 10000);
</script>
</body>
</html>
'''


# ==================== Flask 路由 ====================

@app.route('/')
def index():
    _init_session()
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/status')
def api_status():
    _init_session()
    return jsonify(get_client_info())


@app.route('/api/mode', methods=['POST'])
def api_mode():
    _init_session()
    data = request.json
    session['mode'] = data.get('mode', 'auto')
    return jsonify({'success': True, 'mode': session['mode']})


@app.route('/api/prompt', methods=['POST'])
def api_prompt():
    _init_session()
    data = request.json
    session['use_light'] = (data.get('type', 'light') == 'light')
    return jsonify({'success': True, 'light': session['use_light']})


@app.route('/api/projects')
def api_projects():
    _init_session()
    projects = list_projects_fast()
    return jsonify({'projects': projects, 'current': session.get('current_project')})


@app.route('/api/project/select', methods=['POST'])
def api_project_select():
    _init_session()
    data = request.json
    name = data.get('name', '')
    if name:
        session['current_project'] = name
    return jsonify({'success': True, 'current': session.get('current_project')})


@app.route('/api/files')
def api_files():
    """获取项目文件列表"""
    _init_session()
    project = request.args.get('project', session.get('current_project', ''))
    if not project:
        return jsonify({'files': []})
    pulse_dir = _get_pulse_dir()
    project_dir = os.path.join(pulse_dir, project)
    files = []
    if os.path.exists(project_dir):
        for f in os.listdir(project_dir):
            if f.endswith('.md'):
                files.append({'name': f, 'path': os.path.join(project_dir, f)})
        modules_dir = os.path.join(project_dir, 'modules')
        if os.path.exists(modules_dir):
            for f in os.listdir(modules_dir):
                if f.endswith('.md'):
                    files.append({'name': f'modules/{f}', 'path': os.path.join(modules_dir, f)})
    return jsonify({'files': files})


@app.route('/api/file/read')
def api_file_read():
    """读取项目文件内容"""
    path = request.args.get('path', '')
    if not path:
        return jsonify({'error': '缺少路径参数'})
    pulse_dir = os.path.realpath(_get_pulse_dir())
    file_path = os.path.realpath(path)
    if not file_path.startswith(pulse_dir):
        return jsonify({'error': '路径不允许'})
    content = _read_file_safe(file_path)
    if not content:
        return jsonify({'error': '文件不存在或为空'})
    return jsonify({'content': content, 'path': file_path})


@app.route('/api/file/write', methods=['POST'])
def api_file_write():
    """写入项目文件"""
    data = request.json
    path = data.get('path', '')
    content = data.get('content', '')
    if not path:
        return jsonify({'error': '缺少路径参数'})
    pulse_dir = os.path.realpath(_get_pulse_dir())
    file_path = os.path.realpath(path)
    if not file_path.startswith(pulse_dir):
        return jsonify({'error': '路径不允许'})
    ok = _write_file_safe(file_path, content)
    if ok:
        return jsonify({'success': True, 'path': file_path})
    return jsonify({'error': '写入失败'})


def _sse_chunk(content=None, error=None):
    """生成 SSE 数据块 (bytes)，确保 Windows GBK 兼容"""
    if error:
        payload = json.dumps({'error': str(error)}, ensure_ascii=True)
    else:
        payload = json.dumps({'content': content}, ensure_ascii=True)
    return f"data: {payload}\n\n".encode('utf-8')


def _sse_done():
    """SSE 结束标记"""
    return b"data: [DONE]\n\n"


_SSE_HEADERS = {'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}


@app.route('/api/chat/stream', methods=['POST'])
def api_chat_stream():
    """流式聊天接口（SSE）— 使用 POST 避免 GET 缓存问题"""
    _init_session()
    data = request.json or {}
    message = data.get('message', '') or request.args.get('msg', '')
    if not message:
        return jsonify({'error': '请输入内容'})

    # ---- 快速命令（不走 LLM，立即响应） ----
    if ('项目' in message and ('列表' in message or '所有' in message or '查看' in message)
            and '状态' not in message):
        from tools.pulse_tools import list_projects
        def gen():
            try:
                result = list_projects()
            except Exception as e:
                result = f"列表获取失败: {e}"
            yield _sse_chunk(result)
            yield _sse_done()
        return Response(gen(), mimetype='text/event-stream', headers=_SSE_HEADERS)

    if '状态' in message or '进度' in message:
        proj = session.get('current_project')
        def gen():
            try:
                from tools.pulse_tools import get_project_status
                r = get_project_status(proj) if proj else "请先创建或选择项目"
            except Exception as e:
                r = f"状态获取失败: {e}"
            yield _sse_chunk(r)
            yield _sse_done()
        return Response(gen(), mimetype='text/event-stream', headers=_SSE_HEADERS)

    if '浏览文件' in message or ('文件' in message and '浏览' in message):
        proj = session.get('current_project')
        def gen():
            if not proj:
                yield _sse_chunk("请先选择项目")
            else:
                file_list = _list_project_files(proj)
                text = f"项目 {proj} 的文件：\n\n" + "\n".join(["- " + f for f in file_list])
                yield _sse_chunk(text)
            yield _sse_done()
        return Response(gen(), mimetype='text/event-stream', headers=_SSE_HEADERS)

    if ('finish' in message or '完成脉冲' in message or '完成模块' in message) and session.get('current_project'):
        proj = session.get('current_project')
        # 尝试从消息中提取 module_id
        import re
        mid = None
        m = re.search(r'\bmodule[ _-]?(\d+)\b', message, re.IGNORECASE)
        if m:
            mid = int(m.group(1))
        def gen():
            try:
                from tools.pulse_tools import finish_module
                result = finish_module(proj, module_id=mid)
            except Exception as e:
                result = f"finish 失败: {e}"
            yield _sse_chunk(result)
            yield _sse_done()
        return Response(gen(), mimetype='text/event-stream', headers=_SSE_HEADERS)

    if message in ['帮助', 'help', '?']:
        help_text = (
            "# 脉冲学习系统使用指南\n\n"
            "## 命令\n"
            "- 告诉我你想学什么 -> 帮你创建学习项目\n"
            "- 创建项目 -> 开始新项目\n"
            "- 查看项目 -> 列出所有项目\n"
            "- 新建模块 -> 添加学习模块\n"
            "- 完成挑战 -> 获得分数奖励\n"
            "- finish / 完成脉冲 -> 完成微挑战后进入检验阶段\n"
            "- 浏览文件 -> 查看项目文件\n\n"
            "## 设置\n"
            "- 顶部按钮可切换模型（云端/Ollama/LM Studio）\n"
            "- 支持精简/完整提示词切换\n\n"
            "## 游戏化\n"
            "- 连击奖励：连续完成挑战分数翻倍\n"
            "- 分数系统：每个挑战5-20分\n"
            "- Boss挑战：双倍评分\n\n"
            "有什么想学的吗？"
        )
        def gen():
            yield _sse_chunk(help_text)
            yield _sse_done()
        return Response(gen(), mimetype='text/event-stream', headers=_SSE_HEADERS)

    if '查看文件' in message:
        filename = message.replace('查看文件', '').strip()
        proj = session.get('current_project')
        def gen():
            if not proj:
                yield _sse_chunk("请先选择项目")
            else:
                pulse_dir = _get_pulse_dir()
                filepath = os.path.join(pulse_dir, proj, filename)
                content = _read_file_safe(filepath)
                if content:
                    yield _sse_chunk(f"**{filename}**:\n\n{content[:2000]}")
                else:
                    yield _sse_chunk(f"文件 {filename} 不存在")
            yield _sse_done()
        return Response(gen(), mimetype='text/event-stream', headers=_SSE_HEADERS)

    # ---- LLM 流式响应 ----
    # 从文件加载历史记录（不依赖 session）
    session_mode = session.get('mode', 'auto')
    session_use_light = session.get('use_light', True)
    with _chat_history_lock:
        file_history = _load_chat_history()

    def generate():
        full_response = ''
        try:
            for chunk in _do_llm_stream(message, session_mode, session_use_light, file_history):
                full_response += chunk
                yield _sse_chunk(chunk)
            yield _sse_done()
        except Exception as e:
            yield _sse_chunk(error=str(e))

    return Response(generate(), mimetype='text/event-stream', headers=_SSE_HEADERS)


@app.route('/api/chat', methods=['POST'])
def api_chat():
    """非流式聊天接口（fallback）"""
    _init_session()
    data = request.json
    message = data.get('message', '')
    if not message:
        return jsonify({'response': '请输入内容'})
    response = send_to_llm(message)
    return jsonify({'response': response})


@app.route('/api/clear', methods=['POST'])
def api_clear():
    _init_session()
    session['history'] = []
    return jsonify({'success': True})


# File-based chat history storage (persists across requests)
_CHAT_HISTORY_FILE = os.path.join(PROJECTS_DIR, 'data', 'chat_history.json')
_chat_history_lock = threading.Lock()


def _load_chat_history():
    """Load chat history from file"""
    try:
        if os.path.exists(_CHAT_HISTORY_FILE):
            with open(_CHAT_HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return []


def _save_chat_history(history):
    """Save chat history to file"""
    try:
        os.makedirs(os.path.dirname(_CHAT_HISTORY_FILE), exist_ok=True)
        with open(_CHAT_HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


@app.route('/api/save_history', methods=['POST'])
def api_save_history():
    """保存对话历史（用于流式响应后）"""
    data = request.json or {}
    user_msg = data.get('user', '')
    assistant_msg = data.get('assistant', '')
    if user_msg and assistant_msg:
        # 使用新的记忆系统
        if _memory_bridge:
            try:
                _memory_bridge.save_chat_exchange(user_msg, assistant_msg)
                history = _memory_bridge.get_chat_history_for_llm()
                return jsonify({'success': True, 'history_length': len(history), 'source': 'memory_bridge'})
            except Exception as e:
                print(f"[Memory] 保存失败: {e}")
        # 回退到文件存储
        with _chat_history_lock:
            history = _load_chat_history()
            history.append({"role": "user", "content": user_msg})
            history.append({"role": "assistant", "content": assistant_msg})
            if len(history) > 20:
                history = history[-20:]
            _save_chat_history(history)
        return jsonify({'success': True, 'history_length': len(history), 'source': 'file'})
    return jsonify({'success': False, 'error': 'Missing messages'})


@app.route('/api/history', methods=['GET'])
def api_get_history():
    """获取对话历史"""
    with _chat_history_lock:
        history = _load_chat_history()
    return jsonify({'history': history})


@app.route('/api/history/clear', methods=['POST'])
def api_clear_history():
    """清除对话历史"""
    if _memory_bridge:
        try:
            _memory_bridge.clear_chat()
            return jsonify({'success': True, 'source': 'memory_bridge'})
        except Exception as e:
            print(f"[Memory] 清除失败: {e}")
    with _chat_history_lock:
        _save_chat_history([])
    return jsonify({'success': True, 'source': 'file'})


# ==================== 记忆系统 API ====================

@app.route('/api/memory/project', methods=['POST'])
def api_memory_create_project():
    """创建学习项目"""
    if not _memory_bridge:
        return jsonify({'success': False, 'error': 'Memory system not available'})
    data = request.json or {}
    name = data.get('name', '')
    description = data.get('description', '')
    goal = data.get('goal', '')
    try:
        project_id = _memory_bridge.create_project(name, description, goal)
        return jsonify({'success': True, 'project_id': project_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/memory/project/<name>', methods=['GET'])
def api_memory_get_project(name):
    """获取项目信息"""
    if not _memory_bridge:
        return jsonify({'success': False, 'error': 'Memory system not available'})
    try:
        info = _memory_bridge.get_project_status(name)
        return jsonify({'success': True, 'data': info})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/memory/note', methods=['POST'])
def api_memory_save_note():
    """保存学习笔记"""
    if not _memory_bridge:
        return jsonify({'success': False, 'error': 'Memory system not available'})
    data = request.json or {}
    title = data.get('title', '')
    content = data.get('content', '')
    tags = data.get('tags', [])
    try:
        _memory_bridge.save_learning_note(title, content, tags)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/memory/notes', methods=['GET'])
def api_memory_search_notes():
    """搜索笔记"""
    if not _memory_bridge:
        return jsonify({'success': False, 'error': 'Memory system not available'})
    keyword = request.args.get('keyword', '')
    try:
        notes = _memory_bridge.search_notes(keyword)
        return jsonify({'success': True, 'notes': notes})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/memory/daily', methods=['GET'])
def api_memory_daily_summary():
    """获取今日学习摘要"""
    if not _memory_bridge:
        return jsonify({'success': False, 'error': 'Memory system not available'})
    try:
        summary = _memory_bridge.get_daily_summary()
        return jsonify({'success': True, 'summary': summary})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ==================== 启动 ====================

if __name__ == '__main__':
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    print("=" * 50)
    print("Pulse Learning System - Web UI v2.1")
    print("=" * 50)
    print("fix: status cache, bg thread timeout, SSE stream, POST request")
    print("Open browser: http://localhost:5050")
    print("Press Ctrl+C to stop")
    print("=" * 50)
    # 启动时刷新一次状态
    try:
        _refresh_status_cache()
    except Exception:
        pass
    _start_status_bg_thread()
    app.run(host='0.0.0.0', port=5050, debug=False, threaded=True)
