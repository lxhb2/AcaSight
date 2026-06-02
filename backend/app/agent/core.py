"""
Agent Core — 学术 Agent 推理循环引擎（v3.0）
照搬 Hermes Agent conversation_loop.py + tool_executor.py 核心逻辑

改进（v3.0）：
1. 消息序列修复 — role alternation + tool_call JSON fix（防 API 400 错误）
2. Jittered backoff 重试 — 指数退避 + 随机抖动
3. 错误分类 — 区分 rate_limit/context_overflow/auth_error
4. 工具执行隔离 — 单工具失败不影响并行任务
5. 中断机制 — 用户可取消跑偏的 Agent
6. 活动心跳 — 长任务期间发出进度事件

参考架构：
- Hermes Agent: conversation_loop.py 的完整 ReAct 循环
- Hermes Agent: tool_executor.py 的并行工具执行
"""

import asyncio
import json
import os
import structlog
from typing import AsyncGenerator, Dict, Any, List, Optional

from app.agent.message_sanitization import (
    sanitize_messages_surrogates,
    repair_tool_call_arguments,
    repair_message_sequence,
    fix_message_roles,
)
from app.agent.retry_utils import (
    jittered_backoff,
    classify_api_error,
)
from app.agent.loop_detector import LoopDetector, create_loop_detector_for_agent

# LangSmith 可观测性集成（可选依赖）
try:
    from langsmith import traceable as _ls_traceable, trace as _ls_trace
    _LANGSMITH_AVAILABLE = True
except ImportError:
    _LANGSMITH_AVAILABLE = False
    # 降级：空装饰器
    def _ls_traceable(name=None, run_type="chain", **kw):
        def deco(fn):
            return fn
        return deco
    from contextlib import nullcontext
    class _ls_trace:
        def __init__(self, *a, **kw):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *a):
            pass

logger = structlog.get_logger()


def _get_ai_service():
    from app.services.ai_service import ai_service
    return ai_service


# ============================================================
# 系统提示词 — 深度嵌入 Nature 学术标准
# ============================================================

ACADEMIC_SYSTEM_PROMPT = """# AcaSight 学术 Agent 指令

你是 AcaSight 学术智能体，一位顶级的学术研究助手。你遵循 Nature 期刊级别的学术标准。

## 核心原则

1. **不编造** — 不编造数据、结果、参考文献、统计量、实验方法
2. **证据优先** — 所有声明必须有文献或数据支撑
3. **精确表述** — 声明强度必须与证据强度匹配，避免过度声明
4. **可追溯** — 引用标注来源，翻译保留原文位置
5. **学术语言** — 正式、精确、简洁，句子不超过 30 词

## 可用工具

{tool_list}

## 工作流程

1. 分析用户任务的学术需求
2. 选择最合适的工具（可并行调用多个）
3. 执行工具并分析结果
4. 如果结果不充分，继续调用工具
5. 给出最终回答，附带来源引用

## 上下文信息

{context}

## 输出要求

- 中文回答默认使用简体中文
- 英文术语首次出现时附中文翻译
- 引用格式：[作者, 年份]
- 代码块标注语言
"""


class AgentCore:
    """AcaSight 学术 Agent 核心推理引擎（v3.0）
    
    基于 Hermes Agent 的 ReAct 模式 Function Calling Agent:
    1. 消息序列修复 → API 调用（带重试）→ tool_calls 或文本
    2. tool_calls → 并行执行工具（隔离错误）→ 结果返回 LLM
    3. 文本 → 流式返回给用户
    """
    
    def __init__(self):
        self.skill_registry: Optional[Any] = None
        self.max_turns = 15              # 最大推理轮次
        self.max_retries = 3             # provider 失败的恢复重试次数
        self.max_json_retries = 2        # JSON 修复重试
        self.max_empty_retries = 2       # 空内容重试
        self.max_context_compressions = 3  # 最大压缩轮次
        self._initialized = False
        
        # 中断机制
        self._interrupt_requested = False
        self._interrupt_lock = asyncio.Lock()
        
        # 循环检测 (方向P.3)
        self._loop_detector: Optional[LoopDetector] = None
        
        # 统计
        self.api_call_count = 0
        self.tool_call_count = 0
    
    def _ensure_initialized(self):
        if not self._initialized:
            from app.agent.skill_registry import SkillRegistry
            from app.agent.skills.nature_skills import register_nature_skills
            self.skill_registry = SkillRegistry()
            register_nature_skills(self.skill_registry)
            self._initialized = True
    
    async def interrupt(self):
        """请求中断当前 Agent 任务"""
        async with self._interrupt_lock:
            self._interrupt_requested = True
            logger.info("Agent interrupt requested")
    
    async def _check_interrupt(self):
        """检查是否被中断"""
        async with self._interrupt_lock:
            return self._interrupt_requested
    
    async def _reset_interrupt(self):
        """重置中断标志"""
        async with self._interrupt_lock:
            self._interrupt_requested = False
    
    @_ls_traceable(name="acasight_agent_run", run_type="chain")
    async def run(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List[Dict]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """执行 Agent 任务，流式返回推理步骤（v3.0 — Hermes 级可靠性）
        
        Yields:
            {"type": "thinking", "content": "..."}       — Agent 思考过程
            {"type": "tool_call", "name": "...", "args": {...}}  — 工具调用
            {"type": "tool_result", "name": "...", "result": "..."} — 工具执行结果
            {"type": "answer", "content": "..."}          — 最终回答
            {"type": "heartbeat", ...}                    — 活动心跳（长任务时）
            {"type": "error", "content": "..."}           — 错误
            {"type": "interrupted", ...}                  — 被用户中断
        """
        context = context or {}
        await self._reset_interrupt()
        self.api_call_count = 0
        self.tool_call_count = 0
        
        # 初始化循环检测器
        self._loop_detector = create_loop_detector_for_agent()
        
        self._ensure_initialized()
        
        # 1. 构建系统提示词
        tool_list = self._format_tool_list()
        system_prompt = ACADEMIC_SYSTEM_PROMPT.format(
            tool_list=tool_list,
            context=self._format_context(context),
        )
        
        # 2. 构建消息列表
        messages: List[Dict] = [{"role": "system", "content": system_prompt}]
        
        if conversation_history:
            for msg in conversation_history[-10:]:
                if msg.get("role") != "system":
                    messages.append(dict(msg))
        
        messages.append({"role": "user", "content": task})
        
        # 3. 获取工具定义
        tools = self.skill_registry.get_tool_schemas()
        if not tools:
            yield {"type": "error", "content": "无可用技能"}
            return
        
        yield {"type": "thinking", "content": "正在分析任务..."}
        
        # 4. 主推理循环（Hermes 式）
        turn = 0
        compression_attempts = 0
        empty_content_retries = 0
        
        while turn < self.max_turns:
            # 中断检查
            if await self._check_interrupt():
                yield {"type": "interrupted", "content": "任务已被用户中断"}
                return
            
            turn += 1
            
            # 4a. 上下文压缩检查
            if self._should_compress(messages, tools):
                compression_attempts += 1
                if compression_attempts <= self.max_context_compressions:
                    yield {"type": "thinking", "content": f"上下文过长，正在压缩（第 {compression_attempts} 次）..."}
                    messages = self._compress_context(messages, conversation_history is not None)
                    # 压缩后重置计数器
                    empty_content_retries = 0
                else:
                    yield {"type": "thinking", "content": f"上下文压缩已达上限（{self.max_context_compressions} 次），继续处理..."}
            
            # 4b. 消息序列修复（Hermes 级 sanitization）
            repair_message_sequence(messages)
            fix_message_roles(messages)
            
            # 4c. 调用 LLM（带分类重试）
            result = await self._llm_call_with_classified_retry(messages, tools, turn)
            if result.get("error"):
                yield {"type": "error", "content": result["error"]}
                return
            
            content = result.get("content", "")
            tool_calls = result.get("tool_calls", [])
            self.api_call_count += 1
            
            if tool_calls:
                # 空内容重试：有工具调用但无思考内容
                if not content and empty_content_retries < self.max_empty_retries:
                    empty_content_retries += 1
                    if empty_content_retries == 1:
                        # 第一次：重试一次
                        continue
                
                empty_content_retries = 0
                
                # 4d. 并行执行所有工具调用（Hermes 式）
                yield {"type": "thinking", "content": f"正在执行 {len(tool_calls)} 个工具..."}
                
                if content:
                    yield {"type": "thinking", "content": content}
                
                # 构建 assistant 消息
                assistant_msg = {
                    "role": "assistant",
                    "content": content or None,
                    "tool_calls": self._build_tool_call_messages(tool_calls),
                }
                
                # 并发执行工具（隔离错误）
                tool_results = await self._execute_tools_concurrent(tool_calls)
                
                # 循环检测 (方向P.3) — 在 run() 的 async generator 上下文中
                if self._loop_detector:
                    for tc in tool_calls:
                        detection = self._loop_detector.record_tool_call(tc["name"], tc.get("arguments", {}))
                        if detection.is_looping:
                            logger.warning("Loop detected in agent", details=detection.details)
                            yield {
                                "type": "warning",
                                "content": f"⚠️ 检测到循环: {detection.details}",
                                "suggestion": detection.suggestion,
                            }
                            # 在3次检测后自动中断
                            if len(self._loop_detector.get_all_detections()) >= 3:
                                yield {
                                    "type": "error",
                                    "content": f"Agent 循环检测触发中断: {detection.details}",
                                }
                                return
                
                # 将 assistant 消息和 tool 结果加入对话
                messages.append(assistant_msg)
                messages.extend(tool_results)
                
                # 心跳
                yield {"type": "heartbeat", "turn": turn, "total_tools": self.tool_call_count}
                
            else:
                # 4e. 无工具调用 — 直接回答
                yield {"type": "heartbeat", "turn": turn, "total_tools": self.tool_call_count}
                
                if content:
                    yield {"type": "answer", "content": content}
                else:
                    yield {"type": "answer", "content": "任务完成，但我没有生成可用的回答。请尝试更具体地描述您的需求。"}
                return
        
        # 5. 超过最大轮次
        yield {
            "type": "answer",
            "content": f"任务较复杂，已完成 {turn} 步操作。请继续提问以完成剩余部分，或提供更多上下文信息。"
        }
    
    async def _trace_tool_execution(self, tool_name: str, tool_args: Dict) -> Any:
        """LangSmith trace 包装的工具执行"""
        if _LANGSMITH_AVAILABLE:
            with _ls_trace(name=f"tool_{tool_name}", run_type="tool"):
                return await self.skill_registry.execute(tool_name, tool_args)
        else:
            return await self.skill_registry.execute(tool_name, tool_args)

    async def _execute_tools_concurrent(self, tool_calls: List[Dict]) -> List[Dict]:
        """并行执行工具调用（Hermes 式 — 隔离错误）"""
        results = []
        
        async def _exec_one(i: int, tc: Dict):
            """并行 worker：执行单个工具并 yield 事件"""
            tool_name = tc["name"]
            tool_args = tc["arguments"]
            self.tool_call_count += 1
            
            try:
                # 中断检查
                if await self._check_interrupt():
                    return {
                        "tc": tc,
                        "result": {"error": "已被用户中断", "cancelled": True},
                        "event": {"type": "tool_call", "name": tool_name, "args": tool_args}
                    }
                
                result = await asyncio.wait_for(
                    self._trace_tool_execution(tool_name, tool_args),
                    timeout=120.0,
                )
                
                # 检查工具返回的错误
                if isinstance(result, dict) and result.get("error"):
                    logger.warning(f"Tool {tool_name} returned error: {result['error'][:200]}")
                
                return {
                    "tc": tc,
                    "result": result,
                    "event": {"type": "tool_call", "name": tool_name, "args": tool_args}
                }
            except asyncio.TimeoutError:
                logger.error(f"Tool {tool_name} timed out (120s)")
                return {
                    "tc": tc,
                    "result": {"error": f"工具 {tool_name} 执行超时（120s）"},
                    "event": {"type": "tool_call", "name": tool_name, "args": tool_args}
                }
            except Exception as e:
                logger.error(f"Tool {tool_name} failed: {e}")
                return {
                    "tc": tc,
                    "result": {"error": f"工具 {tool_name} 执行异常: {str(e)}"},
                    "event": {"type": "tool_call", "name": tool_name, "args": tool_args}
                }
        
        # 使用 gather 并行执行
        tasks = [_exec_one(i, tc) for i, tc in enumerate(tool_calls)]
        completed = await asyncio.gather(*tasks)
        
        for item in completed:
            tc = item["tc"]
            tool_name = tc["name"]
            result = item["result"]
            
            # 序列化结果
            result_str = json.dumps(result, ensure_ascii=False, indent=2)
            if len(result_str) > 4000:
                result_str = result_str[:4000] + "\n... (结果截断，完整结果已保存)"
            
            # 构建 tool result 消息
            results.append({
                "role": "tool",
                "tool_call_id": tc.get("id", ""),
                "name": tool_name,
                "content": json.dumps(result, ensure_ascii=False)[:8000],
            })
        
        return results
    
    def _build_tool_call_messages(self, tool_calls: List[Dict]) -> List[Dict]:
        """构建 OpenAI 兼容的 tool_calls 消息"""
        return [
            {
                "id": tc.get("id", f"call_{i}"),
                "type": "function",
                "function": {
                    "name": tc["name"],
                    "arguments": json.dumps(tc["arguments"], ensure_ascii=False),
                }
            }
            for i, tc in enumerate(tool_calls)
        ]
    
    async def _llm_call_with_classified_retry(
        self, messages: List[Dict], tools: List[Dict], turn: int
    ) -> Dict:
        """调用 LLM（v3.0 — 分类化重试策略）
        
        根据错误类型采用不同策略：
        - rate_limit → 等待更长后重试
        - context_overflow → 触发压缩后重试
        - auth_error → 跳过此 provider
        - timeout/server_error → 标准重试
        """
        ai_svc = _get_ai_service()
        
        # 获取可用 providers
        providers = []
        try:
            providers = await ai_svc.get_available_providers_with_tools()
        except Exception:
            providers = []
        if not providers:
            providers = [ai_svc._config.get('default_provider', 'ollama')]
        
        last_error = ""
        
        for provider_idx, provider in enumerate(providers):
            for attempt in range(self.max_retries + 1):
                try:
                    # 活动心跳
                    if attempt > 0:
                        delay = jittered_backoff(attempt)
                        logger.info(f"Retry #{attempt} for {provider}, waiting {delay:.1f}s")
                        await asyncio.sleep(delay)
                    
                    result = await asyncio.wait_for(
                        ai_svc.chat_with_tools(
                            messages=messages,
                            tools=tools,
                            provider=provider,
                            temperature=0.3,
                            max_tokens=4096,
                        ),
                        timeout=90.0,
                    )
                    
                    if not result.get("error"):
                        # 成功 — 修复返回的 tool_call arguments
                        tool_calls = result.get("tool_calls", [])
                        for tc in tool_calls:
                            if isinstance(tc.get("arguments"), str):
                                tc["arguments"] = json.loads(
                                    repair_tool_call_arguments(tc["arguments"], tc.get("name", "?"))
                                )
                        return result
                    
                    # 有错误 — 分类处理
                    err_msg = result.get("error", "unknown")
                    err_type = classify_api_error(
                        Exception(err_msg),
                        status_code=result.get("status_code"),
                    )
                    last_error = err_msg
                    
                    if err_type == 'auth_error':
                        logger.warning(f"Provider {provider} auth error, skipping: {err_msg[:200]}")
                        break  # 不重试，换 provider
                    elif err_type == 'rate_limit':
                        logger.warning(f"Provider {provider} rate limited: {err_msg[:200]}")
                        if attempt < self.max_retries:
                            await asyncio.sleep(jittered_backoff(attempt, base=3.0))  # 更长的退避
                        continue
                    elif err_type == 'context_overflow':
                        logger.warning(f"Provider {provider} context overflow: {err_msg[:200]}")
                        return {"error": f"上下文过长: {err_msg[:200]}"}  # 让调用者触发压缩
                    else:
                        logger.warning(f"Provider {provider} attempt {attempt + 1}: {err_msg[:200]}")
                        continue
                    
                except asyncio.TimeoutError:
                    last_error = f"Provider {provider} 超时（90s）"
                    logger.warning(last_error)
                except asyncio.CancelledError:
                    last_error = f"Provider {provider} 被取消"
                    break
                except Exception as e:
                    last_error = str(e)
                    err_type = classify_api_error(e)
                    
                    if err_type == 'auth_error':
                        logger.warning(f"Provider {provider} auth error, skipping")
                        break
                    elif err_type == 'context_overflow':
                        return {"error": last_error}
                    
                    logger.warning(f"Provider {provider} attempt {attempt + 1} error: {last_error[:200]}")
                    if attempt < self.max_retries:
                        await asyncio.sleep(jittered_backoff(attempt))
                    continue
            
            logger.info(f"Provider {provider} exhausted (共 {self.max_retries + 1} 次尝试)，尝试下一个...")
        
        # 所有 provider 都失败 — 回退到纯文本对话
        logger.warning("All providers failed for function calling, falling back to plain chat")
        try:
            fallback_provider = providers[0] if providers else None
            messages_for_chat = [m for m in messages if m.get("role") not in ("tool",)]
            response = ""
            async for chunk in ai_svc.chat(
                messages=messages_for_chat,
                provider=fallback_provider,
                temperature=0.3,
                max_tokens=4096,
            ):
                response += chunk
            return {"content": response, "tool_calls": []}
        except Exception as e:
            return {
                "content": "",
                "tool_calls": [],
                "error": f"所有 AI 服务不可用: {last_error}。请检查 AI 配置。"
            }
    
    def _should_compress(self, messages: List[Dict], tools: List[Dict]) -> bool:
        """检查是否需要压缩上下文（v3.0 — 含 tool schema token 估算）"""
        try:
            from app.agent.context_compressor import context_compressor
            return context_compressor.should_compress(messages)
        except ImportError:
            pass
        
        # 简易估算：超过 30 条消息或 50KB 内容
        total_chars = sum(len(str(m)) for m in messages)
        return len(messages) > 30 or total_chars > 50000
    
    def _compress_context(self, messages: List[Dict], has_history: bool) -> List[Dict]:
        """压缩上下文"""
        try:
            from app.agent.context_compressor import context_compressor
            return context_compressor.compress(messages)
        except ImportError:
            pass
        
        # 简易压缩：保留 system + 最后 10 条消息
        system_msgs = [m for m in messages if m.get("role") == "system"]
        other_msgs = [m for m in messages if m.get("role") != "system"]
        keep = min(10, len(other_msgs))
        return system_msgs + other_msgs[-keep:]
    
    def _format_tool_list(self) -> str:
        """格式化工具列表供系统提示词使用"""
        tools = self.skill_registry.get_tool_schemas()
        lines = []
        for t in tools:
            name = t['function']['name']
            desc = t['function']['description']
            params = t['function'].get('parameters', {}).get('properties', {})
            required = t['function'].get('parameters', {}).get('required', [])
            
            param_lines = []
            for pname, pinfo in params.items():
                req = " (必填)" if pname in required else ""
                pdesc = pinfo.get('description', '')
                param_lines.append(f"    - {pname}{req}: {pdesc}")
            
            lines.append(f"- **{name}**: {desc}")
            if param_lines:
                lines.extend(param_lines)
            lines.append("")
        
        return "\n".join(lines) or "（无可用工具）"
    
    def _format_context(self, context: dict) -> str:
        """格式化上下文信息"""
        parts = []
        if context.get("pdf_title"):
            parts.append(f"- 当前文献: **{context['pdf_title']}**")
        if context.get("pdf_id"):
            parts.append(f"- 当前 PDF 标识: `{context['pdf_id']}`（如需使用 paper_qa/paper_summarize 工具，将此值作为 pdf_id 参数）")
        if context.get("pdf_full_text"):
            text = context["pdf_full_text"]
            if len(text) > 15000:
                text = text[:15000] + "\n...(内容过长已截断)"
            parts.append(f"- PDF 全文内容:\n```\n{text}\n```")
        if context.get("pdf_text"):
            text = context["pdf_text"]
            if len(text) > 2000:
                text = text[:2000] + "\n...(截断)"
            parts.append(f"- 文献片段内容:\n```\n{text}\n```")
        if context.get("selected_text"):
            parts.append(f"- 用户选中文本: `{context['selected_text']}`")
        if context.get("collection"):
            parts.append(f"- 当前收藏夹: {context['collection']}")
        if context.get("notes"):
            parts.append(f"- 笔记: {context['notes']}")
        return "\n".join(parts) if parts else "无特定上下文"


# 全局实例
agent_core = AgentCore()
