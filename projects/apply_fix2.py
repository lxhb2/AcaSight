# -*- coding: utf-8 -*-
"""Fix using the correct byte pattern with full-width ）"""
import re

F = r'C:\Users\Administrator\.qclaw\workspace\projects\src\tools\pulse_tools.py'

with open(F, 'rb') as f:
    raw = f.read()

# CONFIRMED: the file uses full-width ） instead of )
# table_end\xef\xbc\x89 = table_end + full-width ）
OLD_B = (
    b'if table_start > 0:\n'
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

print(f"OLD_B count: {raw.count(OLD_B)}")
print(f"OLD_B: {OLD_B}")
print(f"NEW_B length: {len(NEW_B)}")

if raw.count(OLD_B) == 2:
    txt2 = raw.replace(OLD_B, NEW_B, 2)
    with open(F, 'wb') as f:
        f.write(txt2)
    print("SUCCESS - file written")
else:
    print(f"ERROR: found {raw.count(OLD_B)} occurrences, need 2")
    # Find what's actually at those positions
    # Show the context around each 'if table_start > 0:\n        new_content'
    pos = 0
    while True:
        idx = raw.find(b'if table_start > 0:\n        new_content', pos)
        if idx == -1: break
        seg = raw[idx:idx+200]
        print(f"\nContext at {idx}:")
        # Try UTF-8 decode
        try:
            txt = seg.decode('utf-8')
            print(txt)
        except Exception as e:
            print(f"UTF-8 error: {e}")
            for i, b in enumerate(seg[:200]):
                if 32 <= b < 127: print(chr(b), end='')
                elif b == 10: print('\\n')
                else: print(f'\\x{b:02x}', end='')
            print()
        pos = idx + 1
