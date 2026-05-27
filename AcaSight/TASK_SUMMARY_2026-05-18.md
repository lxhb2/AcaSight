# AcaSight 学术视界 - 设计方案完成

## 完成内容

### 1. 设计文档
- **DESIGN_SPEC.md** - 详细设计规格书 (14KB)
  - Obsidian 风格界面设计
  - PDF 阅读器三栏布局
  - AI 被动触发设计
  - Office 编辑器方案 (OnlyOffice)
  - 浏览器方案 (Electron WebView)

- **ARCHITECTURE.md** - 技术架构详解 (12KB)
  - 整体架构图
  - 核心设计决策
  - 模块详细设计
  - 数据存储设计
  - AI 集成架构

### 2. 前端代码框架
- **Sidebar.tsx** - Obsidian 风格侧边栏
- **ProjectHome.tsx** - 论文项目管理首页
- **PDFReader.tsx** - 三栏 PDF 阅读器
- **AIToolbar.tsx** - 悬浮 AI 工具栏
- **AISidePanel.tsx** - AI 侧边面板
- **App.tsx** - 主应用组件

### 3. 配置文件
- package.json, vite.config.ts, tsconfig.json
- tailwind.config.js, index.html

## 核心设计特点

1. **Obsidian 风格界面**
   - 左侧图标导航栏
   - 点击切换功能模块
   - 深色主题默认

2. **PDF 阅读器**
   - 三栏布局: 缩略图-阅读区-AI区
   - 选中文本弹出 AI 工具栏
   - 右侧 AI/笔记切换面板

3. **AI 被动触发**
   - 不主动打扰用户
   - 选中文字才显示 AI 按钮
   - 用户点击才启动 AI 功能

4. **多功能集成**
   - 论文项目管理
   - AI 文献检索
   - PDF 阅读 + AI 辅助
   - 笔记写作
   - 数据分析
   - 实验设计
   - 内嵌浏览器
   - Office 编辑器 (OnlyOffice)

## 技术栈
- **前端**: Electron + React + TypeScript + Tailwind CSS
- **AI**: Ollama (本地) + OpenRouter/DeepSeek (云端)
- **PDF**: PDF.js
- **编辑器**: OnlyOffice / Monaco Editor
- **存储**: SQLite + 文件系统

## 下一步
1. 初始化前端项目 (`npm install`)
2. 实现 PDF 阅读器核心功能
3. 集成 Ollama 本地模型
4. 开发文献检索功能

---

*完成时间: 2026-05-18*
*状态: 设计完成，待开发*
