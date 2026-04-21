# -*- coding: utf-8 -*-
with open(r'C:\Users\Administrator\.qclaw\workspace\projects\src\tools\pulse_tools.py', 'r', encoding='utf-8') as f:
    txt = f.read()

# Show what's actually around position 15288 and 19256
for pos in [15288, 19256]:
    print(f"Around pos {pos}:")
    print(repr(txt[pos-50:pos+120]))
    print()
