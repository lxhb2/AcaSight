#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导出功能集成模块
整合Origin、Word等软件导出功能
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import traceback

class ExportIntegration:
    """导出功能集成"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # 初始化导出器
        self.exporters = {}
        self._init_exporters()
    
    def _init_exporters(self):
        """初始化导出器"""
        try:
            # 尝试导入Origin导出器
            from origin_exporter import OriginExporter
            self.exporters['origin'] = OriginExporter()
            print("Origin导出器已加载")
        except ImportError as e:
            print(f"Origin导出器加载失败: {e}")
            self.exporters['origin'] = None
        
        try:
            # 尝试导入Word报告生成器
            from word_report_generator import WordReportGenerator
            self.exporters['word'] = WordReportGenerator()
            print("Word报告生成器已加载")
        except ImportError as e:
            print(f"Word报告生成器加载失败: {e}")
            self.exporters['word'] = None
        
        # 内置导出器
        self.exporters['json'] = self._export_json
        self.exporters['csv'] = self._export_csv
        self.exporters['txt'] = self._export_txt
    
    def export_analysis(self, analysis_data: Dict[str, Any], 
                       export_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        导出分析结果
        
        参数:
            analysis_data: 分析数据
            export_config: 导出配置
        
        返回:
            导出结果
        """
        try:
            format_type = export_config.get('format', 'json')
            output_dir = Path(export_config.get('output_dir', 'exports'))
            output_dir.mkdir(exist_ok=True)
            
            # 生成输出文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = export_config.get('filename', f"xrd_analysis_{timestamp}")
            
            # 根据格式选择导出方法
            if format_type in ['opju', 'origin']:
                return self._export_to_origin(analysis_data, output_dir, filename, export_config)
            elif format_type in ['docx', 'word']:
                return self._export_to_word(analysis_data, output_dir, filename, export_config)
            elif format_type == 'json':
                return self._export_json(analysis_data, output_dir, filename, export_config)
            elif format_type == 'csv':
                return self._export_csv(analysis_data, output_dir, filename, export_config)
            elif format_type == 'txt':
                return self._export_txt(analysis_data, output_dir, filename, export_config)
            elif format_type == 'all':
                return self._export_all_formats(analysis_data, output_dir, filename, export_config)
            else:
                raise ValueError(f"不支持的导出格式: {format_type}")
                
        except Exception as e:
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "export_config": export_config
            }
    
    def _export_to_origin(self, data: Dict[str, Any], output_dir: Path, 
                         filename: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """导出到Origin格式"""
        if not self.exporters.get('origin'):
            return {
                "success": False,
                "error": "Origin导出器未加载",
                "format": "origin"
            }
        
        try:
            # 确定输出格式
            format_type = config.get('origin_format', 'opju')
            if format_type == 'opju':
                output_path = output_dir / f"{filename}.opju"
            else:
                output_path = output_dir / f"{filename}.txt"
            
            # 执行导出
            result = self.exporters['origin'].export_to_origin(
                data, str(output_path), format_type
            )
            
            return {
                "success": result.get('success', False),
                "format": "origin",
                "output_path": str(output_path),
                "file_size": output_path.stat().st_size if output_path.exists() else 0,
                "details": result
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "format": "origin",
                "output_path": str(output_dir / f"{filename}.opju")
            }
    
    def _export_to_word(self, data: Dict[str, Any], output_dir: Path, 
                       filename: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """导出到Word格式"""
        if not self.exporters.get('word'):
            return {
                "success": False,
                "error": "Word报告生成器未加载",
                "format": "word"
            }
        
        try:
            # 确定模板
            template = config.get('template', 'default')
            
            # 确定输出格式
            output_format = config.get('word_format', 'docx')
            if output_format == 'docx':
                output_path = output_dir / f"{filename}.docx"
            else:
                output_path = output_dir / f"{filename}.txt"
            
            # 执行导出
            result = self.exporters['word'].generate_report(
                data, str(output_path), template
            )
            
            return {
                "success": result.get('success', False),
                "format": "word",
                "template": template,
                "output_path": str(output_path),
                "file_size": output_path.stat().st_size if output_path.exists() else 0,
                "details": result
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "format": "word",
                "output_path": str(output_dir / f"{filename}.docx")
            }
    
    def _export_json(self, data: Dict[str, Any], output_dir: Path, 
                    filename: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """导出为JSON格式"""
        try:
            output_path = output_dir / f"{filename}.json"
            
            # 格式化选项
            indent = config.get('indent', 2)
            ensure_ascii = config.get('ensure_ascii', False)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=ensure_ascii, indent=indent)
            
            return {
                "success": True,
                "format": "json",
                "output_path": str(output_path),
                "file_size": output_path.stat().st_size,
                "indent": indent,
                "ensure_ascii": ensure_ascii
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "format": "json",
                "output_path": str(output_dir / f"{filename}.json")
            }
    
    def _export_csv(self, data: Dict[str, Any], output_dir: Path, 
                   filename: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """导出为CSV格式"""
        try:
            import csv
            
            output_path = output_dir / f"{filename}.csv"
            
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # 写入元数据
                writer.writerow(["XRD Analysis Export"])
                writer.writerow(["Generated:", datetime.now().isoformat()])
                writer.writerow(["Filename:", data.get('file_info', {}).get('filename', 'N/A')])
                writer.writerow([])
                
                # 写入摘要
                writer.writerow(["Summary"])
                summary = data.get('summary', {})
                writer.writerow(["Peak Count", summary.get('peak_count', 0)])
                writer.writerow(["Phase Count", summary.get('phase_count', 0)])
                writer.writerow(["Top Phase", summary.get('top_phase', '')])
                writer.writerow(["Confidence", f"{summary.get('confidence', 0):.3f}"])
                writer.writerow([])
                
                # 写入峰数据
                if 'peaks' in data.get('analysis_results', {}):
                    writer.writerow(["Peaks"])
                    writer.writerow(["Angle", "Intensity", "FWHM", "d-value"])
                    
                    peaks = data['analysis_results']['peaks']
                    for angle, intensity, fwhm, d_value in zip(
                        peaks.get('angles', []),
                        peaks.get('intensities', []),
                        peaks.get('fwhms', []),
                        peaks.get('d_values', [])
                    ):
                        writer.writerow([f"{angle:.4f}", f"{intensity:.2f}", f"{fwhm:.4f}", f"{d_value:.4f}"])
                    
                    writer.writerow([])
                
                # 写入物相数据
                if 'matched_phases' in data.get('analysis_results', {}):
                    writer.writerow(["Matched Phases"])
                    writer.writerow(["Name", "Formula", "Card#", "Matched d", "Score", "Type"])
                    
                    phases = data['analysis_results']['matched_phases']
                    for phase in phases:
                        writer.writerow([
                            phase.get('name', ''),
                            phase.get('formula', ''),
                            phase.get('card_num', ''),
                            f"{phase.get('matched_d', 0):.4f}",
                            f"{phase.get('match_score', 0):.3f}",
                            phase.get('card_type', '')
                        ])
            
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
                "output_path": str(output_dir / f"{filename}.csv")
            }
    
    def _export_txt(self, data: Dict[str, Any], output_dir: Path, 
                   filename: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """导出为文本格式"""
        try:
            output_path = output_dir / f"{filename}.txt"
            
            with open(output_path, 'w', encoding='utf-8') as f:
                # 写入报告
                from word_report_generator import WordReportGenerator
                generator = WordReportGenerator()
                report_content = generator._create_report_content(data, "default")
                f.write(report_content)
            
            return {
                "success": True,
                "format": "txt",
                "output_path": str(output_path),
                "file_size": output_path.stat().st_size
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "format": "txt",
                "output_path": str(output_dir / f"{filename}.txt")
            }
    
    def _export_all_formats(self, data: Dict[str, Any], output_dir: Path, 
                           filename: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """导出所有格式"""
        formats = ['json', 'csv', 'txt', 'origin', 'word']
        
        results = {}
        for format_type in formats:
            export_config = config.copy()
            export_config['format'] = format_type
            
            result = self.export_analysis(data, export_config)
            results[format_type] = result
        
        # 统计结果
        successful = sum(1 for r in results.values() if r.get('success', False))
        total = len(formats)
        
        return {
            "success": successful > 0,
            "formats_exported": results,
            "summary": {
                "total_formats": total,
                "successful_formats": successful,
                "success_rate": f"{(successful/total*100):.1f}%" if total > 0 else "0%"
            }
        }
    
    def get_supported_formats(self) -> List[Dict[str, Any]]:
        """获取支持的导出格式"""
        formats = []
        
        # JSON格式
        formats.append({
            "format": "json",
            "name": "JSON",
            "description": "结构化数据格式，适合程序处理",
            "extensions": [".json"],
            "enabled": True
        })
        
        # CSV格式
        formats.append({
            "format": "csv",
            "name": "CSV",
            "description": "逗号分隔值，适合Excel导入",
            "extensions": [".csv"],
            "enabled": True
        })
        
        # 文本格式
        formats.append({
            "format": "txt",
            "name": "文本",
            "description": "纯文本报告，可读性好",
            "extensions": [".txt"],
            "enabled": True
        })
        
        # Origin格式
        formats.append({
            "format": "origin",
            "name": "Origin",
            "description": "Origin项目文件，包含数据和图表",
            "extensions": [".opju", ".txt"],
            "enabled": self.exporters.get('origin') is not None
        })
        
        # Word格式
        formats.append({
            "format": "word",
            "name": "Word",
            "description": "Word文档报告，包含完整分析",
            "extensions": [".docx", ".txt"],
            "enabled": self.exporters.get('word') is not None
        })
        
        return formats
    
    def create_export_template(self, template_name: str, 
                              template_config: Dict[str, Any]) -> Dict[str, Any]:
        """创建导出模板"""
        try:
            template_dir = Path("export_templates")
            template_dir.mkdir(exist_ok=True)
            
            template_file = template_dir / f"{template_name}.json"
            
            # 添加元数据
            template_config['metadata'] = {
                "name": template_name,
                "created": datetime.now().isoformat(),
                "version": "1.0"
            }
            
            with open(template_file, 'w', encoding='utf-8') as f:
                json.dump(template_config, f, ensure_ascii=False, indent=2)
            
            return {
                "success": True,
                "template_name": template_name,
                "template_file": str(template_file),
                "config": template_config
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "template_name": template_name
            }
    
    def batch_export(self, analyses: List[Dict[str, Any]], 
                    export_config: Dict[str, Any]) -> Dict[str, Any]:
        """批量导出"""
        try:
            results = []
            
            for i, analysis in enumerate(analyses):
                # 为每个分析生成唯一的文件名
                config = export_config.copy()
                if 'filename' not in config:
                    filename = analysis.get('file_info', {}).get('filename', f"analysis_{i+1}")
                    config['filename'] = Path(filename).stem
                
                # 执行导出
                result = self.export_analysis(analysis, config)
                results.append(result)
            
            # 统计结果
            successful = sum(1 for r in results if r.get('success', False))
            total = len(analyses)
            
            return {
                "success": successful == total,
                "batch_results": results,
                "summary": {
                    "total_analyses": total,
                    "successful_exports": successful,
                    "failed_exports": total - successful,
                    "success_rate": f"{(successful/total*100):.1f}%" if total > 0 else "0%"
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "analyses_count": len(analyses)
            }

# 使用示例
if __name__ == "__main__":
    # 创建集成器
    integrator = ExportIntegration()
    
    # 获取支持的格式
    formats = integrator.get_supported_formats()
    print("支持的导出格式:")
    for fmt in formats:
        status = "✅" if fmt['enabled'] else "❌"
        print(f"{status} {fmt['name']} ({fmt['format']}): {fmt['description']}")
    
    # 示例数据
    sample_data = {
        "metadata": {
            "analysis_time": datetime.now().isoformat(),
            "parameters": {
                "smooth_window": 5,
                "background_lambda": 1000.0
            }
        },
        "file_info": {
            "filename": "sample.xrd",
            "size": 1024,
            "data_points": 1000
        },
        "analysis_results": {
            "peaks": {
                "angles": [20.0, 40.0, 60.0],
                "intensities": [1000, 800, 600],
                "fwhms": [0.1, 0.15, 0.12],
                "d_values": [3.34, 2.56, 1.82]
            },
            "matched_phases": [
                {
                    "name": "Quartz",
                    "formula": "SiO2",
                    "card_num": "12345",
                    "matched_d": 3.34,
                    "match_score": 0.85,
                    "card_type": "Mineral"
                }
            ]
        },
        "summary": {
            "peak_count": 3,
            "phase_count": 1,
            "top_phase": "Quartz",
            "confidence": 0.85
        },
        "processing_time": 2.5
    }
    
    # 导出示例
    export_config = {
        "format": "json",
        "output_dir