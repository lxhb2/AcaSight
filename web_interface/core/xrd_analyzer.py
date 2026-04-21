#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XRD分析器核心模块
"""

import json
import asyncio
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional
import traceback
from datetime import datetime

from .plot_generator import PlotGenerator
from .ai_assistant import AIAssistant
from ..utils.file_parser import parse_xrd_file

class XRDAnalyzer:
    """XRD分析器"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.plot_generator = PlotGenerator()
        self.ai_assistant = AIAssistant()
        
        # 默认分析参数
        self.default_params = {
            "smooth_window": 5,
            "background_lambda": 1000.0,
            "peak_height_threshold": 2.0,
            "peak_prominence": 1.0,
            "min_peak_distance": 0.3,
            "search_tolerance": 0.02,
            "min_matched_peaks": 3,
            "enable_ai": True
        }
    
    async def analyze_file(self, file_path: str, user_params: Dict[str, Any] = None) -> Dict[str, Any]:
        """分析XRD文件"""
        try:
            start_time = datetime.now()
            
            # 合并参数
            params = {**self.default_params, **(user_params or {})}
            
            # 1. 解析文件
            print(f"解析文件: {file_path}")
            xrd_data = await parse_xrd_file(file_path)
            
            if not xrd_data:
                raise ValueError("无法解析XRD文件")
            
            # 2. 预处理数据
            print("预处理数据...")
            processed_data = self._preprocess_data(xrd_data, params)
            
            # 3. 峰检测
            print("检测峰...")
            peaks = self._detect_peaks(processed_data, params)
            
            # 4. 物相匹配
            print("物相匹配...")
            matched_phases = await self._match_phases(peaks, params)
            
            # 5. AI分析（如果启用）
            ai_analysis = None
            if params.get("enable_ai", True):
                print("AI分析...")
                ai_analysis = await self._ai_analysis(xrd_data, peaks, matched_phases)
            
            # 6. 生成图表
            print("生成图表...")
            plots = await self._generate_plots(xrd_data, peaks, matched_phases)
            
            # 7. 计算统计信息
            print("计算统计...")
            statistics = self._calculate_statistics(xrd_data, peaks, matched_phases)
            
            # 8. 生成报告
            print("生成报告...")
            report = self._generate_report(
                file_path, xrd_data, peaks, matched_phases, 
                ai_analysis, statistics, params
            )
            
            # 计算总耗时
            elapsed = (datetime.now() - start_time).total_seconds()
            report["processing_time"] = elapsed
            
            print(f"分析完成！耗时: {elapsed:.2f}秒")
            
            return report
            
        except Exception as e:
            print(f"分析失败: {e}")
            traceback.print_exc()
            raise
    
    def _preprocess_data(self, xrd_data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """预处理数据"""
        angles = np.array(xrd_data["angles"])
        intensities = np.array(xrd_data["intensities"])
        
        # 平滑处理
        if params["smooth_window"] > 1:
            from scipy.ndimage import uniform_filter1d
            intensities = uniform_filter1d(intensities, size=params["smooth_window"])
        
        # 背景扣除
        if params["background_lambda"] > 0:
            from scipy import sparse
            from scipy.sparse.linalg import spsolve
            
            # 使用AsLS算法扣除背景
            L = len(intensities)
            D = sparse.diags([1, -2, 1], [0, 1, 2], shape=(L-2, L))
            w = np.ones(L)
            
            for _ in range(10):  # 迭代次数
                W = sparse.spdiags(w, 0, L, L)
                Z = W + params["background_lambda"] * D.dot(D.T)
                background = spsolve(Z, w * intensities)
                w = np.where(intensities > background, params["peak_height_threshold"] / 100, 1)
            
            intensities = intensities - background
        
        return {
            "angles": angles.tolist(),
            "intensities": intensities.tolist(),
            "original_intensities": xrd_data["intensities"]
        }
    
    def _detect_peaks(self, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """检测峰"""
        from scipy.signal import find_peaks
        
        angles = np.array(data["angles"])
        intensities = np.array(data["intensities"])
        
        # 计算峰高阈值
        max_intensity = np.max(intensities)
        height_threshold = max_intensity * (params["peak_height_threshold"] / 100)
        
        # 查找峰
        peaks, properties = find_peaks(
            intensities,
            height=height_threshold,
            prominence=params["peak_prominence"],
            distance=params["min_peak_distance"] / (angles[1] - angles[0])  # 转换为索引距离
        )
        
        # 计算FWHM
        fwhms = []
        from scipy.signal import peak_widths
        if len(peaks) > 0:
            widths, width_heights, left_ips, right_ips = peak_widths(
                intensities, peaks, rel_height=0.5
            )
            fwhms = (angles[1] - angles[0]) * widths  # 转换为角度
        
        # 计算d值（假设Cu Kα辐射，λ=1.5406Å）
        wavelength = 1.5406  # Cu Kα
        d_values = wavelength / (2 * np.sin(np.radians(np.array(angles[peaks]) / 2)))
        
        return {
            "indices": peaks.tolist(),
            "angles": angles[peaks].tolist(),
            "intensities": intensities[peaks].tolist(),
            "d_values": d_values.tolist(),
            "fwhms": fwhms if fwhms else [0.1] * len(peaks),
            "properties": {
                "peak_heights": properties["peak_heights"].tolist() if "peak_heights" in properties else [],
                "prominences": properties["prominences"].tolist() if "prominences" in properties else [],
                "widths": fwhms
            }
        }
    
    async def _match_phases(self, peaks: Dict[str, Any], params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """物相匹配"""
        matched_phases = []
        
        if not peaks["d_values"]:
            return matched_phases
        
        # 使用数据库进行匹配
        for d_value, intensity in zip(peaks["d_values"], peaks["intensities"]):
            # 搜索匹配的卡片
            matched_cards = self.db_manager.search_by_d_value(
                d_value, 
                tolerance=params["search_tolerance"]
            )
            
            for card in matched_cards[:5]:  # 取前5个匹配
                # 计算匹配分数
                match_score = self._calculate_match_score(card, peaks, params)
                
                if match_score >= 0.5:  # 阈值
                    matched_phases.append({
                        "card_num": card["card_num"],
                        "name": card.get("display_name", card.get("name", "")),
                        "formula": card.get("display_formula", card.get("formula", "")),
                        "card_type": card.get("card_type", ""),
                        "matched_d": d_value,
                        "intensity": intensity,
                        "match_score": match_score,
                        "card_info": card
                    })
        
        # 按匹配分数排序
        matched_phases.sort(key=lambda x: x["match_score"], reverse=True)
        
        # 去重（相同的卡片）
        seen_cards = set()
        unique_phases = []
        for phase in matched_phases:
            card_key = phase["card_num"]
            if card_key not in seen_cards:
                seen_cards.add(card_key)
                unique_phases.append(phase)
        
        return unique_phases[:10]  # 返回前10个
    
    def _calculate_match_score(self, card: Dict[str, Any], peaks: Dict[str, Any], params: Dict[str, Any]) -> float:
        """计算匹配分数"""
        # 获取卡片的峰数据
        card_peaks = self.db_manager.get_card_peaks(card["card_num"])
        
        if not card_peaks:
            return 0.0
        
        # 计算匹配的峰数量
        matched_count = 0
        d_errors = []
        
        for exp_d in peaks["d_values"]:
            for card_peak in card_peaks:
                card_d = card_peak["d_value"]
                if abs(exp_d - card_d) <= params["search_tolerance"]:
                    matched_count += 1
                    d_errors.append(abs(exp_d - card_d))
                    break
        
        # 计算分数
        if matched_count == 0:
            return 0.0
        
        # 匹配率
        match_rate = matched_count / len(peaks["d_values"])
        
        # d值误差分数
        avg_d_error = np.mean(d_errors) if d_errors else 0
        d_error_score = max(0, 1 - (avg_d_error / params["search_tolerance"]))
        
        # 总分数
        total_score = (match_rate * 0.6) + (d_error_score * 0.4)
        
        return total_score
    
    async def _ai_analysis(self, xrd_data: Dict[str, Any], peaks: Dict[str, Any], 
                          phases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """AI分析"""
        try:
            # 准备分析上下文
            context = {
                "data_summary": {
                    "n_points": len(xrd_data["angles"]),
                    "angle_range": f"{min(xrd_data['angles']):.1f}-{max(xrd_data['angles']):.1f}",
                    "max_intensity": max(xrd_data["intensities"]),
                    "detected_peaks": len(peaks["angles"])
                },
                "peaks": {
                    "count": len(peaks["angles"]),
                    "strongest_peaks": [
                        {"d": d, "intensity": i}
                        for d, i in zip(peaks["d_values"][:5], peaks["intensities"][:5])
                    ]
                },
                "matched_phases": [
                    {
                        "name": phase["name"],
                        "formula": phase["formula"],
                        "match_score": phase["match_score"]
                    }
                    for phase in phases[:5]
                ]
            }
            
            # 调用AI分析
            ai_result = await self.ai_assistant.analyze_xrd(context)
            
            return ai_result
            
        except Exception as e:
            print(f"AI分析失败: {e}")
            return {
                "error": str(e),
                "fallback": True,
                "analysis": "AI分析服务暂时不可用，请查看匹配结果。"
            }
    
    async def _generate_plots(self, xrd_data: Dict[str, Any], peaks: Dict[str, Any], 
                             phases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成图表"""
        try:
            plots = {}
            
            # 1. 原始数据图
            plots["raw_plot"] = await self.plot_generator.create_raw_plot(
                xrd_data["angles"], xrd_data["intensities"]
            )
            
            # 2. 带峰标记的图
            plots["peak_plot"] = await self.plot_generator.create_peak_plot(
                xrd_data["angles"], xrd_data["intensities"],
                peaks["angles"], peaks["intensities"]
            )
            
            # 3. 物相标注图
            if phases:
                phase_angles = [phase["matched_d"] for phase in phases[:5]]
                phase_names = [phase["name"] for phase in phases[:5]]
                
                plots["phase_plot"] = await self.plot_generator.create_phase_plot(
                    xrd_data["angles"], xrd_data["intensities"],
                    phase_angles, phase_names
                )
            
            # 4. 统计图
            plots["stat_plot"] = await self.plot_generator.create_statistics_plot(peaks)
            
            return plots
            
        except Exception as e:
            print(f"生成图表失败: {e}")
            return {"error": str(e)}
    
    def _calculate_statistics(self, xrd_data: Dict[str, Any], peaks: Dict[str, Any], 
                             phases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算统计信息"""
        angles = np.array(xrd_data["angles"])
        intensities = np.array(xrd_data["intensities"])
        
        # 基础统计
        stats = {
            "data_points": len(angles),
            "angle_range": {
                "min": float(np.min(angles)),
                "max": float(np.max(angles)),
                "span": float(np.max(angles) - np.min(angles))
            },
            "intensity_stats": {
                "min": float(np.min(intensities)),
                "max": float(np.max(intensities)),
                "mean": float(np.mean(intensities)),
                "std": float(np.std(intensities))
            },
            "peak_stats": {
                "count": len(peaks["angles"]),
                "avg_intensity": float(np.mean(peaks["intensities"])) if peaks["intensities"] else 0,
                "avg_fwhm": float(np.mean(peaks["fwhms"])) if peaks["fwhms"] else 0,
                "strongest_peak": {
                    "angle": float(peaks["angles"][0]) if peaks["angles"] else 0,
                    "intensity": float(peaks["intensities"][0]) if peaks["intensities"] else 0,
                    "d_value": float(peaks["d_values"][0]) if peaks["d_values"] else 0
                }
            },
            "phase_stats": {
                "matched_count": len(phases),
                "top_matches": [
                    {
                        "name": phase["name"],
                        "formula": phase["formula"],
                        "score": float(phase["match_score"])
                    }
                    for phase in phases[:3]
                ]
            }
        }
        
        return stats
    
    def _generate_report(self, file_path: str, xrd_data: Dict[str, Any], 
                        peaks: Dict[str, Any], phases: List[Dict[str, Any]],
                        ai_analysis: Dict[str, Any], statistics: Dict[str, Any],
                        params: Dict[str, Any]) -> Dict[str, Any]:
        """生成分析报告"""
        filename = Path(file_path).name
        
        report = {
            "metadata": {
                "filename": filename,
                "analysis_time": datetime.now().isoformat(),
                "parameters": params
            },
            "file_info": {
                "path": file_path,
                "size": Path(file_path).stat().st_size,
                "data_points": len(xrd_data["angles"])
            },
            "analysis_results": {
                "peaks": peaks,
                "matched_phases": phases,
                "statistics": statistics
            },
            "ai_analysis": ai_analysis,
            "summary": {
                "peak_count": len(peaks["angles"]),
                "phase_count": len(phases),
                "top_phase": phases[0]["name"] if phases else "无匹配",
                "confidence": phases[0]["match_score"] if phases else 0.0
            },
            "recommendations": self._generate_recommendations(peaks, phases, statistics)
        }
        
        return report
    
    def _generate_recommendations(self, peaks: Dict[str, Any], phases: List[Dict[str, Any]], 
                                 statistics: Dict[str, Any]) -> List[str]:
        """生成建议"""
        recommendations = []
        
        # 基于峰数量的建议
        peak_count = len(peaks["angles"])
        if peak_count < 3:
            recommendations.append("检测到的峰数量较少，建议检查数据质量或调整峰检测参数。")
        elif peak_count > 20:
            recommendations.append("检测到大量峰，可能是噪声或需要调整峰检测参数。")
        
        # 基于匹配结果的建议
        if phases:
            top_score = phases[0]["match_score"]
            if top_score > 0.8:
                recommendations.append("匹配置信度很高，结果可靠。")
            elif top_score > 0.5:
                recommendations.append("匹配置信度中等，建议进一步验证。")
            else:
                recommendations.append("匹配置信度较低，可能需要其他分析方法。")
        
        # 基于数据质量的建议
        intensity_std = statistics["intensity_stats"]["std"]
        if intensity_std < 100:
            recommendations.append("数据噪声较低，质量良好。")
        else:
            recommendations.append("数据噪声较大，建议增加平滑或背景扣除。")
        
        return recommendations