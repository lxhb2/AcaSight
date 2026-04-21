- **2026-04-13**：记忆系统启用

## 当前项目与关注

### Hermes Portable 配置 (2026-04-17)
- 完整项目报告：`H:\HermesPortable\PROJECT_REPORT_2026-04-17.md`
- 目录：`H:\HermesPortable\HermesAgent\`（主程序）、`H:\HermesPortable\ConfigPanel\`（配置面板）、`H:\HermesPortable\dashboard_server.py`（备用 Dashboard）
- config.yaml 路径：`H:\HermesPortable\HermesAgent\data\.hermes\config.yaml`
- 当前 provider=ollama-cloud（云端），models=minimax-m2.7，本地 qwen3.5:0.8b 未配置

### 已完成工作（2026-04-17）
- ✅ Dashboard 按钮集成到 Config Panel
- ✅ 5 个快捷脚本已创建
- ✅ Dashboard 自带中文，无需额外汉化
- ✅ 命令行配置可视化
- ✅ api-server.js Dashboard API 修复（Python312 硬编码路径）
- ✅ 备用 Dashboard HTTP 服务器（Python，端口 9119）

### 技术经验教训
- **npm --prefix 在当前 PowerShell 环境无效**：npm 始终从 workspace 读 package.json，Set-Location cd 有效
- **QClaw 缓存 api-server.js**：QClaw 重启后自动加载最新版本，旧 PID 缓存问题
- **hermes web_dist/assets 目录**：FastAPI StaticFiles 启动时检查，缺目录则崩溃
- **Python HTTP 服务器**: Start-Process -NoNewWindow 会关闭 stdin，导致 server_forever() 提前退出；用 `cmd /c start` 或 `python -m uvicorn` 更可靠

### 待处理
- Hermes Chat (18080) 未启动 → 需手动运行 launch_chat.bat 或通过 Config Panel
- npm build 失败 → 需在 CMD 中手动 `npm install && npm run build`
- providers:{} 为空 → 本地 Ollama 未注册为 provider，需编辑 config.yaml

### XRD 数据处理（继续关注）
- GUI 修图、数据解析（.raw/.txt）、堆叠图和精矿分析图重新生成、学术级图谱制作（SCI 标准）
- export_btn 变量名错误（第402行应为 export_report_btn）
- .raw 逗号分隔，.txt Bruker RAW 格式（;RAW4.00 注释头）
- 精矿分析图和堆叠图需重新生成

## 用户身份与偏好

- 绘图风格参考：学术 SCI 论文级，复刻 Origin/HighScore Plus 风格，高分辨率 ≥300dpi
