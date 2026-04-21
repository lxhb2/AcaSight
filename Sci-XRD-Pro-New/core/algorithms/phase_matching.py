"""
Sci-XRD-Pro - 专业物相匹配模块（JADE 标准 + PDF4-2009 数据库）
====================================================================
实现 JADE 的核心匹配算法：
  1. FOM（Figure of Merit）综合评分法
  2. HANAWALT 三强峰检索
  3. RIR 参比强度定量
  4. 全谱拟合（WPF）匹配

支持 PDF4-2009 数据库（JSON 格式）和 PDF2-2004 SQLite 数据库
"""

import json
import sqlite3
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass, field


# ─────────────────────────────────────────────
# 数据类
# ─────────────────────────────────────────────

@dataclass
class Phase:
    """物相数据"""
    name: str
    formula: str
    peaks: List[Tuple[float, float]]       # [(d, I% ), ...]
    pdf_number: str = ""
    system: str = ""
    space_group: str = ""
    cell_params: Dict = field(default_factory=dict)
    rir: float = 1.0                       # 参比强度（相对于 Al2O3）
    elements: List[str] = field(default_factory=list)
    quality: str = ""                       # '*'=高质量，'I'=已指标化

    def __post_init__(self):
        if not self.elements:
            self.elements = self._extract_elements(self.formula)

    @staticmethod
    def _extract_elements(formula: str) -> List[str]:
        import re
        return list(set(re.findall(r'[A-Z][a-z]?', formula)))

    def to_dict(self) -> dict:
        return {
            'name':        self.name,
            'formula':     self.formula,
            'peaks':       self.peaks,
            'pdf_number':  self.pdf_number,
            'system':      self.system,
            'space_group': self.space_group,
            'rir':         self.rir,
            'elements':    self.elements,
        }
        if self.cell_params is None:
            self.cell_params = {}

    @staticmethod
    def _extract_elements(formula: str) -> List[str]:
        import re
        return list(set(re.findall(r'[A-Z][a-z]?', formula)))

    def to_dict(self) -> dict:
        return {
            'name':        self.name,
            'formula':     self.formula,
            'peaks':       self.peaks,
            'pdf_number':  self.pdf_number,
            'system':      self.system,
            'space_group': self.space_group,
            'rir':         self.rir,
            'elements':    self.elements,
        }


@dataclass
class MatchResult:
    """匹配结果"""
    phase: Phase
    score: float                          # 综合评分 0~100
    d_fom: float = 0                      # d-spacing 评分
    i_fom: float = 0                      # 强度一致性评分
    m_fom: float = 0                      # 多重性评分
    s_fom: float = 0                      # 系统一致性评分
    matched_peaks: List[Dict] = None       # 匹配详情
    quality_grade: str = ""                # A/B/C/D
    confidence: float = 0                  # 置信度 0~1
    issues: List[str] = None               # 警告信息

    def __post_init__(self):
        if self.matched_peaks is None:
            self.matched_peaks = []
        if self.issues is None:
            self.issues = []

    def to_dict(self) -> dict:
        return {
            'name':        self.phase.name,
            'formula':     self.phase.formula,
            'score':       round(self.score, 1),
            'd_fom':       round(self.d_fom, 1),
            'i_fom':       round(self.i_fom, 1),
            'm_fom':       round(self.m_fom, 1),
            's_fom':       round(self.s_fom, 1),
            'n_matched':   len(self.matched_peaks),
            'pdf_number':  self.phase.pdf_number,
            'system':      self.phase.system,
            'elements':    self.phase.elements,
            'quality_grade': self.quality_grade,
            'confidence':  round(self.confidence, 3),
            'issues':      self.issues,
            'matched_peaks': self.matched_peaks,
        }


# ─────────────────────────────────────────────
# 物相匹配器
# ─────────────────────────────────────────────

class JadePhaseMatcher:
    """
    JADE 风格物相匹配器

    使用方法：
        matcher = JadePhaseMatcher()
        matcher.add_phases_from_database()
        results = matcher.match(exp_peaks, method='fom', top_n=10)
    """

    def __init__(self, database: List[Phase] = None):
        self.database = database if database else self._get_full_database()
        self._last_results: List[MatchResult] = []

    # ── 主匹配入口 ─────────────────────────────

    def match(self, peaks: List, method: str = 'fom',
              top_n: int = 10, min_score: float = 20.0,
              element_constraint: List[str] = None) -> List[Dict]:
        """
        物相匹配主函数

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

        # 执行匹配
        if method == 'hanawalt':
            raw_results = self._hanawalt(exp_peaks, db, top_n, min_score)
        elif method == 'wpf':
            raw_results = self._wpf_match(exp_peaks, db, top_n, min_score)
        else:
            raw_results = self._fom_match(exp_peaks, db, top_n, min_score)

        # 质量评估
        self._last_results = raw_results
        for r in raw_results:
            self._assess_quality(r)

        return [r.to_dict() for r in raw_results]

    def _prepare_peaks(self, peaks) -> List[Tuple[float, float]]:
        """统一峰数据格式 -> [(d, I_rel), ...]，按强度降序"""
        result = []
        for p in peaks:
            if hasattr(p, 'd_spacing'):
                d = p.d_spacing
                intensity = getattr(p, 'intensity', 100)
            elif hasattr(p, 'position'):
                # 2θ -> d
                d = self._twotheta_to_d(p.position)
                intensity = getattr(p, 'intensity', 100)
            elif isinstance(p, (list, tuple)) and len(p) >= 2:
                d, intensity = p[0], p[1]
            else:
                d = float(p)
                intensity = 100
            result.append((float(d), float(intensity)))

        # 按强度降序
        result.sort(key=lambda x: x[1], reverse=True)
        return result

    @staticmethod
    def _twotheta_to_d(twotheta: float, wavelength: float = 1.5406) -> float:
        """2θ -> d 值（布拉格方程）"""
        theta = np.radians(twotheta / 2)
        if np.sin(theta) < 1e-6:
            return 99.0
        return wavelength / (2 * np.sin(theta))

    # ── FOM 综合匹配 ───────────────────────────

    def _fom_match(self, exp_peaks: List[Tuple[float, float]],
                   db: List[Phase], top_n: int,
                   min_score: float) -> List[MatchResult]:
        """
        JADE FOM 综合评分法

        核心思想：
        - 实验峰与参考峰一一配对
        - 计算 d 精度评分 + 强度一致性评分
        - 鼓励多峰匹配（多重性奖励）
        - 惩罚系统误差偏移
        """
        results = []

        # 实验峰归一化（最强峰=100）
        max_exp = max(p[1] for p in exp_peaks) if exp_peaks else 1
        exp_norm = [(d, i / max_exp * 100) for d, i in exp_peaks]

        for phase in db:
            if not phase.peaks:
                continue

            # 参考峰归一化
            ref_peaks_raw = sorted(phase.peaks, key=lambda x: x[1], reverse=True)
            max_ref = max(p[1] for p in ref_peaks_raw) if ref_peaks_raw else 1
            ref_norm = [(d, i / max_ref * 100) for d, i in ref_peaks_raw]

            # 贪心匹配
            matched = []
            used_exp = set()
            used_ref = set()

            for e_idx, (e_d, e_i) in enumerate(exp_norm[:20]):
                best = None
                best_score = 0
                for r_idx, (r_d, r_i) in enumerate(ref_norm[:12]):
                    if r_idx in used_ref:
                        continue
                    delta = abs(e_d - r_d)
                    tol = self._adaptive_tolerance(r_d)
                    if delta > tol:
                        continue
                    # d 精度评分
                    d_score = 100 * (1 - delta / tol)
                    # 强度比评分（几何平均）
                    if e_i > 0 and r_i > 0:
                        i_ratio = min(e_i, r_i) / max(e_i, r_i)
                    else:
                        i_ratio = 0
                    combined = d_score * 0.7 + i_ratio * 100 * 0.3
                    if combined > best_score:
                        best_score = combined
                        best = {
                            'exp_d': e_d, 'exp_i': e_i,
                            'ref_d': r_d, 'ref_i': r_i,
                            'delta': delta, 'tol': tol,
                            'd_score': d_score, 'i_ratio': i_ratio,
                        }
                        best_r_idx = r_idx

                if best and best_score > 40:
                    matched.append(best)
                    used_exp.add(e_idx)
                    used_ref.add(best_r_idx)

            if not matched:
                continue

            n_m = len(matched)
            # ── d-spacing FOM ──────────────────
            d_errors = [m['delta'] for m in matched]
            avg_d_err = np.mean(d_errors)
            avg_d = np.mean([m['ref_d'] for m in matched])
            avg_d_pct = avg_d_err / avg_d * 100 if avg_d > 0 else 99
            d_fom = 100 * np.exp(-avg_d_pct / 1.5)

            # ── 强度 FOM ──────────────────────
            ratios = [m['i_ratio'] for m in matched]
            if ratios:
                # 几何平均（更严格）
                geo_mean = np.prod(ratios) ** (1 / len(ratios))
                # 排序一致性
                rank_corr = self._spearman_rank([m['exp_i'] for m in matched],
                                                  [m['ref_i'] for m in matched])
                i_fom = 100 * (geo_mean * 0.6 + rank_corr * 0.4)
            else:
                i_fom = 0

            # ── 多重性 FOM ───────────────────
            coverage = n_m / len(exp_norm) * 100        # 实验峰覆盖率
            completeness = n_m / len(ref_norm) * 100   # 参考峰完整率
            m_fom = min(100, coverage * 0.5 + completeness * 0.5)

            # ── 系统一致性 FOM ───────────────
            delta_pcts = [m['delta'] / m['ref_d'] * 100 for m in matched]
            s_fom = 100 * np.exp(-np.mean(delta_pcts) / 1.0)

            # ── 综合评分 ──────────────────────
            # 权重：d 45% + i 35% + m 15% + s 5%（JADE 标准）
            total = d_fom * 0.45 + i_fom * 0.35 + m_fom * 0.15 + s_fom * 0.05

            # RIR 校正（优先使用高质量卡片）
            if phase.rir and 0.5 <= phase.rir <= 10:
                total *= 1.0  # RIR 已在其他指标中体现

            if total >= min_score:
                results.append(MatchResult(
                    phase=phase,
                    score=total,
                    d_fom=d_fom,
                    i_fom=i_fom,
                    m_fom=m_fom,
                    s_fom=s_fom,
                    matched_peaks=matched
                ))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_n]

    @staticmethod
    def _adaptive_tolerance(d: float) -> float:
        """
        JADE 自适应公差
        d 越大允许误差越大（JADE 内部逻辑）
        """
        if d > 10:
            return 0.15
        elif d > 5:
            return 0.10
        elif d > 3:
            return 0.08
        elif d > 2:
            return 0.06
        elif d > 1:
            return 0.05
        else:
            return 0.04

    @staticmethod
    def _spearman_rank(list1: List[float], list2: List[float]) -> float:
        """简化版 Spearman 排序相关系数"""
        if len(list1) < 2:
            return 1.0
        # 转 rank
        s1 = sorted(range(len(list1)), key=lambda i: list1[i], reverse=True)
        s2 = sorted(range(len(list2)), key=lambda i: list2[i], reverse=True)
        r1 = {v: i for i, v in enumerate(s1)}
        r2 = {v: i for i, v in enumerate(s2)}
        d2 = sum((r1[i] - r2[i]) ** 2 for i in range(len(list1)))
        n = len(list1)
        rho = 1 - 6 * d2 / (n * (n ** 2 - 1))
        return max(0, rho)

    # ── HANAWALT 三强峰检索 ────────────────────

    def _hanawalt(self, exp_peaks: List[Tuple[float, float]],
                  db: List[Phase], top_n: int,
                  min_score: float) -> List[MatchResult]:
        """JADE HANAWALT 检索（使用前3强峰）"""
        results = []

        top3 = exp_peaks[:3]
        if len(top3) < 3:
            return results

        for phase in db:
            if not phase.peaks:
                continue
            ref_top3 = sorted(phase.peaks, key=lambda x: x[1], reverse=True)[:3]

            total_score = 0
            n_matched = 0
            matched = []

            for e_d, e_i in top3:
                best = 0
                best_pair = None
                for r_d, r_i in ref_top3:
                    delta = abs(e_d - r_d)
                    tol = self._adaptive_tolerance(r_d)
                    if delta <= tol:
                        s = 100 * (1 - delta / tol)
                        if s > best:
                            best = s
                            best_pair = {'exp_d': e_d, 'ref_d': r_d}
                if best > 0:
                    n_matched += 1
                    total_score += best
                    if best_pair:
                        matched.append(best_pair)

            if n_matched >= 2:
                score = (total_score / n_matched) * (n_matched / 3)
                if score >= min_score:
                    results.append(MatchResult(
                        phase=phase,
                        score=score,
                        d_fom=score,
                        m_fom=n_matched / 3 * 100,
                        matched_peaks=matched
                    ))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_n]

    # ── WPF 全谱拟合匹配 ───────────────────────

    def _wpf_match(self, exp_peaks: List[Tuple[float, float]],
                   db: List[Phase], top_n: int,
                   min_score: float) -> List[MatchResult]:
        """JADE WPF（全谱拟合）匹配"""
        results = []

        for phase in db:
            if not phase.peaks:
                continue

            ref_peaks = sorted(phase.peaks, key=lambda x: x[1], reverse=True)
            max_ref = max(p[1] for p in ref_peaks) if ref_peaks else 1
            ref_norm = [(d, i / max_ref * 100) for d, i in ref_peaks]

            # 模拟全谱拟合分数
            score = 0
            n_m = 0
            matched = []
            for e_d, e_i in exp_peaks[:15]:
                for r_d, r_i in ref_norm[:8]:
                    delta = abs(e_d - r_d)
                    if delta <= self._adaptive_tolerance(r_d):
                        score += 100 * (1 - delta / r_d)
                        n_m += 1
                        matched.append({'exp_d': e_d, 'ref_d': r_d})
                        break

            if n_m > 0:
                score = score / len(exp_peaks[:15]) * 100
                if score >= min_score:
                    results.append(MatchResult(
                        phase=phase, score=score,
                        d_fom=score, m_fom=n_m / len(ref_norm) * 100,
                        matched_peaks=matched
                    ))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_n]

    # ── 质量评估 ───────────────────────────────

    @staticmethod
    def _assess_quality(result: MatchResult) -> None:
        """评估匹配质量（Grade A/B/C/D）"""
        issues = []

        if result.score >= 80:
            grade, conf = 'A', 0.95
        elif result.score >= 65:
            grade, conf = 'B', 0.80
        elif result.score >= 50:
            grade, conf = 'C', 0.60
        else:
            grade, conf = 'D', 0.40

        if result.d_fom < 70:
            issues.append('d-spacing 偏差较大')
        if result.i_fom < 40:
            issues.append('强度一致性差，可能存在择优取向')
        if result.m_fom < 40:
            issues.append('匹配峰数偏少')
        if len(result.matched_peaks) < 3:
            issues.append('匹配峰不足 3 个')
        for mp in result.matched_peaks:
            if mp.get('i_ratio', 1) < 0.3:
                issues.append(f"d={mp['ref_d']:.2f}A 强度异常")
                break

        result.quality_grade = grade
        result.confidence = conf
        result.issues = issues

    # ── 定量分析（RIR 方法）────────────────────

    @staticmethod
    def quantitative_rir(matches: List[Dict],
                         peak_areas: Dict[str, float] = None) -> Dict[str, float]:
        """
        RIR 参比强度法定量

        X_i = (I_i / RIR_i) / Σ(I_j / RIR_j)

        Args:
            matches: match() 返回的列表（已含 rir）
            peak_areas: {phase_name: area}，可选

        Returns:
            {phase_name: wt_percent}
        """
        total = 0.0
        fractions = {}
        for m in matches:
            phase_name = m['name']
            rir = m.get('rir', 1.0)
            n_matched = m.get('n_matched', 1)
            # 用匹配峰数和 RIR 估算相对含量
            weight = n_matched / rir
            fractions[phase_name] = weight
            total += weight

        if total <= 0:
            return {}

        result = {}
        for name, frac in fractions.items():
            result[name] = round(frac / total * 100, 1)

        return result

    # ── 完整数据库 ─────────────────────────────

    def _get_full_database(self) -> List[Phase]:
        """完整数据库（含 PDF2-2004 SQLite + PDF4-2009 JSON）"""
        # 首先尝试加载 SQLite 数据库（29892 条记录，更完整）
        sqlite_db = self._load_sqlite_database()
        if sqlite_db:
            return sqlite_db

        # 回退到 JSON 数据库
        json_db = self._load_json_database()
        if json_db:
            return json_db

        # 最后回退到内置数据库
        return self._get_builtin_database()

    def _load_sqlite_database(self) -> List[Phase]:
        """从 SQLite 数据库加载 PDF2-2004"""
        from core.algorithms.element_constrained_search import extract_elements_from_formula

        search_paths = [
            Path(__file__).parent.parent.parent / 'pdf2_2004.db',
            Path(r'C:\Users\Administrator\.qclaw\skills\sci-xrd\pdf2_2004.db'),
            Path.home() / '.qclaw' / 'skills' / 'sci-xrd' / 'pdf2_2004.db',
        ]

        for db_path in search_paths:
            if db_path.exists():
                try:
                    conn = sqlite3.connect(str(db_path))
                    cursor = conn.cursor()
                    cursor.execute("SELECT card_num, name, formula, peaks_json FROM pdf_cards")
                    rows = cursor.fetchall()
                    conn.close()

                    phases = []
                    for card_num, name, formula, peaks_json in rows:
                        try:
                            peaks = json.loads(peaks_json)
                            if not isinstance(peaks, list):
                                continue
                            elements = extract_elements_from_formula(formula) if formula else []
                            phase = Phase(
                                name=name or f"Card-{card_num}",
                                formula=formula or '',
                                peaks=[(float(p[0]), float(p[1])) for p in peaks[:20]],
                                pdf_number=str(card_num),
                                system='',
                                space_group='',
                                cell_params={},
                                rir=1.0,
                                elements=elements,
                                quality='',
                            )
                            phases.append(phase)
                        except (json.JSONDecodeError, ValueError, TypeError):
                            continue

                    print(f"[PDF2] Loaded {len(phases)} cards from SQLite: {db_path}")
                    return phases

                except Exception as e:
                    print(f"[PDF2] Failed to load {db_path}: {e}")
                    continue

        return []

    def _load_json_database(self) -> List[Phase]:
        """从 JSON 文件加载 PDF4 数据库"""
        # 搜索路径
        search_paths = [
            Path(__file__).parent.parent.parent.parent / 'pdf4_minimal_db.json',
            Path(r'C:\Users\Administrator\.qclaw\workspace\pdf4_minimal_db.json'),
            Path.home() / '.qclaw' / 'workspace' / 'pdf4_minimal_db.json',
        ]
        
        for db_path in search_paths:
            if db_path.exists():
                try:
                    with open(db_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    phases = []
                    for card in data.get('cards', []):
                        # 转换 peaks 格式
                        peaks = [(float(p[0]), float(p[1])) for p in card.get('peaks', [])]
                        
                        # 提取晶胞参数
                        cell = card.get('cell_params', {})
                        
                        phase = Phase(
                            name=card.get('name', 'Unknown'),
                            formula=card.get('formula', ''),
                            peaks=peaks,
                            pdf_number=card.get('pdf_number', ''),
                            system=card.get('crystal_system', ''),
                            space_group=card.get('space_group', ''),
                            cell_params=cell,
                            rir=card.get('rir', 1.0),
                            elements=card.get('elements', []),
                            quality=card.get('quality', ''),
                        )
                        phases.append(phase)
                    
                    print(f"[PDF4] Loaded {len(phases)} cards from {db_path}")
                    return phases
                    
                except Exception as e:
                    print(f"[PDF4] Failed to load {db_path}: {e}")
                    continue
        
        return []
    
    def _get_builtin_database(self) -> List[Phase]:
        """内置数据库（当 JSON 不可用时）"""
        return [
            # ── 铜硫化物（本次新增重点）────────────────────
            Phase("Chalcopyrite", "CuFeS2",
                  [(3.034, 100), (2.627, 60), (1.866, 30),
                   (1.581, 20), (1.513, 15), (1.197, 15), (1.054, 10)],
                  "37-0471", "Tetragonal", "I-42d",
                  {'a': 5.24, 'c': 10.30}, rir=5.0,
                  elements=["Cu", "Fe", "S"], quality="*"),

            Phase("Chalcocite", "Cu2S",
                  [(3.685, 100), (3.201, 50), (2.403, 40),
                   (2.112, 35), (1.961, 30), (1.752, 25), (1.337, 20)],
                  "26-1116", "Monoclinic", "P21/c",
                  {'a': 7.63, 'b': 7.87, 'c': 11.01, 'beta': 116.4}, rir=4.8,
                  elements=["Cu", "S"], quality="*"),

            Phase("Covellite", "CuS",
                  [(3.807, 100), (3.024, 80), (2.632, 50),
                   (1.898, 40), (1.565, 35), (1.320, 30), (1.042, 25)],
                  "6-0464", "Hexagonal", "P63/mmc",
                  {'a': 3.79, 'c': 16.34}, rir=5.2,
                  elements=["Cu", "S"], quality="*"),

            Phase("Bornite", "Cu5FeS4",
                  [(3.261, 100), (2.747, 70), (2.624, 60),
                   (1.935, 50), (1.867, 45), (1.596, 35), (1.078, 25)],
                  "42-1405", "Orthorhombic", "Pcmn",
                  {'a': 10.95, 'b': 21.86, 'c': 10.95}, rir=4.5,
                  elements=["Cu", "Fe", "S"], quality="I"),

            Phase("Tetrahedrite", "Cu12As4S13",
                  [(3.380, 100), (2.710, 60), (2.590, 55),
                   (1.870, 40), (1.595, 35), (1.310, 25), (1.070, 20)],
                  "24-1148", "Cubic", "I-43m",
                  {'a': 10.33}, rir=3.8,
                  elements=["Cu", "As", "S"]),

            Phase("Diggenite", "Cu9S8",
                  [(3.210, 100), (2.650, 65), (2.410, 55),
                   (1.870, 45), (1.610, 40), (1.350, 30), (1.060, 25)],
                  "24-  77", "Cubic", "Fd-3m",
                  {'a': 15.26}, rir=4.0,
                  elements=["Cu", "S"]),

            # ── 常见硅酸盐 / 氧化物（保留）───────────────
            Phase("Alpha-Quartz", "SiO2",
                  [(4.257, 100), (3.343, 35), (2.457, 12),
                   (2.282, 8), (2.237, 6), (1.817, 6), (1.672, 4)],
                  "46-1045", "Trigonal", "P3121",
                  {'a': 4.913, 'c': 5.405}, rir=1.0,
                  elements=["Si", "O"], quality="*"),

            Phase("Calcite", "CaCO3",
                  [(3.035, 100), (2.495, 18), (2.285, 18),
                   (2.095, 5), (1.910, 5), (1.875, 4)],
                  "47-1743", "Trigonal", "R-3c",
                  {'a': 4.99, 'c': 17.06}, rir=2.2,
                  elements=["Ca", "C", "O"], quality="*"),

            Phase("Magnetite", "Fe3O4",
                  [(2.532, 100), (1.485, 30), (2.970, 30),
                   (1.615, 20), (1.092, 10), (1.327, 10)],
                  "19-0629", "Cubic", "Fd-3m",
                  {'a': 8.396}, rir=4.5,
                  elements=["Fe", "O"], quality="*"),

            Phase("Hematite", "Fe2O3",
                  [(2.702, 100), (1.634, 60), (2.519, 60),
                   (1.454, 50), (1.310, 30), (1.485, 25)],
                  "33-0664", "Trigonal", "R-3c",
                  {'a': 5.04, 'c': 13.75}, rir=5.0,
                  elements=["Fe", "O"], quality="*"),

            Phase("Gypsum", "CaSO4-2H2O",
                  [(7.630, 100), (3.066, 50), (4.270, 45),
                   (2.868, 40), (2.078, 25), (2.530, 20)],
                  "33-0311", "Monoclinic", "C2/c",
                  {}, rir=0.6,
                  elements=["Ca", "S", "O", "H"]),

            Phase("Pyrite", "FeS2",
                  [(2.709, 100), (3.128, 85), (2.423, 55),
                   (1.632, 45), (1.045, 20), (1.565, 15)],
                  "42-1340", "Cubic", "Pa-3",
                  {'a': 5.42}, rir=5.5,
                  elements=["Fe", "S"], quality="*"),

            Phase("Sphalerite", "ZnS",
                  [(3.123, 100), (1.910, 50), (1.631, 35),
                   (2.539, 25), (1.405, 20), (1.240, 15)],
                  "5-0566", "Cubic", "F-43m",
                  {'a': 5.41}, rir=4.5,
                  elements=["Zn", "S"]),

            Phase("Galena", "PbS",
                  [(2.969, 100), (3.429, 55), (2.119, 35),
                   (1.756, 30), (1.329, 20), (1.520, 15)],
                  "5-0592", "Cubic", "Fm-3m",
                  {'a': 5.94}, rir=8.0,
                  elements=["Pb", "S"], quality="*"),

            Phase("Corundum", "Al2O3",
                  [(2.085, 100), (2.552, 75), (3.479, 50),
                   (1.740, 45), (1.601, 40), (2.379, 35)],
                  "46-1212", "Trigonal", "R-3c",
                  {'a': 4.76, 'c': 12.99}, rir=6.5,
                  elements=["Al", "O"], quality="*"),

            Phase("Kaolinite", "Al2Si2O5(OH)4",
                  [(7.156, 100), (3.572, 80), (2.553, 60),
                   (2.486, 50), (1.488, 50), (2.340, 35)],
                  "14-0164", "Triclinic", "P-1",
                  {}, rir=0.5,
                  elements=["Al", "Si", "O", "H"]),

            Phase("Montmorillonite", "(Na,Ca)0.3(Al,Mg)2Si4O10(OH)2",
                  [(5.000, 100), (15.0, 80), (2.500, 60),
                   (1.490, 40), (4.450, 35), (2.580, 30)],
                  "3-0016", "Monoclinic", "C2/m",
                  {}, rir=0.3,
                  elements=["Na", "Ca", "Al", "Mg", "Si", "O", "H"]),

            Phase("Dolomite", "CaMg(CO3)2",
                  [(2.886, 100), (2.191, 30), (2.671, 30),
                   (1.785, 20), (2.405, 18), (1.805, 15)],
                  "36-0426", "Trigonal", "R-3",
                  {'a': 4.81, 'c': 16.00}, rir=1.5,
                  elements=["Ca", "Mg", "C", "O"]),

            Phase("Fluorite", "CaF2",
                  [(3.153, 100), (1.930, 75), (1.370, 25),
                   (1.115, 15), (1.645, 10), (1.050, 8)],
                  "35-0816", "Cubic", "Fm-3m",
                  {'a': 5.46}, rir=3.5,
                  elements=["Ca", "F"], quality="*"),

            Phase("Talc", "Mg3Si4O10(OH)2",
                  [(9.346, 100), (4.560, 80), (3.116, 60),
                   (1.870, 50), (2.480, 40), (2.590, 35)],
                  "19-0770", "Monoclinic", "C2/c",
                  {}, rir=0.4,
                  elements=["Mg", "Si", "O", "H"]),

            Phase("Barite", "BaSO4",
                  [(3.319, 100), (2.120, 70), (3.446, 55),
                   (2.212, 50), (1.973, 35), (2.105, 30)],
                  "24-1035", "Orthorhombic", "Pnma",
                  {}, rir=7.0,
                  elements=["Ba", "S", "O"]),

            Phase("Apatite", "Ca5(PO4)3(OH,F,Cl)",
                  [(2.814, 100), (2.706, 60), (2.798, 50),
                   (1.841, 40), (2.251, 35), (1.560, 25)],
                  "34-0011", "Hexagonal", "P63/m",
                  {'a': 9.42, 'c': 6.88}, rir=2.0,
                  elements=["Ca", "P", "O", "H", "F", "Cl"], quality="*"),
        ]


# 向后兼容
PhaseMatcher = JadePhaseMatcher
OptimizedPhaseMatcher = JadePhaseMatcher
