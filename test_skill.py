"""Test script for updated sci-xrd skill"""
from sci_xrd import parse_xrd, identify_minerals, plot_xrd_thesis, analyze_flotation_effect

# Test files
files = {
    'raw': r'F:\xwechat_files\wxid_02k0z8c1gb8i22_115d\msg\file\2026-04\tongliukuang yuankuang.raw',
    'conc': r'F:\xwechat_files\wxid_02k0z8c1gb8i22_115d\msg\file\2026-04\2cu2jing jingkuang tongliukuang.raw',
    'tail': r'F:\xwechat_files\wxid_02k0z8c1gb8i22_115d\msg\file\2026-04\2cu2jing weikuang tongliukuang.raw'
}

datasets = {}
mineral_results = {}

print("=" * 60)
print("Testing Sci-XRD Skill v2.0")
print("=" * 60)

for key, path in files.items():
    print(f"\nParsing {key}...")
    angle, intensity = parse_xrd(path)
    datasets[key] = (angle, intensity)
    minerals = identify_minerals(angle, intensity)
    mineral_results[key] = minerals
    
    print(f"  Points: {len(intensity)}")
    print(f"  Max intensity: {intensity.max():.1f}")
    print(f"  Minerals found:")
    for m in minerals[:5]:
        print(f"    - {m['name']} ({m['formula']}): {m['match_count']} peaks matched")

# Generate comparison plot
print("\n" + "-" * 60)
print("Generating thesis-level comparison plot...")
output = r"C:\Users\Administrator\.qclaw\workspace\skill_test_output.png"
plot_xrd_thesis(datasets, output=output, show_ref=True, offset=50)
print(f"Output: {output}")

# Analyze flotation effect
print("\n" + "-" * 60)
print("Analyzing flotation effect...")
analysis = analyze_flotation_effect(
    datasets,
    mineral_results,
    target_minerals=['CuFeS2', 'Cu2S', 'CuS'],
    sample_names={'raw': 'Raw Ore', 'conc': 'Concentrate', 'tail': 'Tailings'}
)

print(analysis['summary'])
print()
print(analysis['conclusion'])

print("\n" + "=" * 60)
print("Test completed successfully!")
print("=" * 60)
