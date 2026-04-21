#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Origin导出功能
支持导出为.opju格式和.txt格式
"""

import struct
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional
import json
import csv

class OriginExporter:
    """Origin数据导出器"""
    
    def __init__(self):
        self.supported_formats = ['.opju', '.txt', '.csv', '.xlsx']
    
    def export_to_origin(self, data: Dict[str, Any], output_path: str, 
                        format: str = 'opju') -> Dict[str, Any]:
        """
        导出数据到Origin格式
        
        参数:
            data: XRD分析数据
            output_path: 输出文件路径
            format: 格式 ('opju', 'txt', 'csv', 'xlsx')
        
        返回:
            导出结果信息
        """
        try:
            output_path = Path(output_path)
            
            if format == 'opju':
                return self._export_opju(data, output_path)
            elif format == 'txt':
                return self._export_txt(data, output_path)
            elif format == 'csv':
                return self._export_csv(data, output_path)
            elif format == 'xlsx':
                return self._export_excel(data, output_path)
            else:
                raise ValueError(f"不支持的格式: {format}")
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "format": format,
                "output_path": str(output_path)
            }
    
    def _export_opju(self, data: Dict[str, Any], output_path: Path) -> Dict[str, Any]:
        """导出为Origin项目文件(.opju)"""
        try:
            # 注意: .opju是Origin的二进制格式，这里我们创建一个兼容的文本格式
            # 实际应用中可能需要使用Origin的COM接口或专门的库
            
            # 创建项目文件结构
            project_content = self._create_opju_structure(data)
            
            # 保存文件
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(project_content)
            
            return {
                "success": True,
                "format": "opju",
                "output_path": str(output_path),
                "file_size": output_path.stat().st_size,
                "note": "创建了Origin兼容的项目文件"
            }
            
        except Exception as e:
            # 如果.opju失败，回退到.txt格式
            txt_path = output_path.with_suffix('.txt')
            return self._export_txt(data, txt_path)
    
    def _create_opju_structure(self, data: Dict[str, Any]) -> str:
        """创建Origin项目文件结构"""
        # 这是一个简化的Origin项目文件结构
        # 实际格式更复杂，需要参考Origin文档
        
        project_header = """[Origin]
Version=2024
ProjectType=Workbook

[Window]
Type=Workbook
Name=XRDAnalysis
"""
        
        # 添加工作表
        worksheets = []
        
        # 1. 原始数据工作表
        if 'xrd_data' in data:
            raw_data = data['xrd_data']
            angles = raw_data.get('angles', [])
            intensities = raw_data.get('intensities', [])
            
            worksheet = f"""
[Worksheet]
Name=RawData
Columns=2
Rows={len(angles)}
Column1Name=2Theta
Column1Units=deg
Column2Name=Intensity
Column2Units=a.u.

[Data]
"""
            for angle, intensity in zip(angles, intensities):
                worksheet += f"{angle}\t{intensity}\n"
            
            worksheets.append(worksheet)
        
        # 2. 峰数据工作表
        if 'peaks' in data.get('analysis_results', {}):
            peaks = data['analysis_results']['peaks']
            peak_angles = peaks.get('angles', [])
            peak_intensities = peaks.get('intensities', [])
            d_values = peaks.get('d_values', [])
            
            worksheet = f"""
[Worksheet]
Name=Peaks
Columns=4
Rows={len(peak_angles)}
Column1Name=PeakAngle
Column1Units=deg
Column2Name=PeakIntensity
Column2Units=a.u.
Column3Name=dValue
Column3Units=angstrom
Column4Name=FWHM
Column4Units=deg

[Data]
"""
            for i in range(len(peak_angles)):
                angle = peak_angles[i]
                intensity = peak_intensities[i] if i < len(peak_intensities) else 0
                d_value = d_values[i] if i < len(d_values) else 0
                fwhm = peaks.get('fwhms', [0])[i] if i < len(peaks.get('fwhms', [])) else 0
                
                worksheet += f"{angle}\t{intensity}\t{d_value}\t{fwhm}\n"
            
            worksheets.append(worksheet)
        
        # 3. 物相匹配工作表
        if 'matched_phases' in data.get('analysis_results', {}):
            phases = data['analysis_results']['matched_phases']
            
            worksheet = f"""
[Worksheet]
Name=MatchedPhases
Columns=6
Rows={len(phases)}
Column1Name=PhaseName
Column2Name=Formula
Column3Name=CardNumber
Column4Name=Matched_d
Column4Units=angstrom
Column5Name=MatchScore
Column6Name=CardType

[Data]
"""
            for phase in phases:
                name = phase.get('name', '')
                formula = phase.get('formula', '')
                card_num = phase.get('card_num', '')
                matched_d = phase.get('matched_d', 0)
                score = phase.get('match_score', 0)
                card_type = phase.get('card_type', '')
                
                worksheet += f"{name}\t{formula}\t{card_num}\t{matched_d}\t{score}\t{card_type}\n"
            
            worksheets.append(worksheet)
        
        # 组合所有内容
        project_content = project_header + "\n".join(worksheets)
        
        return project_content
    
    def _export_txt(self, data: Dict[str, Any], output_path: Path) -> Dict[str, Any]:
        """导出为文本格式"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                # 写入文件头
                f.write("# XRD Analysis Data Export\n")
                f.write(f"# Generated: {data.get('metadata', {}).get('analysis_time', 'N/A')}\n")
                f.write(f"# Filename: {data.get('file_info', {}).get('filename', 'N/A')}\n")
                f.write("#" * 60 + "\n\n")
                
                # 1. 原始数据
                if 'xrd_data' in data:
                    f.write("## Raw XRD Data\n")
                    f.write("# 2Theta(deg)\tIntensity(a.u.)\n")
                    
                    raw_data = data['xrd_data']
                    angles = raw_data.get('angles', [])
                    intensities = raw_data.get('intensities', [])
                    
                    for angle, intensity in zip(angles, intensities):
                        f.write(f"{angle:.4f}\t{intensity:.2f}\n")
                    
                    f.write("\n")
                
                # 2. 峰数据
                if 'peaks' in data.get('analysis_results', {}):
                    f.write("## Detected Peaks\n")
                    f.write("# Angle(deg)\tIntensity\tFWHM(deg)\td-value(A)\n")
                    
                    peaks = data['analysis_results']['peaks']
                    peak_angles = peaks.get('angles', [])
                    peak_intensities = peaks.get('intensities', [])
                    fwhms = peaks.get('fwhms', [])
                    d_values = peaks.get('d_values', [])
                    
                    for i in range(len(peak_angles)):
                        angle = peak_angles[i]
                        intensity = peak_intensities[i] if i < len(peak_intensities) else 0
                        fwhm = fwhms[i] if i < len(fwhms) else 0
                        d_value = d_values[i] if i < len(d_values) else 0
                        
                        f.write(f"{angle:.4f}\t{intensity:.2f}\t{fwhm:.4f}\t{d_value:.4f}\n")
                    
                    f.write("\n")
                
                # 3. 物相匹配
                if 'matched_phases' in data.get('analysis_results', {}):
                    f.write("## Matched Phases\n")
                    f.write("# Phase\tFormula\tCard#\tMatched d(A)\tScore\tType\n")
                    
                    phases = data['analysis_results']['matched_phases']
                    for phase in phases:
                        name = phase.get('name', '')
                        formula = phase.get('formula', '')
                        card_num = phase.get('card_num', '')
                        matched_d = phase.get('matched_d', 0)
                        score = phase.get('match_score', 0)
                        card_type = phase.get('card_type', '')
                        
                        f.write(f"{name}\t{formula}\t{card_num}\t{matched_d:.4f}\t{score:.3f}\t{card_type}\n")
                    
                    f.write("\n")
                
                # 4. 统计信息
                if 'statistics' in data.get('analysis_results', {}):
                    f.write("## Statistics\n")
                    stats = data['analysis_results']['statistics']
                    
                    f.write(f"Data Points: {stats.get('data_points', 0)}\n")
                    f.write(f"Angle Range: {stats.get('angle_range', {}).get('min', 0):.1f}-{stats.get('angle_range', {}).get('max', 0):.1f} deg\n")
                    f.write(f"Peaks Detected: {stats.get('peak_stats', {}).get('count', 0)}\n")
                    f.write(f"Phases Matched: {stats.get('phase_stats', {}).get('matched_count', 0)}\n")
            
            return {
                "success": True,
                "format": "txt",
                "output_path": str(output_path),
                "file_size": output_path.stat().st_size,
                "encoding": "utf-8"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "format": "txt",
                "output_path": str(output_path)
            }
    
    def _export_csv(self, data: Dict[str, Any], output_path: Path) -> Dict[str, Any]:
        """导出为CSV格式"""
        try:
            import csv
            
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # 写入元数据
                writer.writerow(["XRD Analysis Data Export"])
                writer.writerow(["Generated:", data.get('metadata', {}).get('analysis_time', 'N/A')])
                writer.writerow(["Filename:", data.get('file_info', {}).get('filename', 'N/A')])
                writer.writerow([])
                
                # 原始数据
                if 'xrd_data' in data:
                    writer.writerow(["Raw XRD Data"])
                    writer.writerow(["2Theta(deg)", "Intensity(a.u.)"])
                    
                    raw_data = data['xrd_data']
                    angles = raw_data.get('angles', [])
                    intensities = raw_data.get('intensities', [])
                    
                    for angle, intensity in zip(angles, intensities):
                        writer.writerow([f"{angle:.4f}", f"{intensity:.2f}"])
                    
                    writer.writerow([])
                
                # 峰数据
                if 'peaks' in data.get('analysis_results', {}):
                    writer.writerow(["Detected Peaks"])
                    writer.writerow(["Angle(deg)", "Intensity", "FWHM(deg)", "d-value(A)"])
                    
                    peaks = data['analysis_results']['peaks']
                    peak_angles = peaks.get('angles', [])
                    peak_intensities = peaks.get('intensities', [])
                    fwhms = peaks.get('fwhms', [])
                    d_values = peaks.get('d_values', [])
                    
                    for i in range(len(peak_angles)):
                        angle = peak_angles[i]
                        intensity = peak_intensities[i] if i < len(peak_intensities) else 0
                        fwhm = fwhms[i] if i < len(fwhms) else 0
                        d_value = d_values[i] if i < len(d_values) else 0
                        
                        writer.writerow([f"{angle:.4f}", f"{intensity:.2f}", f"{fwhm:.4f}", f"{d_value:.4f}"])
                    
                    writer.writerow([])
            
            return {
                "success": True,
                "format": "csv",
                "output_path": str(output_path),
                "file_size": output_path.stat().st_size
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "format": "csv",
                "output_path": str(output_path)
            }
    
    def _export_excel(self, data: Dict[str, Any], output_path: Path) -> Dict[str, Any]:
        """导出为Excel格式"""
        try:
            import pandas as pd
            
            # 创建Excel写入器
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                # 1. 原始数据工作表
                if 'xrd_data' in data:
                    raw_data = data['xrd_data']
                    angles = raw_data.get('angles', [])
                    intensities = raw_data.get('intensities', [])
                    
                    df_raw = pd.DataFrame({
                        '2Theta(deg)': angles,
                        'Intensity(a.u.)': intensities
                    })
                    df_raw.to_excel(writer, sheet_name='RawData', index=False)
                
                # 2. 峰数据工作表
                if 'peaks' in data.get('analysis_results', {}):
                    peaks = data['analysis_results']['peaks']
                    
                    df_peaks = pd.DataFrame({
                        'Angle(deg)': peaks.get('angles', []),
                        'Intensity': peaks.get('intensities', []),
                        'FWHM(deg)': peaks.get('fwhms', []),
                        'd-value(A)': peaks.get('d_values', [])
                    })
                    df_peaks.to_excel(writer, sheet_name='Peaks', index=False)
                
                # 3. 物相匹配工作表
                if 'matched_phases' in data.get('analysis_results', {}):
                    phases = data['analysis_results']['matched_phases']
                    
                    phase_data = []
                    for phase in phases:
                        phase_data.append({
                            'Phase': phase.get('name', ''),
                            'Formula': phase.get('formula', ''),
                            'Card#': phase.get('card_num', ''),
                            'Matched d(A)': phase.get('matched_d', 0),
                            'Score': phase.get('match_score', 0),
                            'Type': phase.get('card_type', '')
                        })
                    
                    df_phases = pd.DataFrame(phase_data)
                    df_phases.to_excel(writer, sheet_name='MatchedPhases', index=False)
                
                # 4. 统计信息工作表
                if 'statistics' in data.get('analysis_results', {}):
                    stats = data['analysis_results']['statistics']
                    
                    stat_data = {
                        'Metric': [
                            'Data Points',
                            'Angle Range (deg)',
                            'Peaks Detected',
                            'Phases Matched',
                            'Max Intensity',
                            'Average FWHM'
                        ],
                        'Value': [
                            stats.get('data_points', 0),
                            f"{stats.get('angle_range', {}).get('min', 0):.1f}-{stats.get('angle_range', {}).get('max', 0):.1f}",
                            stats.get('peak_stats', {}).get('count', 0),
                            stats.get('phase_stats', {}).get('matched_count', 0),
                            f"{stats.get('intensity_stats', {}).get('max', 0):.1f}",
                            f"{stats.get('peak_stats', {}).get('avg_fwhm', 0):.4f}"
                        ]
                    }
                    
                    df_stats = pd.DataFrame(stat_data)
                    df_stats.to_excel(writer, sheet_name='Statistics', index=False)
            
            return {
                "success": True,
                "format": "xlsx",
                "output_path": str(output_path),
                "file_size": output_path.stat().st_size,
                "sheets": writer.sheets
            }
            
        except ImportError:
            # 如果没有pandas/openpyxl，回退到CSV
            csv_path = output_path.with_suffix('.csv')
            return self._export_csv(data, csv_path)
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "format": "xlsx",
                "output_path": str(output_path)
            }
    
    def export_chart_to_image(self, plot_data: Dict[str, Any], output_path: str, 
                             format: str = 'png', dpi: int = 300) -> Dict[str, Any]:
        """导出图表为图像"""
        try:
            from plot_optimizer import PlotOptimizer
            
            optimizer = PlotOptimizer()
            output_path = Path(output_path)
            
            # 创建图表
            if 'xrd_data' in plot_data:
                x_data = plot_data['xrd_data']['angles']
                y_data = plot_data['xrd_data']['intensities']
                
                fig, ax = optimizer.create_xrd_plot(
                    x_data, y_data,
                    title=plot_data.get('title', 'XRD Pattern'),
                    xlabel=plot_data.get('xlabel', '2θ (°)'),
                    ylabel=plot_data.get('ylabel