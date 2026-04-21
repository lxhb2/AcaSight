"""Test script for Sci-XRD Skill v2.0"""
import sys
sys.path.insert(0, 'C:/Users/Administrator/.qclaw/skills/sci-xrd')

from sci_xrd import parse_xrd, identify_minerals, plot_xrd_thesis, analyze_flotation_effect

files = {
    'raw': r'F:\xwechat_files\wxid_02k0z8c1gb8i22_115d\msg\file\2026-04\tongliukuang yuankuang.raw',
    'conc': r'F:\xwechat_files\wxid_02k0z8c1gb8i22_115d\msg\file\2026-04\2cu2jing jingkuang tongliukuang.raw',
    'tail': r'F:\xwechat_files\wxid_02k0z8c1gb8i22_115d\msg\file\2026-04\2cu2jing weikuang tongliukuang.raw'
}

datasets = {}
mineral_results = {}

print('Parsing XRD data...')
for key, path in files.items():
    angle, intensity = parse_xrd(path)
    datasets[key] = (angle, intensity)
    minerals = identify_minerals(angle, intensity)
    mineral_results[key] = minerals
    print(f'{key}: {len(intensity)} points, max={intensity.max():.0f}')
    for m in minerals[:3]:
        name = m['name']
        cnt = m['match_count']
        print(f'  {name}: {cnt} peaks')

print('\nGenerating thesis comparison plot...')
output = r'C:\Users\Administrator\Desktop\skill_v2_test.png'
plot_xrd_thesis(datasets, output=output, show_ref=True, offset=50)
print(f'Saved: {output}')

print('\nAnalyzing flotation effect...')
analysis = analyze_flotation_effect(
    datasets, 
    mineral_results, 
    target_minerals=['CuFeS2', 'Cu2S', 'CuS']
)
print(analysis['conclusion'])

print('\nDone!')
