"""
Agent 工具调度核心框架 (ToolRegistry + AgentOrchestrator)
Phase 2 — 实现六大模块 Agent 跨模块调度能力

设计原则：
1. 所有模块工具通过 @tool 装饰器注册到全局 ToolRegistry
2. Agent 通过 function_calling 调用工具，ToolRegistry 路由到对应处理器
3. 各模块工具独立，可被 Agent 调度，也可被前端直接调用
4. 工具定义遵循 OpenAI function_calling schema 格式
"""

import json
import inspect
import asyncio
from typing import Callable, Any, Dict, List, Optional, get_type_hints
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

# ─── 工具定义 ───

@dataclass
class ToolDefinition:
    name: str
    description: str
    module: str  # literature | writing | charts | agent | knowledge | notes
    parameters: Dict[str, Any]  # JSON Schema
    handler: Callable = field(default=None, repr=False)
    requires_auth: bool = False
    tags: List[str] = field(default_factory=list)

    def to_openai_schema(self) -> Dict:
        """转换为 OpenAI function_calling schema"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


@dataclass
class ToolCall:
    tool_name: str
    arguments: Dict[str, Any]
    call_id: str = ""
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


# ─── 全局工具注册表 ───

class ToolRegistry:
    """
    全局工具注册表
    所有模块通过 registry.register(tool_def) 注册工具
    Agent 通过 registry.call(tool_name, arguments) 执行工具
    """
    
    _instance = None
    _tools: Dict[str, ToolDefinition] = {}
    _modules: Dict[str, List[str]] = {}  # module_name -> [tool_names]
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._tools = {}
            cls._modules = {}
        return cls._instance
    
    def register(self, tool: ToolDefinition) -> None:
        """注册工具"""
        self._tools[tool.name] = tool
        if tool.module not in self._modules:
            self._modules[tool.module] = []
        if tool.name not in self._modules[tool.module]:
            self._modules[tool.module].append(tool.name)
        print(f"[ToolRegistry] Registered: {tool.module}.{tool.name}")
    
    def unregister(self, name: str) -> bool:
        """注销工具"""
        if name in self._tools:
            tool = self._tools.pop(name)
            if tool.module in self._modules and name in self._modules[tool.module]:
                self._modules[tool.module].remove(name)
            return True
        return False
    
    def get(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)
    
    def get_by_module(self, module: str) -> List[ToolDefinition]:
        names = self._modules.get(module, [])
        return [self._tools[n] for n in names if n in self._tools]
    
    def list_all(self) -> List[ToolDefinition]:
        return list(self._tools.values())
    
    def list_all_schemas(self) -> List[Dict]:
        """列出所有工具的 OpenAI schema（用于 Agent system prompt）"""
        return [t.to_openai_schema() for t in self._tools.values()]
    
    def list_by_module_schemas(self, module: str) -> List[Dict]:
        return [t.to_openai_schema() for t in self.get_by_module(module)]
    
    async def call(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """执行工具"""
        tool = self._tools.get(tool_name)
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")
        
        if not tool.handler:
            raise ValueError(f"Tool {tool_name} has no handler")
        
        # 注入参数验证
        sig = inspect.signature(tool.handler)
        valid_args = {}
        for p_name, p_val in arguments.items():
            if p_name in sig.parameters:
                valid_args[p_name] = p_val
        
        # 调用处理器
        handler = tool.handler
        if asyncio.iscoroutinefunction(handler):
            return await handler(**valid_args)
        else:
            return handler(**valid_args)
    
    def summary(self) -> Dict:
        return {
            "total_tools": len(self._tools),
            "modules": {
                m: len(names) for m, names in self._modules.items()
            },
            "tools": [
                {"name": t.name, "module": t.module, "description": t.description[:50]}
                for t in self._tools.values()
            ]
        }


# ─── 工具装饰器 ───

registry = ToolRegistry()

def tool(
    name: str = "",
    module: str = "agent",
    description: str = "",
    parameters: Dict = None,
    tags: List[str] = None,
):
    """
    工具注册装饰器
    
    用法:
    @tool(name="search_literature", module="literature", description="...", parameters={...})
    async def search_literature(query: str, limit: int = 10):
        ...
    """
    def decorator(func: Callable) -> Callable:
        tool_name = name or func.__name__
        tool_desc = description or func.__doc__ or ""
        
        # 自动生成 parameters schema
        hints = get_type_hints(func)
        if parameters is None:
            props = {}
            required = []
            for p_name, p_type in hints.items():
                type_map = {
                    str: "string", int: "integer", float: "number",
                    bool: "boolean", list: "array", dict: "object", Any: "string"
                }
                py_type = p_type.__name__ if hasattr(p_type, '__name__') else "string"
                json_type = type_map.get(py_type, "string")
                
                props[p_name] = {
                    "type": json_type,
                    "description": f"Parameter: {p_name}",
                }
                # str, int, float 默认必填
                if json_type in ("string", "integer", "number"):
                    required.append(p_name)
            
            params_schema = {
                "type": "object",
                "properties": props,
                "required": required,
            }
        else:
            params_schema = parameters
        
        tool_def = ToolDefinition(
            name=tool_name,
            description=tool_desc.strip(),
            module=module,
            parameters=params_schema,
            handler=func,
            tags=tags or [],
        )
        registry.register(tool_def)
        return func
    return decorator


# ─── Agent 编排器 ───

class AgentOrchestrator:
    """
    Agent 任务编排器
    接收高层任务，自动拆解为子任务，调度各模块工具执行
    
    使用场景：
    - 用户说"帮我写第三章，需要引用相关文献" 
      → Orchestrator 调用 literature.search + writing.generate_section
    - 用户说"分析这篇 PDF 的研究方法" 
      → Orchestrator 调用 literature.decompose + agent.analyze
    """
    
    def __init__(self):
        self.registry = registry
    
    async def execute_task(self, task: str, context: Dict = None) -> Dict:
        """
        执行高层任务
        
        task: 自然语言描述的任务
        context: 上下文（topic, current_section, pdf_id 等）
        
        返回: {success, result, tools_used, next_steps}
        """
        context = context or {}
        
        # 意图分类
        intent = self._classify_intent(task)
        
        if intent == "write":
            return await self._handle_write_task(task, context)
        elif intent == "search":
            return await self._handle_search_task(task, context)
        elif intent == "chart":
            return await self._handle_chart_task(task, context)
        elif intent == "analyze":
            return await self._handle_analyze_task(task, context)
        elif intent == "cite":
            return await self._handle_cite_task(task, context)
        else:
            return {"success": False, "error": f"未知任务类型: {task}"}
    
    def _classify_intent(self, task: str) -> str:
        """简单的意图分类"""
        task_lower = task.lower()
        if any(k in task_lower for k in ["写", "生成", "撰写", "draft", "write", "generate"]):
            return "write"
        elif any(k in task_lower for k in ["搜索", "检索", "找", "search", "find", "query"]):
            return "search"
        elif any(k in task_lower for k in ["画", "图", "图表", "chart", "plot", "可视化"]):
            return "chart"
        elif any(k in task_lower for k in ["分析", "解读", "analyze", "review"]):
            return "analyze"
        elif any(k in task_lower for k in ["引用", "cite", "reference", "文献"]):
            return "cite"
        return "unknown"
    
    async def _handle_write_task(self, task: str, context: Dict) -> Dict:
        """处理写作任务"""
        topic = context.get("topic", "")
        section = context.get("section", "")
        
        # 调用文献检索
        ref_results = []
        if topic:
            try:
                results = await self.registry.call("literature_search", {
                    "query": topic, "limit": 5
                })
                ref_results = results.get("results", [])
            except Exception:
                pass
        
        # 生成章节
        section_content = ""
        if section:
            try:
                section_content = await self.registry.call("write_section", {
                    "topic": topic,
                    "section_title": section,
                    "references": ref_results,
                })
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        return {
            "success": True,
            "result": section_content,
            "tools_used": ["literature_search", "write_section"],
            "references": ref_results,
            "next_steps": ["review_and_polish", "insert_citations"],
        }
    
    async def _handle_search_task(self, task: str, context: Dict) -> Dict:
        """处理检索任务"""
        try:
            results = await self.registry.call("literature_search", {
                "query": task, "limit": 15
            })
            return {
                "success": True,
                "result": results,
                "tools_used": ["literature_search"],
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_chart_task(self, task: str, context: Dict) -> Dict:
        """处理绘图任务"""
        try:
            result = await self.registry.call("auto_generate_chart", {
                "description": task,
                "data": context.get("data", []),
            })
            return {
                "success": True,
                "result": result,
                "tools_used": ["auto_generate_chart"],
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_analyze_task(self, task: str, context: Dict) -> Dict:
        """处理分析任务"""
        pdf_id = context.get("pdf_id", "")
        try:
            result = await self.registry.call("literature_decompose", {
                "paper_id": pdf_id,
                "title": context.get("title", ""),
                "full_text": context.get("full_text", ""),
            })
            return {
                "success": True,
                "result": result,
                "tools_used": ["literature_decompose"],
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_cite_task(self, task: str, context: Dict) -> Dict:
        """处理引用任务"""
        dimension = context.get("dimension", "current_status")
        keywords = context.get("keywords", "")
        try:
            results = await self.registry.call("query_dimension", {
                "dimension": dimension,
                "keywords": keywords,
                "limit": 5,
            })
            return {
                "success": True,
                "result": results,
                "tools_used": ["query_dimension"],
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


# ─── 便捷访问 ───

def get_registry() -> ToolRegistry:
    return registry

def get_orchestrator() -> AgentOrchestrator:
    return AgentOrchestrator()
