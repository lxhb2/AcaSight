import struct, numpy as np

with open(r'F:\xwechat_files\wxid_02k0z8c1gb8i22_115d\msg\file\2026-04\tongliukuang yuankuang.raw','rb') as f:
    data = f.read()

offset = 36
n_full = (len(data) - offset) // 2
counts_full = np.array(struct.unpack(f'<{n_full}H', data[offset:offset+n_full*2]))
counts = counts_full[1::2]  # odd indices
n_pts = len(counts)
print(f'n_pts={n_pts}')

# Known reference peaks (Cu K-alpha, 2theta degrees):
# SiO2: 20.85, 26.64, 36.54, 39.47, 42.44, 50.14, 59.96, 68.15
# CuFeS2: 29.32, 33.85, 36.70, 42.80, 49.32, 58.29, 59.02
# FeS2: 28.52, 33.08, 37.64, 40.78, 47.44, 56.28, 59.36
# Cu2S: 24.69, 27.88, 32.52, 37.73, 45.90
# Cu5FeS4: 23.34, 29.78, 33.38, 36.38, 46.02
# CuS: 27.96, 29.28, 31.36, 48.04, 59.26
# CaCO3: 29.41, 39.46, 43.15, 47.12, 48.53, 57.41
# CaMg(CO3)2: 30.96, 37.40, 41.14, 44.01, 51.07

min_refs = {
    'SiO₂': [20.85, 26.64, 36.54, 39.47, 42.44, 50.14, 59.96, 68.15],
    'CuFeS₂': [29.32, 33.85, 36.70, 42.80, 49.32, 58.29, 59.02],
    'FeS₂': [28.52, 33.08, 37.64, 40.78, 47.44, 56.28, 59.36],
    'Cu₂S': [24.69, 27.88, 32.52, 37.73, 45.90],
    'Cu₅FeS₄': [23.34, 29.78, 33.38, 36.38, 46.02],
    'CuS': [27.96, 29.28, 31.36, 48.04, 59.26],
    'CaCO₃': [29.41, 39.46, 43.15, 47.12, 48.53, 57.41],
    'CaMg(CO₃)₂': [30.96, 37.40, 41.14, 44.01, 51.07],
}

def find_peaks(counts, threshold=None):
    if threshold is None:
        threshold = counts.max() * 0.1
    peaks = []
    for i in range(1, len(counts)-1):
        if counts[i] > counts[i-1] and counts[i] > counts[i+1] and counts[i] > threshold:
            peaks.append((i, counts[i]))
    return sorted(peaks, key=lambda x: -x[1])

def match_peaks(peak_angles, min_refs, tolerance=0.3):
    matches = {}
    for name, refs in min_refs.items():
        matched = []
        for pa in peak_angles:
            for ref in refs:
                if abs(pa - ref) < tolerance:
                    matched.append((ref, pa))
                    break
        if matched:
            matches[name] = matched
    return matches

# Try various start/step combinations
best = None
best_score = 0

for start in np.arange(2.5, 8.0, 0.25):
    for end_target in [85.0, 88.0, 90.0]:
        step = (end_target - start) / n_pts
        if step <= 0 or step > 0.03:
            continue
        
        peaks = find_peaks(counts)
        peak_angles = [start + i * step for i, v in peaks]
        
        matches = match_peaks(peak_angles, min_refs, tolerance=0.5)
        score = sum(len(m) for m in matches.values())
        
        if score > best_score:
            best_score = score
            best = (start, step, peak_angles, matches, peaks)
            print(f'\n★ New best: start={start:.2f}, step={step:.5f}, score={score}')
            for name, matched in matches.items():
                print(f'  {name}: {len(matched)} matches')
                for ref, found in matched:
                    print(f'    ref={ref:.2f}, found={found:.2f}, diff={found-ref:.2f}')

print(f'\n\n=== BEST CONFIG ===')
start, step, peak_angles, matches, peaks = best
print(f'start={start}, step={step}')
print(f'\nTop 20 peaks:')
for i, (angle, v) in enumerate(zip(peak_angles[:20], [p[1] for p in peaks[:20]])):
    print(f'  {angle:.3f}°: {v}')
