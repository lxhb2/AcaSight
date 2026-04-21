#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pulse Learning System - 完整 CLI 界面
支持多模型切换（云端/本地）+ 精简提示词 + 完整学习流程
"""
import os
import sys
import json
import re

# 设置编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 设置工作目录
PROJECTS_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECTS_DIR)

# 项目目录
PROJECTS_BASE = os.path.join(PROJECTS_DIR, "assets", "PulseLearning")


class PulseCLI:
    """Pulse Learning CLI 主类"""

    def __init__(self):
        # 设置路径
        self.src_path = os.path.join(PROJECTS_DIR, "src")
        sys.path.insert(0, self.src_path)

        # 加载统一 LLM 客户端
        from utils.llm_client import create_client, is_online, load_model_config

        self._is_online_fn = is_online
        self._load_config = load_model_config

        # 当前模式
        self.force_mode = None  # None=自动, "online", "ollama", "lmstudio"
        self.use_light_prompt = not is_online()  # 离线时用精简版

        # 创建客户端
        self._refresh_client()

        # 会话状态
        self.current_project = None
        self.current_module = None
        self.conversation_history = []

        # 打印启动信息
        self._print_banner()

    def _refresh_client(self):
        """重新创建 LLM 客户端（切换模式后调用）"""
        from utils.llm_client import create_client

        self.client = create_client(force_mode=self.force_mode)
        self._load_prompt()
        print(f"[模式] {self.client.provider} / {self.client.model} ({self.client.mode})")
        print(f"[提示词] {'精简版' if self.use_light_prompt else '完整版'}")

    def _load_prompt(self):
        """加载系统提示词"""
        from utils.prompt_builder import (
            build_pulse_learning_system_prompt,
            build_pulse_learning_system_prompt_light
        )

        if self.use_light_prompt:
            self.system_prompt = build_pulse_learning_system_prompt_light(language="中文")
        else:
            self.system_prompt = build_pulse_learning_system_prompt(language="中文")

    def _print_banner(self):
        """打印启动横幅"""
        print("=" * 50)
        print("🎯 Pulse Learning System")
        print("=" * 50)
        self._show_status()
        print("=" * 50)
        print("输入 'help' 查看帮助，输入 'exit' 退出")
        print()

    def _show_status(self):
        """显示当前状态"""
        online = self._is_online_fn()
        print(f"网络: {'🟢 在线' if online else '🔴 离线'}")
        if self.force_mode:
            mode_name = {"online": "云端", "ollama": "Ollama", "lmstudio": "LM Studio"}.get(self.force_mode, self.force_mode)
            print(f"强制模式: {mode_name}")
        print(f"提示词: {'精简版' if self.use_light_prompt else '完整版'}")

    def chat(self, user_input: str) -> str:
        """发送聊天请求"""
        messages = [
            {"role": "system", "content": self.system_prompt},
        ] + self.conversation_history + [
            {"role": "user", "content": user_input}
        ]

        try:
            response = self.client.chat(
                messages=messages,
                temperature=self.client.temperature
            )
            content = response["message"]["content"]

            # 保存对话历史
            self.conversation_history.append({"role": "user", "content": user_input})
            self.conversation_history.append({"role": "assistant", "content": content})

            # 限制历史长度
            if len(self.conversation_history) > 10:
                self.conversation_history = self.conversation_history[-10:]

            return content
        except Exception as e:
            return f"❌ 错误: {str(e)}"

    def generate_challenges(self, project_name: str, module_name: str,
                            module_goal: str, discipline: str = "综合") -> list:
        """调用 AI 自动生成微挑战"""
        prompt = f"""请根据以下信息生成 4-6 个微挑战。

项目：{project_name}
模块名称：{module_name}
模块目标：{module_goal}
学习领域：{discipline}

要求：
1. 每个挑战 5-10 分钟可完成
2. 挑战应该循序渐进，由易到难
3. 每个挑战要有明确的"成功标志"

请以 JSON 数组格式输出，不要有其他文字：
[
  {{"description": "挑战1描述", "estimated_time": 5, "success_criteria": "成功标志1", "points": 10}},
  ...
]"""
        try:
            response = self.client.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                timeout=180
            )
            content = response["message"]["content"]

            # 提取 JSON
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return None
        except Exception as e:
            print(f"⚠️ 生成挑战失败: {e}")
            return None

    def handle_new(self, idea: str) -> str:
        """处理新项目创建 - 苏格拉底式对话"""
        if not idea:
            return "请告诉我你想学习什么？例如：new 我想学Python爬虫"

        clarification_prompt = f"""用户说："{idea}"
请通过提问帮助用户明确学习目标。每次只问 1-2 个最关键的问题。
询问：
1. 最终想做出什么具体成果？
2. 从零开始，第一个可验证的小成果是什么？
请用中文，保持友好鼓励的语气。"""

        response = self.chat(clarification_prompt)
        return f"""好的！让我帮你明确学习目标。

{response}

请回答以上问题，我会帮你创建项目并生成学习计划！"""

    def handle_create_project(self, info: dict) -> str:
        """创建项目"""
        from tools.pulse_tools import create_project

        project_name = info.get("name", "")
        goal_short = info.get("goal_short", "")
        goal_long = info.get("goal_long", "")
        discipline = info.get("discipline", "综合")

        if not project_name or not goal_short:
            return "项目信息不完整"

        result = create_project(project_name, goal_short, goal_long, discipline)
        self.current_project = project_name
        return result

    def handle_create_module(self, info: dict) -> str:
        """创建模块并自动生成挑战"""
        from tools.pulse_tools import create_module, add_challenge

        project_name = info.get("project_name", self.current_project)
        module_name = info.get("module_name", "")
        module_goal = info.get("module_goal", "")
        estimated_time = info.get("estimated_time", 30)

        if not project_name:
            return "请先指定项目：use 项目名"
        if not module_name:
            return "请指定模块名称"

        # 创建模块
        result = create_module(project_name, module_name, module_goal, estimated_time)

        # 自动生成挑战
        challenges = self.generate_challenges(project_name, module_name, module_goal)

        if challenges:
            result += "\n\n## 🤖 AI 生成的微挑战\n\n"
            for c in challenges:
                add_challenge(
                    project_name=project_name,
                    module_id=1,
                    challenge_desc=c.get("description", ""),
                    estimated_time=c.get("estimated_time", 5),
                    success_criteria=c.get("success_criteria", ""),
                    points=c.get("points", 10)
                )
                result += f"- {c.get('description')} (+{c.get('points', 10)}分)\n"
            result += "\n挑战已自动添加！开始学习吧！"

        self.current_project = project_name
        self.current_module = module_name
        return result

    def handle_continue(self, project_name: str = "") -> str:
        """继续学习"""
        if not project_name:
            from tools.pulse_tools import list_projects
            return list_projects()

        from tools.pulse_tools import get_project_status
        self.current_project = project_name
        return get_project_status(project_name)

    def handle_complete_challenge(self, project_name: str,
                                  module_id: int = 1, challenge_id: int = 1) -> str:
        """完成挑战"""
        from tools.pulse_tools import complete_challenge

        if not project_name:
            project_name = self.current_project
        if not project_name:
            return "请指定项目名称"

        return complete_challenge(project_name, module_id, challenge_id)

    def show_help(self) -> str:
        """显示帮助"""
        return """# 🎯 Pulse Learning CLI 帮助

## 学习命令

| 命令 | 说明 |
|------|------|
| `new [想法]` | 苏格拉底式创建项目 |
| `create 项目名 目标` | 直接创建项目 |
| `module 模块名 目标` | 创建模块+AI生成挑战 |
| `continue [项目名]` | 继续学习 |
| `use 项目名` | 切换项目 |
| `list` | 列出所有项目 |
| `status` | 查看项目状态 |
| `complete [ID]` | 完成挑战 |
| `help` | 显示帮助 |

## 模式切换命令

| 命令 | 说明 |
|------|------|
| `!online` | 强制使用云端 API |
| `!offline` | 强制使用本地模型 |
| `!ollama` | 使用 Ollama |
| `!lmstudio` | 使用 LM Studio |
| `!auto` | 恢复自动检测 |
| `!status` | 显示当前连接状态 |
| `!light` | 切换到精简提示词 |
| `!full` | 切换到完整提示词 |

## 示例

```
pulse> new 我想学Python爬虫
pulse> create 爬虫项目 学会爬取网页
pulse> module 基础HTML 学会HTML标签
pulse> continue
pulse> complete 1
pulse> !status
```
"""

    def run(self):
        """运行 CLI"""
        while True:
            try:
                user_input = input("\npulse> ").strip()

                if not user_input:
                    continue

                # 退出
                if user_input.lower() in ["exit", "quit", "退出"]:
                    print("再见！继续学习，下次见！👋")
                    break

                # 模式切换命令
                cmd = user_input.lower()
                if cmd == "!online":
                    self.force_mode = "online"
                    self.use_light_prompt = False
                    self._refresh_client()
                    print("已切换到云端 API + 完整提示词")
                    continue
                elif cmd == "!offline":
                    self.force_mode = None
                    self.use_light_prompt = True
                    self._refresh_client()
                    print("已切换到本地模型 + 精简提示词")
                    continue
                elif cmd == "!ollama":
                    self.force_mode = "ollama"
                    self.use_light_prompt = True
                    self._refresh_client()
                    print("已切换到 Ollama + 精简提示词")
                    continue
                elif cmd == "!lmstudio":
                    self.force_mode = "lmstudio"
                    self.use_light_prompt = True
                    self._refresh_client()
                    print("已切换到 LM Studio + 精简提示词")
                    continue
                elif cmd == "!auto":
                    self.force_mode = None
                    self.use_light_prompt = not self._is_online_fn()
                    self._refresh_client()
                    print("已恢复自动检测模式")
                    continue
                elif cmd == "!status":
                    self._show_status()
                    continue
                elif cmd == "!light":
                    self.use_light_prompt = True
                    self._load_prompt()
                    print("已切换到精简提示词")
                    continue
                elif cmd == "!full":
                    self.use_light_prompt = False
                    self._load_prompt()
                    print("已切换到完整提示词")
                    continue

                # 帮助
                if cmd in ["help", "帮助", "?"]:
                    print("\n" + self.show_help())
                    continue

                # 列出项目
                if cmd in ["list", "列表", "ls"]:
                    from tools.pulse_tools import list_projects
                    print("\n" + list_projects())
                    continue

                # 新建项目（苏格拉底）
                if cmd.startswith("new ") or cmd == "new":
                    idea = user_input[4:].strip() if len(user_input) > 4 else ""
                    print("\n" + self.handle_new(idea))
                    continue

                parts = user_input.split()

                # 直接创建项目
                if parts[0].lower() == "create" and len(parts) >= 3:
                    project_name = parts[1]
                    goal_short = " ".join(parts[2:])
                    print("\n" + self.handle_create_project({
                        "name": project_name,
                        "goal_short": goal_short,
                        "goal_long": goal_short
                    }))
                    continue

                # 创建模块
                if parts[0].lower() == "module" and len(parts) >= 2:
                    module_name = parts[1]
                    module_goal = " ".join(parts[2:]) if len(parts) > 2 else module_name
                    print("\n" + self.handle_create_module({
                        "project_name": self.current_project,
                        "module_name": module_name,
                        "module_goal": module_goal
                    }))
                    continue

                # 继续项目
                if cmd.startswith("continue "):
                    project = user_input[9:].strip()
                    print("\n" + self.handle_continue(project))
                    continue
                if cmd == "continue":
                    print("\n" + self.handle_continue())
                    continue

                # 使用项目
                if parts[0].lower() == "use" and len(parts) >= 2:
                    self.current_project = parts[1]
                    print(f"\n已切换到项目: {self.current_project}")
                    continue

                # 完成挑战
                if cmd.startswith("complete "):
                    try:
                        challenge_id = int(user_input.split()[1])
                    except ValueError:
                        challenge_id = 1
                    print("\n" + self.handle_complete_challenge(
                        self.current_project or "", 1, challenge_id))
                    continue

                # 状态
                if cmd == "status":
                    if self.current_project:
                        from tools.pulse_tools import get_project_status
                        print("\n" + get_project_status(self.current_project))
                    else:
                        print("\n请先指定项目：use 项目名")
                    continue

                # 普通对话
                print("\n" + self.chat(user_input))

            except KeyboardInterrupt:
                print("\n\n再见！继续学习，下次见！👋")
                break
            except Exception as e:
                print(f"\n❌ 错误: {str(e)}")


def main():
    """主入口"""
    cli = PulseCLI()
    cli.run()


if __name__ == "__main__":
    main()
