"""
物相匹配引擎 - 基于PDF2数据库的智能匹配

核心特性：
1. 多相同时匹配
2. 置信度评分系统
3. 智能过滤和排序
4. 支持自定义数据库
5. 快速检索和匹配

匹配算法：
- 基于d值的向量距离匹配
- 考虑相对强度权重
- 多相组合优化
- 置信度综合评估
"""

import numpy as np
import sqlite3
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Union, Any
import warnings
from dataclasses import dataclass
from collections import defaultdict
import json


@dataclass
class MineralPhase:
    """矿物物相数据类"""
    mineral_name: str
    formula: str
    cas_number: str
    d_values: List[float]  # 主要d值列表
    intensities: List[float]  # 相对强度列表
    reference: str  # 参考来源
    category: str = ""  # 矿物类别
    
    def __post_init__(self):
        """数据验证和标准化"""
        # 确保d值和强度列表长度一致
        min_len = min(len(self.d_values), len(self.intensities))
        self.d_values = self.d_values[:min_len]
        self.intensities = self.intensities[:min_len]
        
        # 标准化强度（0-100）
        if self.intensities:
            max_intensity = max(self.intensities)
            if max_intensity > 0:
                self.intensities = [i * 100 / max_intensity for i in self.intensities]


class PhaseMatcher:
    """物相匹配引擎"""
    
    def __init__(self, database_path: Optional[Union[str, Path]] = None):
        """
        初始化匹配引擎
        
        Args:
            database_path: PDF2数据库路径（SQLite格式）
        """
        self.database_path = Path(database_path) if database_path else None
        self.connection = None
        self.mineral_database = []
        
        # 匹配参数
        self.match_tolerance = 0.02  # d值匹配容差（Å）
        self.min_matched_peaks = 3   # 最小匹配峰数
        self.intensity_weight = 0.3  # 强度权重
        self.position_weight = 0.7   # 位置权重
        
        # 置信度阈值
        self.min_confidence = 0.4    # 最小置信度
        self.good_confidence = 0.7   # 良好置信度
        self.excellent_confidence = 0.9  # 优秀置信度
        
        # 加载数据库
        if self.database_path and self.database_path.exists():
            self._load_database()
        else:
            self._create_default_database()
    
    def _load_database(self):
        """加载PDF2数据库"""
        try:
            self.connection = sqlite3.connect(str(self.database_path))
            
            # 检查表结构
            cursor = self.connection.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            if not tables:
                warnings.warn("数据库为空，使用默认数据库")
                self._create_default_database()
                return
            
            # 读取矿物数据
            cursor.execute("""
                SELECT mineral_name, formula, cas_number, 
                       d_values, intensities, reference, category
                FROM minerals
            """)
            
            for row in cursor.fetchall():
                try:
                    mineral = MineralPhase(
                        mineral_name=row[0],
                        formula=row[1],
                        cas_number=row[2],
                        d_values=json.loads(row[3]),
                        intensities=json.loads(row[4]),
                        reference=row[5],
                        category=row[6]
                    )
                    self.mineral_database.append(mineral)
                except Exception as e:
                    warnings.warn(f"加载矿物数据失败: {e}")
            
            print(f"成功加载 {len(self.mineral_database)} 个矿物物相")
            
        except Exception as e:
            warnings.warn(f"加载数据库失败: {e}")
            self._create_default_database()
    
    def _create_default_database(self):
        """创建默认矿物数据库"""
        print("创建默认矿物数据库...")
        
        # 常见矿物数据库
        default_minerals = [
            # 石英类
            MineralPhase(
                mineral_name="Quartz",
                formula="SiO2",
                cas_number="14808-60-7",
                d_values=[3.343, 4.257, 1.817, 1.541, 2.282, 2.237, 1.659],
                intensities=[100, 20, 15, 10, 8, 7, 5],
                reference="PDF#46-1045",
                category="Silicate"
            ),
            # 方解石
            MineralPhase(
                mineral_name="Calcite",
                formula="CaCO3",
                cas_number="471-34-1",
                d_values=[3.035, 2.285, 2.095, 1.913, 1.875, 1.604, 1.526],
                intensities=[100, 18, 18, 14, 12, 11, 10],
                reference="PDF#05-0586",
                category="Carbonate"
            ),
            # 赤铁矿
            MineralPhase(
                mineral_name="Hematite",
                formula="Fe2O3",
                cas_number="1309-37-1",
                d_values=[2.700, 2.519, 1.694, 1.484, 2.207, 1.840, 1.452],
                intensities=[100, 70, 40, 30, 25, 20, 15],
                reference="PDF#33-0664",
                category="Oxide"
            ),
            # 黄铜矿
            MineralPhase(
                mineral_name="Chalcopyrite",
                formula="CuFeS2",
                cas_number="1308-56-1",
                d_values=[3.03, 1.86, 1.59, 1.31, 1.04, 0.98, 0.91],
                intensities=[100, 60, 40, 30, 20, 15, 10],
                reference="PDF#37-0471",
                category="Sulfide"
            ),
            # 辉铜矿
            MineralPhase(
                mineral_name="Chalcocite",
                formula="Cu2S",
                cas_number="22205-45-4",
                d_values=[3.20, 2.80, 1.97, 1.87, 1.69, 1.43, 1.26],
                intensities=[100, 80, 60, 40, 30, 20, 15],
                reference="PDF#26-1116",
                category="Sulfide"
            ),
            # 铜
            MineralPhase(
                mineral_name="Copper",
                formula="Cu",
                cas_number="7440-50-8",
                d_values=[2.088, 1.808, 1.278, 1.090, 1.043, 0.904, 0.829],
                intensities=[100, 46, 20, 17, 17, 11, 9],
                reference="PDF#04-0836",
                category="Metal"
            ),
            # 赤铜矿
            MineralPhase(
                mineral_name="Cuprite",
                formula="Cu2O",
                cas_number="1317-39-1",
                d_values=[2.465, 2.135, 1.511, 1.287, 1.233, 1.068, 0.976],
                intensities=[100, 35, 30, 20, 15, 10, 8],
                reference="PDF#05-0667",
                category="Oxide"
            ),
            # 黄铁矿
            MineralPhase(
                mineral_name="Pyrite",
                formula="FeS2",
                cas_number="1309-36-0",
                d_values=[2.71, 1.63, 2.42, 1.04, 0.91, 0.83, 0.76],
                intensities=[100, 60, 50, 30, 20, 15, 10],
                reference="PDF#42-1340",
                category="Sulfide"
            ),
            # 闪锌矿
            MineralPhase(
                mineral_name="Sphalerite",
                formula="ZnS",
                cas_number="1314-98-3",
                d_values=[3.12, 1.91, 1.63, 1.24, 1.10, 0.98, 0.89],
                intensities=[100, 60, 40, 30, 20, 15, 10],
                reference="PDF#05-0566",
                category="Sulfide"
            ),
            # 方铅矿
            MineralPhase(
                mineral_name="Galena",
                formula="PbS",
                cas_number="1314-87-0",
                d_values=[2.97, 2.10, 1.79, 1.49, 1.34, 1.21, 1.12],
                intensities=[100, 60, 40, 30, 25, 20, 15],
                reference="PDF#05-0592",
                category="Sulfide"
            )
        ]
        
        self.mineral_database = default_minerals
        print(f"创建默认数据库，包含 {len(self.mineral_database)} 个矿物物相")
    
    def match_phases(self, peaks: List[Dict], wavelength: float = 1.5406,
                    max_phases: int = 5, min_confidence: float = None) -> List[Dict]:
        """
        匹配物相
        
        Args:
            peaks: 峰信息列表，每个元素必须包含'position'（2θ角度）
            wavelength: X射线波长（Å，默认Cu Kα）
            max_phases: 最大返回物相数
            min_confidence: 最小置信度阈值
            
        Returns:
            匹配的物相列表，每个元素包含：
            - mineral: 矿物名称
            - formula: 化学式
            - match_score: 匹配分数（0-100）
            - confidence: 置信度（0-1）
            - matched_peaks: 匹配的峰索引列表
            - d_values: 匹配的d值列表
            - reference: 参考来源
            - category: 矿物类别
        """
        if min_confidence is None:
            min_confidence = self.min_confidence
        
        # 将2θ角度转换为d值
        peak_d_values = [self._theta_to_d(peak['position'], wavelength) 
                        for peak in peaks]
        
        # 对每个矿物进行匹配
        match_results = []
        
        for mineral in self.mineral_database:
            match_info = self._match_mineral(peak_d_values, mineral)
            
            if match_info['match_score'] > 0:
                confidence = self._calculate_confidence(match_info, len(peaks))
                
                if confidence >= min_confidence:
                    match_results.append({
                        'mineral': mineral.mineral_name,
                        'formula': mineral.formula,
                        'cas_number': mineral.cas_number,
                        'match_score': match_info['match_score'],
                        'confidence': confidence,
                        'matched_peaks': match_info['matched_indices'],
                        'd_values': [peak_d_values[i] for i in match_info['matched_indices']],
                        'reference': mineral.reference,
                        'category': mineral.category,
                        'details': match_info
                    })
        
        # 按置信度排序
        match_results.sort(key=lambda x: x['confidence'], reverse=True)
        
        # 限制返回数量
        return match_results[:max_phases]
    
    def _match_mineral(self, peak_d_values: List[float], 
                      mineral: MineralPhase) -> Dict[str, Any]:
        """匹配单个矿物"""
        matched_indices = []
        position_errors = []
        intensity_scores = []
        
        # 对矿物的每个主要d值进行匹配
        for i, mineral_d in enumerate(mineral.d_values):
            best_match_idx = -1
            best_error = float('inf')
            
            # 在检测到的峰中寻找最佳匹配
            for j, peak_d in enumerate(peak_d_values):
                error = abs(peak_d - mineral_d) / mineral_d
                
                if error < self.match_tolerance and error < best_error:
                    best_match_idx = j
                    best_error = error
            
            if best_match_idx >= 0:
                matched_indices.append(best_match_idx)
                position_errors.append(best_error)
                
                # 强度匹配分数
                if i < len(mineral.intensities):
                    # 这里简化处理，实际应该考虑检测到的峰强度
                    intensity_score = 1.0  # 默认分数
                    intensity_scores.append(intensity_score)
        
        if not matched_indices:
            return {'match_score': 0, 'matched_indices': []}
        
        # 计算位置匹配分数
        avg_position_error = np.mean(position_errors)
        position_score = max(0, 1 - avg_position_error / self.match_tolerance)
        
        # 计算强度匹配分数
        intensity_score = np.mean(intensity_scores) if intensity_scores else 0.5
        
        # 综合匹配分数
        match_score = (position_score * self.position_weight + 
                      intensity_score * self.intensity_weight) * 100
        
        # 考虑匹配峰数
        match_ratio = len(matched_indices) / len(mineral.d_values)
        match_score *= min(1.0, match_ratio * 2)  # 惩罚匹配峰数太少的情况
        
        return {
            'match_score': match_score,
            'matched_indices': matched_indices,
            'position_score': position_score,
            'intensity_score': intensity_score,
            'avg_position_error': avg_position_error,
            'match_ratio': match_ratio,
            'num_matched': len(matched_indices)
        }
    
    def _calculate_confidence(self, match_info: Dict, total_peaks: int) -> float:
        """计算匹配置信度"""
        if total_peaks == 0:
            return 0
        
        # 基础置信度基于匹配分数
        base_confidence = match_info['match_score'] / 100
        
        # 考虑匹配峰数
        peak_ratio = match_info['num_matched'] / total_peaks
        peak_factor = min(1.0, peak_ratio * 2)
        
        # 考虑匹配比例
        match_ratio_factor = match_info['match_ratio']
        
        # 考虑位置误差
        error_factor = max(0, 1 - match_info['avg_position_error'] / (self.match_tolerance * 2))
        
        # 综合置信度
        confidence = (base_confidence * 0.4 + 
                     peak_factor * 0.3 + 
                     match_ratio_factor * 0.2 + 
                     error_factor * 0.1)
        
        return min(1.0, max(0.0, confidence))
    
    def _theta_to_d(self, theta_deg: float, wavelength: float) -> float:
        """将2θ角度转换为d值（Å）"""
        theta_rad = np.radians(theta_deg / 2)  # 转换为θ（半角）
        
        if theta_rad == 0:
            return float('inf')
        
        d = wavelength / (2 * np.sin(theta_rad))
        return d
    
    def find_multiple_phases(self, peaks: List[Dict], wavelength: float = 1.5406,
                            max_phase_combinations: int = 3) -> List[List[Dict]]:
        """
        寻找多相组合
        
        Args:
            peaks: 峰信息列表
            wavelength: X射线波长
            max_phase_combinations: 最大返回组合数
            
        Returns:
            多相组合列表，每个组合是一个物相列表
        """
        # 首先进行单相匹配
        single_phases = self.match_phases(peaks, wavelength, max_phases=10)
        
        if not single_phases:
            return []
        
        # 生成多相组合
        phase_combinations = []
        
        # 尝试两相组合
        for i in range(len(single_phases)):
            for j in range(i + 1, len(single_phases)):
                phase1 = single_phases[i]
                phase2 = single_phases[j]
                
                # 检查峰重叠情况
                overlap = set(phase1['matched_peaks']) & set(phase2['matched_peaks'])
                
                if len(overlap) <= 2:  # 允许少量重叠
                    # 计算组合置信度
                    combined_confidence = (phase1['confidence'] + phase2['confidence']) / 2
                    
                    phase_combinations.append({
                        'phases': [phase1, phase2],
                        'confidence': combined_confidence,
                        'total_matched': len(set(phase1['matched_peaks']) | set(phase2['matched_peaks'])),
                        'overlap': len(overlap)
                    })
        
        # 按置信度排序
        phase_combinations.sort(key=lambda x: x['confidence'], reverse=True)
        
        # 返回最佳组合
        best_combinations = []
        for combo in phase_combinations[:max_phase_combinations]:
            best_combinations.append(combo['phases'])
        
        return best_combinations
    
    def search_by_name(self, name: str, partial: bool = True) -> List[MineralPhase]:
        """按名称搜索矿物"""
        results = []
        name_lower = name.lower()
        
        for mineral in self.mineral_database:
            mineral_name_lower = mineral.mineral_name.lower()
            
            if partial:
                if name_lower in mineral_name_lower:
                    results.append