import struct, numpy as np, sys

filepath = sys.argv[1]
with open(filepath, 'rb') as f:
    data = f.read()

print(f"File: {filepath}, Size: {len(data)} bytes")

# RAW1.01 format key findings:
# Wavelength: ~1.9427 Angstrom (Cu K-alpha)
# Header offset 0x25D: 128 (could be number of steps)
# Offset 0x2CC: 3802

# File size analysis
# 16264 - header_size = data_size
# If header = 512, data bytes = 15752 = 788*20 = 3938*4 = ?
# 16264 - 512 = 15752 -> 15752/4 = 3938 points
# 16264 - 1024 = 15240 -> 15240/4 = 3810 points (close to 3802!)
# 16264 - 2048 = 14216 -> 14216/4 = 3554 points
# 16264 - 4096 = 12168 -> 12168/4 = 3042 points
# 16264 - 3072 = 13192 -> 13192/4 = 3298 points

# Try 15240 / 2 = 7620 (16-bit counts)
# Try 15240 / 4 = 3810 (32-bit counts) - very close to 3802!

# Let's try header = 1024
print("\n=== Trying header_size = 1024 ===")
hsize = 1024
counts_data = data[hsize:]
n = len(counts_data) // 4
print(f"  Points (4-byte): {n}, remainder: {len(counts_data) % 4}")

# Read as uint32
counts = np.array(struct.unpack(f'<{n}I', counts_data[:n*4]))
print(f"  Min: {counts.min()}, Max: {counts.max()}, Mean: {counts.mean():.1f}")
print(f"  Nonzero: {(counts > 0).sum()}, >100: {(counts > 100).sum()}")
print(f"  First 20: {counts[:20]}")
print(f"  Last 20: {counts[-20:]}")
print(f"  Std: {counts.std():.1f}")

# If header = 2048
print("\n=== Trying header_size = 2048 ===")
hsize = 2048
counts_data = data[hsize:]
n = len(counts_data) // 4
print(f"  Points (4-byte): {n}, remainder: {len(counts_data) % 4}")
counts = np.array(struct.unpack(f'<{n}I', counts_data[:n*4]))
print(f"  Min: {counts.min()}, Max: {counts.max()}, Mean: {counts.mean():.1f}")
print(f"  Nonzero: {(counts > 0).sum()}, >100: {(counts > 100).sum()}")
print(f"  First 20: {counts[:20]}")
print(f"  Std: {counts.std():.1f}")

# If header = 4096
print("\n=== Trying header_size = 4096 ===")
hsize = 4096
counts_data = data[hsize:]
n = len(counts_data) // 4
print(f"  Points (4-byte): {n}, remainder: {len(counts_data) % 4}")
counts = np.array(struct.unpack(f'<{n}I', counts_data[:n*4]))
print(f"  Min: {counts.min()}, Max: {counts.max()}, Mean: {counts.mean():.1f}")
print(f"  Nonzero: {(counts > 0).sum()}, >100: {(counts > 100).sum()}")
print(f"  First 20: {counts[:20]}")
print(f"  Std: {counts.std():.1f}")

# Also try 16-bit unsigned
print("\n=== Trying 16-bit unsigned at header_size = 2048 ===")
n16 = len(counts_data) // 2
counts16 = np.array(struct.unpack(f'<{n16}H', counts_data[:n16*2]))
print(f"  Min: {counts16.min()}, Max: {counts16.max()}, Mean: {counts16.mean():.1f}")
print(f"  Nonzero: {(counts16 > 0).sum()}, >100: {(counts16 > 100).sum()}")
print(f"  Std: {counts16.std():.1f}")

# Also try header = 3072
print("\n=== Trying header_size = 3072 ===")
hsize = 3072
counts_data = data[hsize:]
n = len(counts_data) // 4
counts = np.array(struct.unpack(f'<{n}I', counts_data[:n*4]))
print(f"  Min: {counts.min()}, Max: {counts.max()}, Mean: {counts.mean():.1f}")
print(f"  Nonzero: {(counts > 0).sum()}, >100: {(counts > 100).sum()}")
print(f"  Std: {counts.std():.1f}")
