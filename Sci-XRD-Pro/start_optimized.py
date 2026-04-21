#!/usr/bin/env python3
"""
Sci-XRD Pro Phase 4: 优化界面版启动脚本
"""

import sys
import os
from pathlib import Path
import traceback
import warnings

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def setup_environment():
    """设置环境"""
    # 设置Matplotlib后端
    import matplotlib
    matplotlib.use('Qt5Agg')
    
    # 抑制警告
    warnings.filterwarnings('ignore', category=UserWarning)
    warnings.filterwarnings('ignore', category=FutureWarning)
    
    # 创建必要目录
    directories = ['data', 'exports', 'logs', 'temp', 'config', 'database', 'ai_cache']
    for dir_name in directories:
        dir_path = project_root / dir_name
        dir_path.mkdir(exist_ok=True)


def check_dependencies():
    """检查依赖包"""
    required_packages = {
        'PyQt6': 'PyQt6',
        'numpy': 'numpy',
        'scipy': 'scipy',
        'matplotlib': 'matplotlib',
        'pandas': 'pandas',
        'chardet': 'chardet'
    }
    
    missing_packages = []
    
    for package_name, import_name in required_packages.items():
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(package_name)
    
    return missing_packages


def main():
    """主函数"""
    print("=" * 60)
    print("Sci-XRD Pro - Phase 4 优化界面版")
    print("Version: 1.0.0 (Modern UI)")
    print("=" * 60)
    
    # 检查依赖
    print("\nChecking dependencies...")
    missing_packages = check_dependencies()
    
    if missing_packages:
        print(f"Error: Missing packages: {', '.join(missing_packages)}")
        input("\nPress Enter to exit...")
        return 1
    
    print("OK: All dependencies installed")
    
    # 设置环境
    print("\nSetting up environment...")
    setup_environment()
    print("OK: Environment ready")
    
    # 启动应用程序
    print("\nLaunching application...")
    
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import Qt
        
        # 应用现代化主题
        from gui.modern_theme import ModernTheme
        
        # 创建应用程序
        app = QApplication(sys.argv)
        
        # 应用现代化主题
        ModernTheme.apply_theme(app)
        
        # 设置应用程序信息
        app.setApplicationName("Sci-XRD Pro")
        app.setOrganizationName("QClaw")
        app.setApplicationVersion("1.0.0")
        app.setApplicationDisplayName("Sci-XRD Pro")
        
        # 导入并创建主窗口
        from gui.enhanced_main_window import EnhancedXRDWindow
        
        # 创建主窗口
        main_window = EnhancedXRDWindow()
        main_window.setWindowTitle("Sci-XRD Pro - Professional XRD Analysis Platform v1.0.0")
        main_window.show()
        
        print("OK: Application launched successfully")
        print("\n" + "=" * 60)
        print("Modern UI Features:")
        print("- Clean, professional design")
        print("- Responsive color scheme")
        print("- Smooth animations")
        print("- Intuitive layout")
        print("=" * 60)
        print("\nQuick Start:")
        print("1. Load data: File -> Open")
        print("2. Test data: Click 'Load Test Data' button")
        print("3. Analyze: Click 'Start Analysis' button")
        print("4. Export: File -> Export Results")
        print("=" * 60)
        
        # 运行应用程序
        return_code = app.exec()
        
        return return_code
        
    except Exception as e:
        print(f"\nError: Launch failed: {e}")
        traceback.print_exc()
        input("\nPress Enter to exit...")
        return 1


if __name__ == '__main__':
    sys.exit(main())