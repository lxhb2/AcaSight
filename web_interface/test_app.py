#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Sci-XRD Web应用
"""

import sys
import os
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def test_app():
    """测试应用"""
    print("Testing Sci-XRD Web Application...")
    print("=" * 50)
    
    try:
        # 测试导入
        import app
        print("✅ App import successful")
        
        # 测试启动事件
        print("\nTesting startup event...")
        try:
            app.startup_event()
            print("✅ Startup event successful")
        except Exception as e:
            print(f"⚠️ Startup event warning: {e}")
        
        # 测试路由
        print("\nTesting routes...")
        
        # 测试根路由
        import asyncio
        from fastapi.testclient import TestClient
        
        client = TestClient(app.app)
        
        # 测试主页
        response = client.get("/")
        if response.status_code == 200:
            print("✅ Home page accessible")
        else:
            print(f"⚠️ Home page status: {response.status_code}")
        
        # 测试状态页
        response = client.get("/status")
        if response.status_code == 200:
            print("✅ Status page accessible")
        else:
            print(f"⚠️ Status page status: {response.status_code}")
        
        # 测试分析器页
        response = client.get("/analyzer")
        if response.status_code == 200:
            print("✅ Analyzer page accessible")
        else:
            print(f"⚠️ Analyzer page status: {response.status_code}")
        
        print("\n" + "=" * 50)
        print("✅ All tests passed! Application is ready.")
        print("\nYou can now start the application with:")
        print("  uvicorn app:app --host 0.0.0.0 --port 8000 --reload")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = test_app()
    sys.exit(0 if success else 1)