# -*- coding: utf-8 -*-
"""
XRD AI分析助手
==============

为XRD数据分析提供AI智能辅助
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
import json


@dataclass
class XRDAnalysisContext:
    """XRD分析上下文"""
    sample_name: str
    angle_range: tuple  # (min, max)
    peak_count: int
    peaks: List[Dict]
    phases: List[Dict]
    quantitative: Dict


class XRDAssistant:
    """XRD分析AI助手"""
    
    def __init__(self, ollama_client=None):
        from .client import get_ai_client
        self.client = ollama_client or get_ai_client()
    
    def is_available(self) -> bool:
        """检查AI服务是否可用"""
        return self.client.is_available()
    
    def analyze(self, context: XRDAnalysisContext) -> Dict[str, str]:
        """
        执行完整的AI分析
        
        Args:
            context: 分析上下文
            
        Returns:
            分析结果字典
        """
        results = {
            'overview': self._generate_overview(context),
            'phase_analysis': self._analyze_phases(context),
            'suggestions': self._generate_suggestions(context),
            'report': self._generate_report(context)
        }
        return results
    
    def _generate_overview(self, ctx: XRDAnalysisContext) -> str:
        """生成图谱概览"""
        peaks_summary = self.client.analyze(f"""
作为XRD分析专家，请简要分析以下XRD图谱：

样品：{ctx.sample_name}
角度范围：{ctx.angle_range[0]:.1f}° - {ctx.angle_range[1]:.1f}°
检测到的峰数量：{ctx.peak_count}

主要峰位：
{self._format_peaks(ctx.peaks[:5])}

请给出：
1. 图谱整体评价
2. 主要特征
3. 初步判断

简洁回答，150字以内。
""")
        return peaks_summary
    
    def _analyze_phases(self, ctx: XRDAnalysisContext) -> str:
        """分析匹配物相"""
        phases_summary = ""
        if ctx.phases:
            phases_text = self._format_phases(ctx.phases[:5])
            phases_summary = self.client.analyze(f"""
作为XRD分析专家，请分析以下物相匹配结果：

样品：{ctx.sample_name}
检测到的峰：{ctx.peak_count}个

初步物相匹配：
{phases_text}

请分析：
1. 物相匹配的可靠性
2. 各物相的置信度
3. 可能的混淆相

简洁回答，200字以内。
""")
        else:
            phases_summary = "未检测到明确的物相匹配"
        return phases_summary
    
    def _generate_suggestions(self, ctx: XRDAnalysisContext) -> str:
        """生成分析建议"""
        suggestions = self.client.suggest_analysis(ctx.peaks, ctx.phases)
        return suggestions
    
    def _generate_report(self, ctx: XRDAnalysisContext) -> str:
        """生成分析报告"""
        peaks_text = self._format_peaks(ctx.peaks[:10])
        
        phases_text = ""
        if ctx.phases:
            phases_text = "\n物相鉴定结果：\n" + self._format_phases(ctx.phases[:5])
        
        quant_text = ""
        if ctx.quantitative:
            quant_text = "\n定量分析结果：\n" + self._format_quantitative(ctx.quantitative)
        
        report = self.client.analyze(f"""
请为以下XRD分析生成正式报告：

样品名称：{ctx.sample_name}
测试条件：{ctx.angle_range[0]:.1f}° - {ctx.angle_range[1]:.1f}° 2θ

一、测试概况
检测到{ctx.peak_count}个衍射峰

二、衍射峰数据
{peaks_text}

{phases_text}

{quant_text}

请生成完整的XRD分析报告，包含：
1. 样品概述
2. 测试条件
3. 峰位数据表
4. 物相鉴定结果
5. 定量分析（如有）
6. 结论与建议

格式规范，中文输出。
""")
        return report
    
    def _format_peaks(self, peaks: List) -> str:
        """格式化峰位数据"""
        lines = []
        for i, p in enumerate(peaks, 1):
            # 支持Peak对象和字典
            if hasattr(p, 'position'):
                pos, d, inten = p.position, p.d_spacing, p.intensity
            else:
                pos, d, inten = p.get('position', 0), p.get('d_spacing', 0), p.get('intensity', 0)
            lines.append(f"{i}. 2theta={pos:.2f}deg, d={d:.4f}A, I={inten:.0f}")
        return "\n".join(lines) if lines else "无"
    
    def _format_phases(self, phases: List[Dict]) -> str:
        """格式化物相数据"""
        lines = []
        for ph in phases:
            lines.append(f"- {ph.get('name', 'Unknown')} ({ph.get('formula', '')}): {ph.get('score', 0):.1f}%")
        return "\n".join(lines) if lines else "无"
    
    def _format_quantitative(self, quant: Dict) -> str:
        """格式化定量数据"""
        lines = []
        for name, wt in quant.items():
            lines.append(f"- {name}: {wt:.1f} wt%")
        return "\n".join(lines) if lines else "无"


class AIAnalysisPipeline:
    """AI分析流水线"""
    
    def __init__(self):
        self.assistant = XRDAssistant()
        self.results = {}
    
    def run(self, context: XRDAnalysisContext) -> Dict[str, str]:
        """运行完整分析"""
        print("\n" + "=" * 60)
        print("AI智能分析")
        print("=" * 60)
        
        # 检查AI服务
        if not self.assistant.is_available():
            print("[AI] AI服务未连接，将使用本地分析")
            return self._local_analysis(context)
        
        print("[AI] AI服务已连接，开始分析...")
        
        # 执行AI分析
        results = self.assistant.analyze(context)
        
        # 显示结果
        self._display_results(results)
        
        self.results = results
        return results
    
    def _local_analysis(self, ctx: XRDAnalysisContext) -> Dict[str, str]:
        """本地分析（无AI时）"""
        return {
            'overview': f"检测到{ctx.peak_count}个衍射峰，主要集中在{ctx.angle_range[0]:.0f}°-{ctx.angle_range[1]:.0f}°范围",
            'phase_analysis': f"最佳匹配：{ctx.phases[0]['name'] if ctx.phases else '无'}，匹配度{ctx.phases[0]['score']:.1f}%" if ctx.phases else "无匹配",
            'suggestions': "建议：1. 检查样品准备 2. 考虑延长扫描时间 3. 确认样品纯度",
            'report': self._generate_basic_report(ctx)
        }
    
    def _generate_basic_report(self, ctx: XRDAnalysisContext) -> str:
        """生成基础报告"""
        lines = [
            "XRD分析报告",
            "=" * 40,
            f"样品：{ctx.sample_name}",
            f"测试范围：{ctx.angle_range[0]:.1f}° - {ctx.angle_range[1]:.1f}°",
            f"检测峰数：{ctx.peak_count}",
            "",
            "主要衍射峰："
        ]
        
        for i, p in enumerate(ctx.peaks[:10], 1):
            lines.append(f"  {i}. 2θ={p['position']:.2f}°, d={p['d_spacing']:.4f}Å")
        
        if ctx.phases:
            lines.append("")
            lines.append("物相鉴定：")
            for ph in ctx.phases[:3]:
                lines.append(f"  - {ph['name']} ({ph['formula']}): {ph['score']:.1f}%")
        
        return "\n".join(lines)
    
    def _display_results(self, results: Dict[str, str]):
        """显示分析结果"""
        print("\n[AI分析概览]")
        print(results.get('overview', 'N/A'))
        
        print("\n[物相分析]")
        print(results.get('phase_analysis', 'N/A'))
        
        print("\n[分析建议]")
        print(results.get('suggestions', 'N/A'))
        
        print("\n[完整报告]")
        print("-" * 40)
        print(results.get('report', 'N/A'))
    
    def save_results(self, filepath: str):
        """保存分析结果"""
        if not self.results:
            return
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        
        print(f"\n[保存] AI分析结果已保存: {filepath}")
