# -*- coding: utf-8 -*-
with open(r'C:\Users\Administrator\.qclaw\workspace\projects\src\tools\pulse_tools.py', 'r', encoding='utf-8') as f:
    txt = f.read()

# Unicode escape to avoid encoding issues
OLD = ('    # \u6ede\u7f6e\u8868\u683c\u5185\u5bb9\n'
       '    if table_start > 0:\n'
       '        table_end = content.find("\\n\\n", table_start)\n'
       '        if table_end == -1:\n'
       '            table_end = len(content)\n\n'
       '        new_content = content[:table_start] + "\\n".join(table_lines) + "\\n" + content[table_end:]\n'
       '    else:')

FIX = ('    # \u6ede\u7f6e\u8868\u683c\u5185\u5bb9\n'
       '    if table_start > 0:\n'
       '        _table_end = len(content)\n'
       '        _skip_first = False\n'
       '        for i in range(table_start, min(table_start + 3000, len(content)):\n'
       '            if content[i:i+2] == "\\n\\n":\n'
       '                after = content[i+2:i+5]\n'
       '                if _skip_first:\n'
       '                    if after in ("---", "## ", "###"):\n'
       '                        _table_end = i + 1\n'
       '                        break\n'
       '                else:\n'
       '                    _skip_first = True\n\n'
       '        new_content = content[:table_start] + "\\n".join(table_lines) + "\\n" + content[_table_end:]\n'
       '    else:')

count = txt.count(OLD)
print(f'Found {count} occurrences of old pattern')
if count == 2:
    txt2 = txt.replace(OLD, FIX, 2)
    with open(r'C:\Users\Administrator\.qclaw\workspace\projects\src\tools\pulse_tools.py', 'w', encoding='utf-8') as f:
        f.write(txt2)
    print('Written OK')
else:
    print(f'ERROR: expected 2, got {count}')
    # Find all occurrences
    pos = 0
    found = 0
    while True:
        idx = txt.find('table_end = content.find', pos)
        if idx == -1: break
        print(f'  find at {idx}: {repr(txt[idx-20:idx+60])}')
        pos = idx + 1
        found += 1
    print(f'Total find(): {found}')
