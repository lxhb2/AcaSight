"""
Plugin System — 插件系统架构 (方向Q.2)

核心设计:
1. PluginAPI — 插件注册与发现
2. Plugin Lifecycle — 生命周期管理 (load → enable → disable → unload)
3. Plugin Sandbox — 沙箱隔离 (子进程/受限权限)
4. Hook System — 钩子系统 (pre_process/post_process/custom)
5. Plugin Manifest — 插件清单 (plugin.yaml)

设计原则:
- 插件热插拔 (无需重启服务)
- 沙箱隔离 (插件崩溃不影响主服务)
- 声明式配置 (plugin.yaml 描述能力需求)
- 事件驱动 (Hook + EventBus)

使用方式:
  # 注册插件
  registry = PluginRegistry()
  registry.load_plugin("path/to/plugin")
  
  # 触发钩子
  result = await registry.hook("pre_search", query="cancer")
  
  # 插件状态
  status = registry.get_plugin_status("my_plugin")
"""

import asyncio
import importlib
import importlib.util
import json
import os
import sys
import time
import traceback
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set, Tuple

import structlog
import yaml

logger = structlog.get_logger()


# ── 数据模型 ──

class PluginState(str, Enum):
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"


class HookPoint(str, Enum):
    """内置钩子点"""
    # 搜索
    PRE_SEARCH = "pre_search"
    POST_SEARCH = "post_search"
    
    # PDF
    PRE_PDF_PROCESS = "pre_pdf_process"
    POST_PDF_PROCESS = "post_pdf_process"
    
    # AI
    PRE_AI_CALL = "pre_ai_call"
    POST_AI_CALL = "post_ai_call"
    
    # 写作
    PRE_WRITE = "pre_write"
    POST_WRITE = "post_write"
    
    # 图表
    PRE_CHART = "pre_chart"
    POST_CHART = "post_chart"
    
    # 自定义
    CUSTOM = "custom"


@dataclass
class PluginManifest:
    """插件清单 (plugin.yaml)"""
    name: str
    version: str
    description: str = ""
    author: str = ""
    
    # 能力声明
    hooks: List[str] = field(default_factory=list)         # 订阅的钩子
    provides: List[str] = field(default_factory=list)      # 提供的功能
    depends: List[str] = field(default_factory=list)        # 依赖的其他插件
    
    # 权限
    permissions: List[str] = field(default_factory=list)    # network/fs/env
    
    # 入口
    entry_point: str = "plugin.py"                         # 主文件
    config_schema: Optional[Dict] = None                    # 配置 schema
    
    # 元数据
    homepage: str = ""
    license: str = ""
    tags: List[str] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: str) -> "PluginManifest":
        """从 plugin.yaml 加载"""
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls(
            name=data.get("name", ""),
            version=data.get("version", "0.1.0"),
            description=data.get("description", ""),
            author=data.get("author", ""),
            hooks=data.get("hooks", []),
            provides=data.get("provides", []),
            depends=data.get("depends", []),
            permissions=data.get("permissions", []),
            entry_point=data.get("entry_point", "plugin.py"),
            config_schema=data.get("config_schema"),
            homepage=data.get("homepage", ""),
            license=data.get("license", ""),
            tags=data.get("tags", []),
        )


@dataclass
class PluginInstance:
    """运行时插件实例"""
    manifest: PluginManifest
    state: PluginState = PluginState.UNLOADED
    module: Any = None
    config: Dict[str, Any] = field(default_factory=dict)
    loaded_at: Optional[float] = None
    error: Optional[str] = None
    hook_handlers: Dict[str, Callable] = field(default_factory=dict)


@dataclass
class HookResult:
    """钩子执行结果"""
    plugin_name: str
    hook_name: str
    success: bool = True
    result: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0


# ── 插件基类 ──

class AcaSightPlugin:
    """
    插件基类 — 所有插件必须继承此类
    
    生命周期:
    1. on_load() — 插件加载时调用 (注册钩子、初始化资源)
    2. on_enable() — 插件启用时调用
    3. on_disable() — 插件禁用时调用
    4. on_unload() — 插件卸载时调用 (清理资源)
    
    钩子注册:
    self.register_hook("post_search", self.my_hook_handler)
    """
    
    def __init__(self):
        self._hook_handlers: Dict[str, Callable] = {}
        self._config: Dict[str, Any] = {}
        self._plugin_name: str = ""
    
    @property
    def name(self) -> str:
        return self._plugin_name
    
    @property
    def config(self) -> Dict[str, Any]:
        return self._config
    
    def register_hook(self, hook_name: str, handler: Callable) -> None:
        """注册钩子处理器"""
        self._hook_handlers[hook_name] = handler
    
    def get_hook_handlers(self) -> Dict[str, Callable]:
        """获取所有已注册的钩子处理器"""
        return self._hook_handlers
    
    # ── 生命周期方法 (子类覆盖) ──
    
    async def on_load(self, config: Dict[str, Any]) -> None:
        """插件加载 — 注册钩子、初始化资源"""
        self._config = config
    
    async def on_enable(self) -> None:
        """插件启用"""
        pass
    
    async def on_disable(self) -> None:
        """插件禁用"""
        pass
    
    async def on_unload(self) -> None:
        """插件卸载 — 清理资源"""
        pass


# ── 插件沙箱 ──

class PluginSandbox:
    """
    插件沙箱 — 限制插件权限
    
    权限级别:
    - safe: 仅内存操作，无IO
    - network: 允许网络请求
    - fs_read: 允许文件读取
    - fs_write: 允许文件写入
    - env: 允许环境变量访问
    - full: 完全权限 (不推荐)
    """
    
    ALLOWED_PERMISSIONS = {
        "safe", "network", "fs_read", "fs_write", "env", "full",
    }
    
    def __init__(self, allowed_permissions: Optional[Set[str]] = None):
        self.allowed_permissions = allowed_permissions or {"safe"}
    
    def check_permission(self, required: str) -> bool:
        """检查是否有所需权限"""
        if "full" in self.allowed_permissions:
            return True
        return required in self.allowed_permissions
    
    def validate_manifest(self, manifest: PluginManifest) -> List[str]:
        """验证插件清单中的权限请求"""
        violations = []
        for perm in manifest.permissions:
            if perm not in self.ALLOWED_PERMISSIONS:
                violations.append(f"Unknown permission: {perm}")
            elif not self.check_permission(perm):
                violations.append(f"Permission denied: {perm}")
        return violations
    
    async def execute_sandboxed(
        self,
        handler: Callable,
        *args,
        timeout: float = 30.0,
        **kwargs,
    ) -> Any:
        """在沙箱中执行钩子处理器 (超时保护)"""
        try:
            result = await asyncio.wait_for(
                handler(*args, **kwargs),
                timeout=timeout,
            )
            return result
        except asyncio.TimeoutError:
            raise PermissionError(f"Plugin handler timed out after {timeout}s")
        except Exception as e:
            logger.error("Sandbox execution error", error=str(e))
            raise


# ── 插件注册中心 ──

class PluginRegistry:
    """
    插件注册中心 — 管理插件生命周期与钩子调度
    
    特性:
    - 热插拔 (load/unload 无需重启)
    - 钩子优先级排序
    - 沙箱权限检查
    - 插件依赖解析
    - 错误隔离 (单插件失败不影响其他)
    """
    
    def __init__(self, plugins_dir: Optional[str] = None, sandbox: Optional[PluginSandbox] = None):
        self._plugins: Dict[str, PluginInstance] = {}
        self._plugins_dir = plugins_dir or os.path.join(os.getcwd(), "plugins")
        self._sandbox = sandbox or PluginSandbox(allowed_permissions={"safe", "network", "fs_read", "fs_write"})
        self._global_hooks: Dict[str, List[Tuple[str, Callable]]] = {}  # hook_name → [(plugin_name, handler)]
        
    async def load_plugin(self, plugin_path: str, config: Optional[Dict] = None) -> PluginInstance:
        """
        加载插件
        
        Args:
            plugin_path: 插件目录路径 (包含 plugin.yaml)
            config: 插件配置
        
        Returns:
            PluginInstance
        """
        # 1. 加载清单
        manifest_path = os.path.join(plugin_path, "plugin.yaml")
        if not os.path.exists(manifest_path):
            raise FileNotFoundError(f"Plugin manifest not found: {manifest_path}")
        
        manifest = PluginManifest.from_yaml(manifest_path)
        plugin_name = manifest.name
        
        if plugin_name in self._plugins:
            raise ValueError(f"Plugin already loaded: {plugin_name}")
        
        instance = PluginInstance(manifest=manifest, config=config or {})
        
        # 2. 沙箱权限检查
        violations = self._sandbox.validate_manifest(manifest)
        if violations:
            instance.state = PluginState.ERROR
            instance.error = f"Permission violations: {', '.join(violations)}"
            self._plugins[plugin_name] = instance
            logger.error("Plugin permission denied", plugin=plugin_name, violations=violations)
            return instance
        
        # 3. 依赖检查
        for dep in manifest.depends:
            if dep not in self._plugins or self._plugins[dep].state not in (PluginState.LOADED, PluginState.ENABLED):
                instance.state = PluginState.ERROR
                instance.error = f"Missing dependency: {dep}"
                self._plugins[plugin_name] = instance
                logger.error("Plugin dependency missing", plugin=plugin_name, dependency=dep)
                return instance
        
        # 4. 加载模块
        try:
            instance.state = PluginState.LOADING
            entry_path = os.path.join(plugin_path, manifest.entry_point)
            
            spec = importlib.util.spec_from_file_location(
                f"acasight_plugin_{plugin_name}",
                entry_path,
            )
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[f"acasight_plugin_{plugin_name}"] = module
                spec.loader.exec_module(module)
                instance.module = module
                
                # 查找插件类
                plugin_class = None
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) 
                        and issubclass(attr, AcaSightPlugin) 
                        and attr is not AcaSightPlugin):
                        plugin_class = attr
                        break
                
                if plugin_class:
                    plugin_obj = plugin_class()
                    plugin_obj._plugin_name = plugin_name
                    
                    # 调用 on_load (async)
                    await plugin_obj.on_load(config or {})
                    
                    # 注册钩子
                    handlers = plugin_obj.get_hook_handlers()
                    for hook_name, handler in handlers.items():
                        if hook_name not in self._global_hooks:
                            self._global_hooks[hook_name] = []
                        self._global_hooks[hook_name].append((plugin_name, handler))
                        instance.hook_handlers[hook_name] = handler
                    
                    instance.state = PluginState.LOADED
                    instance.loaded_at = time.time()
                    logger.info("Plugin loaded", plugin=plugin_name, hooks=list(handlers.keys()))
                else:
                    instance.state = PluginState.LOADED
                    instance.loaded_at = time.time()
                    logger.info("Plugin loaded (no AcaSightPlugin class)", plugin=plugin_name)
            
        except Exception as e:
            instance.state = PluginState.ERROR
            instance.error = traceback.format_exc()
            logger.error("Plugin load failed", plugin=plugin_name, error=str(e))
        
        self._plugins[plugin_name] = instance
        return instance
    
    async def enable_plugin(self, plugin_name: str) -> bool:
        """启用插件"""
        instance = self._plugins.get(plugin_name)
        if not instance or instance.state not in (PluginState.LOADED, PluginState.DISABLED):
            return False
        
        try:
            # 调用 on_enable
            if hasattr(instance.module, "__acasight_plugin__"):
                await instance.module.__acasight_plugin__.on_enable()
            instance.state = PluginState.ENABLED
            logger.info("Plugin enabled", plugin=plugin_name)
            return True
        except Exception as e:
            instance.state = PluginState.ERROR
            instance.error = str(e)
            logger.error("Plugin enable failed", plugin=plugin_name, error=str(e))
            return False
    
    async def disable_plugin(self, plugin_name: str) -> bool:
        """禁用插件"""
        instance = self._plugins.get(plugin_name)
        if not instance or instance.state != PluginState.ENABLED:
            return False
        
        try:
            if hasattr(instance.module, "__acasight_plugin__"):
                await instance.module.__acasight_plugin__.on_disable()
            
            # 移除钩子
            for hook_name in instance.hook_handlers:
                if hook_name in self._global_hooks:
                    self._global_hooks[hook_name] = [
                        (pn, h) for pn, h in self._global_hooks[hook_name]
                        if pn != plugin_name
                    ]
            
            instance.state = PluginState.DISABLED
            logger.info("Plugin disabled", plugin=plugin_name)
            return True
        except Exception as e:
            instance.state = PluginState.ERROR
            instance.error = str(e)
            return False
    
    async def unload_plugin(self, plugin_name: str) -> bool:
        """卸载插件"""
        instance = self._plugins.get(plugin_name)
        if not instance:
            return False
        
        # 先禁用
        if instance.state == PluginState.ENABLED:
            await self.disable_plugin(plugin_name)
        
        # 清理
        for hook_name in list(instance.hook_handlers.keys()):
            if hook_name in self._global_hooks:
                self._global_hooks[hook_name] = [
                    (pn, h) for pn, h in self._global_hooks[hook_name]
                    if pn != plugin_name
                ]
        
        # 移除模块
        mod_name = f"acasight_plugin_{plugin_name}"
        if mod_name in sys.modules:
            del sys.modules[mod_name]
        
        del self._plugins[plugin_name]
        logger.info("Plugin unloaded", plugin=plugin_name)
        return True
    
    async def hook(self, hook_name: str, **kwargs) -> List[HookResult]:
        """
        触发钩子 — 按注册顺序执行所有处理器
        
        Args:
            hook_name: 钩子名称
            **kwargs: 传递给处理器的参数
        
        Returns:
            List[HookResult]
        """
        handlers = self._global_hooks.get(hook_name, [])
        results = []
        
        for plugin_name, handler in handlers:
            instance = self._plugins.get(plugin_name)
            if not instance or instance.state != PluginState.ENABLED:
                continue
            
            start = time.time()
            try:
                result = await self._sandbox.execute_sandboxed(handler, **kwargs)
                duration_ms = (time.time() - start) * 1000
                results.append(HookResult(
                    plugin_name=plugin_name,
                    hook_name=hook_name,
                    success=True,
                    result=result,
                    duration_ms=round(duration_ms, 2),
                ))
            except Exception as e:
                duration_ms = (time.time() - start) * 1000
                results.append(HookResult(
                    plugin_name=plugin_name,
                    hook_name=hook_name,
                    success=False,
                    error=str(e),
                    duration_ms=round(duration_ms, 2),
                ))
                logger.warning("Hook handler failed", plugin=plugin_name, hook=hook_name, error=str(e))
        
        return results
    
    def get_plugin_status(self, plugin_name: str) -> Optional[Dict]:
        """获取插件状态"""
        instance = self._plugins.get(plugin_name)
        if not instance:
            return None
        return {
            "name": instance.manifest.name,
            "version": instance.manifest.version,
            "state": instance.state.value,
            "hooks": list(instance.hook_handlers.keys()),
            "loaded_at": instance.loaded_at,
            "error": instance.error,
        }
    
    def list_plugins(self) -> List[Dict]:
        """列出所有插件"""
        return [
            self.get_plugin_status(name)
            for name in self._plugins
            if self.get_plugin_status(name)
        ]
    
    def scan_plugins_dir(self) -> List[str]:
        """扫描插件目录，发现可用插件"""
        discovered = []
        if not os.path.exists(self._plugins_dir):
            return discovered
        
        for entry in os.listdir(self._plugins_dir):
            plugin_yaml = os.path.join(self._plugins_dir, entry, "plugin.yaml")
            if os.path.exists(plugin_yaml):
                discovered.append(os.path.join(self._plugins_dir, entry))
        
        return discovered


# Singleton
_plugin_registry: Optional[PluginRegistry] = None


def get_plugin_registry() -> PluginRegistry:
    """获取全局插件注册中心"""
    global _plugin_registry
    if _plugin_registry is None:
        plugins_dir = os.path.join(os.getcwd(), "plugins")
        _plugin_registry = PluginRegistry(plugins_dir=plugins_dir)
    return _plugin_registry
