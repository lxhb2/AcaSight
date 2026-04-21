#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化版XRD分析工具
整合所有优化功能
"""

import sqlite3
import json
import time
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import sys

class OptimizedXRDTool:
    """优化版XRD分析工具"""
    
    def __init__(self, db_path: str = None):
        if db_path:
            self.db_path = Path(db_path)
        else:
            self.db_path = Path(r"F:\桌面\pdf2_final_complete.db")
        
        if not self.db_path.exists():
            raise FileNotFoundError(f"数据库不存在: {self.db_path}")
        
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
    
    def search_by_peaks(self, peaks: List[Tuple[float, float]], 
                       tolerance: float = 0.02, 
                       min_matches: int = 3,
                       limit: int = 20) -> List[Dict]:
        """
        按峰数据搜索（优化版）
        peaks: [(d值, 强度), ...]
        """
        if not peaks:
            return []
        
        start_time = time.time()
        
        # 1. 快速筛选阶段
        strong_peaks = sorted(peaks, key=lambda x: x[1], reverse=True)[:5]
        
        cursor = self.conn.cursor()
        
        # 构建查询条件
        conditions = []
        params = []
        
        for d, intensity in strong_peaks:
            conditions.append("(ABS(p.d_value - ?) <= ?)")
            params.extend([d, tolerance])
        
        where_clause = " OR ".join(conditions)
        
        # 快速筛选查询
        query1 = f'''
        SELECT DISTINCT c.card_num, c.display_name, c.display_formula, 
               c.card_type, c.n_peaks, COUNT(p.d_value) as quick_matches
        FROM v_quick_search c
        JOIN pdf2_peaks p ON c.card_num = p.card_num
        WHERE {where_clause}
        GROUP BY c.card_num
        HAVING quick_matches >= {min(2, len(strong_peaks))}
        LIMIT 100
        '''
        
        cursor.execute(query1, params)
        candidates = [dict(row) for row in cursor.fetchall()]
        
        # 2. 精确匹配阶段
        results = []
        
        for candidate in candidates:
            card_num = candidate['card_num']
            
            # 获取卡片的全部峰数据
            cursor.execute('''
            SELECT d_value, intensity 
            FROM pdf2_peaks 
            WHERE card_num = ? 
            ORDER BY intensity DESC
            LIMIT 50
            ''', (card_num,))
            
            card_peaks = [(row[0], row[1]) for row in cursor.fetchall()]
            
            # 执行匹配
            match_info = self._match_peaks_optimized(peaks, card_peaks, tolerance)
            
            if match_info['matched_count'] >= min_matches:
                # 计算匹配分数
                score = self._calculate_match_score(match_info, candidate['n_peaks'])
                
                result = {
                    'card_num': card_num,
                    'name': candidate['display_name'],
                    'formula': candidate['display_formula'],
                    'card_type': candidate['card_type'],
                    'matched_peaks': match_info['matched_count'],
                    'total_peaks': candidate['n_peaks'],
                    'match_score': score,
                    'match_percentage': round((match_info['matched_count'] / max(candidate['n_peaks'], 1)) * 100, 1),
                    'avg_d_error': round(match_info['avg_d_error'], 4) if match_info['matched_count'] > 0 else 0,
                    'intensity_correlation': round(match_info['intensity_correlation'], 3)
                }
                results.append(result)
        
        # 3. 排序结果
        results.sort(key=lambda x: x['match_score'], reverse=True)
        
        elapsed = time.time() - start_time
        
        return {
            'results': results[:limit],
            'search_time_ms': round(elapsed * 1000, 1),
            'candidates_count': len(candidates),
            'final_results_count': len(results)
        }
    
    def _match_peaks_optimized(self, query_peaks: List[Tuple[float, float]], 
                              card_peaks: List[Tuple[float, float]], 
                              tolerance: float) -> Dict:
        """优化版峰匹配算法"""
        matched_pairs = []
        query_matched = [False] * len(query_peaks)
        card_matched = [False] * len(card_peaks)
        
        # 按强度排序
        sorted_query_peaks = sorted(enumerate(query_peaks), key=lambda x: x[1][1], reverse=True)
        sorted_card_peaks = sorted(enumerate(card_peaks), key=lambda x: x[1][1], reverse=True)
        
        # 优先匹配强峰
        for q_idx, (q_d, q_i) in sorted_query_peaks:
            if query_matched[q_idx]:
                continue
                
            best_match = None
            best_error = tolerance
            
            for c_idx, (c_d, c_i) in sorted_card_peaks:
                if card_matched[c_idx]:
                    continue
                
                d_error = abs(q_d - c_d)
                if d_error <= best_error:
                    best_error = d_error
                    best_match = (c_idx, c_d, c_i)
            
            if best_match:
                c_idx, c_d, c_i = best_match
                matched_pairs.append((q_d, q_i, c_d, c_i, best_error))
                query_matched[q_idx] = True
                card_matched[c_idx] = True
        
        # 计算统计信息
        if not matched_pairs:
            return {
                'matched_count': 0,
                'avg_d_error': 0,
                'intensity_correlation': 0
            }
        
        d_errors = [pair[4] for pair in matched_pairs]
        avg_d_error = sum(d_errors) / len(d_errors)
        
        # 计算强度相关性
        query_intensities = [pair[1] for pair in matched_pairs]
        card_intensities = [pair[3] for pair in matched_pairs]
        
        # 简单的强度一致性计算
        intensity_ratios = []
        for q_i, c_i in zip(query_intensities, card_intensities):
            if q_i > 0 and c_i > 0:
                ratio = min(q_i, c_i) / max(q_i, c_i)
                intensity_ratios.append(ratio)
        
        intensity_correlation = sum(intensity_ratios) / len(intensity_ratios) if intensity_ratios else 0
        
        return {
            'matched_count': len(matched_pairs),
            'avg_d_error': avg_d_error,
            'intensity_correlation': intensity_correlation
        }
    
    def _calculate_match_score(self, match_info: Dict, total_peaks: int) -> float:
        """计算匹配分数"""
        matched_count = match_info['matched_count']
        avg_d_error = match_info['avg_d_error']
        intensity_correlation = match_info['intensity_correlation']
        
        # 1. 匹配率分数 (0-40分)
        match_rate = matched_count / max(total_peaks, 1)
        match_rate_score = min(40, match_rate * 40)
        
        # 2. d值误差分数 (0-30分)
        d_error_score = max(0, 30 - (avg_d_error * 1000))
        
        # 3. 强度相关性分数 (0-20分)
        intensity_score = intensity_correlation * 20
        
        # 4. 匹配数量加分 (0-10分)
        count_bonus = min(10, matched_count * 0.5)
        
        total_score = match_rate_score + d_error_score + intensity_score + count_bonus
        
        return round(total_score, 2)
    
    def search_minerals(self, keyword: str = None, limit: int = 20) -> List[Dict]:
        """搜索矿物"""
        cursor = self.conn.cursor()
        
        if keyword:
            query = '''
            SELECT card_num, display_name, display_formula, card_type, 
                   n_peaks, d_min, d_max, i_max, mineral_name
            FROM v_quick_search
            WHERE mineral_name IS NOT NULL 
              AND (display_name LIKE ? OR mineral_name LIKE ?)
            ORDER BY i_max DESC
            LIMIT ?
            '''
            params = (f'%{keyword}%', f'%{keyword}%', limit)
        else:
            query = '''
            SELECT card_num, display_name, display_formula, card_type, 
                   n_peaks, d_min, d_max, i_max, mineral_name
            FROM v_quick_search
            WHERE mineral_name IS NOT NULL
            ORDER BY i_max DESC
            LIMIT ?
            '''
            params = (limit,)
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_database_stats(self) -> Dict:
        """获取数据库统计信息"""
        cursor = self.conn.cursor()
        
        stats = {}
        
        # 基本统计
        cursor.execute('SELECT COUNT(*) FROM v_quick_search')
        stats['total_cards'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM pdf2_peaks')
        stats['total_peaks'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT AVG(n_peaks) FROM v_quick_search WHERE n_peaks > 0')
        stats['avg_peaks_per_card'] = round(cursor.fetchone()[0] or 0, 1)
        
        # 卡片类型分布
        cursor.execute('''
        SELECT card_type, COUNT(*) as count 
        FROM v_quick_search 
        GROUP BY card_type 
        ORDER BY count DESC
        ''')
        stats['card_type_distribution'] = {row[0] or 'Unknown': row[1] for row in cursor.fetchall()}
        
        # 矿物统计
        cursor.execute('SELECT COUNT(*) FROM v_quick_search WHERE mineral_name IS NOT NULL')
        stats['mineral_cards'] = cursor.fetchone()[0]
        
        # 常用查询缓存统计
        cursor.execute('SELECT COUNT(*) FROM common_queries')
        stats['cached_queries'] = cursor.fetchone()[0]
        
        return stats
    
    def quick_d_search(self, d_value: float, tolerance: float = 0.02, limit: int = 10) -> Dict:
        """快速d值搜索（使用缓存优化）"""
        start_time = time.time()
        
        cursor = self.conn.cursor()
        
        # 检查缓存
        cache_key = f"d_search:{d_value}:{tolerance}"
        cursor.execute('SELECT result_count FROM common_queries WHERE query_key = ?', (cache_key,))
        cache_result = cursor.fetchone()
        
        # 执行搜索
        cursor.execute('''
        SELECT DISTINCT c.card_num, c.display_name, c.display_formula, c.card_type,
               p.d_value as matched_d, p.intensity, ABS(p.d_value - ?) as d_error
        FROM v_quick_search c
        JOIN pdf2_peaks p ON c.card_num = p.card_num
        WHERE ABS(p.d_value - ?) <= ?
        ORDER BY d_error, p.intensity DESC
        LIMIT ?
        ''', (d_value, d_value, tolerance, limit))
        
        results = [dict(row) for row in cursor.fetchall()]
        
        elapsed = time.time() - start_time
        
        return {
            'results': results,
            'search_time_ms': round(elapsed * 1000, 1),
            'cached': cache_result is not None,
            'estimated_total': cache_result[0] if cache_result else len(results)
        }
    
    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("优化版XRD分析工具")
        print("=" * 60)
        print("用法: python optimized_xrd_tool.py <命令> [参数]")
        print()
        print("命令:")
        print("  --stats             显示数据库统计")
        print("  --d <值>            快速d值搜索")
        print("  --minerals [关键词] 搜索矿物")
        print("  --peaks             峰数据搜索示例")
        print("  --test              运行测试")
        print()
        print("示例:")
        print("  python optimized_xrd_tool.py --stats")
        print("  python optimized_xrd_tool.py --d 3.34")
        print("  python optimized_xrd_tool.py --minerals quartz")
        print("  python optimized_xrd_tool.py --peaks")
        return
    
    try:
        tool = OptimizedXRDTool()
        
        if sys.argv[1] == '--stats':
            stats = tool.get_database_stats()
            print("数据库统计信息:")
            print(f"  卡片总数: {stats['total_cards']:,}")
            print(f"  峰数据总数: {stats['total_peaks']:,}")
            print(f"  平均峰数/卡片: {stats['avg_peaks_per_card']}")
            print(f"  矿物卡片数: {stats['mineral_cards']}")
            print(f"  缓存查询数: {stats['cached_queries']}")
            print("  卡片类型分布:")
            for card_type, count in stats['card_type_distribution'].items():
                percentage = (count / stats['total_cards']) * 100
                print(f"    {card_type}: {count:,} ({percentage:.1f}%)")
        
        elif sys.argv[1] == '--d' and len(sys.argv) >= 3:
            try:
                d_value = float(sys.argv[2])
                tolerance = 0.02
                if len(sys.argv) >= 4 and sys.argv[3].startswith('--tol'):
                    if len(sys.argv) >= 5:
                        tolerance = float(sys.argv[4])
                
                result = tool.quick_d_search(d_value, tolerance)
                print(f"搜索 d={d_value} (±{tolerance}) 的结果:")
                print(f"  搜索时间: {result['search_time_ms']} ms")
                print(f"  是否使用缓存: {'是' if result['cached'] else '否'}")
                print(f"  估计总数: {result['estimated_total']}")
                print(f"  显示结果: {len(result['results'])} 个")
                
                for i, item in enumerate(result['results'][:5], 1):
                    print(f"\n  {i}. {item['display_name']} ({item['display_formula']})")
                    print(f"     类型: {item['card_type']}")
                    print(f"     匹配d值: {item['matched_d']:.3f} Å, 误差: {item['d_error']:.4f} Å")
                    print(f"     强度: {item['intensity']}")
            except ValueError:
                print("错误: d值必须是数字")
        
        elif sys.argv[1] == '--minerals':
            keyword = sys.argv[2] if len(sys.argv) >= 3 else None
            minerals = tool.search_minerals(keyword, limit=10)
            
            if keyword:
                print(f"搜索矿物 '{keyword}' 的结果 ({len(minerals)} 个):")
            else:
                print(f"所有矿物 ({len(minerals)} 个):")
            
            for i, mineral in enumerate(minerals, 1):
                print(f"\n{i}. {mineral['display_name']} ({mineral['display_formula']})")
                print(f"   类型: {mineral['card_type']}")
                print(f"   矿物名: {mineral['mineral_name']}")
                print(f"   峰数量: {mineral['n_peaks']}")
                print(f"   d值范围: {mineral['d_min']:.3f} - {mineral['d_max']:.3f} Å")
                print(f"   最大强度: {mineral['i_max']}")
        
        elif sys.argv[1] == '--peaks':
            # 示例峰数据（石英特征峰）
            test_peaks = [
                (3.34, 100),  # 最强峰
                (4.26, 80),   # 次强峰
                (1.82, 60),   # 第三强峰
                (2.28, 40),   # 其他峰
                (1.54, 30)    # 其他峰
            ]
            
            print("峰数据搜索示例 (石英特征峰):")
            print("输入峰数据:")
            for d, i in test_peaks:
                print(f"  d={d:.3f} Å, I={i}")
            
            result = tool.search_by_peaks(test_peaks, min_matches=3)
            
            print(f"\n搜索结果:")
            print(f"  搜索时间: {result['search_time_ms']} ms")
            print(f"  候选卡片: {result['candidates_count']}")
            print(f"  最终结果: {result['final_results_count']}")
            
            for i, match in enumerate(result['results'][:5], 1):
                print(f"\n{i}. {match['name']} ({match['formula']})")
                print(f"   类型: {match['card_type']}")
                print(f"   匹配分数: {match['match_score']}/100")
                print(f"   匹配率: {match['match_percentage']}% ({match['matched_peaks']}/{match['total_peaks']})")
                print(f"   平均d误差: {match['avg_d_error']} Å")
                print(f"   强度相关性: {match['intensity_correlation']:.3f}")
        
        elif sys.argv[1] == '--test':
            print("运行综合测试...")
            
            # 测试1: 数据库统计
            print("\n1. 数据库统计测试:")
            stats = tool.get_database_stats()
            print(f"   卡片总数: {stats['total_cards']:,}")
            print(f"   矿物卡片: {stats['mineral_cards']}")
            
            # 测试2: d值搜索
            print("\n2. d值搜索测试 (d=3.34):")
            d_result = tool.quick_d_search(3.34)
            print(f"   搜索时间: {d_result['search_time_ms']} ms")
            print(f"   结果数量: {len(d_result['results'])}")
            
            # 测试3: 矿物搜索
            print("\n3. 矿物搜索测试:")
            minerals = tool.search_minerals(limit=5)
            print(f"   找到 {len(minerals)} 种矿物")
            for i, mineral in enumerate(minerals[:3], 1):
                print(f"   {i}. {mineral['display_name']}")
        
        else:
            print("错误: 未知命令")
            main()
        
        tool.close()
        
    except FileNotFoundError as e:
        print(f"错误: {e}")
    except Exception as e:
        print(f"错误: {e}")

if __name__ == '__main__':
    main()