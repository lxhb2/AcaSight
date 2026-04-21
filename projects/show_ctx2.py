# -*- coding: utf-8 -*-
with open(r'C:\Users\Administrator\.qclaw\workspace\projects\src\tools\pulse_tools.py', 'r', encoding='utf-8') as f:
    txt = f.read()

OLD = ')\n\n        table_end = content.find("\\n\\n", table_start)\n        if table_end == -1:\n            table_end = len(content)\n\n        new_content = content[:table_start] + "\\n".join(table_lines) + "\\n" + content[table_end:]'

print(repr(OLD))
print()
print(f'Count: {txt.count(OLD)}')

# Check what's after each occurrence
for pos_str in ['15288', '19256']:
    pos = int(pos_str)
    after = txt.find(')\n\n        table_end = content.find', pos)
    print(f"\nOccurrence at {after}:")
    print(repr(txt[after:after+200]))
