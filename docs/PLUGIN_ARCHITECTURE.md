# AcaSight 插件系统架构设计文档

> 版本: 1.0 | 方向Q.2 | 2026-05-31

## 1. 设计目标

| 目标 | 说明 |
|------|------|
| **热插拔** | 插件加载/卸载无需重启服务 |
| **沙箱隔离** | 插件崩溃不影响主服务，权限声明式 |
| **声明式配置** | plugin.yaml 描述能力、依赖、权限 |
| **事件驱动** | Hook + EventBus 模式 |
| **零侵入** | 主代码无需修改即可扩展功能 |

## 2. 核心架构

```
┌──────────────────────────────────────────────┐
│                Plugin Registry                │
│  (生命周期管理 + 钩子调度 + 依赖解析)          │
├──────────────────────────────────────────────┤
│  ┌─────────┐  ┌─────────┐  ┌─────────┐      │
│  │ Plugin A│  │ Plugin B│  │ Plugin C│      │
│  │(enabled)│  │(enabled)│  │(loaded) │      │
│  └────┬────┘  └────┬────┘  └─────────┘      │
│       │            │                          │
│  ┌────▼────────────▼────┐                    │
│  │   Hook Dispatcher    │                    │
│  │  (pre_search ──────→ │──→ [A.handler, B.handler] │
│  │   post_search ─────→ │──→ [B.handler]    │
│  └──────────────────────┘                    │
├──────────────────────────────────────────────┤
│              Plugin Sandbox                   │
│  (权限检查 + 超时保护 + 错误隔离)              │
└──────────────────────────────────────────────┘
```

## 3. 生命周期

```
UNLOADED → LOADING → LOADED → ENABLED → DISABLED → UNLOADED
                       ↓          ↑
                     ERROR ←──────┘
```

| 状态 | 说明 |
|------|------|
| UNLOADED | 未加载 |
| LOADING | 正在加载模块 |
| LOADED | 模块加载完成，钩子已注册 |
| ENABLED | 已启用，钩子可被调度 |
| DISABLED | 已禁用，钩子不会被调用 |
| ERROR | 加载/执行失败 |

## 4. 插件清单 (plugin.yaml)

```yaml
name: my-plugin
version: 1.0.0
description: 插件描述
author: 作者

# 订阅的钩子
hooks:
  - pre_search
  - post_search

# 提供的功能 (供其他插件依赖)
provides:
  - search_translate

# 依赖的其他插件
depends:
  - core-search

# 权限声明
permissions:
  - network      # 允许网络请求
  - fs_read      # 允许文件读取

# 入口文件
entry_point: plugin.py

# 配置 schema
config_schema:
  type: object
  properties:
    api_key:
      type: string
      description: Translation API key
    target_language:
      type: string
      default: zh

tags:
  - search
  - translation
```

## 5. 权限模型

| 权限 | 说明 | 风险 |
|------|------|------|
| `safe` | 仅内存操作 | 无 |
| `network` | 允许 HTTP 请求 | 中 (数据泄露) |
| `fs_read` | 读取文件 | 中 (信息泄露) |
| `fs_write` | 写入文件 | 高 (数据篡改) |
| `env` | 读取环境变量 | 中 (密钥泄露) |
| `full` | 完全权限 | 极高 |

**沙箱策略**:
- 默认允许: `safe`, `network`, `fs_read`
- 需审批: `fs_write`, `env`
- 禁止: `full` (除非管理员配置)

## 6. 内置钩子点

| 钩子 | 触发时机 | 参数 |
|------|---------|------|
| `pre_search` | 搜索执行前 | query, filters, limit |
| `post_search` | 搜索执行后 | results, query |
| `pre_pdf_process` | PDF 处理前 | file_path, options |
| `post_pdf_process` | PDF 处理后 | pages, annotations |
| `pre_ai_call` | AI 调用前 | messages, model, params |
| `post_ai_call` | AI 调用后 | response, model |
| `pre_write` | 写作执行前 | topic, outline, style |
| `post_write` | 写作执行后 | content, sections |
| `pre_chart` | 图表生成前 | data, chart_type, style |
| `post_chart` | 图表生成后 | image, chart_type |

## 7. API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/plugins/` | 列出已安装插件 |
| GET | `/api/plugins/discover` | 发现可用插件 |
| POST | `/api/plugins/load` | 加载插件 |
| POST | `/api/plugins/{name}/enable` | 启用插件 |
| POST | `/api/plugins/{name}/disable` | 禁用插件 |
| DELETE | `/api/plugins/{name}` | 卸载插件 |
| POST | `/api/plugins/hook` | 触发钩子 |
| GET | `/api/plugins/{name}/status` | 插件状态 |

## 8. 示例插件

见 `plugins/example-search-enhancer/`

```python
from app.services.plugin_system import AcaSightPlugin

class MyPlugin(AcaSightPlugin):
    async def on_load(self, config):
        self.register_hook("post_search", self.enhance)
    
    async def enhance(self, results, **kwargs):
        # 增强搜索结果
        for r in results:
            r["auto_tags"] = self._extract_tags(r["title"])
        return {"enhanced": True}
```

## 9. 性能考虑

- 钩子调度顺序: 按注册顺序，无优先级 (v1.0)
- 超时保护: 默认 30s，可配置
- 错误隔离: 单插件失败不阻断其他处理器
- 异步执行: 所有钩子处理器为 async
- 未来: 支持插件子进程隔离 (ProcessPoolExecutor)

## 10. 未来扩展

| 版本 | 特性 |
|------|------|
| v1.1 | 钩子优先级 + 异步并行钩子 |
| v1.2 | 插件子进程沙箱 (ProcessPoolExecutor) |
| v1.3 | 插件市场 (远程安装/更新) |
| v2.0 | 可视化插件管理 UI + 配置编辑器 |
