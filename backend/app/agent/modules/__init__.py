"""
六大模块Agent注册表

统一管理五大模块Agent实例，供主控Agent和工作流引擎调度
"""

from app.agent.base_module import BaseModule
from app.agent.modules.knowledge_agent import KnowledgeAgent
from app.agent.modules.writing_agent import WritingAgent
from app.agent.modules.output_agent import OutputAgent
from app.agent.modules.chart_agent import ChartAgent
from app.agent.modules.storage_agent import StorageAgent

_agents: dict[str, BaseModule] = {}


def _init_agents():
    global _agents
    if _agents:
        return
    _agents = {
        "knowledge": KnowledgeAgent(),
        "writing": WritingAgent(),
        "output": OutputAgent(),
        "chart": ChartAgent(),
        "storage": StorageAgent(),
    }


def get_agent(name: str) -> BaseModule | None:
    _init_agents()
    return _agents.get(name)


def get_all_agents() -> dict[str, BaseModule]:
    _init_agents()
    return dict(_agents)


def list_agents() -> list[dict]:
    _init_agents()
    return [agent.get_status() for agent in _agents.values()]
