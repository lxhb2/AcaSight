# AcaSight 学术 Agent 集成技术路线图 v1.0

> **生成日期**: 2026-05-24
> **状态**: 定稿
> **定位**: AcaSight 内置学术 Agent — 从 Hermes Agent 提取核心模式，打造学术场景专用智能体
> **权威级别**: 本文档是 Agent 集成的唯一执行参考，与 TECHNICAL_MANUAL.md 互补

---

## 核心设计理念

**不是移植 Hermes Agent，而是提取其 Agent 范式并学术化。**

Hermes Agent 的价值不在于代码本身（它是通用聊天 Agent），而在于其 **Agent 架构模式**：
- **工具调用循环**：LLM → 工具选择 → 执行 → 观察结果 → 继续推理
- **技能系统**：可声明式注册能力，Agent 自动调度
- **记忆管理**：跨会话持久化 + 上下文压缩
- **子代理并行**：拆分复杂任务为并行工作流

AcaSight 要做的是：**把这些模式映射到学术场景，构建"学术工具链"而非"通用聊天"**。

---

## 第一部分：架构设计

### 1.1 Agent 内核架构（借鉴 Hermes，适配学术）

```
┌─────────────────────────────────────────────────────────┐
│                    AcaSight Frontend                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ PDF 阅读器│ │ 写作面板 │ │ 数据面板 │ │ Zotero   │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘  │
│       │             │            │             │         │
│  ┌────▼─────────────▼────────────▼─────────────▼─────┐  │
│  │              Agent Controller (前端)               │  │
│  │  · 任务分发 · 状态管理 · 流式渲染 · 气泡交互     │  │
│  └─────────────────────┬───────────────────────────┘  │
└────────────────────────┼──────────────────────────────┘
                         │ HTTP/SSE
┌────────────────────────▼──────────────────────────────┐
│              AcaSight Backend (FastAPI)                │
│  ┌──────────────────────────────────────────────────┐ │
│  │              Agent Core (Python)                  │ │
│  │  ┌────────────┐  ┌─────────────┐  ┌───────────┐ │ │
│  │  │ Planner    │  │ Executor    │  │ Observer  │ │ │
│  │  │ 任务规划   │→ │ 工具调用    │→ │ 结果评估  │ │ │
│  │  └────────────┘  └─────────────┘  └───────────┘ │ │
│  │        ↑               │                  │      │ │
│  │        └───────────────┘──────────────────┘      │ │
│  │              (推理循环，最多 N 轮)                │ │
│  └──────────────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────────────┐ │
│  │           Academic Skill Registry                 │ │
│  │  文献搜索│PDF精读│写作润色│数据分析│格式排版│…  │ │
│  └──────────────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────────────┐ │
│  │           Memory & Context Engine                 │ │
│  │  会话记忆│文献知识库│用户偏好│研究上下文         │ │
│  └──────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

### 1.2 Agent Loop 核心流程（简化版 ReAct）

```python
# 简化的 Agent 推理循环
async def agent_loop(task: str, context: dict, max_turns: int = 10):
    messages = [build_system_prompt(task, context)]
    
    for turn in range(max_turns):
        # 1. LLM 推理 → 选择工具或直接回答
        response = await llm.chat(messages, tools=skill_registry.get_tool_schemas())
        
        # 2. 如果是直接回答 → 返回结果
        if not response.tool_calls:
            return response.content
        
        # 3. 执行工具调用
        for tool_call in response.tool_calls:
            result = await skill_registry.execute(tool_call)
            messages.append(tool_result_message(tool_call, result))
        
        # 4. 继续循环，LLM 观察结果后决定下一步
    
    return "任务复杂度超出单次处理能力，已部分完成。"
```

### 1.3 与现有架构的集成点

| 现有模块 | Agent 增强 | 改动量 |
|----------|-----------|--------|
| `ai_service.py` | 扩展为 AgentCore，保留现有 chat() 接口 | 中 |
| `routers/chat.py` | 增加 `/api/agent/task` 端点 | 小 |
| `AISidePanel.tsx` | 增加 Agent 模式切换（聊天/Agent） | 中 |
| `routers/writing.py` | 注册为 Agent Skill | 小 |
| `routers/search.py` | 注册为 Agent Skill | 小 |
| `services/vector_service.py` | 作为 RAG Skill 的检索后端 | 小 |

---

## 第二部分：学术技能体系（Skill Registry）

### 2.1 技能注册表设计

```python
# backend/app/agent/skill_registry.py

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Any
from enum import Enum

class SkillCategory(Enum):
    LITERATURE = "literature"    # 文献管理
    READING = "reading"          # PDF 阅读
    WRITING = "writing"          # 写作辅助
    ANALYSIS = "analysis"        # 数据分析
    FORMATTING = "formatting"    # 格式排版
    TRANSLATION = "translation"  # 翻译
    SEARCH = "search"            # 检索

@dataclass
class SkillDefinition:
    """学术技能定义（对标 Hermes skill_utils.parse_frontmatter）"""
    name: str                           # 技能名称
    description: str                    # LLM 可读描述
    category: SkillCategory             # 分类
    parameters: dict                    # JSON Schema 参数定义
    handler: Callable                   # 实际执行函数
    examples: List[str] = field(default_factory=list)  # 使用示例
    requires_context: List[str] = field(default_factory=list)  # 需要的上下文（如 pdf_text, collection_id）

class SkillRegistry:
    """技能注册表 — Agent 通过此表发现和调用技能"""
    
    def __init__(self):
        self._skills: Dict[str, SkillDefinition] = {}
    
    def register(self, skill: SkillDefinition):
        self._skills[skill.name] = skill
    
    def get_tool_schemas(self) -> List[dict]:
        """生成 OpenAI function calling 格式的工具定义"""
        return [
            {
                "type": "function",
                "function": {
                    "name": s.name,
                    "description": s.description,
                    "parameters": s.parameters,
                }
            }
            for s in self._skills.values()
        ]
    
    async def execute(self, tool_name: str, arguments: dict) -> Any:
        skill = self._skills.get(tool_name)
        if not skill:
            return {"error": f"未知技能: {tool_name}"}
        return await skill.handler(**arguments)
```

### 2.2 学术技能清单（Phase 1-3 对应用户需求）

#### Phase 1 技能（MVP，3个月）

| 技能名 | 分类 | 描述 | 参数 | 依赖 |
|--------|------|------|------|------|
| `paper_qa` | reading | 基于PDF全文回答问题 | query, pdf_id | vector_service |
| `paper_summarize` | reading | 生成论文摘要 | pdf_id, length | ai_service |
| `translate_text` | translation | 学术翻译 | text, source_lang, target_lang | ai_service |
| `polish_text` | writing | 学术润色 | text, style | ai_service |
| `rewrite_text` | writing | 降重改写 | text | ai_service |
| `expand_text` | writing | 段落扩写 | text, context | ai_service |
| `shrink_text` | writing | 段落缩写 | text | ai_service |
| `search_literature` | search | 多源文献检索 | query, sources, limit | search_service |
| `format_bibliography` | formatting | 参考文献格式化 | references, style | ai_service |

#### Phase 2 技能（6个月）

| 技能名 | 分类 | 描述 | 参数 | 依赖 |
|--------|------|------|------|------|
| `cross_paper_compare` | reading | 跨文献对比分析 | paper_ids, aspect | vector_service, ai_service |
| `generate_introduction` | writing | 自动生成引言 | topic, references | ai_service |
| `generate_literature_review` | writing | 文献综述生成 | topic, paper_ids | ai_service, vector_service |
| `analyze_data` | analysis | 实验数据统计分析 | data_path, analysis_type | pandas, scipy |
| `generate_chart` | analysis | 学术图表生成 | data, chart_type, template | plotly |
| `extract_citations` | formatting | 引用提取与检查 | doc_path | ai_service |
| `check_format_compliance` | formatting | 格式合规检查 | doc_path, template | python-docx |

#### Phase 3 技能（12个月）

| 技能名 | 分类 | 描述 | 参数 | 依赖 |
|--------|------|------|------|------|
| `build_knowledge_graph` | literature | 构建知识图谱 | paper_ids | networkx |
| `find_research_gaps` | literature | 识别研究空白 | topic, paper_ids | ai_service, vector_service |
| `trend_analysis` | literature | 研究趋势分析 | topic, year_range | search_service, ai_service |
| `design_experiment` | analysis | 实验方案设计 | topic, constraints | ai_service |
| `sample_size_calc` | analysis | 样本量计算 | effect_size, alpha, power | scipy |

### 2.3 技能描述模板（LLM 可读，关键！）

技能描述是 Agent 能否正确选择工具的关键。每个技能的 `description` 必须包含：
1. **何时使用**：触发条件
2. **做什么**：功能说明
3. **返回什么**：输出格式

```python
SkillDefinition(
    name="paper_qa",
    description="""基于PDF全文回答学术问题。当用户询问某篇论文的具体内容、方法、结果时使用。
输入查询问题和PDF标识符，返回基于全文的精准回答，附带引用位置。
适用于：'这篇论文用了什么方法？' '实验结果是什么？' '作者的主要贡献是什么？'""",
    category=SkillCategory.READING,
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "用户关于论文的问题"},
            "pdf_id": {"type": "string", "description": "PDF文件标识符"}
        },
        "required": ["query", "pdf_id"]
    },
    handler=paper_qa_handler,
    examples=[
        "这篇论文的研究方法是什么？",
        "作者在实验中使用了哪些数据集？"
    ]
)
```

---

## 第三部分：Agent Core 实现

### 3.1 文件结构

```
backend/app/agent/
├── __init__.py
├── core.py              # Agent 推理循环（ReAct 模式）
├── skill_registry.py    # 技能注册表
├── skills/              # 技能实现
│   ├── __init__.py
│   ├── reading.py       # 阅读类技能（paper_qa, paper_summarize）
│   ├── writing.py       # 写作类技能（polish, expand, shrink, rewrite）
│   ├── translation.py   # 翻译技能
│   ├── search.py        # 检索技能
│   ├── analysis.py      # 数据分析技能
│   └── formatting.py    # 格式排版技能
├── memory.py            # 会话记忆 + 研究上下文
├── planner.py           # 任务规划器（复杂任务拆解）
└── context.py           # 上下文管理（借鉴 Hermes context_engine）
```

### 3.2 Agent Core 核心代码

```python
# backend/app/agent/core.py

import json
import structlog
from typing import AsyncGenerator, Optional, Dict, Any, List
from app.services.ai_service import ai_service
from app.agent.skill_registry import SkillRegistry

logger = structlog.get_logger()

# 学术 Agent 系统提示词
ACADEMIC_AGENT_SYSTEM_PROMPT = """你是 AcaSight 学术智能体，一位专业的学术研究助手。

你可以使用以下工具来帮助用户完成学术任务：
- 文献搜索、阅读、对比
- 论文写作、润色、翻译、降重
- 数据分析、图表生成
- 格式排版、引用检查

工作原则：
1. 理解用户的学术需求，选择最合适的工具
2. 如果任务复杂，拆分为多个步骤逐步完成
3. 基于文献原文回答，不要编造内容
4. 翻译保持学术术语准确
5. 每步操作都要向用户说明正在做什么

当前上下文：
{context}
"""


class AgentCore:
    """AcaSight 学术 Agent 核心"""
    
    def __init__(self):
        self.skill_registry = SkillRegistry()
        self.max_turns = 10
        self._register_default_skills()
    
    def _register_default_skills(self):
        """注册所有默认技能"""
        from app.agent.skills.reading import register_reading_skills
        from app.agent.skills.writing import register_writing_skills
        from app.agent.skills.translation import register_translation_skills
        from app.agent.skills.search import register_search_skills
        
        register_reading_skills(self.skill_registry)
        register_writing_skills(self.skill_registry)
        register_translation_skills(self.skill_registry)
        register_search_skills(self.skill_registry)
    
    async def run(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List[Dict]] = None,
        stream: bool = True,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """执行 Agent 任务，流式返回中间步骤和最终结果
        
        Yields:
            {"type": "thinking", "content": "..."}  — Agent 思考过程
            {"type": "tool_call", "name": "...", "args": {...}}  — 工具调用
            {"type": "tool_result", "name": "...", "result": "..."}  — 工具结果
            {"type": "answer", "content": "..."}  — 最终回答
        """
        context = context or {}
        
        # 构建消息
        messages = [
            {"role": "system", "content": ACADEMIC_AGENT_SYSTEM_PROMPT.format(
                context=self._format_context(context)
            )}
        ]
        
        # 添加对话历史
        if conversation_history:
            messages.extend(conversation_history[-6:])  # 最近3轮
        
        messages.append({"role": "user", "content": task})
        
        # 获取工具定义
        tools = self.skill_registry.get_tool_schemas()
        
        for turn in range(self.max_turns):
            # LLM 推理
            response = await self._llm_call(messages, tools)
            
            # 检查是否有工具调用
            tool_calls = self._extract_tool_calls(response)
            
            if not tool_calls:
                # 直接回答
                answer = self._extract_text(response)
                yield {"type": "answer", "content": answer}
                return
            
            # 执行工具调用
            assistant_msg = {"role": "assistant", "content": response}
            messages.append(assistant_msg)
            
            for tc in tool_calls:
                yield {"type": "tool_call", "name": tc["name"], "args": tc["arguments"]}
                yield {"type": "thinking", "content": f"正在执行: {tc['name']}..."}
                
                result = await self.skill_registry.execute(tc["name"], tc["arguments"])
                
                yield {"type": "tool_result", "name": tc["name"], "result": str(result)[:2000]}
                messages.append({"role": "tool", "content": json.dumps(result, ensure_ascii=False), "tool_call_id": tc["id"]})
        
        # 超过最大轮次
        yield {"type": "answer", "content": "任务步骤较多，已完成部分操作。请继续提问以完成剩余部分。"}
    
    async def _llm_call(self, messages: list, tools: list) -> str:
        """调用 LLM，支持工具调用"""
        # 使用现有 ai_service，增加 tools 参数
        chunks = []
        async for chunk in ai_service.chat_with_tools(messages, tools=tools):
            chunks.append(chunk)
        return "".join(chunks)
    
    def _extract_tool_calls(self, response: str) -> list:
        """从 LLM 响应中提取工具调用（兼容多种格式）"""
        # OpenAI function calling 格式
        # 或解析 <tool_call/> XML 标签（对于不支持 function calling 的模型）
        pass
    
    def _format_context(self, context: dict) -> str:
        """格式化上下文信息"""
        parts = []
        if "pdf_title" in context:
            parts.append(f"当前文献: {context['pdf_title']}")
        if "pdf_text" in context:
            parts.append(f"文献全文(截断): {context['pdf_text'][:3000]}...")
        if "selected_text" in context:
            parts.append(f"选中文本: {context['selected_text']}")
        if "collection" in context:
            parts.append(f"当前收藏夹: {context['collection']}")
        return "\n".join(parts) if parts else "无特定上下文"


# 全局实例
agent_core = AgentCore()
```

### 3.3 技能实现示例

```python
# backend/app/agent/skills/reading.py

from app.agent.skill_registry import SkillDefinition, SkillCategory, SkillRegistry
from app.services.ai_service import ai_service
from app.services.vector_service import vector_service
import structlog

logger = structlog.get_logger()


async def paper_qa_handler(query: str, pdf_id: str) -> dict:
    """基于PDF全文回答问题"""
    try:
        # 1. 从向量库检索相关段落
        relevant_chunks = await vector_service.search(query, filter={"pdf_id": pdf_id}, top_k=5)
        
        if not relevant_chunks:
            return {"answer": "未找到相关内容，请确认PDF已正确导入。", "citations": []}
        
        # 2. 构建RAG提示
        context_text = "\n\n---\n\n".join([c["text"] for c in relevant_chunks])
        
        messages = [
            {"role": "system", "content": "基于以下文献内容回答问题。如果无法从文献中找到答案，请明确说明。引用时标注段落来源。"},
            {"role": "user", "content": f"文献内容：\n{context_text}\n\n问题：{query}"}
        ]
        
        # 3. LLM 生成回答
        result = await ai_service.chat(messages, max_tokens=1500)
        
        return {
            "answer": result,
            "citations": [
                {"text": c["text"][:100], "page": c.get("page", "?"), "score": c.get("score", 0)}
                for c in relevant_chunks[:3]
            ]
        }
    except Exception as e:
        logger.error("paper_qa failed", error=str(e))
        return {"answer": f"处理失败: {str(e)}", "citations": []}


async def paper_summarize_handler(pdf_id: str, length: str = "medium") -> dict:
    """生成论文摘要"""
    length_map = {"short": 200, "medium": 500, "long": 1000}
    max_len = length_map.get(length, 500)
    
    # 获取PDF全文
    pdf_text = await _get_pdf_full_text(pdf_id)
    if not pdf_text:
        return {"summary": "无法获取PDF全文", "word_count": 0}
    
    messages = [
        {"role": "system", "content": f"请生成学术论文摘要，约{max_len}字。包含：研究背景、方法、主要发现、结论。"},
        {"role": "user", "content": pdf_text[:12000]}
    ]
    
    summary = await ai_service.chat(messages, max_tokens=max_len + 200)
    return {"summary": summary, "word_count": len(summary)}


async def _get_pdf_full_text(pdf_id: str) -> str:
    """获取PDF全文"""
    from app.services.pdf_service import PDFService
    return await PDFService.extract_text(pdf_id)


def register_reading_skills(registry: SkillRegistry):
    """注册阅读类技能"""
    registry.register(SkillDefinition(
        name="paper_qa",
        description="基于PDF全文回答学术问题。当用户询问某篇论文的具体内容、方法、结果时使用。输入查询问题和PDF标识符，返回基于全文的精准回答，附带引用位置。",
        category=SkillCategory.READING,
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "关于论文的问题"},
                "pdf_id": {"type": "string", "description": "PDF文件标识符"}
            },
            "required": ["query", "pdf_id"]
        },
        handler=paper_qa_handler,
    ))
    
    registry.register(SkillDefinition(
        name="paper_summarize",
        description="生成学术论文摘要。当用户要求总结、概括论文时使用。支持短/中/长三种长度。",
        category=SkillCategory.READING,
        parameters={
            "type": "object",
            "properties": {
                "pdf_id": {"type": "string", "description": "PDF文件标识符"},
                "length": {"type": "string", "enum": ["short", "medium", "long"], "description": "摘要长度"}
            },
            "required": ["pdf_id"]
        },
        handler=paper_summarize_handler,
    ))
```

---

## 第四部分：前端 Agent 交互设计

### 4.1 Agent 模式 UI

在 AISidePanel 中增加模式切换：

```
┌──────────────────────────────┐
│  [💬 聊天] [🤖 Agent] [📋 历史] │  ← 模式切换标签
├──────────────────────────────┤
│                              │
│  🤖 Agent 模式               │
│  ─────────────────           │
│  我可以帮你完成复杂的学术任务：│
│                              │
│  🔍 搜索并整理10篇相关文献    │
│  📖 对比这3篇论文的方法差异   │
│  ✍️ 帮我写一段关于XX的引言    │
│  📊 分析这组实验数据          │
│                              │
│  ┌────────────────────────┐  │
│  │ 请描述你的学术任务...    │  │
│  └────────────────────────┘  │
└──────────────────────────────┘
```

### 4.2 Agent 执行过程可视化

```
┌──────────────────────────────┐
│  👤 帮我搜索近3年知识图谱相关 │
│     文献，并总结研究趋势      │
│                              │
│  🤖 好的，我来帮你完成这个    │
│     任务。分步执行：          │
│                              │
│  ① 搜索文献... ✅ 找到 23 篇 │
│  ② 去重排序... ✅ 保留 18 篇 │
│  ③ 提取关键信息... ✅        │
│  ④ 生成趋势分析... ✅        │
│                              │
│  📊 **近3年知识图谱研究趋势** │
│                              │
│  **热点方向**：               │
│  1. 大语言模型+知识图谱融合  │
│  2. 多模态知识图谱构建       │
│  3. 时序知识图谱推理         │
│  ...                         │
│                              │
│  **发文趋势**：年增长约35%    │
│  **核心团队**：清华、浙大...  │
│                              │
│  [📋 详细报告] [📊 趋势图]   │
└──────────────────────────────┘
```

### 4.3 前端组件改造

```typescript
// frontend/src/components/PDFReader/AgentPanel.tsx (新建)

interface AgentStep {
  type: 'thinking' | 'tool_call' | 'tool_result' | 'answer';
  content: string;
  name?: string;
  args?: Record<string, any>;
  status?: 'running' | 'done' | 'error';
}

export const AgentPanel: React.FC<AgentPanelProps> = ({ pdfId, pdfTitle, pdfFullText }) => {
  const [steps, setSteps] = useState<AgentStep[]>([]);
  const [input, setInput] = useState('');
  const [isRunning, setIsRunning] = useState(false);

  const handleRun = async () => {
    setIsRunning(true);
    setSteps([]);
    
    const response = await fetch('/api/agent/task', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        task: input,
        context: { pdf_id: pdfId, pdf_title: pdfTitle, pdf_text: pdfFullText?.slice(0, 5000) }
      }),
    });
    
    // SSE 流式接收
    const reader = response.body!.getReader();
    const decoder = new TextDecoder();
    
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      const events = decoder.decode(value).split('\n\n');
      for (const event of events) {
        if (!event.startsWith('data: ')) continue;
        const data = JSON.parse(event.slice(6));
        setSteps(prev => [...prev, data]);
      }
    }
    
    setIsRunning(false);
  };

  return (
    <div className="flex flex-col h-full">
      {/* 执行步骤 */}
      <div className="flex-1 overflow-auto p-3 space-y-2">
        {steps.map((step, i) => (
          <AgentStepCard key={i} step={step} />
        ))}
      </div>
      
      {/* 输入区 */}
      <div className="p-3 border-t">
        <textarea
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="描述你的学术任务..."
          className="w-full rounded-lg px-3 py-2 text-sm resize-none"
          rows={3}
        />
        <button onClick={handleRun} disabled={isRunning}>
          {isRunning ? '执行中...' : '开始执行'}
        </button>
      </div>
    </div>
  );
};
```

---

## 第五部分：后端 API 设计

### 5.1 Agent 端点

```yaml
# Agent API

POST /api/agent/task
  body:
    task: string           # 用户任务描述
    context?:              # 可选上下文
      pdf_id?: string
      pdf_title?: string
      pdf_text?: string
      selected_text?: string
      collection_id?: string
    conversation_history?: list  # 对话历史
    max_turns?: int        # 最大推理轮次（默认10）
  response: SSE stream
    data: {"type": "thinking", "content": "..."}
    data: {"type": "tool_call", "name": "...", "args": {...}}
    data: {"type": "tool_result", "name": "...", "result": "..."}
    data: {"type": "answer", "content": "..."}

GET /api/agent/skills
  response: 可用技能列表

POST /api/agent/skills/{name}/execute
  body: 技能参数
  response: 技能执行结果（直接调用，不经 Agent 循环）
```

### 5.2 Router 实现

```python
# backend/app/routers/agent.py

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import json

from app.agent.core import agent_core

router = APIRouter()


class AgentTaskRequest(BaseModel):
    task: str
    context: Optional[Dict[str, Any]] = None
    conversation_history: Optional[List[Dict]] = None
    max_turns: int = 10


@router.post("/task")
async def run_agent_task(request: AgentTaskRequest):
    """执行 Agent 任务，SSE 流式返回"""
    
    async def event_stream():
        async for event in agent_core.run(
            task=request.task,
            context=request.context,
            conversation_history=request.conversation_history,
        ):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/skills")
async def list_skills():
    """列出所有可用技能"""
    skills = agent_core.skill_registry.get_tool_schemas()
    return {"skills": skills}
```

---

## 第六部分：分阶段实施计划

### Phase 1: Agent MVP（第1-4周）— 核心循环 + 5个基础技能

| 周 | 任务 | 产出 | 工作量 |
|---|------|------|--------|
| W1 | Agent Core 推理循环 + Skill Registry | `agent/core.py`, `agent/skill_registry.py` | 3天 |
| W1 | AI Service 增加 tools/function calling 支持 | `services/ai_service.py` 扩展 | 1天 |
| W2 | 实现5个基础技能：paper_qa, paper_summarize, translate, polish, search | `agent/skills/reading.py`, `writing.py`, `translation.py`, `search.py` | 3天 |
| W2 | Agent Router + SSE 流式端点 | `routers/agent.py` | 1天 |
| W3 | 前端 AgentPanel 组件 | `PDFReader/AgentPanel.tsx` | 2天 |
| W3 | 模式切换（聊天/Agent）集成到 AISidePanel | `AISidePanel.tsx` 改造 | 1天 |
| W4 | 联调测试 + 快捷任务预设 | 预设任务模板 | 2天 |
| W4 | Bug 修复 + 性能优化 | | 1天 |

**Phase 1 验收标准**：
- [ ] Agent 能接收自然语言任务，自动选择工具执行
- [ ] 5个基础技能正常工作
- [ ] 前端能看到 Agent 执行步骤
- [ ] SSE 流式输出正常
- [ ] `npm run build` 零错误

### Phase 2: 深度学术能力（第5-12周）

| 周 | 任务 | 技能 |
|---|------|------|
| W5-6 | 跨文献对比 + 文献综述生成 | `cross_paper_compare`, `generate_literature_review` |
| W7-8 | 数据分析 + 图表生成 | `analyze_data`, `generate_chart` |
| W9-10 | 引言/结论自动生成 + 写作增强 | `generate_introduction`, `generate_conclusion` |
| W11-12 | 参考文献格式化 + 格式合规检查 | `format_bibliography`, `check_format_compliance` |

### Phase 3: 高级 Agent 能力（第13-20周）

| 周 | 任务 | 技能 |
|---|------|------|
| W13-14 | 知识图谱构建 + 可视化 | `build_knowledge_graph` |
| W15-16 | 研究趋势分析 + 空白识别 | `trend_analysis`, `find_research_gaps` |
| W17-18 | 实验设计 + 样本量计算 | `design_experiment`, `sample_size_calc` |
| W19-20 | 多文档协同 + 版本对比 | `content_reuse`, `diff_documents` |

---

## 第七部分：关键技术决策

### 7.1 工具调用方式

| 方案 | 优点 | 缺点 | 决策 |
|------|------|------|------|
| OpenAI function calling | 原生支持，结构化 | 仅 OpenAI 兼容 API | ✅ 主力方案 |
| XML 标签解析 | 模型无关 | 不可靠，需手动解析 | 备选 |
| ReAct prompt | 最通用 | 效率低 | 仅用于不支持 FC 的模型 |

**策略**：优先使用 function calling（硅基流动/DeepSeek/Qwen 均支持），对不支持的模型 fallback 到 ReAct prompt。

### 7.2 上下文管理

借鉴 Hermes Agent 的 `context_engine.py` 模式：

```python
class AgentContext:
    """管理 Agent 的上下文窗口"""
    
    def __init__(self, max_tokens: int = 8000):
        self.max_tokens = max_tokens
        self.pdf_text_budget = 4000   # PDF 全文最多占 4000 tokens
        self.history_budget = 2000    # 对话历史 2000 tokens
        self.tool_result_budget = 1500 # 工具结果 1500 tokens
        self.system_budget = 500      # 系统提示 500 tokens
    
    def build_messages(self, task, context, history, tool_results):
        """在 token 预算内组装消息"""
        messages = [{"role": "system", "content": self._build_system_prompt()}]
        messages.extend(self._truncate_history(history))
        messages.append({"role": "user", "content": task})
        # 按预算截断各部分...
        return messages
```

### 7.3 与 Hermes Agent 源码的映射

| Hermes 模块 | AcaSight 对应 | 复用方式 |
|-------------|---------------|----------|
| `agent/run_agent.py` | `agent/core.py` | 提取 ReAct 循环模式，重写 |
| `agent/skill_utils.py` | `agent/skill_registry.py` | 提取 frontmatter 解析，简化 |
| `agent/prompt_builder.py` | `agent/core.py` (系统提示部分) | 参考上下文注入逻辑 |
| `agent/memory_manager.py` | `agent/memory.py` | 参考记忆管理架构，简化 |
| `agent/tool_executor.py` | `agent/core.py` (工具执行部分) | 提取并发执行模式 |
| `agent/context_engine.py` | `agent/context.py` | 参考上下文压缩策略 |
| `agent/conversation_loop.py` | `agent/core.py` | 参考对话循环管理 |
| `tools/` | `agent/skills/` | 不复用，完全重写为学术技能 |

**原则**：Hermes 代码作为架构参考，不直接复制。原因：
1. Hermes 是通用 Agent，AcaSight 是学术专用
2. Hermes 依赖链深（hermes_cli, hermes_constants 等），剥离成本高
3. AcaSight 已有自己的 AI service、向量服务等基础设施

---

## 第八部分：风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| function calling 不稳定 | 中 | 高 | ReAct prompt 作为 fallback |
| Agent 循环死循环 | 低 | 高 | max_turns 硬限制 + 超时机制 |
| 工具结果超出上下文 | 中 | 中 | 智能截断 + 摘要压缩 |
| LLM 幻觉学术内容 | 高 | 高 | RAG 检索原文 + 引用标注 + "无法确定" 提示 |
| 并发工具调用冲突 | 低 | 中 | 顺序执行为主，读操作可并发 |
| 前端 SSE 兼容性 | 低 | 低 | polyfill + 超时重连 |

---

> **文档版本**: v1.0
> **核心原则**: 提取架构模式，不移植代码；学术场景优先，工具链而非聊天；渐进式增强，每个 Phase 独立可用
