"""
Stage Orchestrator — Stage 编排优化 (方向P.2)

设计参考: agentic-data-scientist Stage编排
核心功能:
- 并行 Stage 执行 (独立步骤并发)
- 可配置重试策略 (指数退避/固定间隔)
- Stage 回滚 (失败时回退)
- Stage 依赖图 (DAG) 自动拓扑排序
- 执行快照 (断点恢复)

与现有 WorkflowEngine 的关系:
- WorkflowEngine 处理线性/条件工作流
- StageOrchestrator 处理 DAG 并行编排
- 两者互补，可嵌套使用
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set, Tuple

import structlog

logger = structlog.get_logger()


# ── 数据模型 ──

class StageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    ROLLED_BACK = "rolled_back"


class RetryStrategy(str, Enum):
    NONE = "none"           # 不重试
    FIXED = "fixed"         # 固定间隔重试
    EXPONENTIAL = "exponential"  # 指数退避


@dataclass
class RetryPolicy:
    """重试策略"""
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    max_retries: int = 3
    base_delay: float = 1.0    # 秒
    max_delay: float = 60.0    # 秒
    retryable_exceptions: List[str] = field(default_factory=lambda: ["TimeoutError", "ConnectionError"])


@dataclass
class StageDefinition:
    """Stage 定义"""
    stage_id: str
    name: str
    handler: Optional[Callable[..., Coroutine]] = None  # async fn(params) -> result
    dependencies: List[str] = field(default_factory=list)  # 依赖的 stage_id 列表
    timeout: float = 300.0       # 秒
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    rollback_handler: Optional[Callable[..., Coroutine]] = None  # async fn(result) -> None
    critical: bool = True        # 关键步骤：失败则中止整个pipeline
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StageResult:
    """Stage 执行结果"""
    stage_id: str
    status: StageStatus = StageStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    attempts: int = 0
    duration_seconds: float = 0.0
    started_at: Optional[float] = None
    finished_at: Optional[float] = None


@dataclass
class PipelineResult:
    """Pipeline 执行结果"""
    pipeline_id: str
    success: bool = False
    stages: Dict[str, StageResult] = field(default_factory=dict)
    duration_seconds: float = 0.0
    snapshot: Optional[Dict[str, Any]] = None


# ── Stage Orchestrator ──

class StageOrchestrator:
    """Stage 编排器 — DAG 并行执行 + 重试 + 回滚"""

    def __init__(self, pipeline_id: str, max_concurrent: int = 4):
        self.pipeline_id = pipeline_id
        self.max_concurrent = max_concurrent
        self._stages: Dict[str, StageDefinition] = {}
        self._results: Dict[str, StageResult] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)

    def add_stage(self, stage: StageDefinition) -> "StageOrchestrator":
        """添加 Stage"""
        self._stages[stage.stage_id] = stage
        self._results[stage.stage_id] = StageResult(stage_id=stage.stage_id)
        return self

    def add_stages(self, stages: List[StageDefinition]) -> "StageOrchestrator":
        """批量添加 Stage"""
        for stage in stages:
            self.add_stage(stage)
        return self

    async def execute(self, initial_params: Optional[Dict[str, Any]] = None) -> PipelineResult:
        """
        执行 Pipeline — DAG 拓扑排序 + 并行执行

        1. 构建依赖图
        2. 拓扑排序
        3. 按层并行执行 (同层无依赖的 Stage 并发)
        4. 失败处理: 关键Stage失败→中止+回滚; 非关键→跳过
        """
        start_time = time.time()
        params = initial_params or {}

        # 验证依赖图
        cycle = self._detect_cycle()
        if cycle:
            logger.error("Pipeline has cycle", cycle=cycle)
            return PipelineResult(
                pipeline_id=self.pipeline_id,
                success=False,
                duration_seconds=time.time() - start_time,
            )

        # 拓扑排序 → 按层
        layers = self._topological_layers()
        logger.info("Pipeline execution started", pipeline=self.pipeline_id, layers=len(layers))

        for layer_idx, layer in enumerate(layers):
            logger.info(f"Executing layer {layer_idx + 1}/{len(layers)}", stages=[s.stage_id for s in layer])

            # 同层并行执行
            tasks = []
            for stage in layer:
                # 检查依赖是否都成功
                deps_ok = all(
                    self._results.get(dep, StageResult(stage_id=dep)).status == StageStatus.SUCCESS
                    for dep in stage.dependencies
                )

                if not deps_ok:
                    # 依赖失败 → 跳过
                    self._results[stage.stage_id].status = StageStatus.SKIPPED
                    self._results[stage.stage_id].error = "Dependency failed"
                    logger.info(f"Stage skipped (dependency failed)", stage=stage.stage_id)
                    continue

                tasks.append(self._execute_stage(stage, params))

            if tasks:
                await asyncio.gather(*tasks)

            # 检查是否有关键 Stage 失败
            critical_failed = [
                s for s in layer
                if s.critical and self._results[s.stage_id].status == StageStatus.FAILED
            ]
            if critical_failed:
                logger.error("Critical stage failed, aborting pipeline", failed=[s.stage_id for s in critical_failed])
                # 回滚已成功的 Stage
                await self._rollback_completed()
                break

        # 构建快照
        snapshot = self._create_snapshot()

        all_success = all(
            r.status in (StageStatus.SUCCESS, StageStatus.SKIPPED)
            for r in self._results.values()
        )

        return PipelineResult(
            pipeline_id=self.pipeline_id,
            success=all_success,
            stages=dict(self._results),
            duration_seconds=round(time.time() - start_time, 2),
            snapshot=snapshot,
        )

    async def _execute_stage(self, stage: StageDefinition, params: Dict[str, Any]) -> StageResult:
        """执行单个 Stage (含重试)"""
        result = self._results[stage.stage_id]
        result.status = StageStatus.RUNNING
        result.started_at = time.time()

        async with self._semaphore:
            # 合并参数: 全局参数 + 依赖输出 + Stage 专属参数
            resolved_params = {**params, **stage.params}

            # 注入依赖输出
            for dep_id in stage.dependencies:
                dep_result = self._results.get(dep_id)
                if dep_result and dep_result.result:
                    resolved_params[f"{dep_id}_output"] = dep_result.result

            policy = stage.retry_policy
            last_error = None

            for attempt in range(policy.max_retries + 1):
                result.attempts = attempt + 1
                try:
                    if stage.handler:
                        task_result = await asyncio.wait_for(
                            stage.handler(resolved_params),
                            timeout=stage.timeout,
                        )
                    else:
                        task_result = {"status": "no_handler", "stage_id": stage.stage_id}

                    result.status = StageStatus.SUCCESS
                    result.result = task_result
                    result.finished_at = time.time()
                    result.duration_seconds = round(result.finished_at - result.started_at, 2)

                    logger.info("Stage completed", stage=stage.stage_id, attempt=attempt + 1, duration=result.duration_seconds)
                    return result

                except asyncio.TimeoutError:
                    last_error = f"Timeout after {stage.timeout}s"
                    logger.warning("Stage timeout", stage=stage.stage_id, attempt=attempt + 1)

                except Exception as e:
                    last_error = str(e)
                    logger.warning("Stage failed", stage=stage.stage_id, attempt=attempt + 1, error=last_error)

                # 重试等待
                if attempt < policy.max_retries:
                    delay = self._calculate_delay(policy, attempt)
                    logger.info("Retrying stage", stage=stage.stage_id, delay=delay)
                    await asyncio.sleep(delay)

            # 所有重试耗尽
            result.status = StageStatus.FAILED
            result.error = last_error
            result.finished_at = time.time()
            result.duration_seconds = round(result.finished_at - result.started_at, 2)

            logger.error("Stage failed after all retries", stage=stage.stage_id, attempts=result.attempts)
            return result

    async def _rollback_completed(self) -> None:
        """回滚已成功的 Stage (逆序)"""
        completed = [
            (stage_id, r) for stage_id, r in self._results.items()
            if r.status == StageStatus.SUCCESS
        ]

        # 逆序回滚 (最后完成的先回滚)
        for stage_id, result in reversed(completed):
            stage = self._stages.get(stage_id)
            if stage and stage.rollback_handler:
                try:
                    await stage.rollback_handler(result.result)
                    self._results[stage_id].status = StageStatus.ROLLED_BACK
                    logger.info("Stage rolled back", stage=stage_id)
                except Exception as e:
                    logger.error("Rollback failed", stage=stage_id, error=str(e))

    def _detect_cycle(self) -> Optional[List[str]]:
        """检测依赖图中的环"""
        visited = set()
        rec_stack = set()
        path = []

        def dfs(stage_id: str) -> Optional[List[str]]:
            visited.add(stage_id)
            rec_stack.add(stage_id)
            path.append(stage_id)

            stage = self._stages.get(stage_id)
            if stage:
                for dep in stage.dependencies:
                    if dep not in visited:
                        cycle = dfs(dep)
                        if cycle:
                            return cycle
                    elif dep in rec_stack:
                        # 找到环
                        idx = path.index(dep)
                        return path[idx:] + [dep]

            path.pop()
            rec_stack.discard(stage_id)
            return None

        for stage_id in self._stages:
            if stage_id not in visited:
                cycle = dfs(stage_id)
                if cycle:
                    return cycle

        return None

    def _topological_layers(self) -> List[List[StageDefinition]]:
        """拓扑排序 → 按层 (同层可并行)"""
        # 计算入度
        in_degree = {sid: 0 for sid in self._stages}
        for stage in self._stages.values():
            for dep in stage.dependencies:
                if dep in in_degree:
                    # dep → stage (stage 依赖 dep)
                    pass
                # stage 的入度 = 依赖数
            in_degree[stage.stage_id] = len([d for d in stage.dependencies if d in self._stages])

        layers = []
        remaining = set(self._stages.keys())

        while remaining:
            # 当前层: 入度为0的节点
            current_layer = [
                sid for sid in remaining
                if in_degree[sid] == 0
            ]

            if not current_layer:
                # 所有剩余节点都有依赖 (不应发生, cycle 检测已保证)
                break

            layer_stages = [self._stages[sid] for sid in current_layer]
            layers.append(layer_stages)

            # 移除当前层, 更新入度
            for sid in current_layer:
                remaining.discard(sid)
                for other_sid in remaining:
                    other = self._stages[other_sid]
                    if sid in other.dependencies:
                        in_degree[other_sid] -= 1

        return layers

    @staticmethod
    def _calculate_delay(policy: RetryPolicy, attempt: int) -> float:
        """计算重试延迟"""
        if policy.strategy == RetryStrategy.FIXED:
            return policy.base_delay
        elif policy.strategy == RetryStrategy.EXPONENTIAL:
            delay = policy.base_delay * (2 ** attempt)
            return min(delay, policy.max_delay)
        return 0.0

    def _create_snapshot(self) -> Dict[str, Any]:
        """创建执行快照 (用于断点恢复)"""
        return {
            "pipeline_id": self.pipeline_id,
            "timestamp": time.time(),
            "stages": {
                sid: {
                    "status": r.status.value,
                    "result": r.result,
                    "attempts": r.attempts,
                }
                for sid, r in self._results.items()
            },
        }

    async def restore_from_snapshot(self, snapshot: Dict[str, Any]) -> "StageOrchestrator":
        """从快照恢复 (跳过已成功的 Stage)"""
        for sid, stage_data in snapshot.get("stages", {}).items():
            if stage_data["status"] == StageStatus.SUCCESS.value:
                self._results[sid] = StageResult(
                    stage_id=sid,
                    status=StageStatus.SUCCESS,
                    result=stage_data.get("result"),
                    attempts=stage_data.get("attempts", 0),
                )
                # 跳过已成功的 stage (移除 handler)
                if sid in self._stages:
                    self._stages[sid].handler = None
        return self


# ── 便捷构造器 ──

def create_pipeline(
    pipeline_id: str,
    stages: List[StageDefinition],
    max_concurrent: int = 4,
) -> StageOrchestrator:
    """快速创建 Pipeline"""
    orchestrator = StageOrchestrator(pipeline_id, max_concurrent)
    orchestrator.add_stages(stages)
    return orchestrator
