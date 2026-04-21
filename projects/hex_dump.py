# -*- coding: utf-8 -*-
"""Analyze exact bytes and fix the file"""
import os, re

F = r'C:\Users\Administrator\.qclaw\workspace\projects\src\tools\pulse_tools.py'

with open(F, 'rb') as f:
    raw = f.read()

# Find the exact context around each table_end = content.find
import re
pat = rb'if table_start > 0:\n        table_end = content\.find'
for m in re.finditer(pat, raw):
    start = m.start()
    print(f"\n=== Match at byte {start} ===")
    seg = raw[start:start+250]
    print("Hex dump:")
    for i in range(0, len(seg), 40):
        hex_part = seg[i:i+40]
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in hex_part)
        print(f"  +{i:3d}: {hex_part.hex(' ')}  {ascii_part}")
    # Also show as UTF-8 text
    try:
        txt_seg = seg.decode('utf-8')
        print(f"\nText:\n{txt_seg}")
    except Exception as e:
        print(f"UTF-8 decode error: {e}")
        # show escaped
        for i, b in enumerate(seg):
            if 32 <= b < 127:
                print(chr(b), end='')
            elif b == 10:
                print('\\n')
            else:
                print(f'\\x{b:02x}', end='')
        print()
