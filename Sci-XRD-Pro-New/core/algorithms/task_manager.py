"""
Sci-XRD-Pro - 异步任务管理器
==========================================
用于在后台线程执行耗时算法计算，保持GUI响应

功能：
  - 异步执行算法任务
  - 进度报告
  - 取消操作支持
  - 结果回调机制
"""

import threading
import queue
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Any, Optional, Dict, List
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
import traceback


class TaskState(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"


class ProgressCallback:
    """进度回调函数接口"""

    def on_progress(self, current: int, total: int, message: str = ""):
        """进度更新回调"""
        pass

    def on_complete(self, result: Any):
        """完成回调"""
        pass

    def on_error(self, error: Exception):
        """错误回调"""
        pass

    def on_cancelled(self):
        """取消回调"""
        pass


@dataclass
class TaskResult:
    """任务结果"""
    task_id: str
    state: TaskState
    result: Any = None
    error: Optional[str] = None
    progress: int = 0
    message: str = ""
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None

    @property
    def duration(self) -> float:
        """获取任务执行时长（秒）"""
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time


class AsyncTask:
    """异步任务封装"""

    def __init__(self, task_id: str, func: Callable, args: tuple = (), kwargs: dict = None):
        self.task_id = task_id
        self.func = func
        self.args = args
        self.kwargs = kwargs or {}
        self.state = TaskState.PENDING
        self.future: Optional[Future] = None
        self.progress_callback: Optional[ProgressCallback] = None
        self._cancel_event = threading.Event()

    def cancel(self):
        """取消任务"""
        self._cancel_event.set()
        self.state = TaskState.CANCELLED

    def is_cancelled(self) -> bool:
        """检查是否已取消"""
        return self._cancel_event.is_set()


class TaskManager:
    """任务管理器 - 单例模式"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="SciXRD_Worker")
        self._tasks: Dict[str, AsyncTask] = {}
        self._task_lock = threading.Lock()
        self._result_queue = queue.Queue()
        self._initialized = True

    def submit(
        self,
        task_id: str,
        func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        progress_callback: Optional[ProgressCallback] = None,
        description: str = ""
    ) -> AsyncTask:
        """
        提交异步任务

        Args:
            task_id: 任务唯一标识
            func: 要执行的函数
            args: 函数位置参数
            kwargs: 函数关键字参数
            progress_callback: 进度回调
            description: 任务描述

        Returns:
            AsyncTask: 异步任务对象
        """
        kwargs = kwargs or {}

        async_task = AsyncTask(task_id, func, args, kwargs)
        async_task.progress_callback = progress_callback
        async_task.description = description

        with self._task_lock:
            self._tasks[task_id] = async_task

        def run_task():
            async_task.state = TaskState.RUNNING
            try:
                if progress_callback:
                    progress_callback.on_progress(0, 100, "开始执行...")

                kwargs_with_callback = dict(async_task.kwargs)
                if progress_callback:
                    def progress_handler(current, total, message=""):
                        if not async_task.is_cancelled():
                            progress_callback.on_progress(current, total, message)

                    kwargs_with_callback['_progress_callback'] = progress_handler

                result = async_task.func(*async_task.args, **kwargs_with_callback)

                if async_task.is_cancelled():
                    async_task.state = TaskState.CANCELLED
                    if progress_callback:
                        progress_callback.on_cancelled()
                else:
                    async_task.state = TaskState.COMPLETED
                    async_task.result = result
                    if progress_callback:
                        progress_callback.on_complete(result)

            except Exception as e:
                async_task.state = TaskState.FAILED
                async_task.error = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
                if progress_callback:
                    progress_callback.on_error(e)

        async_task.future = self._executor.submit(run_task)

        return async_task

    def get_task(self, task_id: str) -> Optional[AsyncTask]:
        """获取任务对象"""
        with self._task_lock:
            return self._tasks.get(task_id)

    def get_task_state(self, task_id: str) -> Optional[TaskState]:
        """获取任务状态"""
        task = self.get_task(task_id)
        return task.state if task else None

    def get_task_result(self, task_id: str) -> Optional[Any]:
        """获取任务结果"""
        task = self.get_task(task_id)
        return task.result if task else None

    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        task = self.get_task(task_id)
        if task and task.state in (TaskState.PENDING, TaskState.RUNNING):
            task.cancel()
            return True
        return False

    def cancel_all(self):
        """取消所有任务"""
        with self._task_lock:
            for task in self._tasks.values():
                if task.state in (TaskState.PENDING, TaskState.RUNNING):
                    task.cancel()

    def is_running(self, task_id: str) -> bool:
        """检查任务是否正在运行"""
        task = self.get_task(task_id)
        return task.state == TaskState.RUNNING if task else False

    def wait_for_completion(self, task_ids: List[str], timeout: float = None) -> Dict[str, TaskResult]:
        """
        等待任务完成

        Args:
            task_ids: 要等待的任务ID列表
            timeout: 超时时间（秒）

        Returns:
            Dict[str, TaskResult]: 任务结果字典
        """
        results = {}
        start_time = time.time()

        for task_id in task_ids:
            task = self.get_task(task_id)
            if not task:
                continue

            remaining_timeout = None
            if timeout:
                elapsed = time.time() - start_time
                remaining_timeout = max(0.1, timeout - elapsed)
                if elapsed >= timeout:
                    break

            if task.future:
                try:
                    task.future.result(timeout=remaining_timeout)
                except TimeoutError:
                    pass

            results[task_id] = TaskResult(
                task_id=task_id,
                state=task.state,
                result=task.result,
                error=getattr(task, 'error', None)
            )

        return results

    def clear_completed(self):
        """清理已完成的任务"""
        with self._task_lock:
            completed_ids = [
                tid for tid, task in self._tasks.items()
                if task.state in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED)
            ]
            for tid in completed_ids:
                del self._tasks[tid]

    def get_all_tasks(self) -> Dict[str, TaskState]:
        """获取所有任务状态"""
        with self._task_lock:
            return {tid: task.state for tid, task in self._tasks.items()}

    def shutdown(self, wait: bool = True):
        """关闭任务管理器"""
        self.cancel_all()
        if wait:
            self._executor.shutdown(wait=True)
        else:
            self._executor.shutdown(wait=False)


class ProgressTracker:
    """进度追踪器 - 用于算法内部报告进度"""

    def __init__(self, total: int, callback: Optional[Callable] = None):
        self.total = total
        self.current = 0
        self.callback = callback
        self.last_reported_percent = -1
        self.min_update_interval = 0.1
        self.last_update_time = 0

    def update(self, increment: int = 1, message: str = ""):
        """更新进度"""
        self.current = min(self.current + increment, self.total)

        current_time = time.time()
        if current_time - self.last_update_time < self.min_update_interval:
            return

        self.last_update_time = current_time

        percent = int(100 * self.current / self.total) if self.total > 0 else 0

        if percent != self.last_reported_percent and self.callback:
            self.callback(percent, 100, message)
            self.last_reported_percent = percent

    def set_progress(self, current: int, message: str = ""):
        """设置进度值"""
        self.current = min(current, self.total)
        percent = int(100 * self.current / self.total) if self.total > 0 else 0

        if self.callback:
            self.callback(percent, 100, message)


_task_manager: Optional[TaskManager] = None


def get_task_manager() -> TaskManager:
    """获取任务管理器单例"""
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager


def submit_task(
    task_id: str,
    func: Callable,
    args: tuple = (),
    kwargs: dict = None,
    progress_callback: Optional[ProgressCallback] = None
) -> AsyncTask:
    """提交任务的快捷函数"""
    return get_task_manager().submit(task_id, func, args, kwargs, progress_callback)


def cancel_task(task_id: str) -> bool:
    """取消任务的快捷函数"""
    return get_task_manager().cancel_task(task_id)


def create_progress_callback(
    on_progress: Optional[Callable] = None,
    on_complete: Optional[Callable] = None,
    on_error: Optional[Callable] = None
) -> ProgressCallback:
    """创建简单的进度回调对象"""

    class SimpleProgressCallback(ProgressCallback):
        def on_progress(self, current: int, total: int, message: str = ""):
            if on_progress:
                on_progress(current, total, message)

        def on_complete(self, result: Any):
            if on_complete:
                on_complete(result)

        def on_error(self, error: Exception):
            if on_error:
                on_error(error)

        def on_cancelled(self):
            pass

    return SimpleProgressCallback()
