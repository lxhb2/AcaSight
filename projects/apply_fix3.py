# -*- coding: utf-8 -*-
"""Apply precise fixes for both table_end replacement blocks"""
import re

F = r'C:\Users\Administrator\.qclaw\workspace\projects\src\tools\pulse_tools.py'

with open(F, 'rb') as f:
    raw = f.read()

def fix_block(after_if, next_else_or_comment):
    """Build the OLD block for a specific context"""
    OLD = (
        b'if table_start > 0:\n'
        b'        new_content = content[:table_start] + "\\n".join(table_lines) + "\\n" + content[table_end:]\n'
        + after_if +
        b'    else:'
    )
    NEW = (
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
        + after_if +
        b'    else:'
    )
    return OLD, NEW

# Block 1: add_challenge - no blank line after replacement, then '    else:'
OLD1 = (
    b'if table_start > 0:\n'
    b'        new_content = content[:table_start] + "\\n".join(table_lines) + "\\n" + content[table_end:]\n'
    b'\n'
    b'    else:\n'
    b'        list_section = "## '
)
NEW1 = (
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
    b'    else:\n'
    b'        list_section = "## '
)

# Block 2: complete_challenge - no blank line after replacement, then '\n    # ...frontmatter'
OLD2 = (
    b'if table_start > 0:\n'
    b'        new_content = content[:table_start] + "\\n".join(table_lines) + "\\n" + content[table_end:]\n'
    b'\n'
    b'    # '
)
NEW2 = (
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
    b'    # '
)

c1 = raw.count(OLD1)
c2 = raw.count(OLD2)
print(f"OLD1 count: {c1}, OLD2 count: {c2}")

if c1 == 1 and c2 == 1:
    txt2 = raw.replace(OLD1, NEW1, 1).replace(OLD2, NEW2, 1)
    with open(F, 'wb') as f:
        f.write(txt2)
    print("SUCCESS - both fixed")
else:
    print("ERROR: counts not as expected")
    print(f"OLD1 found at: {[raw.find(OLD1)]}")
    print(f"OLD2 found at: {[raw.find(OLD2)]}")
