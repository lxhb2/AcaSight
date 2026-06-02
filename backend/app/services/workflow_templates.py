"""
预定义工作流模板
基于文档 5.2 节 — 论文撰写 / 文献综述 / 试验方案三大工作流
"""

from app.services.workflow_engine import (
    WorkflowDefinition, WorkflowStep,
    OperationMode, ParamSource, StepCondition,
)


# ─── 工作流 1：论文撰写完整流程 ───

PAPER_WRITING_WORKFLOW = WorkflowDefinition(
    workflow_id="paper_writing",
    name="学术论文撰写",
    description="从文献检索到论文导出的完整流程：搜索→选定→阅读→方向→提纲→写作→导出",
    tags=["写作", "论文", "全流程"],
    initial_params_schema={
        "topic": {"type": "string", "required": True, "description": "论文主题"},
        "style": {"type": "string", "default": "academic", "description": "写作风格"},
    },
    steps=[
        WorkflowStep(
            step_id="search_papers",
            module="literature",
            operation="search",
            description="搜索相关文献",
            mode=OperationMode.ASSIST,
            params_source=ParamSource.USER_INPUT,
            next_steps=["read_papers"],
            timeout=30,
        ),
        WorkflowStep(
            step_id="read_papers",
            module="literature",
            operation="decompose",
            description="AI 深度阅读论文（拆分为11字段）",
            mode=OperationMode.FULL_CONTROL,
            params_source=ParamSource.PREVIOUS_STEP,
            next_steps=["generate_direction"],
            timeout=120,
        ),
        WorkflowStep(
            step_id="generate_direction",
            module="writing",
            operation="generate_outline",
            description="生成研究方向与论文提纲",
            mode=OperationMode.ASSIST,
            params_source=ParamSource.PREVIOUS_STEP,
            next_steps=["write_chapters"],
            timeout=60,
        ),
        WorkflowStep(
            step_id="write_chapters",
            module="writing",
            operation="generate_section",
            description="逐章节撰写论文",
            mode=OperationMode.ASSIST,
            params_source=ParamSource.PREVIOUS_STEP,
            next_steps=["polish_and_export"],
            timeout=180,
        ),
        WorkflowStep(
            step_id="polish_and_export",
            module="writing",
            operation="polish",
            description="润色并导出 Word 文档",
            mode=OperationMode.FULL_CONTROL,
            params_source=ParamSource.PREVIOUS_STEP,
            timeout=60,
        ),
    ],
)


# ─── 工作流 2：文献综述生成 ───

LITERATURE_REVIEW_WORKFLOW = WorkflowDefinition(
    workflow_id="literature_review",
    name="文献综述生成",
    description="快速生成某主题的文献综述：搜索→分析→综述撰写",
    tags=["文献综述", "快速"],
    steps=[
        WorkflowStep(
            step_id="search",
            module="literature",
            operation="search",
            description="搜索相关文献",
            mode=OperationMode.FULL_CONTROL,
            params_source=ParamSource.USER_INPUT,
            next_steps=["analyze"],
            timeout=30,
        ),
        WorkflowStep(
            step_id="analyze",
            module="literature",
            operation="decompose",
            description="文献深度分析",
            mode=OperationMode.FULL_CONTROL,
            params_source=ParamSource.PREVIOUS_STEP,
            next_steps=["summarize"],
            timeout=90,
        ),
        WorkflowStep(
            step_id="summarize",
            module="writing",
            operation="generate_section",
            description="生成文献综述",
            mode=OperationMode.FULL_CONTROL,
            params_source=ParamSource.PREVIOUS_STEP,
            static_params={"section": "文献综述"},
            timeout=120,
        ),
    ],
)


# ─── 工作流 3：研究方向/试验方案生成 ───

EXPERIMENT_PLAN_WORKFLOW = WorkflowDefinition(
    workflow_id="experiment_plan",
    name="研究方向/试验方案生成",
    description="基于论文分析生成研究方向、创新点和试验方案",
    tags=["研究方向", "创新点", "试验方案"],
    steps=[
        WorkflowStep(
            step_id="analyze_papers",
            module="literature",
            operation="search",
            description="搜索并分析前沿论文",
            mode=OperationMode.FULL_CONTROL,
            params_source=ParamSource.USER_INPUT,
            next_steps=["extract_innovation"],
            timeout=60,
        ),
        WorkflowStep(
            step_id="extract_innovation",
            module="literature",
            operation="dimension_query",
            description="提取创新点和研究空白",
            mode=OperationMode.FULL_CONTROL,
            params_source=ParamSource.PREVIOUS_STEP,
            static_params={"dimension": "innovation"},
            next_steps=["generate_plan"],
            timeout=60,
        ),
        WorkflowStep(
            step_id="generate_plan",
            module="writing",
            operation="generate_outline",
            description="生成试验方案和建议",
            mode=OperationMode.ASSIST,
            params_source=ParamSource.PREVIOUS_STEP,
            timeout=120,
        ),
    ],
)


# ─── 工作流 4：快速润色导出 ───

QUICK_POLISH_WORKFLOW = WorkflowDefinition(
    workflow_id="quick_polish",
    name="快速润色 + Word 导出",
    description="润色已有文本并导出为 Word 文档",
    tags=["润色", "导出", "快速"],
    steps=[
        WorkflowStep(
            step_id="polish",
            module="writing",
            operation="polish",
            description="学术润色",
            mode=OperationMode.FULL_CONTROL,
            params_source=ParamSource.USER_INPUT,
            timeout=60,
        ),
    ],
)


# ─── 工作流 5：论文问答 + 图表生成 ───

PAPER_QA_CHART_WORKFLOW = WorkflowDefinition(
    workflow_id="paper_qa_chart",
    name="论文问答 + 图表生成",
    description="对论文进行问答，并按需生成图表",
    tags=["问答", "图表"],
    steps=[
        WorkflowStep(
            step_id="qa",
            module="agent",
            operation="summarize",
            description="分析论文",
            mode=OperationMode.FULL_CONTROL,
            params_source=ParamSource.USER_INPUT,
            next_steps=["generate_chart"],
            timeout=60,
        ),
        WorkflowStep(
            step_id="generate_chart",
            module="charts",
            operation="auto_generate",
            description="生成图表",
            mode=OperationMode.ASSIST,
            params_source=ParamSource.PREVIOUS_STEP,
            timeout=60,
        ),
    ],
)


# ─── 注册到引擎 ───

ALL_WORKFLOWS = [
    PAPER_WRITING_WORKFLOW,
    LITERATURE_REVIEW_WORKFLOW,
    EXPERIMENT_PLAN_WORKFLOW,
    QUICK_POLISH_WORKFLOW,
    PAPER_QA_CHART_WORKFLOW,
]


def register_all_workflows() -> list[str]:
    """将所有预定义工作流注册到引擎"""
    from app.services.workflow_engine import get_workflow_engine
    engine = get_workflow_engine()
    for wf in ALL_WORKFLOWS:
        engine.define(wf)
    return [wf.workflow_id for wf in ALL_WORKFLOWS]