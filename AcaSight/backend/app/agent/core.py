"""
Agent Core — 学术 Agent 推理循环引擎（v2.0）
基于 ReAct 模式：Think → Act → Observe → ...

核心改进（对比 v1）：
1. 真正的 Function Calling — 使用 chat_with_tools() 而非文本解析
2. 多工具并行执行 — 一次 LLM 调用可触发多个工具
3. 上下文压缩 — 超 token 阈值时自动压缩历史
4. 错误恢复 — provider 失败自动重试/降级
5. 深度 Skill 规则 — Nature 期刊标准嵌入系统提示

参考架构：
- Hermes Agent: run_agent.py + conversation_loop.py 的对话循环设计
- nature-skills: 完整的学术规则体系
"""

import asyncio
import json
import structlog
from typing import AsyncGenerator, Dict, Any, List, Optional

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
    """AcaSight 学术 Agent 核心推理引擎
    
    基于 ReAct 模式的 Function Calling Agent:
    1. LLM 接收消息 + 工具定义 → 返回 tool_calls 或文本
    2. 如果是 tool_calls → 执行工具 → 结果返回给 LLM
    3. 如果是文本 → 作为最终回答返回给用户
    """
    
    def __init__(self):
        self.skill_registry: Optional[Any] = None
        self.max_turns = 12          # 最大推理轮次
        self.max_retries = 2         # provider 失败的恢复重试次数
        self._initialized = False
    
    def _ensure_initialized(self):
        if not self._initialized:
            from app.agent.skill_registry import SkillRegistry
            from app.agent.skills.nature_skills import register_nature_skills
            self.skill_registry = SkillRegistry()
            register_nature_skills(self.skill_registry)
            self._initialized = True
    
    async def run(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List[Dict]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """执行 Agent 任务，流式返回推理步骤
        
        Yields:
            {"type": "thinking", "content": "..."}       — Agent 思考过程
            {"type": "tool_call", "name": "...", "args": {...}}  — 工具调用
            {"type": "tool_result", "name": "...", "result": "..."} — 工具执行结果
            {"type": "answer", "content": "..."}          — 最终回答
            {"type": "error", "content": "..."}           — 错误
        """
        context = context or {}
        self._ensure_initialized()
        
        # 1. 构建系统提示词
        tool_list = self._format_tool_list()
        system_prompt = ACADEMIC_SYSTEM_PROMPT.format(
            tool_list=tool_list,
            context=self._format_context(context),
        )
        
        # 2. 构建消息列表
        messages: List[Dict] = [{"role": "system", "content": system_prompt}]
        
        # 添加对话历史（保留最近 3 轮）
        if conversation_history:
            for msg in conversation_history[-6:]:
                if msg["role"] != "system":  # 不重复 system
                    messages.append(msg)
        
        messages.append({"role": "user", "content": task})
        
        # 3. 获取工具定义
        tools = self.skill_registry.get_tool_schemas()
        if not tools:
            yield {"type": "error", "content": "无可用技能"}
            return
        
        yield {"type": "thinking", "content": "正在分析任务..."}
        
        # 4. 主推理循环
        for turn in range(self.max_turns):
            # 4a. 检查上下文是否需要压缩
            messages = self._maybe_compress(messages)
            
            # 4b. 调用 LLM（带重试）
            result = await self._llm_call_with_retry(messages, tools)
            if result.get("error"):
                yield {"type": "error", "content": result["error"]}
                return
            
            content = result.get("content", "")
            tool_calls = result.get("tool_calls", [])
            
            if tool_calls:
                # 4c. 并行执行所有工具调用
                yield {"type": "thinking", "content": f"正在执行 {len(tool_calls)} 个工具..."}
                
                # 构建 assistant 消息（含 tool_calls，供后续 LLM 多轮理解）
                assistant_msg = {
                    "role": "assistant",
                    "content": content or None,
                    "tool_calls": [
                        {
                            "id": tc.get("id", f"call_{i}"),
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": json.dumps(tc["arguments"], ensure_ascii=False),
                            }
                        }
                        for i, tc in enumerate(tool_calls)
                    ],
                }
                if content:
                    yield {"type": "thinking", "content": content}
                
                tool_results = []
                
                # 并发执行工具
                async def execute_one(tc: Dict) -> tuple:
                    tool_name = tc["name"]
                    tool_args = tc["arguments"]
                    yield_event = {"type": "tool_call", "name": tool_name, "args": tool_args}
                    result = await self.skill_registry.execute(tool_name, tool_args)
                    return (tc, result, yield_event)
                
                # 使用 asyncio.gather 并行执行
                tasks = [execute_one(tc) for tc in tool_calls]
                completed = await asyncio.gather(*tasks, return_exceptions=True)
                
                # 处理结果
                for item in completed:
                    if isinstance(item, Exception):
                        logger.error(f"Tool execution failed: {item}")
                        continue
                    tc, result, yield_event = item
                    tool_name = tc["name"]
                    
                    yield yield_event
                    
                    result_str = json.dumps(result, ensure_ascii=False, indent=2)
                    if len(result_str) > 3000:
                        result_str = result_str[:3000] + "\n... (结果截断)"
                    
                    yield {"type": "tool_result", "name": tool_name, "result": result_str}
                    
                    tool_results.append({
                        "role": "tool",
                        "tool_call_id": tc.get("id", ""),
                        "name": tool_name,
                        "content": json.dumps(result, ensure_ascii=False)[:4000],
                    })
                
                # 将 assistant 消息（含 tool_calls）和 tool 结果加入对话
                messages.append(assistant_msg)
                messages.extend(tool_results)
                
            else:
                # 4d. 无工具调用 — 直接回答
                if content:
                    yield {"type": "answer", "content": content}
                else:
                    yield {"type": "answer", "content": "任务完成，但我没有生成可用的回答。请尝试更具体地描述您的需求。"}
                return
        
        # 5. 超过最大轮次
        yield {
            "type": "answer",
            "content": "任务较复杂，已执行多步操作。请继续提问以完成剩余部分，或提供更多上下文信息。"
        }
    
    async def _llm_call_with_retry(
        self, messages: List[Dict], tools: List[Dict], retries: int = None
    ) -> Dict:
        """调用 LLM（带重试和 provider 降级）
        
        使用 chat_with_tools() 实现真正的 Function Calling。
        失败时自动重试，然后尝试降级到其他可用 provider。
        如果所有 provider 都失败，回退到纯文本对话（不带工具）。
        """
        if retries is None:
            retries = self.max_retries
        
        ai_svc = _get_ai_service()
        
        providers = []
        try:
            providers = await ai_svc.get_available_providers_with_tools()
        except Exception:
            providers = []
        if not providers:
            providers = [ai_svc._config.get('default_provider', 'ollama')]
        
        last_error = ""
        
        for provider in providers:
            for attempt in range(retries + 1):
                try:
                    result = await asyncio.wait_for(
                        ai_svc.chat_with_tools(
                            messages=messages,
                            tools=tools,
                            provider=provider,
                            temperature=0.3,
                            max_tokens=4096,
                        ),
                        timeout=60.0,
                    )
                    
                    if result.get("error"):
                        last_error = result["error"]
                        logger.warning(f"Provider {provider} attempt {attempt + 1} failed: {last_error}")
                        continue
                    
                    return result
                    
                except asyncio.TimeoutError:
                    last_error = f"Provider {provider} 超时（60s）"
                    logger.warning(f"Provider {provider} attempt {attempt + 1} timeout")
                except asyncio.CancelledError:
                    last_error = f"Provider {provider} 被取消"
                    logger.warning(f"Provider {provider} attempt {attempt + 1} cancelled")
                    break
                except Exception as e:
                    last_error = str(e)
                    logger.warning(f"Provider {provider} attempt {attempt + 1} error: {last_error}")
                    if attempt < retries:
                        await asyncio.sleep(1 * (attempt + 1))
                    continue
            
            logger.info(f"Provider {provider} exhausted, trying next...")
        
        # 所有 provider 的 function calling 都失败，回退到纯文本对话
        logger.warning("All providers failed for function calling, falling back to plain chat")
        try:
            fallback_provider = providers[0] if providers else None
            response = ""
            async for chunk in ai_svc.chat(
                messages=messages,
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
                "error": f"所有 AI 服务不可用: {last_error}。请检查 AI 配置或确保 Ollama 正在运行。"
            }
    
    def _maybe_compress(self, messages: List[Dict]) -> List[Dict]:
        """检查并压缩上下文"""
        try:
            from app.agent.context_compressor import context_compressor
            if context_compressor.should_compress(messages):
                return context_compressor.compress(messages)
        except ImportError:
            pass
        return messages
    
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
        if context.get("pdf_full_text"):
            text = context["pdf_full_text"]
            truncated = context.get("pdf_text_truncated", False)
            if len(text) > 18000:
                text = text[:18000] + "\n...(内容过长已截断)"
            warning = "\n> ⚠️ 注：PDF 全文较长，已截断，仅显示前 18000 字符。" if truncated and len(text) >= 18000 else ""
            parts.append(f"- PDF 全文内容:\n```\n{text}\n```{warning}")
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
