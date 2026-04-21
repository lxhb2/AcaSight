import re

content = open('xrd_plot.py', 'r', encoding='utf-8').read()

# Search for PDF phase names in PDF_CARDS dictionary
pdf_section = content[content.find('PDF_CARDS'):content.find('# 图表配色方案')]
# Find all subscript-related characters
subscripts = [(i, ord(c), c) for i, c in enumerate(pdf_section) if ord(c) == 0x2082]
print(f'Subscript 2 in PDF_CARDS section: {subscripts}')

# Also check for other subscript chars
subscripts_all = [(i, ord(c), c) for i, c in enumerate(content) if ord(c) == 0x2082]
print(f'Total subscript 2 in file: {len(subscripts_all)}')

# Show context around each
for pos, code, ch in subscripts_all[:5]:
    start = max(0, pos - 30)
    end = min(len(content), pos + 30)
    print(f'  Context: {repr(content[start:end])}')

# Check PDF_CARDS keys
keys_section = content[content.find('PDF_CARDS'):content.find('# 图表配色方案')]
for line in keys_section.split('\n')[:5]:
    print('Line:', repr(line[:80]))
