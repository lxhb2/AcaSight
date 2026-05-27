# Chapter B 技术复盘 — 玻璃浮雕 UI

**时间**: 2026-05-26 22:26–22:35 GMT+8 | **版本**: v8.0

## 执行摘要

Chapter B 的 CSS 变量体系 + 组件玻璃化**在 v7.0 就已经全部埋好**，所有面板（图标栏、面板容器、设置面板）一致使用 `var(--glass-*)`。唯一缺陷：**light mode 的 `--glass-blur: 0px`** 导致玻璃效果在浅色模式完全不可见。

**实际工作量: 10 分钟（修改 2 个 CSS 变量块）= 3h 预估的 5.6%**

---

## 任务清单对照

| # | 任务 | 文件 | 状态 | 说明 |
|---|------|------|------|------|
| B.1 | CSS 变量体系 | index.css | ✅ | 仅修值，不动结构 |
| B.2 | 面板容器玻璃化 | 已就绪 | ✅ | `.acasight-panel` 已用 `var(--glass-*)` |
| B.3 | 图标栏玻璃化 | 已就绪 | ✅ | `.acasight-icon-bar` 已用 `var(--glass-icon-bar-bg)` |
| B.4 | 设置面板玻璃化 | 已就绪 | ✅ | `SettingsModal` 已用 inline style `var(--glass-*)` |
| B.5 | 浅色主题适配 | index.css | ✅ | `--glass-blur` 0→10px |
| B.6 | 绘图保持方框 | 已就绪 | ✅ | `.acasight-panel.panel-charts { border-radius: 0; }` |

---

## 实际修改

### 文件: `frontend/src/index.css`（2 处编辑）

#### 1. Light mode（~109-115行）
```diff
- --glass-bg:         rgba(255, 255, 255, 0.92);
+ --glass-bg:         rgba(255, 255, 255, 0.78);

- --glass-blur:       0px;
+ --glass-blur:       10px;

- --glass-shadow:     0 8px 32px rgba(0, 0, 0, 0.08);
+ --glass-shadow:     0 8px 32px rgba(0, 0, 0, 0.10);

- --glass-shadow-sm:  0 2px 8px rgba(0, 0, 0, 0.04);
+ --glass-shadow-sm:  0 2px 12px rgba(0, 0, 0, 0.06);

- --glass-icon-bar-bg: rgba(250, 250, 250, 0.95);
+ --glass-icon-bar-bg: rgba(250, 250, 250, 0.82);
```

#### 2. Dark mode（~196-202行）
```diff
- --glass-bg:         rgba(17, 17, 17, 0.72);
+ --glass-bg:         rgba(30, 30, 46, 0.75);

- --glass-blur:       12px;
+ --glass-blur:       16px;

- --glass-shadow:     0 8px 32px rgba(0, 0, 0, 0.4);
+ --glass-shadow:     0 8px 32px rgba(0, 0, 0, 0.35);

- --glass-shadow-sm:  0 4px 16px rgba(0, 0, 0, 0.3);
+ --glass-shadow-sm:  0 4px 16px rgba(0, 0, 0, 0.25);

- --glass-icon-bar-bg: rgba(17, 17, 17, 0.65);
+ --glass-icon-bar-bg: rgba(30, 30, 46, 0.72);
```

---

## 验收结果

| 标准 | 结果 |
|------|------|
| `npx tsc --noEmit` | ✅ 零错误 |
| `npx vite build` | ✅ 成功（1m 14s） |
| 深色模式：面板毛玻璃 + 圆角 | ✅ `--glass-blur: 16px`，暗蓝底 |
| 浅色模式：面板半透 + 柔和阴影 + 圆角 | ✅ `--glass-blur: 10px`，白底微透 |
| ChartPanel 保留方框 | ✅ `.panel-charts { border-radius: 0; }` 不受影响 |

---

## 受影响组件（自动生效，无需额外修改）

| 组件 | CSS 类 | 玻璃变量 |
|------|--------|----------|
| 图标栏 | `.acasight-icon-bar` | `--glass-icon-bar-bg`, `--glass-blur`, `--glass-border` |
| 面板容器 | `.acasight-panel` | `--glass-bg`, `--glass-blur`, `--glass-border`, `--glass-radius`, `--glass-shadow-sm` |
| 设置面板 | `SettingsModal` (inline) | `--glass-bg`, `--glass-blur`, `--glass-border`, `--glass-shadow` |
| ContextualAgentBar | `.ctx-bubble-panel` | `--glass-bg`, `backdrop-filter: blur(20px)` (硬编码) |
| Tooltip 提示 | `.acasight-icon-item::after` | `--glass-bg`, `--glass-blur`, `--glass-border` |
| 搜索面板 | `.search-page-container` | `--glass-bg`, `--glass-blur`, `--glass-border` |
| Markdown 编辑器 | inline/style | `--glass-bg`, `--glass-blur` |

---

## 下一步

```
Phase 1 (剩余):
  ├─ Chapter B: 玻璃浮雕 UI ✅ (10min)
  ├─ Chapter C: 论文数据库 CRUD (6h) ← 下一步
  └─ Chapter D: Markdown 增强 (4h)
```

**Chapter C** 需要新建 `routers/papers.py`（CRUD API）+ 改造 `FileExplorerView` + 实现 `TagsView`。