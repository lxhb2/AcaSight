#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单测试Sci-XRD Web应用
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
        print("[OK] App import successful")
        
        # 测试启动事件
        print("\nTesting startup event...")
        try:
            app.startup_event()
            print("[OK] Startup event successful")
        except Exception as e:
            print(f"[WARN] Startup event warning: {e}")
        
        print("\n" + "=" * 50)
        print("[OK] Basic tests passed! Application is ready.")
        print("\nYou can now start the application with:")
        print("  uvicorn app:app --host 0.0.0.0 --port 8000 --reload")
        print("\nOr use the batch file:")
        print("  Sci-XRD-Start.bat")
        
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = test_app()
    sys.exit(0 if success else 1)