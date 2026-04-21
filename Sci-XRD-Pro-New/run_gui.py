"""
Sci-XRD-Pro GUI 启动器
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.xrd_gui import main

if __name__ == '__main__':
    main()
