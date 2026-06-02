# AcaSight 实现指南

## 已完成的设计文档

1. **DESIGN_SPEC.md** - 详细设计规格书
2. **ARCHITECTURE.md** - 技术架构详解

## 已完成的前端代码

### 核心组件
- `src/App.tsx` - 主应用组件
- `src/components/Layout/Sidebar.tsx` - Obsidian 风格侧边栏
- `src/components/Projects/ProjectHome.tsx` - 论文项目管理首页
- `src/components/PDFReader/PDFReader.tsx` - PDF 阅读器
- `src/components/PDFReader/AIToolbar.tsx` - 悬浮 AI 工具栏
- `src/components/PDFReader/AISidePanel.tsx` - AI 侧边面板

### 配置文件
- `package.json`, `vite.config.ts`, `tsconfig.json`, `tailwind.config.js`

## 下一步开发步骤

### 1. 初始化项目
```bash
cd AcaSight/frontend
npm install
npm run dev
```

### 2. 安装额外依赖
```bash
npm install react-pdf pdf-lib @monaco-editor/react recharts
```

### 3. 实现功能模块
- PDF 阅读器完整实现
- 论文项目管理
- Ollama 本地模型集成
- 文献检索 API 集成

## 关键技术点

### 本地文件系统访问 (Electron)
```typescript
// 主进程
ipcMain.handle('select-pdf', async () => {
  const result = await dialog.showOpenDialog({
    filters: [{ name: 'PDF', extensions: ['pdf'] }]
  });
  return result.filePaths;
});
```

### Ollama 本地模型
```typescript
async function chatWithOllama(message: string): Promise<string> {
  const response = await fetch('http://localhost:11434/api/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model: 'llama2',
      prompt: message,
      stream: false
    })
  });
  const data = await response.json();
  return data.response;
}
```

### 文献检索
```typescript
// OpenAlex
const response = await fetch(
  `https://api.openalex.org/works?search=${query}&per-page=20`
);

// Semantic Scholar
const response = await fetch(
  `https://api.semanticscholar.org/graph/v1/paper/search?query=${query}&fields=title,authors,year&limit=20`
);
```

## 参考资源
- Obsidian: https://obsidian.md/
- Electron: https://www.electronjs.org/docs
- React PDF: https://react-pdf.org/
- Ollama: https://ollama.ai/

---

*文档版本: v1.0*
*最后更新: 2026-05-18*
*状态: 开发准备完成*
