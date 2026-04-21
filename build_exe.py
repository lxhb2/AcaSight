#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sci-XRD 系统打包脚本
将系统打包为可执行文件
"""

import os
import sys
import shutil
from pathlib import Path
import subprocess
import json

def build_executable():
    """构建可执行文件"""
    print("""
    ╔══════════════════════════════════════════════════════╗
    ║            Sci-XRD 系统打包工具                      ║
    ╠══════════════════════════════════════════════════════╣
    ║ 版本: 2.0.0                                         ║
    ║ 功能: 打包为可执行文件                              ║
    ╚══════════════════════════════════════════════════════╝
    """)
    
    workspace = Path(r"C:\Users\Administrator\.qclaw\workspace")
    
    print("1. 检查系统状态...")
    
    # 检查必要文件
    required_files = [
        workspace / "web_interface" / "app.py",
        workspace / "web_interface" / "start_server.py",
        workspace / "web_interface" / "config.py",
        workspace / "启动Sci-XRD系统.bat",
        workspace / "启动Sci-XRD系统.ps1"
    ]
    
    missing_files = []
    for file in required_files:
        if not file.exists():
            missing_files.append(str(file))
    
    if missing_files:
        print("❌ 缺少必要文件:")
        for file in missing_files:
            print(f"   - {file}")
        print("请先完成系统构建。")
        return False
    
    print("✅ 所有必要文件都存在")
    
    # 创建打包目录
    print("\n2. 创建打包目录...")
    build_dir = workspace / "build"
    dist_dir = workspace / "dist"
    
    # 清理旧的构建文件
    for dir_path in [build_dir, dist_dir]:
        if dir_path.exists():
            shutil.rmtree(dir_path)
    
    build_dir.mkdir(exist_ok=True)
    dist_dir.mkdir(exist_ok=True)
    
    print(f"✅ 打包目录: {build_dir}")
    print(f"✅ 输出目录: {dist_dir}")
    
    # 创建启动脚本
    print("\n3. 创建启动脚本...")
    
    # 主启动脚本
    main_script = build_dir / "sci_xrd_launcher.py"
    main_script_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sci-XRD 系统启动器 (可执行文件版本)
"""

import os
import sys
import webbrowser
import threading
import time
from pathlib import Path
import subprocess

def start_system():
    """启动系统"""
    print("\\n" + "="*60)
    print("Sci-XRD 智能分析系统 v2.0.0")
    print("="*60)
    
    # 获取当前目录
    current_dir = Path(sys.executable).parent if hasattr(sys, 'frozen') else Path(__file__).parent
    print(f"工作目录: {current_dir}")
    
    # 检查Python
    try:
        import fastapi
        print("✅ FastAPI已安装")
    except ImportError:
        print("❌ FastAPI未安装，正在安装...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "fastapi", "uvicorn[standard]"])
            print("✅ 依赖安装完成")
        except Exception as e:
            print(f"❌ 依赖安装失败: {e}")
            input("按Enter键退出...")
            return
    
    # 启动Web服务
    print("\\n启动Web服务...")
    print("服务地址: http://localhost:8000")
    print("API文档: http://localhost:8000/docs")
    print("按 Ctrl+C 停止服务")
    print("="*60)
    
    # 打开浏览器
    try:
        webbrowser.open("http://localhost:8000")
        print("✅ 浏览器已打开")
    except:
        print("⚠️ 无法自动打开浏览器")
    
    # 启动服务
    web_dir = current_dir / "web_interface"
    if not web_dir.exists():
        print(f"❌ Web目录不存在: {web_dir}")
        input("按Enter键退出...")
        return
    
    os.chdir(web_dir)
    
    try:
        import uvicorn
        uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
    except KeyboardInterrupt:
        print("\\n服务已停止")
    except Exception as e:
        print(f"❌ 服务启动失败: {e}")
    
    input("\\n按Enter键退出...")

if __name__ == "__main__":
    start_system()
'''
    
    with open(main_script, 'w', encoding='utf-8') as f:
        f.write(main_script_content)
    
    print(f"✅ 启动脚本已创建: {main_script}")
    
    # 复制必要文件
    print("\n4. 复制系统文件...")
    
    # 复制web_interface目录
    web_src = workspace / "web_interface"
    web_dst = build_dir / "web_interface"
    
    if web_src.exists():
        shutil.copytree(web_src, web_dst, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        print(f"✅ Web界面已复制: {web_dst}")
    
    # 复制优化工具
    tools_to_copy = [
        "ai_optimizer.py",
        "plot_optimizer.py", 
        "origin_exporter.py",
        "word_report_generator.py"
    ]
    
    for tool in tools_to_copy:
        src = workspace / tool
        if src.exists():
            shutil.copy2(src, build_dir / tool)
            print(f"✅ 工具已复制: {tool}")
    
    # 创建配置文件
    print("\n5. 创建配置文件...")
    
    config_data = {
        "system": {
            "name": "Sci-XRD",
            "version": "2.0.0",
            "build_date": time.strftime("%Y-%m-%d %H:%M:%S")
        },
        "paths": {
            "workspace": str(workspace),
            "database": "F:\\桌面\\pdf2_final_complete.db",
            "web_interface": "web_interface"
        },
        "web": {
            "host": "0.0.0.0",
            "port": 8000,
            "reload": True
        }
    }
    
    config_file = build_dir / "config.json"
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 配置文件已创建: {config_file}")
    
    # 创建说明文件
    print("\n6. 创建说明文件...")
    
    readme_content = """# Sci-XRD 智能分析系统

## 系统简介
Sci-XRD 是一个专业的X射线衍射分析系统，集成了智能分析、批量处理、AI推荐和专业图表生成功能。

## 系统要求
- Windows 7/8/10/11
- Python 3.8+
- 4GB RAM (推荐8GB)
- 1GB 可用磁盘空间

## 安装说明
1. 解压文件到任意目录
2. 运行 `Sci-XRD.exe` 启动系统
3. 系统将自动打开浏览器访问 http://localhost:8000

## 主要功能
1. **单文件分析** - 上传XRD文件进行智能分析
2. **批量处理** - 同时处理多个XRD文件
3. **AI推荐** - 智能参数推荐和结果解释
4. **专业图表** - 出版级图表输出
5. **多格式导出** - 支持Origin、Word、Excel等格式

## 使用说明
1. **启动系统**: 双击 `Sci-XRD.exe`
2. **上传文件**: 在Web界面中上传XRD数据文件
3. **开始分析**: 配置参数后开始分析
4. **查看结果**: 查看图表、表格和AI分析
5. **导出结果**: 导出为需要的格式

## 技术支持
- 系统版本: 2.0.0
- 技术支持: QClaw AI Assistant
- 生成时间: {build_time}

## 注意事项
1. 首次运行会自动安装Python依赖
2. 确保数据库文件存在: F:\\桌面\\pdf2_final_complete.db
3. 系统需要网络连接以使用AI功能
4. 按Ctrl+C停止Web服务
""".format(build_time=time.strftime("%Y-%m-%d %H:%M:%S"))
    
    readme_file = build_dir / "README.md"
    with open(readme_file, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print(f"✅ 说明文件已创建: {readme_file}")
    
    # 使用PyInstaller打包
    print("\n7. 使用PyInstaller打包...")
    
    try:
        # 检查PyInstaller
        import PyInstaller
        print("✅ PyInstaller已安装")
    except ImportError:
        print("⏳ 安装PyInstaller...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
            print("✅ PyInstaller安装完成")
        except Exception as e:
            print(f"❌ PyInstaller安装失败: {e}")
            print("请手动安装: pip install pyinstaller")
            return False
    
    # 构建spec文件
    spec_content = f"""# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['{main_script}'],
    pathex=[],
    binaries=[],
    datas=[
        ('{web_dst}', 'web_interface'),
        ('{config_file}', '.'),
        ('{readme_file}', '.'),
    ],
    hiddenimports=[
        'fastapi',
        'uvicorn',
        'pydantic',
        'starlette',
        'numpy',
        'scipy',
        'matplotlib',
        'pandas',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=2,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Sci-XRD',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='{workspace / "sci_xrd_icon.ico" if (workspace / "sci_xrd_icon.ico").exists() else ""}',
)
"""
    
    spec_file = build_dir / "sci_xrd.spec"
    with open(spec_file, 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print(f"✅ Spec文件已创建: {spec_file}")
    
    # 执行打包
    print("\n8. 执行打包...")
    print("这可能需要几分钟时间，请耐心等待...")
    
    try:
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--clean",
            "--onefile",
            "--console",
            "--name", "Sci-XRD",
            "--add-data", f"{web_dst};web_interface",
            "--add-data", f"{config_file};.",
            "--add-data", f"{readme_file};.",
            "--hidden-import", "fastapi",
            "--hidden-import", "uvicorn",
            "--hidden-import", "pydantic",
            "--hidden-import", "starlette",
            "--hidden-import", "numpy",
            "--hidden-import", "scipy",
            "--hidden-import", "matplotlib",
            "--hidden-import", "pandas",
            str(main_script)
        ]
        
        # 如果有图标，添加图标参数
        icon_file = workspace / "sci_xrd_icon.ico"
        if icon_file.exists():
            cmd.extend(["--icon", str(icon_file)])
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=build_dir)
        
        if result.returncode == 0:
            print("✅ 打包成功!")
            
            # 复制可执行文件到dist目录
            exe_src = build_dir / "dist" / "Sci-XRD.exe"
            if exe_src.exists():
                exe_dst = dist_dir / "Sci-XRD.exe"
                shutil.copy2(exe_src, exe_dst)
                
                # 复制其他文件
                for file in [config_file, readme_file]:
                    if file.exists():
                        shutil.copy2(file, dist_dir / file.name)
                
                print(f"\\n🎉 可执行文件已生成: {exe_dst}")
                print(f"📁 输出目录: {dist_dir}")
                
                # 显示文件大小
                size_mb = exe_dst.stat().st_size / (1024 * 1024)
                print(f"📦 文件大小: {size_mb:.1f} MB")
                
                return True
            else:
                print("❌ 可执行文件未生成")
                return False
        else:
            print("❌ 打包失败:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ 打包过程出错: {e}")
        return False

def create_installer():
    """创建安装程序"""
    print("\n9. 创建安装程序...")
    
    # 创建NSIS安装脚本
    nsis_script = """!include "MUI2.nsh"

; 基本信息
Name "Sci-XRD 智能分析系统"
OutFile "Sci-XRD-Setup.exe"
InstallDir "$PROGRAMFILES\\Sci-XRD"
RequestExecutionLevel admin

; 界面设置
!define MUI_ABORTWARNING
!define MUI_ICON "sci_xrd_icon.ico"
!define MUI_UNICON "sci_xrd_icon.ico"

; 安装页面
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; 卸载页面
!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

; 语言
!insertmacro MUI_LANGUAGE "SimpChinese"

Section "主程序"
  SetOutPath "$INSTDIR"
  
  ; 复制文件
  File "Sci-XRD.exe"
  File "config.json"
  File "README.md"
  File "LICENSE.txt"
  
  ; 创建开始菜单快捷方式
  CreateDirectory "$SMPROGRAMS\\Sci-XRD"
  CreateShortCut "$SMPROGRAMS\\Sci-XRD\\Sci-XRD.lnk" "$INSTDIR\\Sci-XRD.exe"
  CreateShortCut "$SMPROGRAMS\\Sci-XRD\\卸载.lnk" "$INSTDIR\\uninstall.exe"
  
  ; 创建桌面快捷方式
  CreateShortCut "$DESKTOP\\Sci-XRD.lnk" "$INSTDIR\\Sci-XRD.exe"
  
  ; 写入卸载信息
  WriteUninstaller "$INSTDIR\\uninstall.exe"
  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\Sci-XRD" \
                   "DisplayName" "Sci-XRD 智能分析系统"
  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\Sci-XRD" \
                   "UninstallString" '"$INSTDIR\\uninstall.exe"'
  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\Sci-XRD" \
                   "DisplayVersion" "2.0.0"
  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\Sci-XRD" \
                   "Publisher" "QClaw AI Assistant"
SectionEnd

Section "Python依赖"
  ; 检查Python
  ReadRegStr $0 HKLM "Software\\Python\\PythonCore\\3.8\\InstallPath" ""
  IfErrors python_not_found 0
  Goto python_found
  
  python_not_found:
    MessageBox MB_OK "未找到Python 3.8+，请先安装Python"
    Abort
  
  python_found:
    ; 安装Python依赖
    ExecWait '"$0python.exe" -m pip install fastapi uvicorn[standard] numpy scipy matplotlib pandas'
SectionEnd

Section "创建数据库链接"
  ; 检查数据库文件
  IfFileExists "F:\\桌面\\pdf2_final_complete.db" db_exists 0
    MessageBox MB_OK "数据库文件不存在，部分功能可能受限。$\n请将数据库文件复制到: F:\\桌面\\pdf2_final_complete.db"
  db_exists:
SectionEnd

Section "Uninstall"
  ; 删除文件
  Delete "$INSTDIR\\Sci-XRD.exe"
  Delete "$INSTDIR\\config.json"
  Delete "$INSTDIR\\README.md"
  Delete "$INSTDIR\\LICENSE.txt"
  Delete "$INSTDIR\\uninstall.exe"
  
  ; 删除快捷方式
  Delete "$SMPROGRAMS