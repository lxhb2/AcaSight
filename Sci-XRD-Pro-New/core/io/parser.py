"""
Sci-XRD Pro - 数据解析与导出模块
统一处理各种格式的 XRD 数据
"""

import os
import re
import numpy as np
from pathlib import Path
from typing import Tuple, Dict, List, Optional


class XRDDataParser:
    """
    XRD 数据解析器
    支持格式：RAW (1.01/4.00), TXT, CSV, DAT, XRDML
    """
    
    def __init__(self):
        self.current_file = None
        self.angles = None
        self.intensities = None
        self.metadata = {}
        
    def parse(self, filepath: str) -> Tuple[np.ndarray, np.ndarray]:
        """
        解析 XRD 数据文件
        
        Args:
            filepath: 文件路径
            
        Returns:
            (angles, intensities) 元组
        """
        filepath = Path(filepath)
        self.current_file = filepath
        
        if not filepath.exists():
            raise FileNotFoundError(f"文件不存在：{filepath}")
        
        ext = filepath.suffix.lower()
        
        if ext == '.raw':
            return self._parse_raw(filepath)
        elif ext == '.txt':
            return self._parse_txt(filepath)
        elif ext == '.csv':
            return self._parse_csv(filepath)
        elif ext == '.dat':
            return self._parse_dat(filepath)
        elif ext == '.xrdml':
            return self._parse_xrdml(filepath)
        else:
            # 尝试自动检测格式
            return self._parse_auto(filepath)
    
    def _parse_raw(self, filepath: Path) -> Tuple[np.ndarray, np.ndarray]:
        """解析 Bruker RAW 格式（支持 RAW 1.01 和 RAW 4.00）"""
        try:
            # 使用专用的 Bruker RAW 解析器
            from .bruker_raw_parser import BrukerRAWParser
            
            parser = BrukerRAWParser()
            angles, intensities, metadata = parser.parse(str(filepath))
            
            # 保存元数据
            self.metadata.update(metadata)
            
            return angles, intensities
            
        except Exception as e:
            print(f"RAW 解析错误：{e}")
            # 备用解析方法
            return self._parse_raw_fallback(filepath)
    
    def _parse_raw_fallback(self, filepath: Path) -> Tuple[np.ndarray, np.ndarray]:
        """备用 RAW 解析方法"""
        try:
            with open(filepath, 'rb') as f:
                header = f.read(512)
                header_text = header.decode('latin-1', errors='ignore')
                
                # 检测格式
                is_bruker = header_text.startswith('RAW')
                
                if is_bruker:
                    # Bruker 二进制格式
                    f.seek(512)
                    data_bytes = f.read()
                    
                    # 尝试 16 位整数（RAW 1.01 常用）
                    n_points = len(data_bytes) // 2
                    if n_points > 0:
                        intensities = np.frombuffer(data_bytes[:n_points*2], dtype=np.int16)
                        
                        # 标准扫描参数
                        start_angle = 5.0
                        end_angle = 80.0
                        step = 0.02
                        
                        n_expected = int((end_angle - start_angle) / step) + 1
                        
                        # 截取或填充
                        if len(intensities) > n_expected:
                            intensities = intensities[:n_expected]
                        
                        angles = np.arange(len(intensities)) * step + start_angle
                        
                        self.metadata['format'] = 'Bruker RAW (binary, fallback)'
                        self.metadata['n_points'] = len(angles)
                        
                        return angles, intensities
                
                # 尝试文本格式
                f.seek(0)
                content = f.read().decode('utf-8', errors='ignore')
                return self._parse_text_content(content)
                
        except Exception as e:
            print(f"RAW fallback error: {e}")
            return np.array([]), np.array([])
    
    def _parse_txt(self, filepath: Path) -> Tuple[np.ndarray, np.ndarray]:
        """解析 TXT 格式"""
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        return self._parse_text_content(content)
    
    def _parse_csv(self, filepath: Path) -> Tuple[np.ndarray, np.ndarray]:
        """解析 CSV 格式"""
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        return self._parse_text_content(content)
    
    def _parse_dat(self, filepath: Path) -> Tuple[np.ndarray, np.ndarray]:
        """解析 DAT 格式"""
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        return self._parse_text_content(content)
    
    def _parse_xrdml(self, filepath: Path) -> Tuple[np.ndarray, np.ndarray]:
        """解析 Panalytical XRDML 格式"""
        try:
            import xml.etree.ElementTree as ET
            
            tree = ET.parse(filepath)
            root = tree.getroot()
            
            # 查找数据
            angles = []
            intensities = []
            
            # XRDML 格式通常是 XML
            for elem in root.iter():
                if 'x' in elem.tag or 'angle' in elem.tag.lower():
                    try:
                        angles.append(float(elem.text))
                    except:
                        pass
                elif 'y' in elem.tag or 'intensity' in elem.tag.lower():
                    try:
                        intensities.append(float(elem.text))
                    except:
                        pass
            
            if len(angles) > 0 and len(intensities) > 0:
                self.metadata['format'] = 'XRDML (XML)'
                return np.array(angles), np.array(intensities)
            
        except Exception as e:
            print(f"XRDML parse error: {e}")
        
        # 备用：当作文本解析
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        return self._parse_text_content(content)
    
    def _parse_auto(self, filepath: Path) -> Tuple[np.ndarray, np.ndarray]:
        """自动检测格式并解析"""
        # 读取文件内容
        with open(filepath, 'rb') as f:
            content = f.read()
        
        # 尝试检测格式
        # 1. 检查是否包含 XML（XRDML）
        if b'<?xml' in content or b'<XRDML' in content:
            return self._parse_xrdml(filepath)
        
        # 2. 检查是否包含 Bruker 标记
        if content[:10].startswith(b'RAW'):
            return self._parse_raw(filepath)
        
        # 3. 尝试文本格式
        try:
            text = content.decode('utf-8', errors='ignore')
            return self._parse_text_content(text)
        except:
            pass
        
        # 4. 默认返回空
        return np.array([]), np.array([])
    
    def _parse_text_content(self, content: str) -> Tuple[np.ndarray, np.ndarray]:
        """解析文本内容"""
        angles = []
        intensities = []
        
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # 跳过空行和注释
            if not line or line.startswith(';') or line.startswith('#'):
                continue
            
            # 跳过非数据行（包含字母但不是科学计数法）
            if re.search(r'[a-zA-Z]', line) and 'e' not in line.lower() and 'E' not in line:
                continue
            
            # 尝试解析
            # 支持分隔符：空格、制表符、逗号
            parts = re.split(r'[\s,]+', line)
            
            if len(parts) >= 2:
                try:
                    angle = float(parts[0])
                    intensity = float(parts[1])
                    
                    # 验证角度范围
                    if 0.0 <= angle <= 180.0:
                        angles.append(angle)
                        intensities.append(intensity)
                except ValueError:
                    pass
        
        if len(angles) > 0:
            self.metadata['n_points'] = len(angles)
            self.metadata['start_angle'] = min(angles)
            self.metadata['end_angle'] = max(angles)
            
            if len(angles) > 1:
                self.metadata['step'] = np.mean(np.diff(angles))
            
            return np.array(angles), np.array(intensities)
        
        return np.array([]), np.array([])
    
    def save(self, filepath: str, format: str = 'txt') -> bool:
        """
        保存数据
        
        Args:
            filepath: 输出文件路径
            format: 输出格式 ('txt', 'csv', 'origin')
            
        Returns:
            是否成功
        """
        if self.angles is None or self.intensities is None:
            return False
        
        try:
            if format == 'txt':
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write('2-Theta\tIntensity\n')
                    for angle, intensity in zip(self.angles, self.intensities):
                        f.write(f'{angle:.4f}\t{intensity:.1f}\n')
            
            elif format == 'csv':
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write('2-Theta,Intensity\n')
                    for angle, intensity in zip(self.angles, self.intensities):
                        f.write(f'{angle:.4f},{intensity:.1f}\n')
            
            elif format == 'origin':
                # Origin 格式：多列数据
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write('[Data]\n')
                    f.write('2-Theta\tIntensity\n')
                    for angle, intensity in zip(self.angles, self.intensities):
                        f.write(f'{angle:.4f}\t{intensity:.1f}\n')
            
            return True
            
        except Exception as e:
            print(f'Save error: {e}')
            return False


class XRDExporter:
    """
    XRD 数据导出器
    支持导出为各种格式
    """
    
    def __init__(self, angles: np.ndarray, intensities: np.ndarray, peaks: List = None):
        self.angles = angles
        self.intensities = intensities
        self.peaks = peaks or []
    
    def export_to_txt(self, filepath: str) -> bool:
        """导出为 TXT 格式"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('2-Theta\tIntensity\n')
                for angle, intensity in zip(self.angles, self.intensities):
                    f.write(f'{angle:.4f}\t{intensity:.1f}\n')
            return True
        except Exception as e:
            print(f'Export TXT error: {e}')
            return False
    
    def export_to_csv(self, filepath: str) -> bool:
        """导出为 CSV 格式"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('2-Theta,Intensity\n')
                for angle, intensity in zip(self.angles, self.intensities):
                    f.write(f'{angle:.4f},{intensity:.1f}\n')
            return True
        except Exception as e:
            print(f'Export CSV error: {e}')
            return False
    
    def export_to_origin(self, filepath: str) -> bool:
        """导出为 Origin 格式"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('[Data]\n')
                f.write('2-Theta\tIntensity\n')
                for angle, intensity in zip(self.angles, self.intensities):
                    f.write(f'{angle:.4f}\t{intensity:.1f}\n')
                
                # 如果有峰数据，添加峰标记
                if self.peaks:
                    f.write('\n[Peaks]\n')
                    f.write('Position\tIntensity\tFWHM\n')
                    for peak in self.peaks:
                        pos = getattr(peak, 'position', 0)
                        inten = getattr(peak, 'intensity', 0)
                        fwhm = getattr(peak, 'fwhm', 0)
                        f.write(f'{pos:.4f}\t{inten:.1f}\t{fwhm:.4f}\n')
            return True
        except Exception as e:
            print(f'Export Origin error: {e}')
            return False
    
    def export_peak_mapping(self, filepath: str, peak_mineral_map: Dict = None) -> bool:
        """导出峰 - 矿物映射表"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('峰位 (2θ)\td 间距 (Å)\t强度\t矿物标识\n')
                f.write('-' * 50 + '\n')
                
                for peak in self.peaks:
                    pos = getattr(peak, 'position', 0)
                    d_spacing = getattr(peak, 'd_spacing', 0)
                    inten = getattr(peak, 'intensity', 0)
                    label = getattr(peak, 'label', '-')
                    f.write(f'{pos:.3f}\t{d_spacing:.4f}\t{inten:.0f}\t{label}\n')
            return True
        except Exception as e:
            print(f'Export peak mapping error: {e}')
            return False
