# 脉冲学习系统 - 清理总结
**日期**: 2026-04-21  
**操作**: 删除冗余文件，统一命名

---

## 已删除/清理的文件

| 文件/目录 | 操作 | 原因 |
|-----------|------|------|
| `web_ui.py` (旧版) | 删除 | 被 v2 替代 |
| `web_ui_v2.py` | 重命名 | 成为主版本 |
| `src/**/__pycache__/*.pyc` | 删除 | Python 缓存文件 |

---

## 更新后的文件结构

```
projects/
├── web_ui.py              # 主 Web UI (原 v2)
├── cli.py                 # 命令行界面
├── start.bat              # 启动脚本 (已更新)
├── sync_directories.py    # 目录同步
├── src/
│   ├── tools/
│   │   ├── badge_manager.py      # 徽章系统 (新增)
│   │   ├── pulse_tools.py        # 核心工具 (已更新)
│   │   ├── combo_manager.py
│   │   ├── challenge_manager.py
│   │   └── ...
│   └── utils/
│       └── ...
├── assets/
│   └── PulseLearning/     # 统一数据目录
├── config/
│   ├── model_config.json
│   └── agent_llm_config.json
└── scripts/               # 测试脚本
    └── ...
```

---

## 启动方式

```bash
# 方式1: 双击 start.bat
# 方式2: 命令行
python web_ui.py    # Web 界面
python cli.py       # 命令行
```

---

## 清理后状态

- ✅ 无重复文件
- ✅ 无旧版本文件
- ✅ Python 缓存已清理
- ✅ 命名统一
