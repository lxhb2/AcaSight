"""
通用RAW数据解析器 - 支持主流XRD仪器格式

支持的仪器：
1. Bruker D8系列
2. PANalytical X'Pert系列
3. Rigaku SmartLab系列
4. Shimadzu XRD-7000系列
5. 通用ASCII格式

特性：
- 自动格式识别
- 元数据提取
- 错误容错处理
- 编码自动检测
"""

import os
import re
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union, Any
import warnings
import chardet
import struct


class RawDataParser:
    """通用RAW数据解析器"""
    
    # 仪器配置文件
    INSTRUMENT_PROFILES = {
        'bruker': {
            'name': 'Bruker D8系列',
            'extensions': ['.raw', '.xrdml', '.txt'],
            'header_patterns': [
                r'BRUKER',
                r'D8',
                r'GADDS'
            ],
            'data_start_markers': ['2THETA', 'Angle', '##'],
            'separator': '\t',
            'angle_col': 0,
            'intensity_col': 1,
            'skip_lines': 5,
            'encoding': 'utf-8',
            'byte_order': 'little'
        },
        'panalytical': {
            'name': 'PANalytical X\'Pert系列',
            'extensions': ['.xrdml', '.raw', '.dat'],
            'header_patterns': [
                r'PANalytical',
                r'X\'Pert',
                r'Emmy'
            ],
            'data_start_markers': ['##', '*', '2Theta'],
            'separator': ',',
            'angle_col': 0,
            'intensity_col': 1,
            'skip_lines': 10,
            'encoding': 'utf-8',
            'byte_order': 'little'
        },
        'rigaku': {
            'name': 'Rigaku SmartLab系列',
            'extensions': ['.raw', '.ras', '.txt'],
            'header_patterns': [
                r'Rigaku',
                r'SmartLab',
                r'Ultima'
            ],
            'data_start_markers': ['*', '2Theta', 'Angle'],
            'separator': ' ',
            'angle_col': 0,
            'intensity_col': 1,
            'skip_lines': 8,
            'encoding': 'utf-8',
            'byte_order': 'little'
        },
        'shimadzu': {
            'name': 'Shimadzu XRD-7000系列',
            'extensions': ['.raw', '.xrd', '.txt'],
            'header_patterns': [
                r'Shimadzu',
                r'XRD-7000',
                r'LabX'
            ],
            'data_start_markers': ['2Theta', 'Angle', '##'],
            'separator': '\t',
            'angle_col': 0,
            'intensity_col': 1,
            'skip_lines': 12,
            'encoding': 'utf-8',
            'byte_order': 'little'
        },
        'generic': {
            'name': '通用ASCII格式',
            'extensions': ['.txt', '.csv', '.dat', '.xy', '.xrd'],
            'header_patterns': [],
            'data_start_markers': [],
            'separator': 'auto',
            'angle_col': 0,
            'intensity_col': 1,
            'skip_lines': 0,
            'encoding': 'auto',
            'byte_order': 'little'
        }
    }
    
    def __init__(self):
        """初始化解析器"""
        self.metadata = {}
        self.raw_data = None
        self.detected_instrument = None
        
    def detect_instrument(self, filepath: Union[str, Path]) -> str:
        """
        自动检测仪器类型
        
        Args:
            filepath: 文件路径
            
        Returns:
            仪器类型标识符
        """
        filepath = Path(filepath)
        
        # 1. 检查文件扩展名
        ext = filepath.suffix.lower()
        
        for instrument, profile in self.INSTRUMENT_PROFILES.items():
            if ext in profile['extensions']:
                self.detected_instrument = instrument
                return instrument
        
        # 2. 读取文件头部内容进行模式匹配
        try:
            with open(filepath, 'rb') as f:
                raw_content = f.read(4096)  # 读取前4KB
            
            # 检测编码
            encoding_result = chardet.detect(raw_content)
            encoding = encoding_result['encoding'] or 'utf-8'
            
            # 解码为文本
            try:
                content = raw_content.decode(encoding, errors='ignore')
            except:
                content = raw_content.decode('utf-8', errors='ignore')
            
            # 检查仪器特定模式
            content_lower = content.lower()
            
            for instrument, profile in self.INSTRUMENT_PROFILES.items():
                for pattern in profile['header_patterns']:
                    if pattern.lower() in content_lower:
                        self.detected_instrument = instrument
                        return instrument
            
            # 3. 检查数据格式特征
            lines = content.split('\n')[:20]
            
            # 检查分隔符
            if any('\t' in line for line in lines if line.strip()):
                self.detected_instrument = 'bruker'  # Bruker常用制表符
            elif any(',' in line for line in lines if line.strip()):
                self.detected_instrument = 'panalytical'  # PANalytical常用逗号
            elif any('  ' in line for line in lines if line.strip()):
                self.detected_instrument = 'rigaku'  # Rigaku常用空格
            
        except Exception as e:
            warnings.warn(f"仪器检测失败: {e}")
        
        # 默认使用通用格式
        self.detected_instrument = 'generic'
        return 'generic'
    
    def parse_file(self, filepath: Union[str, Path]) -> Dict[str, Any]:
        """
        解析RAW文件
        
        Args:
            filepath: 文件路径
            
        Returns:
            包含数据和元数据的字典
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"文件不存在: {filepath}")
        
        # 检测仪器类型
        instrument = self.detect_instrument(filepath)
        profile = self.INSTRUMENT_PROFILES[instrument]
        
        # 解析文件
        if instrument == 'bruker':
            return self._parse_bruker(filepath, profile)
        elif instrument == 'panalytical':
            return self._parse_panalytical(filepath, profile)
        elif instrument == 'rigaku':
            return self._parse_rigaku(filepath, profile)
        elif instrument == 'shimadzu':
            return self._parse_shimadzu(filepath, profile)
        else:
            return self._parse_generic(filepath, profile)
    
    def _parse_bruker(self, filepath: Path, profile: Dict) -> Dict:
        """解析Bruker格式"""
        result = {
            'instrument': 'bruker',
            'filename': filepath.name,
            'filepath': str(filepath),
            'metadata': {},
            'data': None
        }
        
        try:
            # 读取文件
            with open(filepath, 'r', encoding=profile['encoding'], errors='ignore') as f:
                lines = f.readlines()
            
            # 提取元数据
            metadata_lines = []
            data_lines = []
            in_data_section = False
            
            for i, line in enumerate(lines):
                line = line.strip()
                
                if not line:
                    continue
                
                # 检查是否进入数据部分
                if any(marker in line for marker in profile['data_start_markers']):
                    in_data_section = True
                    continue
                
                if in_data_section:
                    data_lines.append(line)
                else:
                    metadata_lines.append(line)
            
            # 解析元数据
            for line in metadata_lines[:50]:  # 只解析前50行
                if ':' in line:
                    key, value = line.split(':', 1)
                    result['metadata'][key.strip()] = value.strip()
                elif '=' in line:
                    key, value = line.split('=', 1)
                    result['metadata'][key.strip()] = value.strip()
            
            # 解析数据
            if data_lines:
                data = []
                for line in data_lines:
                    parts = line.split(profile['separator'])
                    if len(parts) >= 2:
                        try:
                            angle = float(parts[profile['angle_col']].strip())
                            intensity = float(parts[profile['intensity_col']].strip())
                            data.append([angle, intensity])
                        except ValueError:
                            continue
                
                if data:
                    data_array = np.array(data)
                    result['data'] = {
                        'angles': data_array[:, 0],
                        'intensities': data_array[:, 1]
                    }
        
        except Exception as e:
            warnings.warn(f"Bruker解析错误: {e}")
            # 尝试通用解析
            return self._parse_generic(filepath, profile)
        
        return result
    
    def _parse_panalytical(self, filepath: Path, profile: Dict) -> Dict:
        """解析PANalytical格式"""
        result = {
            'instrument': 'panalytical',
            'filename': filepath.name,
            'filepath': str(filepath),
            'metadata': {},
            'data': None
        }
        
        try:
            # 读取文件
            with open(filepath, 'r', encoding=profile['encoding'], errors='ignore') as f:
                content = f.read()
            
            # 分割头部和数据
            sections = content.split('##')
            
            if len(sections) >= 2:
                # 解析头部
                header = sections[0]
                for line in header.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        result['metadata'][key.strip()] = value.strip()
                
                # 解析数据
                data_section = '##'.join(sections[1:])
                data_lines = data_section.split('\n')
                
                data = []
                for line in data_lines:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parts = line.split(profile['separator'])
                        if len(parts) >= 2:
                            try:
                                angle = float(parts[profile['angle_col']].strip())
                                intensity = float(parts[profile['intensity_col']].strip())
                                data.append([angle, intensity])
                            except ValueError:
                                continue
                
                if data:
                    data_array = np.array(data)
                    result['data'] = {
                        'angles': data_array[:, 0],
                        'intensities': data_array[:, 1]
                    }
        
        except Exception as e:
            warnings.warn(f"PANalytical解析错误: {e}")
            return self._parse_generic(filepath, profile)
        
        return result
    
    def _parse_rigaku(self, filepath: Path, profile: Dict) -> Dict:
        """解析Rigaku格式"""
        result = {
            'instrument': 'rigaku',
            'filename': filepath.name,
            'filepath': str(filepath),
            'metadata': {},
            'data': None
        }
        
        try:
            # 读取文件
            with open(filepath, 'r', encoding=profile['encoding'], errors='ignore') as f:
                lines = f.readlines()
            
            # 提取元数据
            metadata = {}
            data_start = 0
            
            for i, line in enumerate(lines):
                line = line.strip()
                
                if line.startswith('*'):
                    # 元数据行
                    if ':' in line:
                        key, value = line[1:].split(':', 1)
                        metadata[key.strip()] = value.strip()
                elif line and not line.startswith('*'):
                    # 数据开始
                    data_start = i
                    break
            
            result['metadata'] = metadata
            
            # 解析数据
            data_lines = lines[data_start:]
            data = []
            
            for line in data_lines:
                line = line.strip()
                if line:
                    # Rigaku格式可能使用多个空格分隔
                    parts = re.split(r'\s+', line)
                    if len(parts) >= 2:
                        try:
                            angle = float(parts[profile['angle_col']].strip())
                            intensity = float(parts[profile['intensity_col']].strip())
                            data.append([angle, intensity])
                        except ValueError:
                            continue
            
            if data:
                data_array = np.array(data)
                result['data'] = {
                    'angles': data_array[:, 0],
                    'intensities': data_array[:, 1]
                }
        
        except Exception as e:
            warnings.warn(f"Rigaku解析错误: {e}")
            return self._parse_generic(filepath, profile)
        
        return result
    
    def _parse_shimadzu(self, filepath: Path, profile: Dict) -> Dict:
        """解析Shimadzu格式"""
        result = {
            'instrument': 'shimadzu',
            'filename': filepath.name,
            'filepath': str(filepath),
            'metadata': {},
            'data': None
        }
        
        try:
            # 读取文件
            with open(filepath, 'r', encoding=profile['encoding'], errors='ignore') as f:
                lines = f.readlines()
            
            # Shimadzu格式通常有固定头部
            metadata = {}
            data_start = profile['skip_lines']
            
            # 解析头部
            for i in range(min(data_start, len(lines))):
                line = lines[i].strip()
                if ':' in line:
                    key, value = line.split(':', 1)
                    metadata[key.strip()] = value.strip()
            
            result['metadata'] = metadata
            
            # 解析数据
            data_lines = lines[data_start:]
            data = []
            
            for line in data_lines:
                line = line.strip()
                if line:
                    parts = line.split(profile['separator'])
                    if len(parts) >= 2:
                        try:
                            angle = float(parts[profile['angle_col']].strip())
                            intensity = float(parts[profile['intensity_col']].strip())
                            data.append([angle, intensity])
                        except ValueError:
                            continue
            
            if data:
                data_array = np.array(data)
                result['data'] = {
                    'angles': data_array[:, 0],
                    'intensities': data_array[:, 1]
                }
        
        except Exception as e:
            warnings.warn(f"Shimadzu解析错误: {e}")
            return self._parse_generic(filepath, profile)
        
        return result
    
    def _parse_generic(self, filepath: Path, profile: Dict) -> Dict:
        """解析通用ASCII格式"""
        result = {
            'instrument': 'generic',
            'filename': filepath.name,
            'filepath': str(filepath),
            'metadata': {},
            'data': None
        }
        
        try:
            # 自动检测编码
            with open(filepath, 'rb') as f:
                raw_content = f.read()
            
            encoding_result = chardet.detect(raw_content)
            encoding = encoding_result['encoding'] or 'utf-8'
            
            # 读取文件
            content = raw_content.decode(encoding, errors='ignore')
            lines = content.split('\n')
            
            # 自动检测分隔符
            separator = self._detect_separator(lines[:100])
            
            # 查找数据开始位置
            data_start = 0
            for i, line in enumerate(lines):
                line = line.strip()
                if line and not line.startswith(('#', '!', '*', '%')):
                    # 尝试解析第一行数据
                    parts = re.split(separator, line)
                    if len(parts) >= 2:
                        try:
                            float(parts[0].strip())
                            float(parts[1].strip())
                            data_start = i
                            break
                        except ValueError:
                            continue
            
            # 解析数据
            data_lines = lines[data_start:]
            data = []
            
            for line in data_lines:
                line = line.strip()
                if line:
                    parts = re.split(separator, line)
                    if len(parts) >= 2:
                        try:
                            angle = float(parts[0].strip())
                            intensity = float(parts[1].strip())
                            data.append([angle, intensity])
                        except ValueError:
                            continue
            
            if data:
                data_array = np.array(data)
                result['data'] = {
                    'angles': data_array[:, 0],
                    'intensities': data_array[:, 1]
                }
            
            # 提取可能的元数据
            if data_start > 0:
                for i in range(min(data_start, 50)):
                    line = lines[i].strip()
                    if ':' in line:
                        key, value = line.split(':', 1)
                        result['metadata'][key.strip()] = value.strip()
        
        except Exception as e:
            raise ValueError(f"通用格式解析失败: {e}")
        
        return result
    
    def _detect_separator(self, lines: List[str]) -> str:
        """自动检测分隔符"""
        if not lines:
            return r'\s+'
        
        # 统计分隔符出现频率
        separators = [r'\t', ',', ';', r'\s+']
        counts = {sep: 0 for sep in separators}
        
        for line in lines[:20]:
            line = line.strip()
            if line:
                for sep in separators:
                    parts = re.split(sep, line)
                    if len(parts) >= 2:
                        # 检查是否为有效数字
                        try:
                            float(parts[0].strip())
                            float(parts[1].strip())
                            counts[sep] += 1
                            break
                        except ValueError:
                            continue
        
        # 选择出现频率最高的分隔符
        if sum(counts.values()) == 0:
            # 如果没有检测到，尝试常见分隔符
            for line in lines[:10]:
                if '\t' in line:
                    return r'\t'
                elif ',' in line:
                    return ','
                elif ';' in line:
                    return ';'
            return r'\s+'
        
        best_sep = max(counts.items(), key=lambda x: x[1])[0]
        return best_sep
        
