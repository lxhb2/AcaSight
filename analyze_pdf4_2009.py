#!/usr/bin/env python3
"""
PDF4-2009 数据库结构分析器
解析 InstallShield CAB 文件和 PDF4 数据库格式
"""

import struct
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import zlib


class InstallShieldCABParser:
    """
    解析 InstallShield CAB 文件格式
    
    PDF4-2009 使用 InstallShield 压缩格式
    文件结构：
    - data1.cab: 安装程序文件 (~9MB)
    - data2.cab: 主要数据库文件 (~679MB)  
    - data3.cab: 数据库文件 (~690MB)
    - data4.cab: 数据库文件 (~303MB)
    """
    
    def __init__(self, cab_path: str):
        self.cab_path = Path(cab_path)
        self.files: List[Dict] = []
        
    def analyze_header(self) -> Dict:
        """分析 CAB 文件头"""
        with open(self.cab_path, 'rb') as f:
            # 读取前 512 字节
            header = f.read(512)
            
        result = {
            'file': str(self.cab_path),
            'size': self.cab_path.stat().st_size,
            'header_hex': header[:64].hex(),
            'header_ascii': self._safe_ascii(header[:64]),
        }
        
        # 检查魔数
        if header[:4] == b'ISc(':
            result['format'] = 'InstallShield CAB (压缩)'
            result['signature'] = 'ISc('
        elif header[:4] == b'MSCF':
            result['format'] = 'Microsoft CAB'
            result['signature'] = 'MSCF'
        else:
            result['format'] = 'Unknown'
            result['signature'] = header[:4].hex()
            
        return result
    
    @staticmethod
    def _safe_ascii(data: bytes) -> str:
        """将字节转换为可打印 ASCII"""
        return ''.join(chr(b) if 32 <= b < 127 else '.' for b in data)
    
    def extract_file_list(self) -> List[Dict]:
        """
        尝试提取文件列表
        InstallShield CAB 格式复杂，这里做基础分析
        """
        files = []
        
        with open(self.cab_path, 'rb') as f:
            data = f.read()
            
        # 搜索常见的文件签名
        signatures = {
            b'MSI': 'Windows Installer Database',
            b'\xD0\xCF\x11\xE0': 'Microsoft Compound Document (OLE)',
            b'PK\x03\x04': 'ZIP Archive',
            b'%PDF': 'PDF Document',
            b'<?xml': 'XML File',
        }
        
        for sig, desc in signatures.items():
            pos = data.find(sig)
            if pos != -1:
                files.append({
                    'signature': sig.hex(),
                    'description': desc,
                    'offset': pos,
                })
                
        # 搜索字符串表（文件名）
        # InstallShield 通常在特定偏移存储文件名
        for i in range(0, min(len(data) - 100, 100000), 1):
            # 查找可能的文件名模式
            chunk = data[i:i+50]
            if b'.' in chunk and all(32 <= b < 127 or b == 0 for b in chunk[:20]):
                try:
                    text = chunk.decode('ascii', errors='ignore')
                    if '.' in text and len(text) > 4:
                        # 可能是文件名
                        pass
                except:
                    pass
                    
        return files


class PDF4DatabaseAnalyzer:
    """
    PDF4-2009 数据库格式分析器
    
    PDF4 数据库通常包含：
    - PDF 卡片数据（d-spacing, I/Icor, hkl, 晶胞参数等）
    - 矿物/化合物名称和化学式
    - 晶体学信息
    - 质量标记（* = 高质量，i = 已指标化）
    """
    
    # PDF4 标准字段
    PDF_FIELDS = {
        'PDF_NO': 'PDF编号 (如 46-1045)',
        'NAME': '矿物/化合物名称',
        'FORMULA': '化学式',
        'D_SPACINGS': 'd-spacing 列表 [(d, I%), ...]',
        'CRYSTAL_SYSTEM': '晶系',
        'SPACE_GROUP': '空间群',
        'CELL_PARAMS': '晶胞参数 {a, b, c, alpha, beta, gamma}',
        'RIR': '参比强度 I/Icor',
        'QUALITY': '质量标记 (*, i, O 等)',
        'REFERENCES': '参考文献',
    }
    
    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.database_info = {}
        
    def scan_directory(self) -> Dict:
        """扫描目录结构"""
        result = {
            'root': str(self.data_dir),
            'total_size_mb': 0,
            'files': [],
        }
        
        for file_path in self.data_dir.rglob('*'):
            if file_path.is_file():
                size_mb = file_path.stat().st_size / (1024 * 1024)
                result['total_size_mb'] += size_mb
                result['files'].append({
                    'path': str(file_path.relative_to(self.data_dir)),
                    'size_mb': round(size_mb, 2),
                    'ext': file_path.suffix.lower(),
                })
                
        result['total_size_mb'] = round(result['total_size_mb'], 2)
        result['file_count'] = len(result['files'])
        
        # 按扩展名统计
        ext_stats = {}
        for f in result['files']:
            ext = f['ext'] or '(no ext)'
            ext_stats[ext] = ext_stats.get(ext, 0) + 1
        result['extension_stats'] = ext_stats
        
        return result
    
    def analyze_cab_contents(self) -> Dict:
        """分析 CAB 文件内容"""
        cab_dir = self.data_dir / 'Setup'
        
        if not cab_dir.exists():
            return {'error': 'Setup directory not found'}
            
        cabs = list(cab_dir.glob('*.cab'))
        
        analysis = {
            'cab_files': [],
            'total_cab_size_mb': 0,
        }
        
        for cab in cabs:
            parser = InstallShieldCABParser(str(cab))
            header = parser.analyze_header()
            analysis['cab_files'].append(header)
            analysis['total_cab_size_mb'] += header['size'] / (1024 * 1024)
            
        analysis['total_cab_size_mb'] = round(analysis['total_cab_size_mb'], 2)
        
        return analysis


def main():
    """主函数"""
    pdf4_path = r"G:\迅雷云盘\1.PDF4-2009"
    
    print("=" * 70)
    print("PDF4-2009 数据库结构分析器")
    print("=" * 70)
    
    analyzer = PDF4DatabaseAnalyzer(pdf4_path)
    
    # 1. 扫描目录结构
    print("\n[1] 目录结构扫描")
    print("-" * 70)
    dir_info = analyzer.scan_directory()
    print(f"根目录: {dir_info['root']}")
    print(f"总文件数: {dir_info['file_count']}")
    print(f"总大小: {dir_info['total_size_mb']} MB")
    print("\n文件类型统计:")
    for ext, count in sorted(dir_info['extension_stats'].items(), key=lambda x: -x[1]):
        print(f"  {ext:12s}: {count:3d} 个文件")
    
    # 2. 分析 CAB 文件
    print("\n[2] CAB 安装包分析")
    print("-" * 70)
    cab_info = analyzer.analyze_cab_contents()
    
    if 'error' in cab_info:
        print(f"错误: {cab_info['error']}")
    else:
        print(f"CAB 文件总数: {len(cab_info['cab_files'])}")
        print(f"CAB 总大小: {cab_info['total_cab_size_mb']} MB")
        print("\n详细列表:")
        for cab in cab_info['cab_files']:
            size_mb = cab['size'] / (1024 * 1024)
            print(f"\n  {Path(cab['file']).name}")
            print(f"    大小: {size_mb:.1f} MB")
            print(f"    格式: {cab['format']}")
            print(f"    签名: {cab['signature']}")
            print(f"    头部(HEX): {cab['header_hex'][:64]}...")
    
    # 3. 输出结论
    print("\n[3] 分析结论")
    print("-" * 70)
    print("""
PDF4-2009 数据库当前状态：
  - 这是一个 InstallShield 安装包，需要安装后才能使用
  - 主要数据文件位于 data2.cab, data3.cab, data4.cab（约 1.7GB）
  - 安装后通常位于 C:\Program Files\ICDD\PDF-4+ 2009\
  
数据库文件格式：
  - 安装后的数据库通常是 Microsoft Access (.mdb) 或 SQL Server 格式
  - 包含 PDF 卡片、矿物数据、晶体学信息等
  
要使用此数据库：
  1. 运行 Setup\setup.exe 安装程序
  2. 或使用破解文件（Crack\OEMStartup.dll）绕过授权
  3. 安装后导出数据为文本/CSV 格式供 Sci-XRD-Pro 使用
""")
    
    print("=" * 70)
    
    # 保存分析报告
    report_path = Path(pdf4_path) / "database_analysis_report.txt"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("PDF4-2009 数据库结构分析报告\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"分析时间: 2026-04-13\n")
        f.write(f"数据库路径: {pdf4_path}\n\n")
        f.write(f"总文件数: {dir_info['file_count']}\n")
        f.write(f"总大小: {dir_info['total_size_mb']} MB\n\n")
        f.write("文件列表:\n")
        for file in sorted(dir_info['files'], key=lambda x: -x['size_mb'])[:50]:
            f.write(f"  {file['path']}: {file['size_mb']} MB\n")
            
    print(f"\n分析报告已保存: {report_path}")


if __name__ == '__main__':
    main()
