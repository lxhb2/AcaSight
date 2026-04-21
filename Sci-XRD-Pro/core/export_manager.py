"""
智能导出管理器 - Origin兼容导出系统

支持格式：
1. Origin标准ASCII XY格式
2. 峰位数据表
3. 物相匹配结果
4. 分析报告
5. 自动生成Origin导入脚本

特性：
- 完美Origin兼容
- 多种导出预设
- 批量导出
- 模板系统
"""

import os
import json
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union, Any
from datetime import datetime
import warnings


class ExportManager:
    """智能导出管理器"""
    
    # 导出预设配置
    EXPORT_PRESETS = {
        'origin_standard': {
            'name': 'Origin标准格式',
            'description': 'Origin可直接导入的标准ASCII XY格式',
            'data_format': 'ascii_xy',
            'separator': '\t',
            'header': True,
            'precision': 6,
            'include_metadata': True,
            'include_peaks': False,
            'include_phases': False,
            'file_extension': '.txt'
        },
        'origin_advanced': {
            'name': 'Origin高级格式',
            'description': '包含峰位和物相数据的完整导出',
            'data_format': 'multi_file',
            'separator': '\t',
            'header': True,
            'precision': 8,
            'include_metadata': True,
            'include_peaks': True,
            'include_phases': True,
            'create_script': True,
            'file_extension': '.txt'
        },
        'excel_friendly': {
            'name': 'Excel友好格式',
            'description': '适合Excel处理的CSV格式',
            'data_format': 'csv',
            'separator': ',',
            'header': True,
            'precision': 4,
            'include_metadata': False,
            'include_peaks': True,
            'include_phases': True,
            'file_extension': '.csv'
        },
        'publication_ready': {
            'name': '出版级格式',
            'description': '适合论文发表的高精度格式',
            'data_format': 'ascii_xy',
            'separator': ' ',
            'header': False,
            'precision': 10,
            'include_metadata': False,
            'include_peaks': True,
            'include_phases': True,
            'file_extension': '.dat'
        },
        'complete_report': {
            'name': '完整报告',
            'description': '包含所有分析结果的完整报告',
            'data_format': 'multi_file',
            'separator': '\t',
            'header': True,
            'precision': 6,
            'include_metadata': True,
            'include_peaks': True,
            'include_phases': True,
            'include_summary': True,
            'create_script': True,
            'file_extension': '.txt'
        }
    }
    
    def __init__(self, output_dir: Optional[Union[str, Path]] = None):
        """
        初始化导出管理器
        
        Args:
            output_dir: 输出目录（默认：当前目录）
        """
        self.output_dir = Path(output_dir) if output_dir else Path.cwd()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 导出历史记录
        self.export_history = []
    
    def export_for_origin(self, data: Dict[str, Any], peaks: List[Dict] = None,
                         phases: List[Dict] = None, preset: str = 'origin_standard',
                         filename: Optional[str] = None) -> Dict[str, Path]:
        """
        导出Origin兼容格式
        
        Args:
            data: 包含XRD数据的字典，必须有'angles'和'intensities'
            peaks: 峰位数据列表
            phases: 物相匹配结果列表
            preset: 导出预设名称
            filename: 基础文件名（不含扩展名）
            
        Returns:
            导出的文件路径字典
        """
        if preset not in self.EXPORT_PRESETS:
            raise ValueError(f"未知预设: {preset}。可用预设: {list(self.EXPORT_PRESETS.keys())}")
        
        config = self.EXPORT_PRESETS[preset].copy()
        
        # 生成文件名
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"xrd_analysis_{timestamp}"
        
        base_path = self.output_dir / filename
        
        # 导出结果字典
        export_results = {}
        
        try:
            # 1. 导出主数据
            if config['data_format'] in ['ascii_xy', 'csv']:
                data_file = self._export_main_data(data, base_path, config)
                export_results['data_file'] = data_file
            
            # 2. 导出峰位数据
            if config.get('include_peaks', False) and peaks:
                peaks_file = self._export_peak_data(peaks, base_path, config)
                export_results['peaks_file'] = peaks_file
            
            # 3. 导出物相数据
            if config.get('include_phases', False) and phases:
                phases_file = self._export_phase_data(phases, base_path, config)
                export_results['phases_file'] = phases_file
            
            # 4. 导出元数据
            if config.get('include_metadata', False) and 'metadata' in data:
                meta_file = self._export_metadata(data.get('metadata', {}), base_path, config)
                export_results['metadata_file'] = meta_file
            
            # 5. 导出摘要报告
            if config.get('include_summary', False):
                summary_file = self._export_summary(data, peaks, phases, base_path, config)
                export_results['summary_file'] = summary_file
            
            # 6. 创建Origin导入脚本
            if config.get('create_script', False):
                script_file = self._create_origin_script(base_path, export_results, data)
                export_results['origin_script'] = script_file
            
            # 记录导出历史
            self._record_export(filename, preset, export_results)
            
            return export_results
            
        except Exception as e:
            raise RuntimeError(f"导出失败: {e}")
    
    def _export_main_data(self, data: Dict[str, Any], base_path: Path, 
                         config: Dict) -> Path:
        """导出主数据（角度-强度对）"""
        if 'angles' not in data or 'intensities' not in data:
            raise ValueError("数据必须包含'angles'和'intensities'")
        
        angles = np.array(data['angles'])
        intensities = np.array(data['intensities'])
        
        # 确保数据长度一致
        if len(angles) != len(intensities):
            min_len = min(len(angles), len(intensities))
            angles = angles[:min_len]
            intensities = intensities[:min_len]
        
        # 构建数据框
        df = pd.DataFrame({
            '2Theta': angles,
            'Intensity': intensities
        })
        
        # 生成文件名
        if config['data_format'] == 'csv':
            filepath = base_path.with_suffix('.csv')
        else:
            filepath = base_path.with_suffix(config['file_extension'])
        
        # 导出文件
        if config['data_format'] == 'csv':
            df.to_csv(filepath, sep=config['separator'], 
                     index=False, header=config['header'],
                     float_format=f'%.{config["precision"]}f')
        else:
            # ASCII XY格式
            with open(filepath, 'w', encoding='utf-8') as f:
                if config['header']:
                    f.write(f"2Theta{config['separator']}Intensity\n")
                
                for angle, intensity in zip(angles, intensities):
                    f.write(f"{angle:.{config['precision']}f}{config['separator']}"
                           f"{intensity:.{config['precision']}f}\n")
        
        return filepath
    
    def _export_peak_data(self, peaks: List[Dict], base_path: Path, 
                         config: Dict) -> Path:
        """导出峰位数据"""
        if not peaks:
            raise ValueError("没有峰位数据可导出")
        
        # 准备峰位数据
        peak_data = []
        for i, peak in enumerate(peaks):
            peak_info = {
                'PeakNo': i + 1,
                'Position_2Theta': peak.get('position', 0),
                'Intensity': peak.get('intensity', 0),
                'FWHM': peak.get('fwhm', 0),
                'Area': peak.get('area', 0),
                'Mineral': peak.get('mineral', 'Unknown'),
                'Confidence': peak.get('confidence', 0)
            }
            peak_data.append(peak_info)
        
        # 创建数据框
        df = pd.DataFrame(peak_data)
        
        # 生成文件名
        filepath = base_path.with_name(f"{base_path.name}_peaks{config['file_extension']}")
        
        # 导出文件
        if config['data_format'] == 'csv':
            df.to_csv(filepath, sep=config['separator'], 
                     index=False, header=config['header'],
                     float_format=f'%.{config["precision"]}f')
        else:
            with open(filepath, 'w', encoding='utf-8') as f:
                if config['header']:
                    headers = list(df.columns)
                    f.write(config['separator'].join(headers) + '\n')
                
                for _, row in df.iterrows():
                    row_values = []
                    for col in df.columns:
                        value = row[col]
                        if isinstance(value, (int, float)):
                            row_values.append(f"{value:.{config['precision']}f}")
                        else:
                            row_values.append(str(value))
                    
                    f.write(config['separator'].join(row_values) + '\n')
        
        return filepath
    
    def _export_phase_data(self, phases: List[Dict], base_path: Path, 
                          config: Dict) -> Path:
        """导出物相数据"""
        if not phases:
            raise ValueError("没有物相数据可导出")
        
        # 准备物相数据
        phase_data = []
        for i, phase in enumerate(phases):
            phase_info = {
                'PhaseNo': i + 1,
                'Mineral': phase.get('mineral', 'Unknown'),
                'Formula': phase.get('formula', ''),
                'CAS': phase.get('cas', ''),
                'MatchScore': phase.get('match_score', 0),
                'Confidence': phase.get('confidence', 0),
                'MajorPeaks': ';'.join([str(p) for p in phase.get('major_peaks', [])]),
                'Reference': phase.get('reference', '')
            }
            phase_data.append(phase_info)
        
        # 创建数据框
        df = pd.DataFrame(phase_data)
        
        # 生成文件名
        filepath = base_path.with_name(f"{base_path.name}_phases{config['file_extension']}")
        
        # 导出文件
        if config['data_format'] == 'csv':
            df.to_csv(filepath, sep=config['separator'], 
                     index=False, header=config['header'],
                     float_format=f'%.{config["precision"]}f')
        else:
            with open(filepath, 'w', encoding='utf-8') as f:
                if config['header']:
                    headers = list(df.columns)
                    f.write(config['separator'].join(headers) + '\n')
                
                for _, row in df.iterrows():
                    row_values = []
                    for col in df.columns:
                        value = row[col]
                        if isinstance(value, (int, float)):
                            row_values.append(f"{value:.{config['precision']}f}")
                        else:
                            row_values.append(str(value))
                    
                    f.write(config['separator'].join(row_values) + '\n')
        
        return filepath
    
    def _export_metadata(self, metadata: Dict, base_path: Path, 
                        config: Dict) -> Path:
        """导出元数据"""
        if not metadata:
            raise ValueError("没有元数据可导出")
        
        # 生成文件名
        filepath = base_path.with_name(f"{base_path.name}_metadata.txt")
        
        # 导出元数据
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("=== XRD分析元数据 ===\n")
            f.write(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"导出预设: {config.get('name', 'Unknown')}\n")
            f.write("\n")
            
            for key, value in metadata.items():
                f.write(f"{key}: {value}\n")
        
        return filepath
    
    def _export_summary(self, data: Dict, peaks: List[Dict], 
                       phases: List[Dict], base_path: Path, 
                       config: Dict) -> Path:
        """导出分析摘要报告"""
        # 生成文件名
        filepath = base_path.with_name(f"{base_path.name}_summary.txt")
        
        # 计算统计信息
        num_peaks = len(peaks) if peaks else 0
        num_phases = len(phases) if phases else 0
        
        if peaks:
            avg_intensity = np.mean([p.get('intensity', 0) for p in peaks])
            avg_fwhm = np.mean([p.get('fwhm', 0) for p in peaks])
        else:
            avg_intensity = 0
            avg_fwhm = 0
        
        if phases:
            avg_confidence = np.mean([p.get('confidence', 0) for p in phases])
        else:
            avg_confidence = 0
        
        # 生成报告
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("XRD分析摘要报告\n")
            f.write("=" * 60 + "\n\n")
            
            f.write("1. 基本信息\n")
            f.write(f"   分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"   数据点数: {len(data.get('angles', []))}\n")
            f.write(f"   角度范围: {min(data.get('angles', [0])):.2f}° - "
                   f"{max(data.get('angles', [0])):.2f}°\n\n")
            
            f.write("2. 峰检测结果\n")
            f.write(f"   检测到峰数: {num_peaks}\n")
            f.write(f"   平均强度: {avg_intensity:.2f}\n")
            f.write(f"   平均半高宽: {avg_fwhm:.3f}°\n\n")
            
            f.write("3. 物相匹配结果\n")
            f.write(f"   匹配物相数: {num_phases}\n")
            f.write(f"   平均置信度: {avg_confidence:.1%}\n\n")
            
            if phases:
                f.write("   主要物相:\n")
                for i, phase in enumerate(phases[:5]):  # 显示前5个
                    f.write(f"   {i+1}. {phase.get('mineral', 'Unknown')} "
                           f"(置信度: {phase.get('confidence', 0):.1%})\n")
                f.write("\n")
            
            f.write("4. 导出信息\n")
            f.write(f"   导出格式: {config.get('name', 'Unknown')}\n")
            f.write(f"   导出文件: {base_path.name}\n")
            f.write(f"   导出时间: {datetime.now().strftime('%H:%M:%S')}\n")
            
            f.write("\n" + "=" * 60 + "\n")
            f.write("报告结束\n")
            f.write("=" * 60 + "\n")
        
        return filepath
    
    def _create_origin_script(self, base_path: Path, export_files: Dict,
                             data: Dict) -> Path:
        """创建Origin导入脚本"""
        script_path = base_path.with_name(f"{base_path.name}_origin_script.ogs")
        
        # 获取数据范围
        angles = data.get('angles', [])
        if angles:
            angle_min = min(angles)
            angle_max = max(angles)
        else:
            angle_min = 0
            angle_max = 90
        
        # 生成Origin C脚本
        script = f"""// Origin C Script - Auto-generated by Sci-XRD Pro
// Import XRD data and create plots

// Clear existing data
newbook;

// Import main data
string mainFile$ = "{export_files.get('data_file', '')}";
impASC fname:=mainFile$;

// Create main plot
plotxy iy:=(1,2) plot:=200;
layer.x.label$ = "2Theta (degrees)";
layer.y.label$ = "Intensity (a.u.)";
layer.x.from = {angle_min};
layer.x.to = {angle_max};

// Add peak markers if available
string peakFile$ = "{export_files.get('peaks_file', '')}";
if(peakFile$ != "") {{
    // Import peak data
    newsheet;
    impASC fname:=peakFile$;
    
    // Add vertical lines for peaks
    worksheet wks = Project.ActiveLayer();
    for(int i=1; i<=wks.GetNumRows(); i++) {{
        double peakPos = wks.Cell(i, 2);  // Peak position column
        draw -l 2 -v peakPos;
    }}
}}

// Add phase information if available
string phaseFile$ = "{export_files.get('phases_file', '')}";
if(phaseFile$ != "") {{
    // Import phase data
    newbook;
    impASC fname:=phaseFile$;
    
    // Create phase table
    // (Add your custom phase display logic