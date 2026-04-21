"""
Bruker RAW 格式解析器
支持 RAW 1.01 和 RAW 4.00 格式
"""
import struct
import numpy as np
from pathlib import Path
from typing import Tuple, Dict


class BrukerRAWParser:
    """Bruker RAW 格式解析器"""
    
    def __init__(self):
        self.metadata: Dict = {}
        
    def parse(self, filepath: str) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """
        解析 Bruker RAW 文件
        
        Args:
            filepath: RAW 文件路径
            
        Returns:
            (angles, intensities, metadata) 元组
        """
        filepath = Path(filepath)
        
        with open(filepath, 'rb') as f:
            content = f.read()
        
        # 检测格式版本
        header = content[:512]
        header_text = header.decode('latin-1', errors='ignore')
        
        if header_text.startswith('RAW4.00') or header_text.startswith('RAW4'):
            return self._parse_raw4(content, header_text)
        elif header_text.startswith('RAW1.01') or header_text.startswith('RAW1'):
            return self._parse_raw1(content, header_text)
        else:
            # 尝试自动检测
            return self._parse_auto(content, header_text)
    
    def _parse_raw4(self, content: bytes, header_text: str) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """解析 RAW 4.00 格式（文本格式）"""
        # RAW 4.00 通常是文本格式
        try:
            text = content.decode('utf-8', errors='ignore')
            lines = text.split('\n')
            
            angles = []
            intensities = []
            
            in_data_section = False
            
            for line in lines:
                line = line.strip()
                
                # 跳过空行和注释
                if not line or line.startswith(';'):
                    continue
                
                # 检查是否进入数据段
                if line.startswith('['):
                    in_data_section = False
                    continue
                
                # 尝试解析数据行
                if not in_data_section:
                    # 尝试解析为角度，强度
                    parts = line.replace(',', ' ').split()
                    if len(parts) >= 2:
                        try:
                            angle = float(parts[0])
                            intensity = float(parts[1])
                            
                            # 验证是否为合理的角度值
                            if 3.0 <= angle <= 120.0:
                                angles.append(angle)
                                intensities.append(intensity)
                                in_data_section = True
                        except ValueError:
                            pass
                else:
                    # 数据段
                    parts = line.replace(',', ' ').split()
                    if len(parts) >= 2:
                        try:
                            angle = float(parts[0])
                            intensity = float(parts[1])
                            angles.append(angle)
                            intensities.append(intensity)
                        except ValueError:
                            pass
            
            if len(angles) > 0:
                self.metadata = {
                    'format': 'Bruker RAW 4.00 (text)',
                    'n_points': len(angles),
                    'start_angle': min(angles),
                    'end_angle': max(angles),
                    'step': np.mean(np.diff(angles)) if len(angles) > 1 else 0.02
                }
                
                return np.array(angles), np.array(intensities), self.metadata
            
        except Exception as e:
            print(f'RAW4 parse error: {e}')
        
        # 如果文本解析失败，尝试二进制
        return self._parse_binary(content)
    
    def _parse_raw1(self, content: bytes, header_text: str) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """解析 RAW 1.01 格式（二进制格式）"""
        # RAW 1.01 格式：头部 256 字节，数据为 uint16
        # 尝试从头部读取参数
        start_angle = 5.0
        end_angle = 80.0
        step = 0.02
        
        try:
            # 尝试不同偏移量读取角度参数
            for off in [24, 28, 32, 36, 40, 44, 48]:
                val = struct.unpack_from('<f', content, off)[0]
                if 3.0 <= val <= 30.0:
                    start_angle = val
                    break
            for off in [28, 32, 36, 40, 44, 48, 52]:
                val = struct.unpack_from('<f', content, off)[0]
                if 0.005 <= val <= 0.1:
                    step = val
                    break
        except Exception:
            pass
        
        # 数据从 256 字节开始（RAW 1.01 标准）
        data_section = content[256:]
        
        # 使用 uint16（无符号16位整数）
        intensities_u16 = np.frombuffer(data_section, dtype=np.uint16)
        
        # 计算期望点数
        n_expected = int((end_angle - start_angle) / step) + 1
        
        # 取合理数量的点
        n_use = min(n_expected, len(intensities_u16))
        intensities = intensities_u16[:n_use].astype(np.float64)
        
        # 生成角度数组
        angles = np.arange(n_use) * step + start_angle
        end_angle_actual = angles[-1]
        
        self.metadata = {
            'format': 'Bruker RAW 1.01 (binary)',
            'n_points': n_use,
            'start_angle': start_angle,
            'end_angle': end_angle_actual,
            'step': step,
            'dtype': 'uint16'
        }
        
        return angles, intensities, self.metadata
    
    def _parse_auto(self, content: bytes, header_text: str) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """自动检测格式并解析"""
        # 尝试各种格式
        # 1. 检查是否包含文本数据
        text = content.decode('utf-8', errors='ignore')
        if any(c.isdigit() for c in text):
            # 尝试按行解析
            lines = text.split('\n')
            data_lines = []
            
            for line in lines:
                line = line.strip()
                if line and not line.startswith(';'):
                    parts = line.replace(',', ' ').split()
                    if len(parts) >= 2:
                        try:
                            angle = float(parts[0])
                            intensity = float(parts[1])
                            if 3.0 <= angle <= 120.0:
                                data_lines.append((angle, intensity))
                        except ValueError:
                            pass
            
            if len(data_lines) > 100:
                angles = np.array([d[0] for d in data_lines])
                intensities = np.array([d[1] for d in data_lines])
                
                self.metadata = {
                    'format': 'Auto-detected (text)',
                    'n_points': len(angles)
                }
                
                return angles, intensities, self.metadata
        
        # 2. 尝试二进制格式
        return self._parse_binary(content)
    
    def _parse_binary(self, content: bytes) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """解析二进制格式"""
        # 假设数据从 512 字节开始
        data_section = content[512:]
        
        # 尝试 16 位整数
        intensities = np.frombuffer(data_section, dtype=np.int16)
        
        # 标准参数
        start_angle = 5.0
        step = 0.02
        
        angles = np.arange(len(intensities)) * step + start_angle
        
        self.metadata = {
            'format': 'Binary (auto-detected)',
            'n_points': len(angles)
        }
        
        return angles, intensities, self.metadata
