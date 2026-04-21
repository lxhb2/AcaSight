# Pulse Learning System - 精简提示词 + 多模型切换

## 完成时间
2026-04-20 晚

## 修改的文件清单

```
projects/
├── cli.py                                    # 重写：支持多模型切换+精简提示词+!online等命令
├── config/
│   ├── agent_llm_config.json                # 精简：提示词从 ~2000 chars → ~600 chars
│   └── model_config.json                    # 新建：多模型配置（硅基流动/Ollama/LM Studio）
├── config/model_config.json                  # 新建：统一模型配置
└── src/
    ├── agents/
    │   └── agent.py                         # 重写：支持多模型+自动检测+精简提示词
    └── utils/
        ├── llm_client.py                    # 新建：统一 LLM 客户端（替代 ollama_client.py）
        └── prompt_builder.py                # 新增：build_pulse_learning_system_prompt_light()
```

## 功能说明

### 1. 统一 LLM 客户端 `llm_client.py`
- `is_online()` - 检测网络
- `check_ollama_available()` - 检测 Ollama
- `check_lmstudio_available()` - 检测 LM Studio
- `get_active_provider()` - 自动选择可用模型
- `LLMClient` - 统一接口，支持 Ollama 原生 API + OpenAI 兼容 API

### 2. 多模型切换
| 配置 | Provider | 模型 | API |
|------|----------|------|-----|
| online | siliconflow | Qwen2.5-7B-Instruct | OpenAI 兼容 |
| offline_ollama | ollama | qwen3.5:4b | 原生 API |
| offline_lmstudio | lmstudio | qwen2.5-3b-instruct | OpenAI 兼容 |

### 3. 精简提示词
| 版本 | 长度 | Token 约 |
|------|------|---------|
| 完整版 | 1920 chars | ~480 |
| 精简版 | 779 chars | ~194 |
| **减少** | **59%** | |

### 4. CLI 模式切换命令
| 命令 | 功能 |
|------|------|
| `!online` | 强制云端 API + 完整提示词 |
| `!offline` | 强制本地模型 + 精简提示词 |
| `!ollama` | 强制 Ollama |
| `!lmstudio` | 强制 LM Studio |
| `!auto` | 恢复自动检测 |
| `!status` | 显示当前状态 |
| `!light` | 切换精简提示词 |
| `!full` | 切换完整提示词 |

## 验证结果

```
online: True
provider: ollama, model: qwen3.5:4b
精简版: 779 chars (~194 tokens)
完整版: 1920 chars (~480 tokens)
精简后减少: 59%
✅ Ollama API 测试通过
```

## 待配置

1. **硅基流动 API Key** - 编辑 `config/model_config.json`，填入 `online.api_key`
2. **LM Studio** - 启动后访问 `http://localhost:1234`，加载模型后启用 API
3. **更小的模型**（可选）：`ollama pull qwen2.5:1.5b`，修改 `model_config.json`
