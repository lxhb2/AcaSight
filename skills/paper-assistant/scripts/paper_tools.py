#!/usr/bin/env python3
"""
论文摘要和润色工具
支持多模型: OpenAI GPT, Anthropic Claude, Groq, Ollama
"""
import argparse
import json
import sys
import os
from pathlib import Path

# 尝试导入必要的库
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


# ============== 模型配置 ==============
DEFAULT_MODEL = "gpt-4"
MODEL_CONFIG = {
    # OpenAI
    "gpt-4": {"provider": "openai", "model": "gpt-4"},
    "gpt-3.5": {"provider": "openai", "model": "gpt-3.5-turbo"},
    # Anthropic
    "claude-3": {"provider": "anthropic", "model": "claude-3-opus-20240229"},
    "claude-3-sonnet": {"provider": "anthropic", "model": "claude-3-sonnet-20240229"},
    # Groq
    "groq-llama": {"provider": "groq", "model": "llama3-70b-8192"},
}


def load_config():
    """加载配置文件"""
    config_path = Path(__file__).parent.parent / "papers" / "config.json"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def call_model(text, task, model=None, api_key=None):
    """调用语言模型"""
    config = load_config()
    model = model or config.get("default_model", DEFAULT_MODEL)
    
    # 获取模型配置
    if model in MODEL_CONFIG:
        provider = MODEL_CONFIG[model]["provider"]
        model_name = MODEL_CONFIG[model]["model"]
    else:
        provider = "openai"
        model_name = model
    
    # 获取 API key
    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY") or config.get("api_keys", {}).get(provider)
    
    # 构建提示词
    system_prompts = {
        "summarize": "你是一个专业的学术论文摘要助手。请为论文生成简洁、准确的中文摘要，突出研究方法和主要发现。",
        "polish": "你是一个专业的学术论文编辑。请对论文片段进行学术化润色，保持原意，提升表达质量。",
        "translate_en": "你是一个专业的学术翻译专家。请将以下中文论文片段翻译为专业的英文学术论文。",
        "translate_cn": "你是一个专业的学术翻译专家。请将以下英文论文片段翻译为流畅的中文学术论文。",
        "outline": "你是一个专业的学术论文写作助手。请根据研究主题生成详细的论文大纲，包括摘要、引言、方法、结果、讨论和结论等部分。",
        "abstract_en": "你是一个专业的学术论文助手。请为论文生成专业的英文摘要（Abstract），包含研究背景、目的、方法、结果和结论。",
    }
    
    user_prompt = f"任务: {task}\n\n内容:\n{text}"
    
    # 调用对应 provider
    if provider == "openai" and OPENAI_AVAILABLE and api_key:
        return call_openai(api_key, model_name, system_prompts.get(task, ""), user_prompt)
    elif provider == "anthropic" and ANTHROPIC_AVAILABLE and api_key:
        return call_anthropic(api_key, model_name, system_prompts.get(task, ""), user_prompt)
    else:
        return {"error": f"需要配置 {provider} API key 或安装对应库"}


def call_openai(api_key, model, system_prompt, user_prompt):
    """调用 OpenAI API"""
    client = openai.OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7,
        max_tokens=2000
    )
    return {"result": response.choices[0].message.content}


def call_anthropic(api_key, model, system_prompt, user_prompt):
    """调用 Anthropic Claude API"""
    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=2000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}]
    )
    return {"result": response.content[0].text}


# ============== 命令行工具 ==============

def summarize(text, model=None):
    """生成摘要"""
    return call_model(text, "summarize", model)


def polish(text, model=None):
    """润色论文"""
    return call_model(text, "polish", model)


def translate(text, direction="en-cn", model=None):
    """翻译论文"""
    task = "translate_en" if direction == "en-cn" else "translate_cn"
    return call_model(text, task, model)


def generate_outline(topic, model=None):
    """生成论文大纲"""
    return call_model(topic, "outline", model)


def main():
    parser = argparse.ArgumentParser(description="论文辅助工具")
    parser.add_argument("--task", "-t", required=True, 
                        choices=["summarize", "polish", "translate", "outline"],
                        help="任务类型")
    parser.add_argument("--text", help="输入文本")
    parser.add_argument("--file", "-f", help="输入文件")
    parser.add_argument("--model", "-m", help="模型名称")
    parser.add_argument("--direction", "-d", choices=["en-cn", "cn-en"], default="en-cn",
                        help="翻译方向")
    parser.add_argument("--output", "-o", help="输出文件")
    
    args = parser.parse_args()
    
    # 读取输入
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            text = f.read()
    else:
        text = args.text or sys.stdin.read()
    
    if not text.strip():
        print("错误: 请提供输入文本或文件")
        sys.exit(1)
    
    # 执行任务
    if args.task == "summarize":
        result = summarize(text, args.model)
    elif args.task == "polish":
        result = polish(text, args.model)
    elif args.task == "translate":
        result = translate(text, args.direction, args.model)
    elif args.task == "outline":
        result = generate_outline(text, args.model)
    
    # 输出结果
    if "error" in result:
        print(f"错误: {result['error']}")
        sys.exit(1)
    else:
        output = result.get("result", "")
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output)
            print(f"结果已保存到: {args.output}")
        else:
            print(output)


if __name__ == "__main__":
    main()
