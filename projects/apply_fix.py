# -*- coding: utf-8 -*-
"""Build and apply the exact byte-level fix"""
import re

F = r'C:\Users\Administrator\.qclaw\workspace\projects\src\tools\pulse_tools.py'

with open(F, 'rb') as f:
    raw = f.read()

# The EXACT block from hex dump analysis:
# Preceded by ')\n\n' then 8 spaces
OLD_B = (
    b'if table_start > 0:\n'
    b'        table_end = content.find("\\n\\n", table_start)\n'
    b'        if table_end == -1:\n'
    b'            table_end = len(content)\n'
    b'\n'
    b'        new_content = content[:table_start] + "\\n".join(table_lines) + "\\n" + content[table_end:]\n'
    b'\n'
)

NEW_B = (
    b'if table_start > 0:\n'
    b'        _table_end = len(content)\n'
    b'        _skip_first = False\n'
    b'        for i in range(table_start, min(table_start + 3000, len(content)):\n'
    b'            if content[i:i+2] == "\\n\\n":\n'
    b'                after = content[i+2:i+5]\n'
    b'                if _skip_first:\n'
    b'                    if after in ("---", "## ", "###"):\n'
    b'                        _table_end = i + 1\n'
    b'                        break\n'
    b'                else:\n'
    b'                    _skip_first = True\n'
    b'\n'
    b'        new_content = content[:table_start] + "\\n".join(table_lines) + "\\n" + content[_table_end:]\n'
    b'\n'
)

print(f"OLD_B length: {len(OLD_B)}")
print(f"NEW_B length: {len(NEW_B)}")
c = raw.count(OLD_B)
print(f"Found {c} occurrences of OLD_B")

if c == 2:
    txt2 = raw.replace(OLD_B, NEW_B, 2)
    with open(F, 'wb') as f:
        f.write(txt2)
    print("Written OK")
else:
    print("ERROR: need exact count = 2")
    # Search for variant
    pos = 0
    while True:
        idx = raw.find(b'table_end = content.find', pos)
        if idx == -1: break
        seg = raw[idx-50:idx+300]
        print(f"\nAt {idx}:")
        for i, b in enumerate(seg):
            if 32 <= b < 127: print(chr(b), end='')
            elif b == 10: print('\\n')
            else: print(f'\\x{b:02x}', end='')
            if i > 0 and i % 50 == 49: print()
        print()
        pos = idx + 1
