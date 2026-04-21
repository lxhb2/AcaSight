import json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

with open(r'C:\Users\Administrator\.qclaw\workspace\Sci-XRD-Pro-New\data\pdf_database.json', encoding='utf-8') as f:
    data = json.load(f)

print(f'Total minerals in pdf_database.json: {len(data)}')
for item in data:
    peaks = list(zip(item['2theta'], item['intensities']))
    peaks_str = ', '.join([f'{t:.2f}({i})' for t, i in peaks])
    print(f'{item["pdf_no"]} | {item["name"]} ({item["formula"]}) | {peaks_str}')

print()

# Also show pdf4_data.json
with open(r'C:\Users\Administrator\.qclaw\workspace\Sci-XRD-Pro-New\data\pdf4_data.json', encoding='utf-8') as f:
    data4 = json.load(f)
print(f'Total minerals in pdf4_data.json: {len(data4)}')
for item in data4:
    peaks = list(zip(item['2theta'], item['intensities']))
    peaks_str = ', '.join([f'{t:.2f}({i})' for t, i in peaks])
    print(f'{item["pdf_no"]} | {item["name"]} ({item["formula"]}) | {peaks_str}')
