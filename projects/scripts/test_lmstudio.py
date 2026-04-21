#!/usr/bin/env python3
import requests, json

url = "http://127.0.0.1:1234/v1/chat/completions"
payload = {
    "model": "qwen2.5-3b-instruct",
    "messages": [{"role": "user", "content": "OK"}],
    "max_tokens": 20
}
try:
    r = requests.post(url, json=payload, timeout=30)
    print("Status:", r.status_code)
    print("Response:", r.text[:500])
except Exception as e:
    print("Error:", e)
