"""
Pulse Learning Agent
支持多模型切换（云端/本地）+ LangChain 原生工具调用

使用 langchain-ollama / langchain-openai 原生集成（支持 bind_tools），
通过 langgraph 自定义工具调用循环，不依赖 langchain.agents.create_agent。
"""
import os
import json
from typing import Annotated, Any, Dict, List, Optional

# LangGraph 状态管理（独立于 langchain.agents）
try:
    from langgraph.graph import MessagesState
    from langgraph.graph.message import add_messages
    from langchain_core.messages import AnyMessage, HumanMessage, AIMessage, ToolMessage
    from langchain_core.runnables import Runnable
    HAS_LANGGRAPH = True
except ImportError:
    HAS_LANGGRAPH = False

# 统一 LLM 客户端（用于网络检测和配置加载）
from utils.llm_client import create_client, is_online, get_active_provider

# 提示词构建
from utils.prompt_builder import (
    build_pulse_learning_system_prompt,
    build_pulse_learning_system_prompt_light,
)

# 工具（使用纯 Python 版本）
try:
    from tools.pulse_tools import (
        create_project, list_projects, get_project_status,
        create_module, get_modules,
        add_challenge, complete_challenge, finish_module,
    )
    # 尝试从独立模块导入（如果存在）
    try:
        from tools.boss_task_manager import generate_boss_task, complete_boss_task, get_boss_task
    except ImportError:
        generate_boss_task = complete_boss_task = get_boss_task = None

    try:
        from tools.challenge_manager import complete_module
    except ImportError:
        complete_module = None

    try:
        from tools.history_manager import get_learning_history, get_learning_statistics, get_daily_summary
    except ImportError:
        get_learning_history = get_learning_statistics = get_daily_summary = None

    try:
        from tools.resource_manager import add_learning_resource, add_code_snippet, get_resources, add_note
    except ImportError:
        add_learning_resource = add_code_snippet = get_resources = add_note = None

    try:
        from tools.combo_manager import reset_combo, pause_combo, resume_combo, get_combo_status
    except ImportError:
        reset_combo = pause_combo = resume_combo = get_combo_status = None

    PULSE_TOOLS_AVAILABLE = True
except ImportError:
    PULSE_TOOLS_AVAILABLE = False

# QMD Markdown 搜索引擎工具
try:
    from tools.qmd_tools import (
        qmd_search, qmd_get, qmd_get_lines,
        qmd_list_collections, qmd_list_files,
        qmd_add_collection, qmd_remove_collection, qmd_status,
    )
    QMD_TOOLS_AVAILABLE = True
except ImportError:
    QMD_TOOLS_AVAILABLE = False

LLM_CONFIG = "config/agent_llm_config.json"
MAX_MESSAGES = 40


# ==================== LangChain LLM 选择器 ====================

if HAS_LANGGRAPH:

    def _windowed_messages(old, new):
        """滑动窗口: 只保留最近 MAX_MESSAGES 条消息"""
        return add_messages(old, new)[-MAX_MESSAGES:]

    class AgentState(MessagesState):
        messages: Annotated[list[AnyMessage], _windowed_messages]

    class PulseLLM(Runnable):
        """
        使用 langchain-ollama 或 langchain-openai 原生集成的 LLM 适配器
        完整支持 bind_tools() 用于工具调用
        """

        def __init__(self, client=None, temperature: float = 0.7):
            self._raw_client = client or create_client()
            self._lc_llm = None
            self._init_lc_llm()
            self.temperature = temperature

        def _init_lc_llm(self):
            """根据 provider 类型选择 LangChain 原生集成"""
            provider = self._raw_client.provider
            base_url = self._raw_client.base_url
            model = self._raw_client.model
            api_key = self._raw_client.api_key
            temperature = self._raw_client.temperature

            if provider == "ollama":
                try:
                    from langchain_ollama import ChatOllama
                    self._lc_llm = ChatOllama(
                        model=model,
                        base_url=base_url,
                        temperature=temperature,
                    )
                    print(f"[Agent] 使用 ChatOllama: {model}")
                except ImportError:
                    print("[WARN] langchain-ollama 未安装")
                    self._lc_llm = None
            elif provider in ("siliconflow", "openai", "lmstudio"):
                try:
                    from langchain_openai import ChatOpenAI
                    self._lc_llm = ChatOpenAI(
                        model=model,
                        base_url=base_url,
                        api_key=api_key,
                        temperature=temperature,
                        timeout=60,
                    )
                    print(f"[Agent] 使用 ChatOpenAI: {model}")
                except ImportError:
                    print("[WARN] langchain-openai 未安装")
                    self._lc_llm = None

        @property
        def raw_client(self):
            return self._raw_client

        @property
        def lc_llm(self):
            return self._lc_llm

        def bind_tools(self, tools, **kwargs):
            """将工具绑定到 LangChain LLM"""
            if self._lc_llm is not None:
                return self._lc_llm.bind_tools(tools, **kwargs)
            raise RuntimeError("没有可用的 LangChain LLM，无法绑定工具")

        def invoke(self, input: Any, config: Optional[Dict] = None) -> AIMessage:
            """使用原生 LLM 调用，或回退到原始 HTTP 客户端"""
            if self._lc_llm is not None:
                return self._lc_llm.invoke(input, config=config)

            # 回退：使用原始 HTTP 客户端
            messages = self._extract_messages(input)
            response = self._raw_client.chat(messages=messages, temperature=self.temperature)
            return AIMessage(content=response["message"]["content"])

        def batch(self, inputs: List[Any], config: Optional[Dict] = None) -> List[AIMessage]:
            return [self.invoke(inp, config) for inp in inputs]

        @staticmethod
        def _extract_messages(input):
            """从各种输入格式提取消息列表"""
            if isinstance(input, dict) and "messages" in input:
                return input["messages"]
            elif isinstance(input, list):
                return input
            else:
                return [{"role": "user", "content": str(input)}]

        @property
        def lc_runnable_type(self) -> str:
            return "llm_adapter"


# ==================== Agent 构建函数 ====================

def _build_tool_list():
    """构建工具列表，过滤 None"""
    all_tools = []

    if PULSE_TOOLS_AVAILABLE:
        all_tools.extend([
            create_project, list_projects, get_project_status,
            create_module, get_modules,
            add_challenge, complete_challenge, finish_module,
            generate_boss_task, complete_boss_task, get_boss_task,
            get_learning_history, get_learning_statistics, get_daily_summary,
            add_learning_resource, add_code_snippet, get_resources, add_note,
            reset_combo, pause_combo, resume_combo, get_combo_status,
        ])

    if QMD_TOOLS_AVAILABLE:
        all_tools.extend([
            qmd_search, qmd_get, qmd_get_lines,
            qmd_list_collections, qmd_list_files,
            qmd_add_collection, qmd_remove_collection, qmd_status,
        ])

    return [t for t in all_tools if t is not None]


def build_agent(ctx=None, use_light_prompt: Optional[bool] = None,
                force_mode: Optional[str] = None):
    """
    构建 Pulse Learning Agent

    Args:
        use_light_prompt: True=精简版, False=完整版, None=自动（离线用精简）
        force_mode: 强制模式: "online"/"ollama"/"lmstudio"/None=自动
    """
    if not HAS_LANGGRAPH:
        raise RuntimeError("需要 langchain_core 和 langgraph，请运行: pip install langchain-core langgraph")

    workspace_path = os.getenv("COZE_WORKSPACE_PATH", ".")
    config_path = os.path.join(workspace_path, LLM_CONFIG)

    with open(config_path, 'r', encoding='utf-8') as f:
        cfg = json.load(f)

    if use_light_prompt is None:
        use_light_prompt = not is_online()

    if use_light_prompt:
        system_prompt = build_pulse_learning_system_prompt_light(language="中文")
    else:
        cfg_sp = cfg.get("sp", "")
        if cfg_sp and len(cfg_sp) > 100:
            system_prompt = cfg_sp
        else:
            system_prompt = build_pulse_learning_system_prompt(language="中文")

    llm = PulseLLM(force_mode=force_mode)

    tools = _build_tool_list()

    # 尝试加载 memory_saver
    checkpointer = None
    try:
        from storage.memory.memory_saver import get_memory_saver
        checkpointer = get_memory_saver()
    except Exception:
        pass

    # 使用 LangGraph 原生 create_agent（通过 langgraph-prebuilt）
    try:
        from langgraph.prebuilt import create_react_agent
        return create_react_agent(
            model=llm.lc_llm or llm,
            tools=tools,
            prompt=system_prompt,
            checkpointer=checkpointer,
            state_schema=AgentState,
        )
    except ImportError:
        # 回退：手动构建 agent
        return _build_manual_agent(llm, tools, system_prompt, checkpointer)


def build_agent_simple(use_light_prompt: Optional[bool] = None,
                       force_mode: Optional[str] = None):
    """简化版本：不依赖 memory_saver，用于快速测试"""
    if not HAS_LANGGRAPH:
        raise RuntimeError("需要 langchain_core 和 langgraph")

    workspace_path = os.getenv("COZE_WORKSPACE_PATH", ".")
    config_path = os.path.join(workspace_path, LLM_CONFIG)

    with open(config_path, 'r', encoding='utf-8') as f:
        cfg = json.load(f)

    if use_light_prompt is None:
        use_light_prompt = not is_online()

    if use_light_prompt:
        system_prompt = build_pulse_learning_system_prompt_light(language="中文")
    else:
        cfg_sp = cfg.get("sp", "")
        if cfg_sp and len(cfg_sp) > 100:
            system_prompt = cfg_sp
        else:
            system_prompt = build_pulse_learning_system_prompt(language="中文")

    llm = PulseLLM(force_mode=force_mode)
    tools = _build_tool_list()

    try:
        from langgraph.prebuilt import create_react_agent
        return create_react_agent(
            model=llm.lc_llm or llm,
            tools=tools,
            prompt=system_prompt,
        )
    except ImportError:
        return _build_manual_agent(llm, tools, system_prompt, None)


def _build_manual_agent(llm, tools, system_prompt, checkpointer):
    """手动构建 ReAct Agent（当 create_react_agent 不可用时）"""
    from langgraph.graph import StateGraph, END

    tool_map = {tool.__name__: tool for tool in tools}
    tool_list = list(tool_map.values())
    bound_llm = llm.bind_tools(tool_list)

    def chatbot(state):
        messages = [{"role": "system", "content": system_prompt}] + state["messages"]
        response = bound_llm.invoke(messages)
        return {"messages": [response]}

    def tool_router(state):
        last_msg = state["messages"][-1]
        if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
            return "tools"
        return END

    def run_tools(state):
        results = []
        for tool_call in state["messages"][-1].tool_calls:
            tool_func = tool_map.get(tool_call["name"])
            if tool_func:
                output = tool_func(**tool_call["args"])
                results.append(ToolMessage(content=str(output), tool_call_id=tool_call["id"]))
        return {"messages": results}

    workflow = StateGraph(AgentState)
    workflow.add_node("chatbot", chatbot)
    workflow.add_node("tools", run_tools)
    workflow.set_entry_point("chatbot")
    workflow.add_conditional_edges("chatbot", tool_router, {"tools": "tools", END: END})
    workflow.add_edge("tools", "chatbot")

    return workflow.compile(checkpointer=checkpointer)


def quick_chat(message: str, use_light: bool = True) -> str:
    """
    快速聊天（不启动完整 Agent）
    用于 CLI 快速测试
    """
    client = create_client()

    if use_light:
        prompt = build_pulse_learning_system_prompt_light(language="中文")
    else:
        cfg_path = os.path.join(
            os.getenv("COZE_WORKSPACE_PATH", "."),
            LLM_CONFIG
        )
        try:
            with open(cfg_path, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            cfg_sp = cfg.get("sp", "")
            prompt = cfg_sp if cfg_sp and len(cfg_sp) > 100 else \
                build_pulse_learning_system_prompt(language="中文")
        except Exception:
            prompt = build_pulse_learning_system_prompt(language="中文")

    response = client.chat(
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": message}
        ],
        temperature=client.temperature
    )
    return response["message"]["content"]


if __name__ == "__main__":
    from utils.llm_client import get_active_provider, is_online

    print("当前模式:", get_active_provider().get("provider"),
          "/", get_active_provider().get("model"))
    print("在线:", is_online())
    print()
    print("精简提示词长度:", len(build_pulse_learning_system_prompt_light()))
    print("完整提示词长度:", len(build_pulse_learning_system_prompt()))
    print()

    print("测试聊天...")
    result = quick_chat("你好", use_light=True)
    print("响应:", result[:200])
