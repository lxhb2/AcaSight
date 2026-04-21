#!/usr/bin/env python3
import sys, os

# projects/scripts/ -> projects/src/
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

from utils.llm_client import check_ollama_available, check_lmstudio_available, is_online

print("=== 连接检测 ===")
print("Online:", is_online())
print("Ollama (11434):", check_ollama_available())
print("LM Studio (1234):", check_lmstudio_available())
