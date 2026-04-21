# -*- coding: utf-8 -*-
"""Fix the two table_end = content.find replacements using byte-level search/replace"""
import os

F = r'C:\Users\Administrator\.qclaw\workspace\projects\src\tools\pulse_tools.py'

with open(F, 'rb') as f:
    raw = f.read()

# The old replacement block to replace (bytes, exact)
OLD_B1 = (
    b')\n\n        table_end = content.find(b"\\n\\n", table_start)\n'
    b'        if table_end == -1:\n'
    b'            table_end = len(content)\n\n'
    b'        new_content = content[:table_start] + "\\n".join(table_lines) + "\\n" + content[table_end:]'
)
# Different variant (no b prefix for string literals)
OLD_B2 = (
    b')\n\n        table_end = content.find("\\n\\n", table_start)\n'
    b'        if table_end == -1:\n'
    b'            table_end = len(content)\n\n'
    b'        new_content = content[:table_start] + "\\n".join(table_lines) + "\\n" + content[table_end:]'
)

NEW_B = (
    b')\n\n        _table_end = len(content)\n'
    b'        _skip_first = False\n'
    b'        for i in range(table_start, min(table_start + 3000, len(content)):\n'
    b'            if content[i:i+2] == "\\n\\n":\n'
    b'                after = content[i+2:i+5]\n'
    b'                if _skip_first:\n'
    b'                    if after in ("---", "## ", "###"):\n'
    b'                        _table_end = i + 1\n'
    b'                        break\n'
    b'                else:\n'
    b'                    _skip_first = True\n\n'
    b'        new_content = content[:table_start] + "\\n".join(table_lines) + "\\n" + content[_table_end:]'
)

print(f"OLD_B1 count: {raw.count(OLD_B1)}")
print(f"OLD_B2 count: {raw.count(OLD_B2)}")

# Try each pattern
for name, pat in [("OLD_B1", OLD_B1), ("OLD_B2", OLD_B2)]:
    c = raw.count(pat)
    print(f"{name}: {c} occurrences")
    if c > 0:
        # Find positions
        pos = 0
        while True:
            idx = raw.find(pat, pos)
            if idx == -1: break
            print(f"  at byte {idx}: {repr(raw[idx-30:idx+50])}")
            pos = idx + 1
