#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XRD算法优化模块
基于PDF2-2004数据库的算法优化
"""

import sqlite3
import numpy as np
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import sys
import time
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class Peak:
    """峰数据类"""
    d: float
    intensity: float
    fwhm: Optional[float] = None
    
@dataclass
class MatchResult:
    """匹配结果类"""
    card_num: int
    name: str
    formula: str
    card_type: str
    matched_peaks: int
    total_peaks: int
    match_score: float
    d_errors: List[float]
    intensity_ratios: List[float]
    
class XRDAlgorithmOptimizer:
    """XRD算法优化器"""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"数据库不存在: {self.db_path}")
        
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
    
    def optimize_peak_matching(self, peaks: List[Peak], tolerance: float = 0.02) -> List[MatchResult]:
        """
        优化峰匹配算法
        使用多级匹配策略提高准确性和速度
        """
        if not peaks:
            return []
        
        # 1. 预处理输入峰
        sorted_peaks = sorted(peaks, key=lambda x: x.intensity, reverse=True)
        strong_peaks = sorted_peaks[:min(10, len(sorted_peaks))]  # 取前10个最强峰
        
        # 2. 第一阶段：快速筛选
        candidate_cards = self._fast_screening(strong_peaks, tolerance)
        
        # 3. 第二阶段：精确匹配
        results = self._precise_matching(candidate_cards, peaks, tolerance)
        
        # 4. 第三阶段：评分排序
        scored_results = self._score_results(results)
        
        return scored_results
    
    def _fast_screening(self, peaks: List[Peak], tolerance: float) -> List[Dict]:
        """快速筛选候选卡片"""
        cursor = self.conn.cursor()
        
        # 构建查询条件
        conditions = []
        params = []
        
        for i, peak in enumerate(peaks):
            conditions.append(f"(ABS(d_value - ?) <= ?)")
            params.extend([peak.d, tolerance])
        
        where_clause = " OR ".join(conditions)
        
        # 执行查询
        query = f'''
        SELECT DISTINCT p.card_num, c.name, c.formula, c.card_type, c.n_peaks
        FROM pdf2_peaks p
        JOIN pdf2_cards c ON p.card_num = c.card_num
        WHERE {where_clause}
        GROUP BY p.card_num
        HAVING COUNT(*) >= {max(1, len(peaks) // 2)}
        LIMIT 100
        '''
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def _precise_matching(self, candidates: List[Dict], peaks: List[Peak], tolerance: float) -> List[MatchResult]:
        """精确匹配"""
        results = []
        
        for candidate in candidates:
            card_num = candidate['card_num']
            
            # 获取卡片的全部峰数据
            cursor = self.conn.cursor()
            cursor.execute('''
            SELECT d_value, intensity 
            FROM pdf2_peaks 
            WHERE card_num = ? 
            ORDER BY intensity DESC
            ''', (card_num,))
            
            card_peaks = [Peak(d=row[0], intensity=row[1]) for row in cursor.fetchall()]
            
            # 执行匹配
            match_info = self._match_peaks(peaks, card_peaks, tolerance)
            
            if match_info['matched_count'] > 0:
                result = MatchResult(
                    card_num=card_num,
                    name=candidate['name'],
                    formula=candidate['formula'],
                    card_type=candidate['card_type'],
                    matched_peaks=match_info['matched_count'],
                    total_peaks=len(card_peaks),
                    match_score=0.0,  # 将在评分阶段计算
                    d_errors=match_info['d_errors'],
                    intensity_ratios=match_info['intensity_ratios']
                )
                results.append(result)
        
        return results
    
    def _match_peaks(self, query_peaks: List[Peak], card_peaks: List[Peak], tolerance: float) -> Dict:
        """匹配两组峰数据"""
        matched_indices = set()
        d_errors = []
        intensity_ratios = []
        
        # 对每个查询峰，在卡片峰中寻找匹配
        for q_peak in query_peaks:
            best_match = None
            best_error = tolerance
            
            for j, c_peak in enumerate(card_peaks):
                if j in matched_indices:
                    continue
                
                d_error = abs(q_peak.d - c_peak.d)
                if d_error <= best_error:
                    best_error = d_error
                    best_match = (j, c_peak)
            
            if best_match:
                j, c_peak = best_match
                matched_indices.add(j)
                d_errors.append(best_error)
                
                # 计算强度比（避免除零）
                if q_peak.intensity > 0 and c_peak.intensity > 0:
                    ratio = min(q_peak.intensity, c_peak.intensity) / max(q_peak.intensity, c_peak.intensity)
                    intensity_ratios.append(ratio)
                else:
                    intensity_ratios.append(0.0)
        
        return {
            'matched_count': len(matched_indices),
            'd_errors': d_errors,
            'intensity_ratios': intensity_ratios
        }
    
    def _score_results(self, results: List[MatchResult]) -> List[MatchResult]:
        """对匹配结果进行评分"""
        scored_results = []
        
        for result in results:
            # 1. 匹配率分数 (0-40分)
            match_rate = result.matched_peaks / max(result.total_peaks, 1)
            match_rate_score = match_rate * 40
            
            # 2. d值误差分数 (0-30分)
            if result.d_errors:
                avg_d_error = np.mean(result.d_errors)
                d_error_score = max(0, 30 - (avg_d_error * 1000))  # 误差越小分数越高
            else:
                d_error_score = 0
            
            # 3. 强度一致性分数 (0-20分)
            if result.intensity_ratios:
                intensity_score = np.mean(result.intensity_ratios) * 20
            else:
                intensity_score = 0
            
            # 4. 卡片类型加分 (0-10分)
            type_bonus = 0
            if result.card_type == 'Mineral':
                type_bonus = 10
            elif result.card_type == 'Inorganic':
                type_bonus = 5
            
            # 总分
            total_score = match_rate_score + d_error_score + intensity_score + type_bonus
            
            # 更新结果
            result.match_score = total_score
            scored_results.append(result)
        
        # 按分数排序
        scored_results.sort(key=lambda x: x.match_score, reverse=True)
        return scored_results
    
    def optimize_phase_identification(self, peaks: List[Peak], max_phases: int = 5) -> List[Dict]:
        """
        优化物相鉴定算法
        支持多物相鉴定
        """
        # 1. 单物相匹配
        single_phase_results = self.optimize_peak_matching(peaks)
        
        if not single_phase_results or max_phases <= 1:
            return [self._format_result(r) for r in single_phase_results[:max_phases]]
        
        # 2. 多物相鉴定
        multi_phase_results = []
        remaining_peaks = peaks.copy()
        
        for phase_num in range(max_phases):
            if not remaining_peaks:
                break
            
            # 为剩余峰寻找最佳匹配
            phase_result = self.optimize_peak_matching(remaining_peaks)
            if not phase_result:
                break
            
            best_match = phase_result[0]
            multi_phase_results.append(best_match)
            
            # 移除已匹配的峰
            remaining_peaks = self._subtract_matched_peaks(remaining_peaks, best_match)
        
        return [self._format_result(r) for r in multi_phase_results]
    
    def _subtract_matched_peaks(self, peaks: List[Peak], match_result: MatchResult) -> List[Peak]:
        """减去已匹配的峰"""
        # 获取匹配卡片的峰数据
        cursor = self.conn.cursor()
        cursor.execute('''
        SELECT d_value, intensity 
        FROM pdf2_peaks 
        WHERE card_num = ? 
        ORDER BY intensity DESC
        LIMIT 20
        ''', (match_result.card_num,))
        
        card_peaks = [Peak(d=row[0], intensity=row[1]) for row in cursor.fetchall()]
        
        # 简单的峰减法：移除与卡片峰匹配的查询峰
        remaining_peaks = []
        tolerance = 0.02
        
        for q_peak in peaks:
            matched = False
            for c_peak in card_peaks:
                if abs(q_peak.d - c_peak.d) <= tolerance:
                    matched = True
                    break
            
            if not matched:
                remaining_peaks.append(q_peak)
        
        return remaining_peaks
    
    def _format_result(self, result: MatchResult) -> Dict:
        """格式化结果"""
        return {
            'card_num': result.card_num,
            'name': result.name,
            'formula': result.formula,
            'card_type': result.card_type,
            'matched_peaks': result.matched_peaks,
            'total_peaks': result.total_peaks,
            'match_score': round(result.match_score, 2),
            'match_percentage': round((result.matched_peaks / max(result.total_peaks, 1)) * 100, 1),
            'avg_d_error': round(np.mean(result.d_errors) if result.d_errors else 0, 4)
        }
    
    def create_search_cache(self):
        """创建搜索缓存优化"""
        cursor = self.conn.cursor()
        
        print("创建搜索缓存优化...")
        
        # 1. 创建常用搜索缓存
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS search_cache (
            cache_key TEXT PRIMARY KEY,
            result_json TEXT,
            hit_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 2. 创建热门矿物缓存
        common_minerals = ['quartz', 'calcite', 'feldspar', 'pyrite', 'hematite']
        
        for mineral in common_minerals:
            # 生成缓存键
            cache_key = f"mineral_search:{mineral}"
            
            # 查询结果
            cursor.execute('''
            SELECT card_num, name, formula, card_type 
            FROM pdf2_cards 
            WHERE name LIKE ? 
            LIMIT 20
            ''', (f'%{mineral}%',))
            
            results = [dict(row) for row in cursor.fetchall()]
            
            if results:
                cursor.execute('''
                INSERT OR REPLACE INTO search_cache (cache_key, result_json)
                VALUES (?, ?)
                ''', (cache_key, json.dumps(results)))
        
        # 3. 创建常用d值搜索缓存
        common_d_values = [3.34, 4.26, 1.82, 2.45, 2.28]  # 常见矿物特征峰
        
        for d_value in common_d_values:
            cache_key = f"d_search:{d_value}:0.02"
            
            cursor.execute('''
            SELECT DISTINCT c.card_num, c.name, c.formula, c.card_type
            FROM pdf2_peaks p
            JOIN pdf2_cards c ON p.card_num = c.card_num
            WHERE ABS(p.d_value - ?) <= 0.02
            LIMIT 20
            ''', (d_value,))
            
            results = [dict(row) for row in cursor.fetchall()]
            
            if results:
                cursor.execute('''
                INSERT OR REPLACE INTO search_cache (cache_key, result_json)
                VALUES (?, ?)
                ''', (cache_key, json.dumps(results)))
        
        self.conn.commit()
        print("搜索缓存创建完成")
    
    def run_algorithm_benchmark(self):
        """运行算法性能基准测试"""
        print("运行算法性能基准测试...")
        
        # 测试数据：石英的特征峰
        test_peaks = [
            Peak(d=3.34, intensity=100),
            Peak(d=4.26, intensity=80),
            Peak(d=1.82, intensity=60),
            Peak(d=2.28, intensity=40),
            Peak(d=1.54, intensity=30)
        ]
        
        # 测试1: 基础匹配算法
        print("\n1. 基础匹配算法测试...")
        start_time = time.time()
        results = self.optimize_peak_matching(test_peaks)
        elapsed = time.time() - start_time
        
        print(f"   耗时: {elapsed*1000:.1f} ms")
        print(f"   找到 {len(results)} 个匹配")
        
        if results:
            print("   前3个匹配结果:")
            for i, result in enumerate(results[:3]):
                print(f"     {i+1}. {result.name} ({result.formula})")
                print(f"         分数: {result.match_score:.1f}, 匹配峰: {result.matched_peaks}/{result.total_peaks}")
        
        # 测试2: 多物相鉴定
        print("\n2. 多物相鉴定测试...")
        start_time = time.time()
        multi_phase_results = self.optimize_phase_identification(test_peaks, max_phases=3)
        elapsed = time.time() - start_time
        
        print(f"   耗时: {elapsed*1000:.1f} ms")
        print(f"   鉴定出 {len(multi_phase_results)} 个物相")
        
        for i, phase in enumerate(multi_phase_results):
            print(f"   物相 {i+1}: {phase['name']} ({phase['formula']})")
            print(f"     匹配分数: {phase['match_score']}, 匹配率: {phase['match_percentage']}%")
        
        # 测试3: 缓存性能测试
        print("\n3. 缓存性能测试...")
        
        # 第一次查询（未命中缓存）
        start_time = time.time()
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM search_cache WHERE cache_key = ?', ('mineral_search:quartz',))
        cache_result = cursor.fetchone()
        elapsed1 = time.time() - start_time
        
        # 第二次查询（命中缓存）
        start_time = time.time()
        cursor.execute('SELECT * FROM search_cache WHERE cache_key = ?', ('mineral_search:quartz',))
        cache_result = cursor.fetchone()
        elapsed2 = time.time() - start_time
        
        print(f"   第一次查询（可能未命中）: {elapsed1*1000:.1f} ms")
        print(f"   第二次查询（命中缓存）: {elapsed2*1000:.1f} ms")
        print(f"   缓存加速比: {elapsed1/elapsed2:.1f}x")
    
    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("XRD算法优化模块")
        print("=" * 60)
        print("用法: python xrd_algorithm_optimizer.py <数据库路径> [命令]")
        print()
        print("命令:")
        print("  --benchmark       运行算法性能基准测试")
        print("  --cache           创建搜索缓存")
        print("  --test            测试匹配算法")
        print("  --all             执行所有操作")
        print()
        print("示例:")
        print("  python xrd_algorithm_optimizer.py F:\\桌面\\pdf2_final_complete.db --all")
        return
    
    db_path = sys.argv[1]
    command = '--all' if len(sys.argv) < 3 else sys.argv[2]
    
    try:
        optimizer = XRDAlgorithmOptimizer(db_path)
        
        if command == '--cache' or command == '--all':
            optimizer.create_search_cache()
        
        if command == '--benchmark' or command == '--all':
            optimizer.run_algorithm_benchmark()
        
        if command == '--test' or command == '--all':
            # 测试匹配算法
            test_peaks = [
                Peak(d=3.34, intensity=100),
                Peak(d=4.26, intensity=80),
                Peak(d=1.82, intensity=60)
            ]
            
            print("测试匹配算法...")
            results = optimizer.optimize_peak_matching(test_peaks)
            
            print(f"找到 {len(results)} 个匹配:")
            for i, result in enumerate(results[:5]):
                print(f"{i+1}. {result.name} ({result.formula})")
                print(f"   分数: {result.match_score:.1f}, 匹配峰: {result.matched_peaks}/{result.total_peaks}")
        
        optimizer.close()
        
    except FileNotFoundError as e:
        print(f"错误: {e}")
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()