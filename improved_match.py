# -*- coding: utf-8 -*-
"""
改进的 XRD 物相匹配算法
======================
包含：
  1. 强度比例验证
  2. 元素过滤
  3. 自适应容差
  4. 多峰同时匹配
  5. 综合评分系统
"""

import re
import math
import json
from typing import List, Dict, Tuple, Optional

# =============================================================================
# 1. 化学式解析
# =============================================================================

def parse_formula(formula: str) -> List[str]:
    """
    解析化学式为元素列表
    例如: "Cu Fe S2" -> ["Cu", "Fe", "S"]
          "CaCO3" -> ["Ca", "C", "O"]
    """
    if not formula:
        return []
    
    # 处理空格分隔格式: "Cu Fe S2"
    if ' ' in formula:
        parts = formula.split()
        elements = []
        for p in parts:
            # 移除数字
            element = re.sub(r'\d+', '', p).strip()
            if element and element[0].isupper():
                elements.append(element)
        return elements
    
    # 处理标准化学式: "CaCO3", "Fe2O3"
    # 匹配: 大写字母 + 可选小写字母 + 可选数字
    pattern = r'([A-Z][a-z]?)(\d*)'
    matches = re.findall(pattern, formula)
    
    elements = []
    for element, count in matches:
        if element:
            elements.append(element)
    
    return elements


def formula_contains_elements(formula: str, required_elements: List[str]) -> bool:
    """
    检查化学式是否包含所需元素
    """
    formula_elements = set(parse_formula(formula))
    required = set(e.strip().title() for e in required_elements)
    
    # 全部 required 元素必须在 formula 中
    return required.issubset(formula_elements)


# =============================================================================
# 2. 自适应容差
# =============================================================================

def adaptive_tolerance(d_spacing: float, wavelength: float = 1.5406) -> float:
    """
    根据 d-spacing 计算自适应容差
    
    高角度 (小 d 值) 需要更严格容差
    因为 Δd/d = -cot(θ) × Δθ
    
    参数:
        d_spacing: d 值 (Å)
        wavelength: 辐射波长 (Å), 默认 Cu Kα
    
    返回:
        容差 (d 的相对误差)
    """
    try:
        # 计算 2θ
        # Bragg law: nλ = 2d sin(θ) -> sin(θ) = λ/(2d)
        sin_theta = wavelength / (2 * d_spacing)
        
        if sin_theta >= 1.0:
            # 超出物理范围，使用默认容差
            return 0.02
        
        theta = math.asin(sin_theta)
        two_theta = math.degrees(2 * theta)
        
        # 自适应容差曲线
        if two_theta >= 80:
            return 0.008  # 0.8% - 超高角度
        elif two_theta >= 60:
            return 0.01   # 1% - 高角度
        elif two_theta >= 40:
            return 0.015  # 1.5% - 中角度
        elif two_theta >= 20:
            return 0.02   # 2% - 低角度
        else:
            return 0.025  # 2.5% - 极低角度
    
    except (ValueError, ZeroDivisionError):
        return 0.02  # 默认容差


def calculate_d_tolerance(d_spacing: float, tolerance_pct: float = None) -> float:
    """
    计算绝对的 d 容差
    
    参数:
        d_spacing: d 值 (Å)
        tolerance_pct: 百分比容差 (默认根据角度自适应)
    
    返回:
        绝对 d 容差 (Å)
    """
    if tolerance_pct is None:
        tolerance_pct = adaptive_tolerance(d_spacing)
    
    return d_spacing * tolerance_pct


# =============================================================================
# 3. 峰匹配核心函数
# =============================================================================

def match_single_peak(exp_d: float, ref_d: float, wavelength: float = 1.5406) -> Tuple[bool, float]:
    """
    单个峰匹配检查
    
    返回: (是否匹配, 匹配分数 0-1)
    """
    tol = adaptive_tolerance(ref_d, wavelength)
    diff = abs(exp_d - ref_d)
    rel_diff = diff / ref_d
    
    if rel_diff <= tol:
        # 匹配分数: 1 - (实际差异 / 最大容差)
        score = 1 - (rel_diff / tol)
        return True, score
    else:
        return False, 0.0


def match_peaks_with_tolerance(
    exp_peaks: List[Tuple[float, float]],
    ref_peaks: List[Tuple[float, float]],
    min_match_ratio: float = 0.5,
    wavelength: float = 1.5406
) -> Tuple[int, float]:
    """
    峰列表匹配，返回匹配数量和总分
    
    参数:
        exp_peaks: 实验峰列表 [(d, I), ...]
        ref_peaks: 参考峰列表 [(d, I), ...]
        min_match_ratio: 最小匹配比例
        wavelength: 辐射波长
    
    返回: (匹配峰数, 总分 0-100)
    """
    if not exp_peaks or not ref_peaks:
        return 0, 0.0
    
    # 归一化强度到 0-100
    exp_max = max(I for d, I in exp_peaks) or 1
    ref_max = max(I for d, I in ref_peaks) or 1
    
    matched_count = 0
    total_score = 0.0
    
    for exp_d, exp_I in exp_peaks:
        best_match = None
        best_score = 0.0
        
        for ref_d, ref_I in ref_peaks:
            matched, score = match_single_peak(exp_d, ref_d, wavelength)
            if matched:
                # 强度相似度
                exp_norm = exp_I / exp_max
                ref_norm = ref_I / ref_max
                intensity_sim = 1 - abs(exp_norm - ref_norm)
                
                # 综合分数 = d匹配 × 强度匹配
                combined_score = score * (0.7 + 0.3 * intensity_sim)
                
                if combined_score > best_score:
                    best_score = combined_score
                    best_match = ref_d
        
        if best_match:
            matched_count += 1
            total_score += best_score
    
    # 要求至少匹配一定比例的峰
    required_matches = int(len(exp_peaks) * min_match_ratio)
    if matched_count < required_matches:
        return 0, 0.0
    
    # 归一化分数
    max_possible = len(exp_peaks)
    normalized_score = (total_score / max_possible) * 100
    
    return matched_count, normalized_score


# =============================================================================
# 4. 综合评分系统
# =============================================================================

def calculate_comprehensive_score(
    exp_peaks: List[Tuple[float, float]],
    ref_peaks: List[Tuple[float, float]],
    formula: str = None,
    required_elements: List[str] = None,
    wavelength: float = 1.5406
) -> Dict:
    """
    综合评分系统
    
    评分因子:
      1. d-spacing 匹配度 (权重 50%)
      2. 强度比例吻合度 (权重 30%)
      3. 元素一致性 (权重 20%)
    
    参数:
        exp_peaks: 实验峰 [(d, I), ...]
        ref_peaks: 参考峰 [(d, I), ...]
        formula: 参考矿物化学式
        required_elements: 用户指定的必需元素
        wavelength: 辐射波长
    
    返回:
        评分结果字典
    """
    result = {
        'matched_peaks': 0,
        'total_peaks': len(exp_peaks),
        'd_score': 0.0,        # d 匹配分数 (0-100)
        'intensity_score': 0.0,  # 强度分数 (0-100)
        'element_score': 0.0,   # 元素分数 (0-100)
        'final_score': 0.0,      # 综合分数 (0-100)
        'matched_d_values': [],  # 匹配的 d 值列表
    }
    
    if not exp_peaks or not ref_peaks:
        return result
    
    # 归一化强度
    exp_max = max(I for d, I in exp_peaks) or 1
    ref_max = max(I for d, I in ref_peaks) or 1
    
    d_scores = []
    intensity_scores = []
    matched_d = []
    
    for exp_d, exp_I in exp_peaks:
        exp_norm = exp_I / exp_max
        
        best_d_score = 0.0
        best_intensity_score = 0.0
        best_ref_d = None
        
        for ref_d, ref_I in ref_peaks:
            # d 匹配
            tol = adaptive_tolerance(ref_d, wavelength)
            diff = abs(exp_d - ref_d)
            rel_diff = diff / ref_d
            
            if rel_diff <= tol:
                d_score = 1 - (rel_diff / tol)
                
                # 强度匹配
                ref_norm = ref_I / ref_max
                intensity_sim = 1 - abs(exp_norm - ref_norm)
                
                combined = d_score * (0.6 + 0.4 * intensity_sim)
                
                if combined > best_d_score:
                    best_d_score = combined
                    best_intensity_score = intensity_sim
                    best_ref_d = ref_d
        
        if best_ref_d is not None:
            d_scores.append(best_d_score)
            intensity_scores.append(best_intensity_score)
            matched_d.append(best_ref_d)
    
    # 计算 d 匹配分数
    if d_scores:
        result['d_score'] = sum(d_scores) / len(d_scores) * 100
        result['intensity_score'] = sum(intensity_scores) / len(intensity_scores) * 100
        result['matched_peaks'] = len(d_scores)
        result['matched_d_values'] = matched_d
    
    # 元素分数
    if required_elements and formula:
        if formula_contains_elements(formula, required_elements):
            result['element_score'] = 100.0
        else:
            result['element_score'] = 0.0
    else:
        result['element_score'] = 100.0  # 无元素要求时给满分
    
    # 综合评分
    # 权重: d匹配50%, 强度30%, 元素20%
    result['final_score'] = (
        result['d_score'] * 0.5 +
        result['intensity_score'] * 0.3 +
        result['element_score'] * 0.2
    )
    
    return result


# =============================================================================
# 5. 完整匹配函数
# =============================================================================

class XRDMatcher:
    """
    XRD 物相匹配器
    """
    
    def __init__(self, reference_db: Dict = None):
        """
        参数:
            reference_db: 参考数据库，格式 {
                "矿物名": {
                    "formula": "化学式",
                    "peaks": [(d, I), ...]
                }, ...
            }
        """
        self.db = reference_db or {}
    
    def set_database(self, db: Dict):
        """设置参考数据库"""
        self.db = db
    
    def match(
        self,
        exp_peaks: List[Tuple[float, float]],
        required_elements: List[str] = None,
        min_score: float = 30.0,
        min_peaks: int = 2,
        wavelength: float = 1.5406
    ) -> List[Dict]:
        """
        匹配实验峰与参考库
        
        参数:
            exp_peaks: 实验峰列表 [(d, I), ...]
            required_elements: 必需元素列表
            min_score: 最小综合分数阈值
            min_peaks: 最小匹配峰数
            wavelength: 辐射波长
        
        返回:
            排序后的匹配结果列表
        """
        results = []
        
        for name, data in self.db.items():
            ref_peaks = data.get('peaks', [])
            formula = data.get('formula', '')
            
            # 元素过滤
            if required_elements:
                if not formula_contains_elements(formula, required_elements):
                    continue
            
            # 综合评分
            score_result = calculate_comprehensive_score(
                exp_peaks, ref_peaks, formula, required_elements, wavelength
            )
            
            # 阈值过滤
            if score_result['final_score'] >= min_score:
                if score_result['matched_peaks'] >= min_peaks:
                    results.append({
                        'name': name,
                        'formula': formula,
                        'score': score_result['final_score'],
                        'matched_peaks': score_result['matched_peaks'],
                        'total_peaks': score_result['total_peaks'],
                        'd_score': score_result['d_score'],
                        'intensity_score': score_result['intensity_score'],
                        'element_score': score_result['element_score'],
                        'matched_d': score_result['matched_d_values'],
                    })
        
        # 按分数降序排序
        results.sort(key=lambda x: x['score'], reverse=True)
        
        return results


# =============================================================================
# 6. 演示
# =============================================================================

def demo():
    """演示改进的匹配算法"""
    
    # 示例参考数据库
    reference_db = {
        "Chalcopyrite": {
            "formula": "Cu Fe S2",
            "peaks": [(3.030, 100), (1.860, 83), (1.590, 20), (1.210, 7), (2.620, 7)],
        },
        "Pyrite": {
            "formula": "Fe S2", 
            "peaks": [(2.710, 100), (2.420, 85), (2.090, 60), (1.630, 50), (1.560, 40)],
        },
        "Quartz": {
            "formula": "Si O2",
            "peaks": [(3.350, 100), (4.250, 25), (1.820, 25), (1.540, 20), (2.450, 15)],
        },
        "Calcite": {
            "formula": "Ca C O3",
            "peaks": [(3.040, 100), (2.280, 40), (2.090, 30), (1.910, 25), (1.870, 20)],
        },
    }
    
    # 模拟实验数据 (假设的测试样品)
    # 铜硫矿样品: 黄铜矿 + 黄铁矿 + 石英
    exp_peaks = [
        (3.035, 100),   # 接近 Chalcopyrite 3.030
        (1.858, 85),   # 接近 Chalcopyrite 1.860
        (2.715, 90),   # 接近 Pyrite 2.710
        (2.425, 80),   # 接近 Pyrite 2.420
        (3.348, 30),   # 接近 Quartz 3.350
    ]
    
    # 演示1: 无元素过滤
    print("="*60)
    print("演示1: 无元素过滤")
    print("="*60)
    
    matcher = XRDMatcher(reference_db)
    results = matcher.match(exp_peaks, min_score=20.0)
    
    for r in results[:5]:
        print(f"\n{r['name']} ({r['formula']})")
        print(f"  综合分数: {r['score']:.1f}")
        print(f"  匹配峰数: {r['matched_peaks']}/{r['total_peaks']}")
        print(f"  d分数: {r['d_score']:.1f}, 强度分数: {r['intensity_score']:.1f}")
        print(f"  匹配的d值: {r['matched_d']}")
    
    # 演示2: 元素过滤
    print("\n" + "="*60)
    print("演示2: 只看 Cu-Fe-S 体系矿物")
    print("="*60)
    
    results = matcher.match(exp_peaks, required_elements=['Cu', 'Fe', 'S'])
    
    for r in results:
        print(f"\n{r['name']} ({r['formula']})")
        print(f"  综合分数: {r['score']:.1f}, 匹配峰: {r['matched_peaks']}")
    
    # 演示3: 自适应容差
    print("\n" + "="*60)
    print("演示3: 自适应容差演示")
    print("="*60)
    
    test_d = [0.8, 1.5, 2.0, 3.0, 4.0, 5.0]
    print(f"{'d(Å)':<8} {'2θ(°)':<10} {'容差(%)':<10}")
    print("-"*30)
    for d in test_d:
        tol = adaptive_tolerance(d)
        sin_theta = 1.5406 / (2 * d)
        theta = math.degrees(math.asin(sin_theta)) if sin_theta < 1 else 90
        two_theta = 2 * theta
        print(f"{d:<8.3f} {two_theta:<10.1f} {tol*100:<10.1f}")


if __name__ == "__main__":
    demo()
