import struct, numpy as np, sys

filepath = sys.argv[1]
with open(filepath, 'rb') as f:
    data = f.read()

print(f"File: {filepath}")
print(f"Size: {len(data)} bytes ({len(data)/1024:.1f} KB)")

# ============================================================
# RAW1.01 format parsing
# ============================================================

sig = data[0:8]
print(f"Signature: {sig}")

version = struct.unpack('<I', data[8:12])[0]
print(f"Version: {version}")

# Parse date/time
date_str = data[16:28].decode('ascii', errors='replace').rstrip('\x00')
time_str = data[28:40].decode('ascii', errors='replace').rstrip('\x00')
print(f"Date: {date_str}, Time: {time_str}")

# Operator (offset 0x20, 32 bytes)
operator = data[0x20:0x40].decode('ascii', errors='replace').rstrip('\x00').rstrip()
print(f"Operator: {operator}")

# Site (offset 0x60, 32 bytes)
site = data[0x60:0x80].decode('ascii', errors='replace').rstrip('\x00').rstrip()
print(f"Site: {site}")

# ============================================================
# Key parameters from offset analysis
# ============================================================
print("\n--- Key Parameters ---")

# Offset 0x238: step size (0.6 degrees)
step_size = struct.unpack('<f', data[0x238:0x23C])[0]
print(f"Step size (0x238): {step_size}")

# Offset 0x240: 
val_240 = struct.unpack('<f', data[0x240:0x244])[0]
print(f"Param 0x240: {val_240}")

# Offset 0x248:
val_248 = struct.unpack('<f', data[0x248:0x24C])[0]
print(f"Param 0x248: {val_248}")

# Offset 0x25D:
num_pts_raw = struct.unpack('<I', data[0x25D:0x261])[0]
print(f"Num points raw (0x25D): {num_pts_raw}")

# Wavelength candidates
for off in [0x26C, 0x274, 0x27C, 0x284]:
    val = struct.unpack('<f', data[off:off+4])[0]
    print(f"Wavelength candidate (0x{off:X}): {val:.6f} A")

# Offset 0x28C:
val_28c = struct.unpack('<f', data[0x28C:0x290])[0]
print(f"Param 0x28C: {val_28c}")
val_290 = struct.unpack('<f', data[0x290:0x294])[0]
print(f"Param 0x290: {val_290}")

# Offset 0x2B2:
val_2b2 = struct.unpack('<f', data[0x2B2:0x2B6])[0]
print(f"Param 0x2B2: {val_2b2}")

# Offset 0x2C0:
val_2c0 = struct.unpack('<I', data[0x2C0:0x2C4])[0]
print(f"Param 0x2C0 (uint): {val_2c0}")

# Offset 0x2CC:
val_2cc = struct.unpack('<I', data[0x2CC:0x2D0])[0]
print(f"Param 0x2CC (uint): {val_2cc}")

# ============================================================
# Search for the count data section
# ============================================================
print("\n--- Searching for count data ---")

# Try offset 0x2C0 as potential data start
data_start = 0x2C0
counts_size = 0

# Try: 128 points * 4 bytes = 512 bytes
npts = 128
start_angle = 10.0  # typical XRD start
step = 0.02  # typical step

# Try: 3802 points or 3802/2 etc.
# Let's check what makes sense

# Try reading from 0x2C0
for npts in [128, 256, 3802, 7604, 16384]:
    try:
        section = data[data_start:data_start + npts*4]
        vals = np.array(struct.unpack(f'<{len(section)//4}I', section))
        if vals.max() > 0 and vals.max() < 1000000:
            print(f"  At 0x2C0, npts={npts}: min={vals.min()}, max={vals.max()}, mean={vals.mean():.1f}")
    except:
        pass

# Try 0x2000 as data start
for data_start in [0x300, 0x400, 0x500, 0x1000, 0x2000, 0x3000]:
    remaining = len(data) - data_start
    for npts in [128, 256, 512, 1000, 2000, 4000]:
        if npts * 4 > remaining:
            continue
        try:
            section = data[data_start:data_start + npts*4]
            vals = np.array(struct.unpack(f'<{len(section)//4}I', section))
            if vals.max() > 100 and vals.max() < 1000000 and vals.min() >= 0:
                # Check if it looks like XRD counts
                # XRD counts typically increase and decrease
                good_ratio = (vals > vals.mean()*0.1).sum() / len(vals)
                if good_ratio > 0.5:
                    print(f"  At 0x{data_start:X}, npts={npts}: min={vals.min()}, max={vals.max()}, mean={vals.mean():.1f}, nonzeros={good_ratio:.2f}")
        except:
            pass

# ============================================================
# Try to find the header/data boundary by looking for where
# the data counts start (they should be 4-byte aligned)
# ============================================================
print("\n--- Looking for data region ---")

# Look for consecutive unsigned int values in range 0-100000
for start in range(0, min(len(data)-128, 8192), 4):
    try:
        vals = np.array(struct.unpack('<32I', data[start:start+128]))
        max_v = vals.max()
        min_v = vals.min()
        # Valid XRD counts: between 0 and 100000, not all zero
        if max_v > 100 and max_v < 100000 and min_v >= 0:
            # Check if they're not all the same
            if vals.std() > 10:
                print(f"  Data candidate at 0x{start:X}: n=32, min={min_v}, max={max_v}, mean={vals.mean():.1f}, std={vals.std():.1f}")
                print(f"    First 8 values: {vals[:8]}")
                break
    except:
        pass
