import struct, numpy as np, sys

filepath = sys.argv[1]
with open(filepath, 'rb') as f:
    data = f.read()

# Known: wavelength ~1.9427, header_size likely 512 or variable
# Let's find all 16-bit unsigned candidates that look like XRD counts

print("=== Scanning all offsets for 16-bit XRD count data ===")
# XRD counts: min ~0, max ~20000-50000, mean ~1000-10000
# Data should span most of the file (several thousand points)
# Typical: 5-80 degrees in 0.02 deg steps = 3750 points

results = []
for offset in range(0, min(len(data)-128, 8192), 2):
    remaining = len(data) - offset
    n = remaining // 2
    if n < 100:
        continue
    try:
        vals = np.array(struct.unpack(f'<{n}H', data[offset:offset+n*2]))
        if vals.max() > 100 and vals.max() < 65535 and vals.min() >= 0:
            # XRD-like characteristics
            std = vals.std()
            mean = vals.mean()
            nonzero = (vals > 0).sum()
            # Counts should span a reasonable range
            if 500 < nonzero < n and 100 < std < 30000:
                # Check if data looks like a spectrum (not just random)
                # Most values should be moderate
                pct_low = (vals < 100).sum() / len(vals)
                pct_high = (vals > mean + 2*std).sum() / len(vals)
                if pct_high < 0.2 and pct_low > 0.1:
                    results.append((offset, n, vals.min(), vals.max(), mean, std, nonzero))
    except:
        pass

# Deduplicate and show
seen_offsets = set()
for r in sorted(results, key=lambda x: -x[5])[:20]:
    offset, n, vmin, vmax, mean, std, nonzero = r
    # Check if this overlaps with previous
    skip = False
    for s in seen_offsets:
        if abs(s - offset) < 100:
            skip = True
            break
    if not skip:
        seen_offsets.add(offset)
        print(f"  Offset 0x{offset:04X} ({offset}): n={n}, min={vmin}, max={vmax}, mean={mean:.0f}, std={std:.0f}, nonzero={nonzero}")

# Also try 32-bit float data (common in some XRD formats)
print("\n=== Scanning all offsets for 32-bit float angle data ===")
for offset in range(512, min(len(data)-128, 4096), 4):
    remaining = len(data) - offset
    n = remaining // 4
    if n < 50:
        continue
    try:
        vals = np.array(struct.unpack(f'<{n}f', data[offset:offset+n*4]))
        # Angles should be in range 0-90 degrees
        if vals.min() >= 0 and vals.max() <= 90:
            nonzero = (vals > 0.01).sum()
            if nonzero > 10:
                print(f"  Offset 0x{offset:04X} ({offset}): n={n}, min={vals.min():.4f}, max={vals.max():.4f}, nonzero={nonzero}")
    except:
        pass

# Try 32-bit float data for counts
print("\n=== Scanning for 32-bit float count data ===")
for offset in range(512, min(len(data)-128, 8192), 4):
    remaining = len(data) - offset
    n = remaining // 4
    if n < 50:
        continue
    try:
        vals = np.array(struct.unpack(f'<{n}f', data[offset:offset+n*4]))
        if vals.min() >= 0 and vals.max() < 100000:
            nonzero = (vals > 1).sum()
            if nonzero > 50 and vals.std() > 100:
                print(f"  Offset 0x{offset:04X} ({offset}): n={n}, min={vals.min():.2f}, max={vals.max():.2f}, mean={vals.mean():.2f}, nonzero={nonzero}")
    except:
        pass
