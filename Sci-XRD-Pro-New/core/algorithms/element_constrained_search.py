"""
Sci-XRD-Pro - 元素限定检索模块
==========================================
实现 JADE 风格的元素限定检索算法：

1. 元素限定检索（Elements Constrained Search）
   - 结合 XRF/EDS 元素信息
   - 过滤不可能物相
   - 大幅提升命中率

2. 元素兼容性分析
   - 检查物相元素与样品元素的一致性
   - 排除污染/杂质元素干扰

参考文献：
  - ICDD PDF-4 系列算法文档
"""

import re
import numpy as np
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict


ELEMENT_SYMBOLS = [
    'H', 'He', 'Li', 'Be', 'B', 'C', 'N', 'O', 'F', 'Ne',
    'Na', 'Mg', 'Al', 'Si', 'P', 'S', 'Cl', 'Ar', 'K', 'Ca',
    'Sc', 'Ti', 'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'Zn',
    'Ga', 'Ge', 'As', 'Se', 'Br', 'Kr', 'Rb', 'Sr', 'Y', 'Zr',
    'Nb', 'Mo', 'Tc', 'Ru', 'Rh', 'Pd', 'Ag', 'Cd', 'In', 'Sn',
    'Sb', 'Te', 'I', 'Xe', 'Cs', 'Ba', 'La', 'Ce', 'Pr', 'Nd',
    'Pm', 'Sm', 'Eu', 'Gd', 'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb',
    'Lu', 'Hf', 'Ta', 'W', 'Re', 'Os', 'Ir', 'Pt', 'Au', 'Hg',
    'Tl', 'Pb', 'Bi', 'Po', 'At', 'Rn', 'Fr', 'Ra', 'Ac', 'Th',
    'Pa', 'U', 'Np', 'Pu', 'Am', 'Cm', 'Bk', 'Cf', 'Es', 'Fm'
]

ELEMENT_WEIGHTS = {
    'H': 1.008, 'He': 4.003, 'Li': 6.941, 'Be': 9.012, 'B': 10.81,
    'C': 12.01, 'N': 14.01, 'O': 16.00, 'F': 19.00, 'Ne': 20.18,
    'Na': 22.99, 'Mg': 24.31, 'Al': 26.98, 'Si': 28.09, 'P': 30.97,
    'S': 32.07, 'Cl': 35.45, 'Ar': 39.95, 'K': 39.10, 'Ca': 40.08,
    'Sc': 44.96, 'Ti': 47.87, 'V': 50.94, 'Cr': 52.00, 'Mn': 54.94,
    'Fe': 55.85, 'Co': 58.93, 'Ni': 58.69, 'Cu': 63.55, 'Zn': 65.38,
    'Ga': 69.72, 'Ge': 72.63, 'As': 74.92, 'Se': 78.97, 'Br': 79.90,
    'Kr': 83.80, 'Rb': 85.47, 'Sr': 87.62, 'Y': 88.91, 'Zr': 91.22,
    'Nb': 92.91, 'Mo': 95.95, 'Tc': 98.00, 'Ru': 101.1, 'Rh': 102.9,
    'Pd': 106.4, 'Ag': 107.9, 'Cd': 112.4, 'In': 114.8, 'Sn': 118.7,
    'Sb': 121.8, 'Te': 127.6, 'I': 126.9, 'Xe': 131.3, 'Cs': 132.9,
    'Ba': 137.3, 'La': 138.9, 'Ce': 140.1, 'Pr': 140.9, 'Nd': 144.2,
    'Pm': 145.0, 'Sm': 150.4, 'Eu': 152.0, 'Gd': 157.3, 'Tb': 158.9,
    'Dy': 162.5, 'Ho': 164.9, 'Er': 167.3, 'Tm': 168.9, 'Yb': 173.0,
    'Lu': 175.0, 'Hf': 178.5, 'Ta': 180.9, 'W': 183.8, 'Re': 186.3,
    'Os': 190.2, 'Ir': 192.2, 'Pt': 195.1, 'Au': 197.0, 'Hg': 200.6,
    'Tl': 204.4, 'Pb': 207.2, 'Bi': 209.0, 'Po': 209.0, 'At': 210.0,
    'Rn': 222.0, 'Ra': 226.0, 'Ac': 227.0, 'Th': 232.0, 'Pa': 231.0,
    'U': 238.0
}


@dataclass
class ElementInfo:
    """元素信息"""
    symbols: Set[str] = field(default_factory=set)
    detected_elements: Set[str] = field(default_factory=set)
    excluded_elements: Set[str] = field(default_factory=set)
    optional_elements: Set[str] = field(default_factory=set)
    concentration: Dict[str, float] = field(default_factory=dict)


@dataclass
class ElementConstraintResult:
    """元素限定检索结果"""
    phase_name: str
    formula: str
    elements: List[str]
    is_compatible: bool
    missing_elements: List[str] = field(default_factory=list)
    extra_elements: List[str] = field(default_factory=list)
    compatibility_score: float = 0.0
    reason: str = ""


class ElementExtractor:
    """从化学式提取元素"""

    @staticmethod
    def extract(formula: str) -> List[str]:
        """
        从化学式提取元素列表

        Examples:
            "Al2O3" -> ['Al', 'O']
            "CaCO3" -> ['Ca', 'C', 'O']
            "Fe0.5Cr0.5" -> ['Fe', 'Cr']
        """
        if not formula:
            return []

        pattern = r'([A-Z][a-z]?)(\d*\.?\d*)?'
        matches = re.findall(pattern, formula)

        elements = []
        for elem, count in matches:
            if elem and elem in ELEMENT_SYMBOLS:
                if elem not in elements:
                    elements.append(elem)

        return elements

    @staticmethod
    def extract_with_stoichiometry(formula: str) -> Dict[str, int]:
        """提取元素及其计量数"""
        if not formula:
            return {}

        pattern = r'([A-Z][a-z]?)(\d*\.?\d*)?'
        matches = re.findall(pattern, formula)

        result = {}
        for elem, count in matches:
            if elem and elem in ELEMENT_SYMBOLS:
                n = float(count) if count else 1.0
                result[elem] = result.get(elem, 0) + n

        return result

    @staticmethod
    def formula_weight(formula: str) -> float:
        """计算化学式分子量"""
        stoichiometry = ElementExtractor.extract_with_stoichiometry(formula)
        weight = 0.0

        for elem, n in stoichiometry.items():
            weight += ELEMENT_WEIGHTS.get(elem, 0) * n

        return weight


class ElementConstraintSearch:
    """
    元素限定检索

    核心功能：
    1. 设置样品检测到的元素
    2. 设置需要排除的元素（污染、杂质）
    3. 可选设置可能存在的元素
    4. 检索时自动过滤不兼容的物相
    """

    def __init__(self):
        self.element_info = ElementInfo()
        self.strict_mode = True

    def set_detected_elements(self, elements: List[str]):
        """设置检测到的元素"""
        self.element_info.detected_elements = set(elements)
        self._validate_elements()

    def set_excluded_elements(self, elements: List[str]):
        """设置需要排除的元素"""
        self.element_info.excluded_elements = set(elements)
        self._validate_elements()

    def set_optional_elements(self, elements: List[str]):
        """设置可选存在的元素"""
        self.element_info.optional_elements = set(elements)
        self._validate_elements()

    def set_elements_from_concentration(self, concentration: Dict[str, float],
                                       threshold: float = 0.1):
        """从浓度数据设置元素（浓度>threshold%视为检测到）"""
        detected = [elem for elem, conc in concentration.items()
                   if conc >= threshold]
        self.set_detected_elements(detected)

    def _validate_elements(self):
        """验证元素符号的有效性"""
        all_valid = set(ELEMENT_SYMBOLS)

        self.element_info.detected_elements &= all_valid
        self.element_info.excluded_elements &= all_valid
        self.element_info.optional_elements &= all_valid

    def check_phase_compatibility(self, phase: Dict) -> ElementConstraintResult:
        """
        检查物相与元素约束的兼容性

        Args:
            phase: 物相信息，包含 'formula', 'name' 等字段

        Returns:
            ElementConstraintResult
        """
        formula = phase.get('formula', '')
        name = phase.get('name', 'Unknown')

        phase_elements = set(ElementExtractor.extract(formula))

        result = ElementConstraintResult(
            phase_name=name,
            formula=formula,
            elements=list(phase_elements),
            is_compatible=False
        )

        if not phase_elements:
            result.reason = "无法解析化学式"
            return result

        detected = self.element_info.detected_elements
        excluded = self.element_info.excluded_elements
        optional = self.element_info.optional_elements

        if not detected:
            result.is_compatible = True
            result.reason = "无元素约束"
            result.compatibility_score = 50.0
            return result

        if excluded:
            conflicting = phase_elements & excluded
            if conflicting:
                result.is_compatible = False
                result.extra_elements = list(conflicting)
                result.reason = f"包含排除元素: {', '.join(conflicting)}"
                result.compatibility_score = 0.0
                return result

        required = detected - optional
        missing = required - phase_elements

        if self.strict_mode and missing:
            result.is_compatible = False
            result.missing_elements = list(missing)
            result.reason = f"缺少必需元素: {', '.join(missing)}"
            result.compatibility_score = 20.0
            return result

        extra = phase_elements - detected - optional

        score = 100.0
        if extra:
            score -= len(extra) * 15
        if missing:
            score -= len(missing) * 10

        score = max(0, min(100, score))

        result.is_compatible = score >= 50
        result.extra_elements = list(extra) if extra else []
        result.compatibility_score = score
        result.reason = "元素兼容" if score >= 50 else "元素不匹配"

        return result

    def filter_database(self, phases: List[Dict]) -> List[Dict]:
        """
        过滤数据库，只保留兼容的物相

        Args:
            phases: 物相列表

        Returns:
            过滤后的物相列表
        """
        compatible_phases = []
        compatibility_info = {}

        for phase in phases:
            result = self.check_phase_compatibility(phase)
            if result.is_compatible:
                compatible_phases.append(phase)
                compatibility_info[phase.get('name', '')] = result

        return compatible_phases

    def rank_phases(self, phases: List[Dict]) -> List[Tuple[Dict, ElementConstraintResult]]:
        """
        对物相进行元素兼容性排序

        Returns:
            [(phase, result), ...] 按兼容性评分降序
        """
        results = []

        for phase in phases:
            result = self.check_phase_compatibility(phase)
            results.append((phase, result))

        results.sort(key=lambda x: x[1].compatibility_score, reverse=True)
        return results

    def get_element_summary(self) -> Dict:
        """获取元素约束摘要"""
        return {
            'detected': sorted(self.element_info.detected_elements),
            'excluded': sorted(self.element_info.excluded_elements),
            'optional': sorted(self.element_info.optional_elements),
            'all_constraints': sorted(
                self.element_info.detected_elements |
                self.element_info.excluded_elements |
                self.element_info.optional_elements
            )
        }


class ElementConstrainedMatcher:
    """
    元素约束匹配器

    将元素约束与峰匹配算法结合，提高检索准确度
    """

    def __init__(self, base_matcher=None):
        self.constraint_search = ElementConstraintSearch()
        self.base_matcher = base_matcher

    def set_elements(self, elements: List[str] = None,
                    concentration: Dict[str, float] = None,
                    excluded: List[str] = None):
        """设置元素信息"""
        if concentration:
            self.constraint_search.set_elements_from_concentration(concentration)

        if elements:
            self.constraint_search.set_detected_elements(elements)

        if excluded:
            self.constraint_search.set_excluded_elements(excluded)

    def match_with_constraints(self, peaks: List,
                               phases: List[Dict],
                               top_n: int = 10,
                               min_score: float = 20.0) -> List[Dict]:
        """
        带元素约束的匹配

        Args:
            peaks: 峰列表
            phases: 物相列表
            top_n: 返回前N个
            min_score: 最低分数阈值

        Returns:
            匹配结果列表
        """
        ranked = self.constraint_search.rank_phases(phases)

        if self.base_matcher and hasattr(self.base_matcher, 'match'):
            base_results = self.base_matcher.match(peaks, top_n=top_n*2, min_score=min_score*0.5)

            combined_results = []
            for base_r in base_results:
                phase_name = base_r.get('name', '')
                for phase, constraint_result in ranked:
                    if phase.get('name', '') == phase_name:
                        combined_score = base_r.get('score', 0) * (constraint_result.compatibility_score / 100)

                        combined_r = base_r.copy()
                        combined_r['element_score'] = constraint_result.compatibility_score
                        combined_r['element_reason'] = constraint_result.reason
                        combined_r['combined_score'] = combined_score
                        combined_r['is_element_compatible'] = constraint_result.is_compatible

                        combined_results.append(combined_r)
                        break

            combined_results.sort(key=lambda x: x.get('combined_score', 0), reverse=True)
            return combined_results[:top_n]

        else:
            filtered = self.constraint_search.filter_database(phases)
            return filtered[:top_n]


def extract_elements_from_formula(formula: str) -> List[str]:
    """便捷函数：提取化学式中的元素"""
    return ElementExtractor.extract(formula)


def calculate_formula_weight(formula: str) -> float:
    """便捷函数：计算化学式分子量"""
    return ElementExtractor.formula_weight(formula)


def check_element_compatibility(phase: Dict,
                               detected_elements: List[str],
                               excluded_elements: List[str] = None) -> ElementConstraintResult:
    """便捷函数：检查物相元素兼容性"""
    search = ElementConstraintSearch()
    search.set_detected_elements(detected_elements)

    if excluded_elements:
        search.set_excluded_elements(excluded_elements)

    return search.check_phase_compatibility(phase)
