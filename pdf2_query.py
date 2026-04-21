#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF2-2004 数据库查询工具
"""

import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Tuple
import sys

class PDF2Query:
    """PDF2数据库查询"""
    
    def __init__(self, db_path: str = None):
        if db_path:
            self.db_path = Path(db_path)
        else:
            # 默认路径
            self.db_path = Path(r"F:\桌面\pdf2_complete.db")
        
        if not self.db_path.exists():
            raise FileNotFoundError(f"数据库不存在: {self.db_path}")
        
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
    
    def search_by_d(self, d_value: float, tolerance: float = 0.02, limit: int = 20) -> List[Dict]:
        """按d值搜索"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
        SELECT DISTINCT c.* 
        FROM pdf2_cards c
        JOIN pdf2_peaks p ON c.card_num = p.card_num
        WHERE ABS(p.d_value - ?) <= ?
        ORDER BY ABS(p.d_value - ?)
        LIMIT ?
        ''', (d_value, tolerance, d_value, limit))
        
        results = []
        for row in cursor.fetchall():
            card = dict(row)
            # 获取匹配的峰
            cursor2 = self.conn.cursor()
            cursor2.execute('''
            SELECT d_value, intensity 
            FROM pdf2_peaks 
            WHERE card_num = ? AND ABS(d_value - ?) <= ?
            ORDER BY intensity DESC
            ''', (card['card_num'], d_value, tolerance))
            
            matched_peaks = cursor2.fetchall()
            card['matched_peaks'] = [dict(p) for p in matched_peaks]
            results.append(card)
        
        return results
    
    def search_by_name(self, keyword: str, limit: int = 20) -> List[Dict]:
        """按名称搜索"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
        SELECT * FROM pdf2_cards 
        WHERE name LIKE ? 
        ORDER BY card_num
        LIMIT ?
        ''', (f'%{keyword}%', limit))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def search_by_formula(self, formula_pattern: str, limit: int = 20) -> List[Dict]:
        """按化学式搜索"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
        SELECT * FROM pdf2_cards 
        WHERE formula LIKE ? 
        ORDER BY card_num
        LIMIT ?
        ''', (f'%{formula_pattern}%', limit))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def search_by_cas(self, cas_number: str) -> List[Dict]:
        """按CAS号搜索"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
        SELECT * FROM pdf2_cards 
        WHERE cas = ? 
        ORDER BY card_num
        ''', (cas_number,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_card_details(self, card_num: int) -> Dict:
        """获取卡片详细信息"""
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT * FROM pdf2_cards WHERE card_num = ?', (card_num,))
        card = cursor.fetchone()
        
        if not card:
            return None
        
        result = dict(card)
        
        # 获取所有峰
        cursor.execute('''
        SELECT d_value, intensity 
        FROM pdf2_peaks 
        WHERE card_num = ? 
        ORDER BY intensity DESC
        ''', (card_num,))
        
        result['peaks'] = [dict(row) for row in cursor.fetchall()]
        
        return result
    
    def get_statistics(self) -> Dict:
        """获取数据库统计信息"""
        cursor = self.conn.cursor()
        
        stats = {}
        
        # 卡片总数
        cursor.execute('SELECT COUNT(*) FROM pdf2_cards')
        stats['total_cards'] = cursor.fetchone()[0]
        
        # 有峰数据的卡片数
        cursor.execute('SELECT COUNT(*) FROM pdf2_cards WHERE n_peaks > 0')
        stats['cards_with_peaks'] = cursor.fetchone()[0]
        
        # 峰数据总数
        cursor.execute('SELECT COUNT(*) FROM pdf2_peaks')
        stats['total_peaks'] = cursor.fetchone()[0]
        
        # 卡片类型分布
        cursor.execute('''
        SELECT card_type, COUNT(*) as count 
        FROM pdf2_cards 
        GROUP BY card_type 
        ORDER BY count DESC
        ''')
        stats['type_distribution'] = {row[0] or 'Unknown': row[1] for row in cursor.fetchall()}
        
        # 平均峰数
        cursor.execute('SELECT AVG(n_peaks) FROM pdf2_cards WHERE n_peaks > 0')
        stats['avg_peaks_per_card'] = cursor.fetchone()[0]
        
        return stats
    
    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("PDF2-2004 数据库查询工具")
        print("=" * 60)
        print("用法: python pdf2_query.py <命令> [参数]")
        print()
        print("命令:")
        print("  --stats             显示数据库统计信息")
        print("  --d <值>            按d值搜索 (例如: --d 3.14)")
        print("  --name <关键词>     按名称搜索")
        print("  --formula <模式>    按化学式搜索")
        print("  --cas <号码>        按CAS号搜索")
        print("  --card <编号>       查看卡片详情")
        print("  --db <路径>         指定数据库路径")
        print()
        print("示例:")
        print("  python pdf2_query.py --stats")
        print("  python pdf2_query.py --d 3.14")
        print("  python pdf2_query.py --name quartz")
        print("  python pdf2_query.py --formula SiO2")
        print("  python pdf2_query.py --cas 14808-60-7")
        print("  python pdf2_query.py --card 1000")
        return
    
    db_path = None
    if '--db' in sys.argv:
        db_idx = sys.argv.index('--db')
        if db_idx + 1 < len(sys.argv):
            db_path = sys.argv[db_idx + 1]
    
    try:
        query = PDF2Query(db_path)
        
        if sys.argv[1] == '--stats':
            stats = query.get_statistics()
            print("数据库统计信息:")
            print(f"  卡片总数: {stats['total_cards']:,}")
            print(f"  有峰数据的卡片: {stats['cards_with_peaks']:,} ({stats['cards_with_peaks']/stats['total_cards']*100:.1f}%)")
            print(f"  峰数据总数: {stats['total_peaks']:,}")
            print(f"  平均峰数/卡片: {stats['avg_peaks_per_card']:.1f}")
            print("  卡片类型分布:")
            for card_type, count in stats['type_distribution'].items():
                print(f"    {card_type}: {count:,} ({count/stats['total_cards']*100:.1f}%)")
        
        elif sys.argv[1] == '--d' and len(sys.argv) >= 3:
            try:
                d_value = float(sys.argv[2])
                tolerance = 0.02
                if len(sys.argv) >= 4 and sys.argv[3].startswith('--tol'):
                    if len(sys.argv) >= 5:
                        tolerance = float(sys.argv[4])
                
                results = query.search_by_d(d_value, tolerance, limit=10)
                print(f"搜索 d={d_value} (±{tolerance}) 的结果 ({len(results)}个):")
                for i, card in enumerate(results, 1):
                    print(f"\n{i}. 卡片号: {card['card_num_str']}")
                    print(f"   名称: {card['name']}")
                    print(f"   化学式: {card['formula']}")
                    print(f"   类型: {card['card_type']}")
                    print(f"   匹配的峰:")
                    for peak in card['matched_peaks']:
                        print(f"     d={peak['d_value']:.3f} Å, I={peak['intensity']}")
            except ValueError:
                print("错误: d值必须是数字")
        
        elif sys.argv[1] == '--name' and len(sys.argv) >= 3:
            keyword = sys.argv[2]
            results = query.search_by_name(keyword, limit=10)
            print(f"搜索名称包含 '{keyword}' 的结果 ({len(results)}个):")
            for i, card in enumerate(results, 1):
                print(f"\n{i}. 卡片号: {card['card_num_str']}")
                print(f"   名称: {card['name']}")
                print(f"   化学式: {card['formula']}")
                print(f"   CAS号: {card['cas']}")
                print(f"   类型: {card['card_type']}")
                print(f"   峰数量: {card['n_peaks']}")
        
        elif sys.argv[1] == '--formula' and len(sys.argv) >= 3:
            pattern = sys.argv[2]
            results = query.search_by_formula(pattern, limit=10)
            print(f"搜索化学式包含 '{pattern}' 的结果 ({len(results)}个):")
            for i, card in enumerate(results, 1):
                print(f"\n{i}. 卡片号: {card['card_num_str']}")
                print(f"   名称: {card['name']}")
                print(f"   化学式: {card['formula']}")
                print(f"   类型: {card['card_type']}")
        
        elif sys.argv[1] == '--cas' and len(sys.argv) >= 3:
            cas_num = sys.argv[2]
            results = query.search_by_cas(cas_num)
            print(f"搜索CAS号 '{cas_num}' 的结果 ({len(results)}个):")
            for i, card in enumerate(results, 1):
                print(f"\n{i}. 卡片号: {card['card_num_str']}")
                print(f"   名称: {card['name']}")
                print(f"   化学式: {card['formula']}")
                print(f"   类型: {card['card_type']}")
        
        elif sys.argv[1] == '--card' and len(sys.argv) >= 3:
            try:
                card_num = int(sys.argv[2])
                card = query.get_card_details(card_num)
                if card:
                    print(f"卡片详情: {card['card_num_str']}")
                    print(f"名称: {card['name']}")
                    print(f"化学式: {card['formula']}")
                    print(f"CAS号: {card['cas']}")
                    print(f"类型: {card['card_type']}")
                    print(f"辐射源: {card['radiation']}")
                    print(f"波长: {card['wavelength']}")
                    print(f"参考文献: {card['reference']}")
                    print(f"年份: {card['year']}")
                    print(f"峰数量: {card['n_peaks']}")
                    print(f"d值范围: {card['d_min']:.3f} - {card['d_max']:.3f} Å")
                    print(f"最大强度: {card['i_max']}")
                    
                    if card['peaks']:
                        print("\n峰数据 (按强度排序):")
                        for i, peak in enumerate(card['peaks'][:10], 1):
                            print(f"  {i}. d={peak['d_value']:.3f} Å, I={peak['intensity']}")
                        if len(card['peaks']) > 10:
                            print(f"  ... 还有 {len(card['peaks']) - 10} 个峰")
                else:
                    print(f"未找到卡片: {card_num}")
            except ValueError:
                print("错误: 卡片编号必须是数字")
        
        else:
            print("错误: 未知命令")
            main()
        
        query.close()
        
    except FileNotFoundError as e:
        print(f"错误: {e}")
    except Exception as e:
        print(f"错误: {e}")

if __name__ == '__main__':
    main()