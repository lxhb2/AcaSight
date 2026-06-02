# G.2 LangChain 评估 POC — AcaSight Agent 框架对比报告

> 日期: 2026-05-30 | 评估者: A方 | 状态: ✅完成

## 1. 评估目标

对比当前自写 Agent 框架（Agent Core v3.0）与 LangChain/LangGraph 迁移方案，评估是否值得迁移。

## 2. 当前架构分析

### 2.1 自写方案概览

| 组件 | 文件 | 行数 | 职责 |
|------|------|------|------|
| Agent Core | `core.py` | 528 | ReAct 推理循环 + LLM 调用 + 工具执行 + 中断机制 |
| 消息修复 | `message_sanitization.py` | 141 | role alternation + tool_call JSON fix + surrogate 清理 |
| 重试策略 | `retry_utils.py` | 109 | jittered backoff + 错误分类(rate_limit/context_overflow/auth) |
| 上下文压缩 | `context_compressor.py` | 107 | 长上下文摘要压缩 + 保留最近消息 |
| 技能注册 | `skill_registry.py` | 185 | 12 学术技能 schema 生成 + 执行路由 |
| 学术技能 | `nature_skills.py` | 1288 | 搜索/维度拆分/引用/图谱/写作/绘图/存储等 12 工具 |
| 路由器 | `router.py` | 303 | SSE 端点 + 会话管理 |
| 5 模块Agent | `modules/*.py` | ~960 | Knowledge/Writing/Output/Chart/Storage Agent |
| 基类 | `base_module.py` | 105 | execute/interrupt/resume/get_status 抽象 |
| 工作流引擎 | `workflow_engine.py` | 528 | 8 状态 DAG 编排 + 中断恢复 |

**自写方案总代码量**: ~4,254 行（agent/ 目录）

### 2.2 自写方案核心优势

1. **完全掌控**: 消息序列修复（role alternation）、tool_call JSON 修复、surrogate 清理等 LLM API 边缘情况全部手控
2. **学术定制**: 12 个学术技能深度定制（维度拆分、引用匹配、文献结构化），非通用 RAG 模式
3. **中断机制**: `asyncio.Lock` 中断控制，支持长任务用户取消
4. **轻量**: 无额外依赖，启动快，无版本锁定风险
5. **SSE 流式**: 原生 AsyncGenerator yield，与 FastAPI StreamingResponse 无缝对接
6. **已验证**: 生产级可靠性（从 Hermes Agent 移植的 conversation_loop 逻辑）

### 2.3 自写方案痛点

1. **工具编排简单**: 当前是单轮 ReAct，缺少 DAG/分支/条件路由
2. **无内置记忆**: 每次会话独立，无跨会话长期记忆
3. **错误恢复粗糙**: 工具失败后重试策略有限，无 checkpoint/rollback
4. **监控缺失**: 无 LangSmith 级别的 trace/span 可观测性
5. **测试覆盖为零**: Agent 逻辑无单元测试

## 3. LangChain/LangGraph 方案评估

### 3.1 LangChain 核心能力映射

| 当前自写能力 | LangChain 对应 | 迁移收益 |
|-------------|---------------|----------|
| ReAct 循环 (core.py) | `AgentExecutor` / `create_react_agent` | ❌ 无收益，自写更可控 |
| 消息修复 (message_sanitization.py) | 无内置 | ❌ LangChain 不解决此问题 |
| 重试策略 (retry_utils.py) | 无内置（需自写） | ❌ 同上 |
| 上下文压缩 (context_compressor.py) | 无内置 | ❌ 需自写 |
| 技能注册 (skill_registry.py) | `@tool` decorator + `Tool` 类 | ⚠️ 语法糖，但丧失自定义 schema 生成 |
| 中断机制 | ❌ 无原生支持 | ❌ 需自写 |
| SSE 流式 | `astream_events` | ⚠️ 可用但需适配 FastAPI |
| 工作流 DAG | **LangGraph** `StateGraph` | ✅ 核心收益 |
| 记忆管理 | `ConversationBufferMemory` 等 | ⚠️ 简单场景可用 |
| 可观测性 | **LangSmith** 集成 | ✅ 核心收益 |
| 错误恢复 | LangGraph checkpoint | ✅ 核心收益 |

### 3.2 LangGraph 详细评估

LangGraph 是 LangChain 生态中唯一有明确迁移价值的组件：

**优势**:
- `StateGraph` 支持 conditional edges + parallel branches
- Checkpointing 自动保存状态，支持 time-travel debugging
- Human-in-the-loop 原生支持（`interrupt_before/after`）
- 与 LangSmith 集成，可观测 Agent 每步执行

**劣势**:
- 学习曲线陡峭（StateGraph API + Persistence + Human-in-the-loop 三个概念层）
- 依赖链重: `langgraph` → `langchain-core` → `langsmith` → `pydantic`
- 版本迭代快，API 不稳定（0.x 阶段）
- 与 FastAPI SSE 流式输出需额外适配层
- 当前 `workflow_engine.py` 已实现 8 状态 DAG，LangGraph 不会显著简化

### 3.3 迁移成本估算

| 迁移项 | 工时 | 风险 |
|--------|------|------|
| 核心循环 → LangChain AgentExecutor | 3-5天 | 🔴 高（丧失消息修复/重试控制） |
| 核心循环 → LangGraph StateGraph | 5-8天 | 🔴 高（重写整个 Agent 层） |
| 技能注册 → @tool | 2天 | 🟡 中（12个技能 schema 重写） |
| SSE 流式适配 | 1-2天 | 🟡 中 |
| 中断机制适配 | 2天 | 🟡 中 |
| 集成测试 | 3天 | 🟡 中 |
| **总计** | **16-22天** | **高风险** |

## 4. 决策矩阵

| 维度 | 自写方案(现状) | LangChain | LangGraph |
|------|---------------|-----------|-----------|
| 可控性 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| 学术定制 | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| DAG 编排 | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| 可观测性 | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 维护成本 | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| 依赖风险 | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| 迁移成本 | N/A | 🔴 高 | 🔴 高 |
| 测试覆盖 | ⭐ | ⭐⭐⭐ | ⭐⭐⭐ |

## 5. 结论与建议

### 5.1 不建议全面迁移至 LangChain

**理由**:
1. 当前自写方案已深度适配学术场景（消息修复、技能注册、中断机制），LangChain 无对应替代
2. 迁移成本 16-22 天，风险高，且无法覆盖所有边缘情况
3. LangChain 0.x 版本 API 不稳定，生产环境风险大
4. AcaSight 的核心差异化在学术技能（12 工具），而非 Agent 框架本身

### 5.2 推荐策略: 渐进式增强

| 优先级 | 动作 | 工时 | 收益 |
|--------|------|------|------|
| P0 | 为现有 Agent 添加单元测试 | 3天 | 可靠性↑↑ |
| P1 | 集成 LangSmith SDK 做可观测性 | 1天 | trace/span 可视化 |
| P2 | workflow_engine 引入 checkpoint | 2天 | 断点恢复 |
| P3 | 评估 LangGraph 仅用于新 DAG 场景 | - | 按需引入 |

### 5.3 LangSmith 集成方案（推荐 P1）

在不改变 Agent Core 架构的前提下，仅引入 `langsmith` SDK 做可观测性：

```python
# 集成方式: 在 core.py 的 run() 方法中添加 trace
from langsmith import traceable

class AgentCore:
    @traceable(name="acasight_agent_run", run_type="chain")
    async def run(self, task, context=None, conversation_history=None):
        # 现有逻辑不变
        ...
    
    # 工具执行也加 trace
    async def _execute_tool(self, name, args):
        with trace(name=f"tool_{name}", run_type="tool"):
            result = await self.skill_registry.execute(name, args)
            return result
```

**依赖**: 仅需 `pip install langsmith`，不影响核心架构。

### 5.4 最终评分

| 方案 | 推荐度 |
|------|--------|
| 保持自写 + 添加测试 + LangSmith | ⭐⭐⭐⭐⭐ (推荐) |
| 迁移至 LangChain | ⭐⭐ (不推荐) |
| 迁移至 LangGraph | ⭐⭐⭐ (未来可选) |
| 混合: 自写核心 + LangGraph DAG | ⭐⭐⭐⭐ (中期) |
