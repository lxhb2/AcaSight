# -*- coding: utf-8 -*-
with open(r'C:\Users\Administrator\.qclaw\workspace\projects\src\tools\pulse_tools.py', 'rb') as f:
    raw = f.read()

# Find both occurrences of the table_end = content.find pattern
pos = 0
idxs = []
while True:
    idx = raw.find(b'table_end = content.find', pos)
    if idx == -1: break
    idxs.append(idx)
    pos = idx + 1

print(f"Found {len(idxs)} occurrences: {idxs}")
for idx in idxs:
    print(f"\nContext at {idx}:")
    # Show 50 bytes before
    before = raw[idx-50:idx]
    try:
        print(f"  Before: {before.decode('utf-8')}")
    except:
        print(f"  Before (hex): {before.hex()}")
    # Show 100 bytes after
    after = raw[idx:idx+100]
    try:
        print(f"  After: {after.decode('utf-8')}")
    except:
        print(f"  After (hex): {after.hex()}")

# Build the replacement bytes
OLD_B = (b')\n\n        table_end = content.find(b"\\n\\n", table_start)\n'
         b'        if table_end == -1:\n'
         b'            table_end = len(content)\n\n'
         b'        new_content = content[:table_start] + "\\n".join(table_lines) + "\\n" + content[table_end:]')

FIX_B = (b')\n\n        _table_end = len(content)\n'
         b'        _skip_first = False\n'
         b'        for i in range(table_start, min(table_start + 3000, len(content)):\n'
         b'            if content[i:i+2] == b"\\n\\n":\n'
         b'                after = content[i+2:i+5]\n'
         b'                if _skip_first:\n'
         b'                    if after in (b"---", b"## ", b"###"):\n'
         b'                        _table_end = i + 1\n'
         b'                        break\n'
         b'                else:\n'
         b'                    _skip_first = True\n\n'
         b'        new_content = content[:table_start] + "\\n".join(table_lines) + "\\n" + content[_table_end:]')

# Search for old pattern in raw bytes
# Find the exact bytes before the find()
for idx in idxs:
    before_marker = idx - 6  # go back to find ')\n\n'
    segment = raw[idx-10:idx+120]
    print(f"\n\nAt occurrence {idx}, segment raw:")
    print(segment)
    print()
    print(f"  Hex: {segment.hex()}")
