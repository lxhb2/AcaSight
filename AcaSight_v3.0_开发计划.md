# AcaSight v3.0 开发计划 — 桌面化 + Office编辑器 + AI写作联通

> 基于全面代码检查、安全审计和技术调研制定 | 2026-06-03

---

## 一、当前状态总结

### 1.1 已完成功能

| 模块 | 状态 | 说明 |
|------|------|------|
| 11维度论文分析 | ✅ | 文献拆解+维度查询+导出 |
| AI写作工作台 | ✅ | 大纲生成+章节撰写+润色 |
| Excalidraw白板 | ✅ | 绘图注入+圈阅标注 |
| DBLP检索 | ✅ | 会议论文搜索 |
| PDF阅读器 | ✅ | 文本选择+翻译+注释 |
| 科研绘图引擎 v1.0 | ✅ | 30+ API端点，11种图表类型 |
| 统一绘图中心 | ✅ | PlotStudio整合4大类11子模块 |
| 帮助中心 | ✅ | 6大分区，API配置+FAQ+快捷键 |
| Zotero集成 | ✅ | 文献库同步+PDF下载 |

### 1.2 已修复问题

| 类别 | 修复数 | 说明 |
|------|--------|------|
| 前端console.log | 5处 | ChartPanel.tsx调试代码清除 |
| 前端内存泄漏 | 3处 | ObjectURL未释放修复 |
| 后端Critical漏洞 | 4处 | RCE/硬编码密钥/SSRF/弱JWT |
| 后端High漏洞 | 8处 | 路径遍历×4/无认证/插件RCE/信息泄露 |

### 1.3 遗留问题（低优先级）

| 问题 | 优先级 | 说明 |
|------|--------|------|
| `any`类型滥用（43处） | P2 | plotService.ts占25处，需逐步替换 |
| useEffect缺少AbortController | P2 | 14处异步操作未取消 |
| 可访问性ARIA缺失 | P3 | ~12处div onClick无role |
| 依赖版本未锁定 | P3 | requirements.txt无上限 |

---

## 二、技术选型

### 2.1 桌面框架：Tauri v2 ✅ 推荐

| 维度 | Tauri v2 | Electron |
|------|----------|----------|
| 安装包大小 | ~8MB | ~150MB |
| 内存占用 | ~30MB | ~200MB |
| 原生API | Rust插件系统 | Node.js |
| 跨平台 | Win/Mac/Linux | Win/Mac/Linux |
| 前端集成 | Vite原生支持 | 需electron-builder |
| 自动更新 | ✅ 内置 | 需electron-updater |
| 系统托盘 | ✅ | ✅ |
| 文件系统 | ✅ fs插件 | ✅ 完整Node.js |
| 安全模型 | 权限白名单 | 完全Node.js访问 |

**选择理由**：AcaSight面向科研用户，安装包小、启动快、内存低是关键优势。Tauri v2已稳定，Rust插件系统可满足原生API需求。

### 2.2 Office编辑器：OnlyOffice ✅ 推荐

| 维度 | OnlyOffice | Collabora | WPS |
|------|-----------|-----------|-----|
| 自部署 | ✅ Docker | ✅ Docker | ❌ SaaS |
| 格式兼容 | .docx/.xlsx/.pptx | .odt优先 | .docx/.xlsx |
| 实时协作 | ✅ | ✅ | ✅ |
| 嵌入方式 | iframe/Connector API | iframe | SDK |
| 插件API | ✅ JavaScript | 有限 | 有限 |
| 中文支持 | ✅ | ⚠️ 一般 | ✅ |
| 许可证 | AGPL v3 (社区版) | MPL 2.0 | 商业 |

**选择理由**：OnlyOffice提供完整的Connector API，可通过JavaScript编程操作文档内容，是实现"AI写作→插入文档"工作流的关键。AGPL社区版可自部署。

### 2.3 Markdown转换：Pandoc ✅ 推荐

| 维度 | Pandoc | Node.js方案 | Python方案 |
|------|--------|-------------|-----------|
| 格式覆盖 | 40+格式 | docx仅 | docx仅 |
| 转换质量 | 最高 | 中等 | 中等 |
| 数学公式 | ✅ LaTeX | ⚠️ 有限 | ⚠️ 有限 |
| 表格 | ✅ | ✅ | ✅ |
| 图片 | ✅ 嵌入 | ✅ | ✅ |
| 双向转换 | ✅ | ⚠️ 单向 | ⚠️ 单向 |
| 集成方式 | 命令行+Python绑定 | npm包 | pip包 |

**选择理由**：Pandoc是学术文档转换的工业标准，支持Markdown↔docx双向转换，数学公式和表格处理质量最高。通过`pypandoc`集成到FastAPI后端。

### 2.4 AI写作联通架构

```
AI写作工作台 ──生成文本──→ OnlyOffice Connector API ──插入到光标位置──→ 文档编辑器
     ↑                              ↓
     └──── 选中文本 ←── 获取选区内容 ←────┘
                    ↓
              AI润色/改写
                    ↓
              替换选区内容
```

---

## 三、分阶段开发计划

### Phase 1：Tauri桌面化（P0，3-4周）

> 目标：将Web应用封装为原生桌面应用，实现文件系统访问和系统级集成

#### 后端任务

| # | 任务 | 优先级 | 说明 |
|---|------|--------|------|
| 1.1 | 安装Tauri v2 CLI | P0 | `npm install @tauri-apps/cli@latest` |
| 1.2 | 初始化Tauri项目 | P0 | `npx tauri init`，配置窗口/权限/打包 |
| 1.3 | 配置Vite开发服务器 | P0 | 开发模式指向localhost:5173，生产模式打包dist |
| 1.4 | 文件系统插件 | P0 | `@tauri-apps/plugin-fs`，替代浏览器File API |
| 1.5 | 对话框插件 | P0 | `@tauri-apps/plugin-dialog`，原生打开/保存对话框 |
| 1.6 | 系统托盘 | P1 | 最小化到托盘，后台运行AI任务 |
| 1.7 | 自动更新 | P1 | `@tauri-apps/plugin-updater`，GitHub Release分发 |
| 1.8 | 原生菜单 | P2 | 应用菜单（文件/编辑/视图/帮助） |
| 1.9 | 全局快捷键 | P1 | `@tauri-apps/plugin-global-shortcut`，系统级热键 |
| 1.10 | 窗口状态持久化 | P2 | 记住窗口位置/大小 |

#### 前端任务

| # | 任务 | 优先级 | 说明 |
|---|------|--------|------|
| 1.11 | Tauri API适配层 | P0 | `src/lib/tauri-adapter.ts`，统一浏览器/Tauri环境 |
| 1.12 | 文件操作迁移 | P0 | 浏览器File API → Tauri fs插件 |
| 1.13 | 拖拽文件到窗口 | P1 | Tauri文件拖放事件处理 |
| 1.14 | 离线模式支持 | P2 | Service Worker + IndexedDB缓存 |
| 1.15 | 打包配置优化 | P0 | Windows NSIS安装包，macOS DMG |

#### 交付物

- Windows安装包（.exe / .msi）
- macOS安装包（.dmg）
- 原生文件打开/保存对话框
- 系统托盘最小化
- 自动更新机制

---

### Phase 2：OnlyOffice集成 + 文档编辑器（P0，4-5周）

> 目标：嵌入OnlyOffice编辑器，实现docx/xlsx/pptx在线编辑

#### 后端任务

| # | 任务 | 优先级 | 说明 |
|---|------|--------|------|
| 2.1 | OnlyOffice Docker部署 | P0 | `onlyoffice/documentserver` 容器 |
| 2.2 | 文档管理API | P0 | CRUD文档，版本控制，存储路径管理 |
| 2.3 | OnlyOffice回调处理 | P0 | 文档保存回调，状态同步 |
| 2.4 | JWT签名 | P0 | OnlyOffice文档服务器JWT认证 |
| 2.5 | 文档模板管理 | P1 | 预置论文模板（Nature/Science/学位论文） |
| 2.6 | 文档权限控制 | P1 | 只读/编辑/审阅模式切换 |
| 2.7 | 协作编辑 | P2 | 多用户实时协作（需用户系统） |

#### 前端任务

| # | 任务 | 优先级 | 说明 |
|---|------|--------|------|
| 2.8 | OnlyOffice嵌入组件 | P0 | `DocumentEditor.tsx`，iframe + Connector API |
| 2.9 | 文档管理面板 | P0 | 文档列表/新建/打开/删除 |
| 2.10 | Connector API封装 | P0 | `onlyoffice-connector.ts`，编程操作文档 |
| 2.11 | 文档→写作工作台联动 | P1 | 从文档选区提取文本到AI写作台 |
| 2.12 | 侧边栏文档属性 | P2 | 字数统计/段落结构/样式信息 |

#### API端点

```
POST   /api/documents/              # 创建文档
GET    /api/documents/              # 文档列表
GET    /api/documents/{id}          # 获取文档（OnlyOffice编辑器URL）
PUT    /api/documents/{id}          # 更新文档元数据
DELETE /api/documents/{id}          # 删除文档
POST   /api/documents/{id}/callback # OnlyOffice保存回调
GET    /api/documents/templates     # 获取文档模板列表
POST   /api/documents/from-template # 从模板创建文档
```

#### 交付物

- OnlyOffice编辑器嵌入AcaSight界面
- docx/xlsx/pptx文件创建和编辑
- 文档保存和版本管理
- 预置论文模板

---

### Phase 3：Markdown ↔ Office 双向转换（P1，2-3周）

> 目标：实现Markdown与Office文档的无缝互转

#### 后端任务

| # | 任务 | 优先级 | 说明 |
|---|------|--------|------|
| 3.1 | 安装Pandoc | P0 | 系统级安装 + `pypandoc` Python绑定 |
| 3.2 | Markdown→docx转换API | P0 | 支持模板引用，公式/表格/图片保留 |
| 3.3 | docx→Markdown转换API | P0 | 结构化提取，保留标题层级 |
| 3.4 | 参考文献格式转换 | P1 | BibTeX → docx引用格式（APA/Nature/GB-T7714） |
| 3.5 | 公式转换 | P1 | LaTeX → OMML（Office MathML）双向 |
| 3.6 | 图片嵌入处理 | P1 | Markdown图片→docx嵌入，docx图片→Markdown引用 |
| 3.7 | 批量转换 | P2 | 多文档批量Markdown→docx导出 |

#### 前端任务

| # | 任务 | 优先级 | 说明 |
|---|------|--------|------|
| 3.8 | 转换对话框组件 | P0 | 选择源格式→目标格式，配置选项 |
| 3.9 | Markdown预览与docx预览对比 | P1 | 并排预览转换结果 |
| 3.10 | 写作台一键导出 | P0 | Markdown写作内容→docx一键导出 |
| 3.11 | 文档一键导入 | P1 | docx→Markdown导入到写作台 |

#### API端点

```
POST /api/convert/md-to-docx       # Markdown → docx
POST /api/convert/docx-to-md       # docx → Markdown
POST /api/convert/md-to-pdf        # Markdown → PDF（Pandoc + LaTeX）
POST /api/convert/batch            # 批量转换
GET  /api/convert/templates        # 获取Pandoc模板列表
```

#### 交付物

- Markdown ↔ docx 双向转换
- 公式/表格/图片保留
- 参考文献格式自动适配
- 写作台一键导出docx

---

### Phase 4：AI写作台 ↔ Office编辑器联通（P0，3-4周）

> 目标：实现AI写作与文档编辑的深度集成

#### 核心工作流

```
┌─────────────────────────────────────────────────┐
│                   AcaSight 主界面                  │
│                                                   │
│  ┌──────────────┐    ┌──────────────────────────┐│
│  │  AI写作工作台  │    │   OnlyOffice文档编辑器    ││
│  │              │    │                          ││
│  │ [大纲生成]    │───→│ 插入到光标位置             ││
│  │ [章节撰写]    │───→│ 追加到文档末尾             ││
│  │ [文本润色]    │←───│ 获取选区文本              ││
│  │ [翻译改写]    │───→│ 替换选区内容              ││
│  │ [引用插入]    │───→│ 插入引用+自动编号          ││
│  │ [图表插入]    │───→│ 插入PlotSchema渲染图       ││
│  └──────────────┘    └──────────────────────────┘│
└─────────────────────────────────────────────────┘
```

#### 后端任务

| # | 任务 | 优先级 | 说明 |
|---|------|--------|------|
| 4.1 | AI写作→文档插入API | P0 | 接收AI生成文本+目标文档ID+插入位置 |
| 4.2 | 文档选区→AI处理API | P0 | 接收选区文本+处理指令（润色/翻译/改写） |
| 4.3 | 引用管理器 | P0 | 文献引用自动编号+BibTeX管理 |
| 4.4 | 图表插入服务 | P1 | PlotSchema→SVG/PNG→插入文档指定位置 |
| 4.5 | 智能排版 | P2 | AI根据期刊要求自动调整格式 |
| 4.6 | 审阅模式 | P2 | AI修改建议以修订模式显示 |

#### 前端任务

| # | 任务 | 优先级 | 说明 |
|---|------|--------|------|
| 4.7 | AI写作台重构 | P0 | 新增"插入到文档"按钮，支持选择目标文档 |
| 4.8 | 文档选区AI操作 | P0 | 右键菜单：选中文本→AI润色/翻译/改写 |
| 4.9 | 引用插入面板 | P1 | 从文献库选择→自动格式化引用→插入 |
| 4.10 | 图表插入面板 | P1 | 从PlotStudio选择图表→插入文档 |
| 4.11 | 修改追踪UI | P2 | 显示AI修改建议，接受/拒绝操作 |
| 4.12 | 写作进度面板 | P2 | 论文各章节完成度可视化 |

#### API端点

```
POST /api/writing/insert-to-doc      # AI文本→插入文档
POST /api/writing/process-selection  # 文档选区→AI处理
POST /api/writing/insert-citation    # 插入引用
POST /api/writing/insert-figure      # 插入图表
GET  /api/writing/document-structure # 获取文档结构（标题树）
```

#### 交付物

- AI生成内容一键插入文档
- 选中文本右键AI润色/翻译
- 文献引用自动编号和格式化
- 绘图中心图表插入文档
- 修改追踪和审阅模式

---

### Phase 5：用户系统 + 认证 + 权限（P1，2-3周）

> 目标：实现用户认证，为协作编辑和多端同步打基础

#### 后端任务

| # | 任务 | 优先级 | 说明 |
|---|------|--------|------|
| 5.1 | 用户模型 | P0 | SQLAlchemy User模型（email/password_hash/role） |
| 5.2 | JWT认证中间件 | P0 | 登录/注册/刷新Token/验证 |
| 5.3 | 密码安全 | P0 | bcrypt哈希 + 盐值 |
| 5.4 | RBAC权限 | P1 | admin/researcher/viewer角色 |
| 5.5 | 数据隔离 | P1 | 用户间文献/文档/笔记隔离 |
| 5.6 | 登录/注册页面 | P0 | 前端认证流程 |
| 5.7 | Token管理 | P0 | 前端axios拦截器 + 自动刷新 |

#### 交付物

- 用户注册/登录
- JWT认证保护所有API
- 数据隔离
- 角色权限控制

---

### Phase 6：高级功能 + 生态完善（P2，4-5周）

> 目标：完善生态，提升专业度和易用性

| # | 任务 | 说明 |
|---|------|------|
| 6.1 | 插件市场 | 用户可安装/卸载第三方插件 |
| 6.2 | 数据云同步 | WebDAV/S3文献和文档云同步 |
| 6.3 | 批量文献处理 | 批量导入/分析/导出文献 |
| 6.4 | 论文查重 | 集成查重API或本地比对 |
| 6.5 | LaTeX编辑器 | CodeMirror + LaTeX编译预览 |
| 6.6 | 实验记录本 | 结构化实验数据记录+关联文献 |
| 6.7 | 知识图谱可视化 | D3.js力导向图+文献关系网络 |
| 6.8 | 移动端适配 | 响应式布局+iOS/Android阅读模式 |

---

## 四、文件结构规划（新增）

```
AcaSight/
├── src-tauri/                          # 🆕 Tauri桌面端
│   ├── Cargo.toml
│   ├── tauri.conf.json
│   ├── capabilities/
│   │   ├── fs.json                     # 文件系统权限
│   │   ├── dialog.json                 # 对话框权限
│   │   └── updater.json                # 自动更新权限
│   └── src/
│       ├── main.rs                     # Tauri入口
│       └── lib.rs                      # 命令注册
├── frontend/src/
│   ├── lib/
│   │   └── tauri-adapter.ts            # 🆕 Tauri/浏览器适配层
│   ├── components/
│   │   ├── Document/                   # 🆕 文档编辑器
│   │   │   ├── DocumentEditor.tsx      # OnlyOffice嵌入
│   │   │   ├── DocumentList.tsx        # 文档管理
│   │   │   └── DocumentToolbar.tsx     # 文档工具栏
│   │   ├── Convert/                    # 🆕 格式转换
│   │   │   ├── ConvertDialog.tsx       # 转换对话框
│   │   │   └── ConvertPreview.tsx      # 转换预览
│   │   ├── Writing/                    # 扩展
│   │   │   ├── WritingWorkspace.tsx    # 重构：增加文档联动
│   │   │   ├── CitationPanel.tsx       # 🆕 引用管理
│   │   │   └── FigureInsertPanel.tsx   # 🆕 图表插入
│   │   ├── Auth/                       # 🆕 认证
│   │   │   ├── LoginPage.tsx
│   │   │   └── RegisterPage.tsx
│   │   └── Help/
│   │       └── HelpCenter.tsx          # ✅ 已完成
│   └── services/
│       ├── documentService.ts          # 🆕 文档API
│       └── convertService.ts           # 🆕 转换API
├── backend/
│   ├── app/
│   │   ├── routers/
│   │   │   ├── documents.py            # 🆕 文档管理路由
│   │   │   ├── convert.py              # 🆕 格式转换路由
│   │   │   └── auth.py                 # 🆕 认证路由
│   │   ├── services/
│   │   │   ├── document_service.py     # 🆕 文档管理服务
│   │   │   ├── convert_service.py      # 🆕 Pandoc转换服务
│   │   │   ├── onlyoffice_service.py   # 🆕 OnlyOffice集成服务
│   │   │   ├── citation_service.py     # 🆕 引用管理服务
│   │   │   └── auth_service.py         # 🆕 认证服务
│   │   └── models/
│   │       ├── user.py                 # 🆕 用户模型
│   │       └── document.py             # 🆕 文档模型
│   ├── docker/
│   │   └── docker-compose.yml          # 🆕 OnlyOffice容器编排
│   └── requirements.txt                # 更新：添加pypandoc等
└── docs/
    └── deployment.md                   # 🆕 部署文档
```

---

## 五、依赖新增

### 桌面端（Tauri）

```bash
npm install @tauri-apps/api @tauri-apps/plugin-fs @tauri-apps/plugin-dialog @tauri-apps/plugin-updater @tauri-apps/plugin-shell
```

### 后端

```bash
pip install pypandoc      # Pandoc Python绑定
pip install python-jose   # JWT（已注释，需启用）
pip install passlib       # 密码哈希（已注释，需启用）
pip install bcrypt        # bcrypt哈希
pip install aiohttp       # OnlyOffice API调用
```

### 系统级

```bash
# Pandoc（文档转换引擎）
winget install JohnMacFarlane.Pandoc

# OnlyOffice Document Server（Docker）
docker run -d -p 8443:443 onlyoffice/documentserver
```

---

## 六、风险与对策

| 风险 | 影响 | 对策 |
|------|------|------|
| OnlyOffice AGPL许可证限制 | 商业分发需商业许可 | MVP使用社区版，后续评估商业许可 |
| Tauri v2插件生态不如Electron | 部分原生功能需自行开发 | 核心插件已稳定，特殊需求可写Rust插件 |
| Pandoc公式转换质量 | LaTeX→OMML可能丢失格式 | 预处理+后处理校验，复杂公式保留LaTeX源码 |
| OnlyOffice嵌入性能 | iframe加载慢（首次3-5s） | 预加载+缓存，文档列表页预初始化 |
| AI写作→文档插入精度 | 插入位置可能不精确 | 使用OnlyOffice书签API精确定位 |
| 桌面端自动更新 | Windows SmartScreen拦截 | 代码签名证书（EV证书约$400/年） |

---

## 七、总览时间线

```
Phase 1: Tauri桌面化              ████████░░░░░░░░░░░░  (3-4周)
Phase 2: OnlyOffice集成           ░░░░░░░░████████░░░░  (4-5周)
Phase 3: Markdown↔Office转换      ░░░░░░░░░░░░░░████░░  (2-3周)
Phase 4: AI写作↔文档联通          ░░░░░░░░░░░░░░░░████  (3-4周)
Phase 5: 用户系统+认证            ░░░░████░░░░░░░░░░░░  (2-3周)
Phase 6: 高级功能+生态            ░░░░░░░░░░░░░░░░░░██  (4-5周)
```

总计约 **18-24周**，按优先级递进交付。Phase 1-4为核心链路，Phase 5-6为增强功能。

---

## 八、验收标准

### Phase 1 验收

- [ ] Windows安装包双击安装，启动后显示AcaSight主界面
- [ ] 原生文件对话框打开/保存PDF
- [ ] 拖拽文件到窗口自动导入
- [ ] 最小化到系统托盘，后台运行
- [ ] 自动检测并提示更新

### Phase 2 验收

- [ ] 新建docx文档，OnlyOffice编辑器正常加载
- [ ] 编辑文档后自动保存，刷新后内容不丢失
- [ ] 从模板创建Nature格式论文
- [ ] 文档列表显示最近编辑的文档

### Phase 3 验收

- [ ] Markdown写作内容一键导出为docx，公式/表格/图片保留
- [ ] docx文件导入为Markdown，标题层级正确
- [ ] 参考文献自动格式化为指定期刊格式
- [ ] 批量导出5篇Markdown为docx

### Phase 4 验收

- [ ] AI生成大纲→一键插入到文档指定位置
- [ ] 文档中选中文本→右键AI润色→修改后替换
- [ ] 从文献库选择引用→自动编号插入文档
- [ ] PlotStudio图表→导出为图片→插入文档

### Phase 5 验收

- [ ] 注册/登录流程完整
- [ ] 未登录用户无法访问API
- [ ] 用户间数据隔离
- [ ] admin角色可管理用户
