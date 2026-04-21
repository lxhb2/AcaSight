# -*- coding: utf-8 -*-
with open(r'C:\Users\Administrator\.qclaw\workspace\projects\src\tools\pulse_tools.py', 'rb') as f:
    raw = f.read()

# Find both occurrences by searching all table_end = content.find positions
pos = 0
idxs = []
while True:
    idx = raw.find(b'table_end = content.find', pos)
    if idx == -1: break
    idxs.append(idx)
    pos = idx + 1

print(f"Found {len(idxs)} occurrences: {idxs}")

# Show the context around each
for idx in idxs:
    print(f"\n=== At byte {idx} ===")
    # Show 60 bytes before and 150 after
    seg = raw[max(0,idx-60):idx+150]
    print("Hex:")
    for i in range(0, len(seg), 20):
        print(f"  {idx-60+i:06x}: {seg[i:i+20].hex()}")
    print("Text:")
    try:
        print(repr(seg.decode('utf-8')))
    except:
        # show as escaped
        for i, b in enumerate(seg[:80]):
            try:
                c = chr(b)
                print(chr(b), end='')
            except:
                print(f'\\x{b:02x}', end='')
        print()

# Build the exact OLD pattern from the actual bytes
# For add_challenge: find the context ending with ')\n\n        table_end = content.find'
# From the hex we saw: '...0a0a202020202020207461626c65...'
# 0a0a = \n\n, 2020202020202020 = 8 spaces
print()
print("Looking for exact OLD pattern bytes...")
OLD_PATTERNS = [
    b')\n\n        table_end = content.find(b"\\n\\n", table_start)',
    b')\n\n        table_end = content.find("\\n\\n", table_start)',
    b')\n\n        table_end = content.find(' + b'\\n\\n".*table_start)',
]
for p in OLD_PATTERNS:
    c = raw.count(p)
    print(f"  {repr(p[:50])}: {c}")

# Try the specific pattern we found at 17905
# Raw from 17905-20=17885 to 17905+120=18025
seg = raw[17885:18025]
print(f"\nAround byte 17905 ({len(seg)} bytes):")
print(seg.hex())
try:
    print(repr(seg.decode('utf-8')))
except Exception as e:
    print(f"Decode error: {e}")

# Try to find it using regex
import re
# Search for the entire if block
pat = rb'if table_start > 0:\n\s{8}table_end = content\.find\('
matches = list(re.finditer(pat, raw))
print(f"\nRegex matches: {len(matches)}")
for m in matches:
    start = m.start()
    print(f"  at {start}: {repr(raw[start:start+100])}")
