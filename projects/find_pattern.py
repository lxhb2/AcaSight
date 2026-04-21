# -*- coding: utf-8 -*-
with open(r'C:\Users\Administrator\.qclaw\workspace\projects\src\tools\pulse_tools.py', 'rb') as f:
    raw = f.read()

# Check what's at bytes 17850-17910
print("Bytes 17850-17910:")
chunk = raw[17850:17910]
print(repr(chunk))
# Try to decode as utf-8
try:
    txt = chunk.decode('utf-8')
    print("As UTF-8:", repr(txt))
except:
    print("Cannot decode as UTF-8")

# Find all occurrences of the exact replace section (if table_start > 0 block)
import re
# Pattern: "if table_start > 0:\n        table_end = content.find..."
pat = rb'if table_start > 0:\n        table_end = content\.find\('
matches = list(re.finditer(pat, raw))
print(f"\nExact pattern matches: {len(matches)}")
for m in matches:
    start = m.start()
    print(f"  at {start}: {repr(raw[start:start+80])}")
