## 任务背景
用户需要为Hermes Agent创建真正的Web交互界面，支持工具调用和Skill功能，并探索与QClaw双Agent协同的可能性。

## 执行过程
1. 修复config.yaml和.env配置
2. 在api-server.js添加/api/chat端点
3. 更新Dashboard HTML对接新API
4. 修复launch_chat.bat的Python路径
5. 分析acp-main.zip项目

## 关键结果
- 新增`/api/chat`和`/api/chat/stream`端点（端口1420）
- Dashboard Web UI运行于http://localhost:9119
- 启动脚本改用Anaconda Python路径
- 确认Hermes内置`hermes acp`命令支持ACP协议
- 当前Web UI仅能对话，工具调用需终端模式

## 结论建议
Web Chat已可用但缺少工具能力，推荐通过ACP协议实现QClaw+Hermes双Agent协同，需进一步探索`hermes acp`具体用法。