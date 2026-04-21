# Python 学习平台 v2.0

## 使用说明

### 1. 启动方式
双击 start.py 启动本地服务器，或在终端运行：
`ash
python start.py
`

启动后会自动打开浏览器访问 http://localhost:8080

### 2. 功能介绍

#### 左侧导航
- 4门课程：Python基础语法、Python爬虫、办公自动化、数据分析
- 共48个章节

#### 中间内容区
- **学习模式**：iframe 加载课程 HTML 内容
- **练习模式**：Python 代码编辑器 + AI 助手

#### 右侧练习模块
- 练习题库（根据课程自动加载）
- Python 代码编辑器（CodeMirror + Pyodide）
- AI 助手（Ollama 本地模型）

### 3. AI 配置
- 确保 Ollama 已启动：ollama serve
- 模型：自动检测可用的 qwen 系列模型
- 如果没有安装，运行：ollama pull qwen2.5:3b

### 4. 文件结构
`
python-learner-v2/
├── index.html          # 主页面
├── start.py            # 服务器启动器
├── css/
│   └── style.css       # 样式文件
├── js/
│   └── app.js          # 主逻辑
├── data/
│   └── courses/       # 课程文件（需复制）
└── 复制课程文件.bat    # 复制课程文件的脚本
`

### 5. 常见问题

Q: 课程内容显示空白
A: 确保已运行"复制课程文件.bat"或手动复制课程文件夹到 data/courses

Q: AI 助手无法使用
A: 确保 Ollama 已启动且已安装模型

Q: Python 代码无法运行
A: 首次加载 Pyodide 需要几秒钟，请耐心等待
