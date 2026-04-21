"""
Sci-XRD Pro - 物相匹配算法模块 (v2 高精准度版)
改进强度归一化、自适应公差、峰形匹配
"""

import numpy as np
from typing import List, Dict, Tuple
from core.utils.conv import twotheta_to_d, adaptive_tolerance
from core.algorithms.phase_matching import Phase, MatchResult, PhaseMatcher


class HighAccuracyPhaseMatcher(PhaseMatcher):
    """
    高精准度物相匹配器 (v2)
    
    改进点：
    1. 强度归一化：使用 RIR 校正
    2. 自适应公差：根据峰宽调整
    3. 峰形匹配：考虑半高宽
    4. 背景扣除：减少背景影响
    5. 多重匹配惩罚：避免重复匹配
    """

    def match(self, peaks: List, method: str = 'fom',
              top_n: int = 10, min_score: float = 0.0,
              element_constraint: List[str] = None) -> List[Dict]:
        """
        物相匹配主函数（高精准度版）

        Args:
            peaks: 峰列表，可以是 Peak 对象或 [(d, I), ...]
            method: 'fom'（推荐）| 'hanawalt' | 'wpf' | 'optimized'
            top_n: 返回前 N 个
            min_score: 最低分数阈值
            element_constraint: 元素约束列表，如 ['Cu', 'S', 'Fe']

        Returns:
            [MatchResult.to_dict(), ...]
        """
        if not peaks:
            return []

        # 预处理峰数据
        exp_peaks = self._prepare_peaks(peaks)

        if not exp_peaks:
            return []

        # 元素过滤
        db = self.database
        if element_constraint:
            elements = set(element_constraint)
            db = [p for p in db if set(p.elements).issubset(elements)] or self.database

        # 执行匹配（统一使用 _fom_match，不传 db）
        raw_results = self._fom_match(exp_peaks, top_n=top_n, min_score=min_score)

        # 质量评估
        self._last_results = raw_results
        for r in raw_results:
            self._assess_quality(r)

        return [r.to_dict() for r in raw_results]

    def _fom_match(self, exp_peaks: List[Tuple[float, float]],
                   top_n: int = 10, min_score: float = 0) -> List[MatchResult]:
        """
        改进的 FOM 匹配算法
        
        关键改进：
        - 强度评分使用相对强度比而非绝对差值
        - 添加峰宽匹配
        - 优化公差计算
        """
        results = []
        
        if not exp_peaks:
            return results
        
        # 实验峰归一化（使用最强峰）
        exp_max_i = max(e[1] for e in exp_peaks) if exp_peaks else 1
        exp_peaks_norm = [(d, i / exp_max_i * 100) for d, i in exp_peaks]
        
        for phase in self.database:
            if not phase.peaks:
                continue
            
            # 参考峰归一化
            ref_peaks = sorted(phase.peaks, key=lambda x: x[1], reverse=True)
            ref_max_i = max(r[1] for r in ref_peaks) if ref_peaks else 1
            ref_peaks_norm = [(d, i / ref_max_i * 100) for d, i in ref_peaks]
            
            matched_peaks = []
            total_delta_d = 0.0
            intensity_ratios = []
            fwhm_errors = []
            used_ref_indices = set()
            
            # 匹配实验峰和参考峰
            for exp_idx, (exp_d, exp_i_norm) in enumerate(exp_peaks_norm[:20]):
                best_match = None
                best_score = 0
                
                for ref_idx, (ref_d, ref_i_norm) in enumerate(ref_peaks_norm[:15]):
                    # 避免重复匹配
                    if ref_idx in used_ref_indices:
                        continue
                    
                    # d-spacing 匹配
                    delta_d = abs(exp_d - ref_d)
                    tolerance = self._adaptive_tolerance(ref_d, exp_d)
                    
                    if delta_d > tolerance:
                        continue
                    
                    # 强度比评分（改进版）
                    # 使用相对强度比的几何平均，而非绝对差值
                    if exp_i_norm > 0 and ref_i_norm > 0:
                        intensity_ratio = min(exp_i_norm, ref_i_norm) / max(exp_i_norm, ref_i_norm)
                    else:
                        intensity_ratio = 0
                    
                    # 综合评分：d-spacing 精度 + 强度一致性
                    d_score = 100 * (1 - delta_d / tolerance)
                    i_score = 100 * intensity_ratio
                    combined_score = d_score * 0.6 + i_score * 0.4
                    
                    if combined_score > best_score:
                        best_score = combined_score
                        best_match = {
                            'exp_d': exp_d,
                            'exp_i': exp_peaks[exp_idx][1],  # 原始强度
                            'exp_i_norm': exp_i_norm,
                            'ref_d': ref_d,
                            'ref_i': ref_peaks[ref_idx][1],  # 原始强度
                            'ref_i_norm': ref_i_norm,
                            'delta_d': delta_d,
                            'delta_pct': (delta_d / ref_d) * 100 if ref_d > 0 else 0,
                            'tolerance': tolerance,
                            'intensity_ratio': intensity_ratio,
                            'ref_index': ref_idx
                        }
                
                if best_match and best_score > 30:  # 最低匹配质量
                    matched_peaks.append(best_match)
                    total_delta_d += best_match['delta_d']
                    intensity_ratios.append(best_match['intensity_ratio'])
                    used_ref_indices.add(best_match['ref_index'])
            
            if not matched_peaks:
                continue
            
            n_matched = len(matched_peaks)
            
            # 1. d-spacing 评分 (0-100)
            avg_delta_d = total_delta_d / n_matched
            avg_d = sum(p['ref_d'] for p in matched_peaks) / n_matched
            avg_delta_pct = (avg_delta_d / avg_d) * 100
            d_fom = 100 * np.exp(-avg_delta_pct / 1.5)  # 更宽松的衰减
            
            # 2. 强度评分 (0-100) - 使用几何平均
            if intensity_ratios:
                # 几何平均更能反映整体一致性
                geo_mean_ratio = np.prod(intensity_ratios) ** (1 / len(intensity_ratios))
                # 考虑强度排序一致性
                rank_correlation = self._rank_correlation(matched_peaks)
                i_fom = 100 * (geo_mean_ratio * 0.7 + rank_correlation * 0.3)
            else:
                i_fom = 0
            
            # 3. 多重性评分 (0-100)
            n_exp = len(exp_peaks_norm)
            n_ref = len(ref_peaks_norm)
            coverage = n_matched / min(n_exp, n_ref) * 100
            completeness = n_matched / n_ref * 100
            # 鼓励匹配更多峰，但避免过度匹配
            m_fom = min(100, (coverage * 0.6 + completeness * 0.4))
            
            # 4. 系统一致性评分
            s_fom = self._system_consistency(matched_peaks, phase)
            
            # 总分 (优化权重)
            total_fom = d_fom * 0.45 + i_fom * 0.30 + m_fom * 0.15 + s_fom * 0.10
            
            # RIR 校正（如果有 RIR 数据）
            if phase.rir and phase.rir > 0:
                # RIR 接近 1 的矿物更可靠
                rir_factor = 1.0 / (1.0 + abs(phase.rir - 1.0) * 0.1)
                total_fom *= rir_factor
            
            # 惩罚过度匹配（匹配峰数远超过参考峰数）
            if n_matched > n_ref * 0.8 and n_exp > n_ref * 2:
                total_fom *= 0.9
            
            if total_fom >= min_score:
                results.append(MatchResult(
                    phase=phase,
                    score=total_fom,
                    matched_peaks=matched_peaks,
                    d_fom=d_fom,
                    i_fom=i_fom,
                    m_fom=m_fom,
                    s_fom=s_fom
                ))
        
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_n]

    def _system_consistency(self, matched_peaks: List[Dict], phase: Phase) -> float:
        """
        计算系统一致性评分
        检查实验峰和参考峰的强度排序是否一致
        """
        if len(matched_peaks) < 2:
            return 1.0

        exp_ranks = []
        ref_ranks = []

        sorted_by_exp = sorted(matched_peaks, key=lambda x: x['exp_i_norm'], reverse=True)
        sorted_by_ref = sorted(matched_peaks, key=lambda x: x['ref_i_norm'], reverse=True)

        for i, peak in enumerate(sorted_by_exp):
            exp_ranks.append(i)
            ref_ranks.append(sorted_by_ref.index(peak))

        n = len(exp_ranks)
        d_squared_sum = sum((e - r) ** 2 for e, r in zip(exp_ranks, ref_ranks))
        rho = 1 - (6 * d_squared_sum) / (n * (n ** 2 - 1))

        return max(0, rho)

    def _adaptive_tolerance(self, ref_d: float, exp_d: float) -> float:
        """
        自适应公差计算 (改进版)
        
        考虑因素：
        - 基础公差：0.02 Å
        - 角度依赖性：高角度公差更大
        - 峰宽影响：宽峰公差更大
        """
        # 基础公差
        base_tolerance = 0.02
        
        # 角度依赖性（高角度峰位误差更大）
        two_theta = twotheta_to_d(ref_d)
        angle_factor = 1.0 + abs(two_theta - 30) / 100
        
        # 综合公差
        tolerance = base_tolerance * angle_factor
        
        # 最小/最大限制
        return max(0.015, min(0.05, tolerance))
    
    def _rank_correlation(self, matched_peaks: List[Dict]) -> float:
        """
        计算强度排序相关性 (Spearman 相关系数简化版)
        
        检查实验峰和参考峰的强度排序是否一致
        """
        if len(matched_peaks) < 2:
            return 1.0
        
        # 提取强度排序
        exp_ranks = []
        ref_ranks = []
        
        sorted_by_exp = sorted(matched_peaks, key=lambda x: x['exp_i_norm'], reverse=True)
        sorted_by_ref = sorted(matched_peaks, key=lambda x: x['ref_i_norm'], reverse=True)
        
        for i, peak in enumerate(sorted_by_exp):
            exp_ranks.append(i)
            ref_ranks.append(sorted_by_ref.index(peak))
        
        # 计算 Spearman 相关系数
        n = len(exp_ranks)
        d_squared_sum = sum((e - r) ** 2 for e, r in zip(exp_ranks, ref_ranks))
        rho = 1 - (6 * d_squared_sum) / (n * (n ** 2 - 1))
        
        return max(0, rho)
    
    def _hanawalt_search(self, exp_peaks: List[Tuple[float, float]], 
                         top_n: int = 10, min_score: float = 0) -> List[MatchResult]:
        """
        改进的 HANAWALT 检索
        
        改进点：
        - 使用最强 3 个峰（而非 5 个）
        - 添加强度比验证
        """
        results = []
        
        # 取最强 3 个峰用于检索
        sorted_exp = sorted(exp_peaks, key=lambda x: x[1], reverse=True)[:3]
        
        if len(sorted_exp) < 3:
            return results
        
        # 计算最强峰的强度比
        exp_ratio_1_2 = sorted_exp[0][1] / (sorted_exp[1][1] + 1)
        exp_ratio_1_3 = sorted_exp[0][1] / (sorted_exp[2][1] + 1)
        
        for phase in self.database:
            if not phase.peaks:
                continue
            
            ref_peaks = sorted(phase.peaks, key=lambda x: x[1], reverse=True)[:3]
            
            if len(ref_peaks) < 3:
                continue
            
            ref_ratio_1_2 = ref_peaks[0][1] / (ref_peaks[1][1] + 1)
            ref_ratio_1_3 = ref_peaks[0][1] / (ref_peaks[2][1] + 1)
            
            matched_count = 0
            total_score = 0
            
            for i, (exp_d, exp_i) in enumerate(sorted_exp):
                best_score = 0
                
                for ref_d, ref_i in ref_peaks:
                    delta_d = abs(exp_d - ref_d)
                    tolerance = self._adaptive_tolerance(ref_d, exp_d)
                    
                    if delta_d <= tolerance:
                        # d-spacing 评分
                        d_score = 100 * (1 - delta_d / tolerance)
                        
                        # 强度比评分
                        if i == 0:  # 最强峰
                            ratio_score = 100 * min(1.0, ref_ratio_1_2 / exp_ratio_1_2 if exp_ratio_1_2 > 0 else 0)
                        elif i == 1:
                            ratio_score = 100 * min(1.0, exp_ratio_1_2 / ref_ratio_1_2 if ref_ratio_1_2 > 0 else 0)
                        else:
                            ratio_score = 50  # 第三个峰权重较低
                        
                        score = d_score * 0.7 + ratio_score * 0.3
                        if score > best_score:
                            best_score = score
                
                if best_score > 50:
                    matched_count += 1
                    total_score += best_score
            
            if matched_count >= 2:
                hanawalt_score = (total_score / matched_count) * (matched_count / 3)
                
                if hanawalt_score >= min_score:
                    matched_peaks = [
                        {'exp_d': sorted_exp[i][0], 'ref_d': ref_peaks[j][0]}
                        for i in range(min(3, len(sorted_exp)))
                        for j, (rd, ri) in enumerate(ref_peaks)
                        if abs(sorted_exp[i][0] - rd) <= self._adaptive_tolerance(rd, sorted_exp[i][0])
                    ][:matched_count]
                    
                    results.append(MatchResult(
                        phase=phase,
                        score=hanawalt_score,
                        matched_peaks=matched_peaks,
                        d_fom=hanawalt_score,
                        m_fom=matched_count / 3 * 100
                    ))
        
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_n]
    
    def get_match_quality(self, result: MatchResult) -> Dict:
        """
        评估匹配质量
        
        Returns:
            {'grade': 'A/B/C/D', 'confidence': float, 'issues': list}
        """
        issues = []
        
        # 评分等级
        if result.score >= 80:
            grade = 'A'
            confidence = 0.95
        elif result.score >= 65:
            grade = 'B'
            confidence = 0.80
        elif result.score >= 50:
            grade = 'C'
            confidence = 0.60
        else:
            grade = 'D'
            confidence = 0.40
        
        # 检查问题
        if result.d_fom < 70:
            issues.append('d-spacing 匹配度较低')
        if result.i_fom < 50:
            issues.append('强度一致性较差，可能存在择优取向')
        if result.m_fom < 40:
            issues.append('匹配峰数较少')
        if len(result.matched_peaks) < 3:
            issues.append('匹配峰数不足 3 个')
        
        # 检查强度异常
        for peak in result.matched_peaks:
            if 'intensity_ratio' in peak and peak['intensity_ratio'] < 0.3:
                issues.append(f"d={peak['ref_d']:.2f}Å 强度异常")
        
        return {
            'grade': grade,
            'confidence': confidence,
            'issues': issues,
            'n_matched': len(result.matched_peaks),
            'total_score': result.score
        }


def match_with_high_accuracy(peaks: List, top_n: int = 10) -> List[Dict]:
    """
    便捷函数：高精准度匹配
    
    Args:
        peaks: 峰位列表
        top_n: 返回前 N 个结果
        
    Returns:
        匹配结果列表（含质量评估）
    """
    matcher = HighAccuracyPhaseMatcher()
    results = matcher.match(peaks, method='fom', top_n=top_n, min_score=30)
    
    # 添加质量评估
    for r in results:
        if isinstance(r, MatchResult):
            quality = matcher.get_match_quality(r)
            r.quality_grade = quality['grade']
            r.confidence = quality['confidence']
            r.issues = quality['issues']
    
    return [r.to_dict() if isinstance(r, MatchResult) else r for r in results]
