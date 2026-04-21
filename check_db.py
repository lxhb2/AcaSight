import sqlite3
from pathlib import Path

db_path = Path(r"F:\桌面\pdf2_final_complete.db")
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

print("数据库状态检查:")
print("=" * 60)

# 检查所有表
cursor.execute("SELECT name, type FROM sqlite_master WHERE type IN ('table', 'view') ORDER BY type, name")
items = cursor.fetchall()

print("表和视图:")
for name, type_ in items:
    if type_ == 'table':
        cursor.execute(f'SELECT COUNT(*) FROM "{name}"')
        count = cursor.fetchone()[0]
        print(f"  表: {name} ({count:,} 条记录)")
    else:
        print(f"  视图: {name}")

print()
print("关键数据统计:")

# 检查卡片总数
cursor.execute("SELECT COUNT(*) FROM pdf2_cards")
total_cards = cursor.fetchone()[0]
print(f"总卡片数: {total_cards:,}")

# 检查峰数据
cursor.execute("SELECT COUNT(*) FROM pdf2_peaks")
total_peaks = cursor.fetchone()[0]
print(f"峰数据总数: {total_peaks:,}")

# 检查是否有summary表
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%summary%'")
summary_tables = cursor.fetchall()
if summary_tables:
    for table in summary_tables:
        cursor.execute(f'SELECT COUNT(*) FROM "{table[0]}"')
        count = cursor.fetchone()[0]
        print(f"{table[0]}: {count:,} 条记录")

# 检查是否有mineral表
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%mineral%'")
mineral_tables = cursor.fetchall()
if mineral_tables:
    for table in mineral_tables:
        cursor.execute(f'SELECT COUNT(*) FROM "{table[0]}"')
        count = cursor.fetchone()[0]
        print(f"{table[0]}: {count:,} 条记录")

# 检查卡片类型分布
print()
print("卡片类型分布:")
cursor.execute("""
SELECT card_type, COUNT(*) as count 
FROM pdf2_cards 
GROUP BY card_type 
ORDER BY count DESC
""")
for card_type, count in cursor.fetchall():
    print(f"  {card_type or 'Unknown'}: {count:,}")

conn.close()