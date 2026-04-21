# -*- coding: utf-8 -*-
"""Find exact boundaries by scanning byte by byte"""
import re

F = r'C:\Users\Administrator\.qclaw\workspace\projects\src\tools\pulse_tools.py'

with open(F, 'rb') as f:
    raw = f.read()

# Find all matches
pos = 0
matches = []
while True:
    idx = raw.find(b'table_end = content.find', pos)
    if idx == -1: break
    matches.append(idx)
    pos = idx + 1
print(f"Matches at: {matches}")

for m in matches:
    print(f"\n=== Match at byte {m} ===")
    # Context: go back to find ')\n\n' then 8 spaces
    # Start: find the 'if table_start > 0:'
    before = raw[max(0,m-200):m]
    if_stmt = raw[m-200:m]
    # Find 'if table_start > 0:' going backwards
    if_idx = if_stmt.rfind(b'if table_start > 0:')
    if if_idx >= 0:
        actual_start = m - 200 + if_idx
        print(f"if_start at {actual_start} (byte {m-200+if_idx})")
        # Find end: find the next '    else:' or '    #'
        segment = raw[actual_start:actual_start+500]
        # Find the else: or the next top-level comment
        else_pos = segment.find(b'    else:')
        alt_pos = segment.find(b'    # \xe6')
        end_poss = [x for x in [else_pos, alt_pos] if x >= 0]
        if end_poss:
            end_pos = min(end_poss)
            actual_block = raw[actual_start:actual_start+end_pos]
            print(f"Block ends at offset {end_pos}, block length {len(actual_block)}")
            print("Block:")
            for i, b in enumerate(actual_block):
                if 32 <= b < 127: print(chr(b), end='')
                elif b == 10: print('\\n')
                else: print(f'\\x{b:02x}', end='')
            print()
            print(f"\nBlock hex: {actual_block.hex()}")
