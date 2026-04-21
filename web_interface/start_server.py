#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sci-XRD Web服务启动脚本
"""

import uvicorn
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def main():
    """启动Web服务"""
    print("""
    ╔══════════════════════════════════════════════════════╗
    ║                Sci-XRD Web 服务启动                  ║
    ╠══════════════════════════════════════════════════════╣
    ║ 版本: 2.0.0                                         ║
    ║ 描述: 智能XRD分析平台                               ║
    ║ 作者: QClaw AI Assistant                            ║
    ╚══════════════════════════════════════════════════════╝
    """)
    
    # 配置参数
    config = {
        "app": "web_interface.app:app",
        "host": "0.0.0.0",
        "port": 8000,
        "reload": True,  # 开发模式启用热重载
        "log_level": "info",
        "workers": 4  # 生产环境建议根据CPU核心数设置
    }
    
    print(f"启动配置:")
    print(f"  主机: {config['host']}")
    print(f"  端口: {config['port']}")
    print(f"  工作进程: {config['workers']}")
    print(f"  热重载: {'启用' if config['reload'] else '禁用'}")
    print(f"  日志级别: {config['log_level']}")
    print()
    
    print("服务启动中...")
    print("访问地址:")
    print(f"  http://localhost:{config['port']}")
    print(f"  http://127.0.0.1:{config['port']}")
    print()
    print("API文档:")
    print(f"  http://localhost:{config['port']}/docs")
    print(f"  http://localhost:{config['port']}/redoc")
    print()
    print("按 Ctrl+C 停止服务")
    print("=" * 60)
    
    try:
        # 启动服务
        uvicorn.run(**config)
        
    except KeyboardInterrupt:
        print("\n服务已停止")
    except Exception as e:
        print(f"服务启动失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()