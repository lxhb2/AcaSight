#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pulse Learning System - Ollama API wrapper
Simple HTTP-based Ollama client for Pulse Learning Agent
"""
import json
import requests
from typing import List, Dict, Any, Optional


class OllamaClient:
    """Simple Ollama API client"""
    
    def __init__(self, model: str = "qwen3.5:4b", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        self.api_chat = f"{base_url}/api/chat"
        self.api_tags = f"{base_url}/api/tags"
    
    def chat(self, messages: List[Dict[str, str]], 
             temperature: float = 0.7,
             stream: bool = False,
             **kwargs) -> Dict[str, Any]:
        """Send chat request to Ollama"""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
            **kwargs
        }
        response = requests.post(self.api_chat, json=payload, timeout=120)
        response.raise_for_status()
        return response.json()
    
    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate completion (non-chat mode)"""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            **kwargs
        }
        response = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=120)
        response.raise_for_status()
        return response.json()
    
    def list_models(self) -> List[str]:
        """List available models"""
        response = requests.get(self.api_tags, timeout=10)
        response.raise_for_status()
        models = response.json()
        return [m["name"] for m in models.get("models", [])]


def test_connection():
    """Test Ollama connection"""
    print("Testing Ollama connection...")
    client = OllamaClient()
    
    # List models
    models = client.list_models()
    print(f"Available models: {models}")
    
    # Simple chat test
    response = client.chat([
        {"role": "user", "content": "Say hello in one sentence"}
    ])
    
    print(f"\nResponse: {response['message']['content']}")
    print("\n[OK] Ollama connection successful!")


if __name__ == "__main__":
    test_connection()
