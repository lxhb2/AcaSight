#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pulse Learning System - Simple test script
Test Ollama connection using ollama library directly
"""
import os
import sys

# Set encoding to UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Set working directory
script_dir = os.path.dirname(os.path.abspath(__file__))
projects_dir = os.path.dirname(script_dir)
os.chdir(projects_dir)
sys.path.insert(0, projects_dir)


def test_ollama():
    """Test Ollama connection using ollama library"""
    print("=" * 50)
    print("Test 1: Ollama Connection (direct)")
    print("=" * 50)
    
    try:
        import ollama
        
        model = os.getenv("MODEL", "qwen3.5:4b")
        ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        
        print(f"Model: {model}")
        print(f"URL: {ollama_url}")
        
        # Test with ollama library
        response = ollama.chat(
            model=model,
            messages=[
                {
                    'role': 'user',
                    'content': 'Hello, please introduce yourself in one sentence'
                }
            ]
        )
        
        print(f"\n[OK] Ollama connection successful!")
        print(f"Response: {response['message']['content'][:200]}...")
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Ollama connection failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_langchain():
    """Test using langchain with manual connection"""
    print("\n" + "=" * 50)
    print("Test 2: LangChain Ollama")
    print("=" * 50)
    
    try:
        # Import langchain without the verbose issue
        import langchain
        # Force older langchain to not use verbose
        if not hasattr(langchain, 'verbose'):
            langchain.verbose = False
        
        from langchain_ollama import ChatOllama
        
        model = os.getenv("MODEL", "qwen3.5:4b")
        ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        
        print(f"Model: {model}")
        print(f"URL: {ollama_url}")
        
        llm = ChatOllama(
            model=model,
            base_url=ollama_url,
            temperature=0.7,
        )
        
        response = llm.invoke("Hello")
        
        print(f"\n[OK] LangChain Ollama works!")
        return True
        
    except Exception as e:
        print(f"\n[ERROR] LangChain Ollama failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("Pulse Learning System - Local Test")
    print("=" * 50)
    
    # Test Ollama direct
    if not test_ollama():
        print("\nPlease ensure Ollama is running and model is downloaded:")
        print("  ollama pull qwen3.5:4b")
        print("  ollama run qwen3.5:4b")
        sys.exit(1)
    
    # Test LangChain
    test_langchain()
    
    print("\n" + "=" * 50)
    print("Test Complete!")
    print("=" * 50)


if __name__ == "__main__":
    main()
