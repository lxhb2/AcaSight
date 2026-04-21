import struct, numpy as np, sys

filepath = sys.argv[1]
with open(filepath, 'rb') as f:
    data = f.read()

print(f"File: {filepath}")
print(f"Size: {len(data)} bytes")
print(f"Signature: {data[0:8]}")

# Parse RAW1.01 header
version = struct.unpack('<I', data[8:12])[0]
print(f"Version: {version}")

# Print all readable strings in header (first 512 bytes)
print("\n--- Header strings ---")
for i in range(0, min(512, len(data)-1)):
    if data[i] >= 32 and data[i] < 127:
        start = i
        s = []
        while i < len(data) and 32 <= data[i] < 127:
            s.append(chr(data[i]))
            i += 1
        if len(s) > 3:
            print(f"  [{start:04d}] {''.join(s)}")
    else:
        i += 1

# Find number of steps
num_bytes = len(data)
print(f"\nLast 32 bytes (hex): {data[-32:].hex()}")
print(f"Last 32 bytes: {data[-32:]}")

# Look for the numeric parameters
# RAW1.01 format: after header strings, there are numeric fields
# Try to find: numPoints, startAngle, stepSize, etc.
# Search for known float patterns

# Find float values that could be angles (5.0 to 90.0 degrees)
print("\n--- Searching for angle values ---")
for i in range(256, min(len(data)-4, 4096)):
    try:
        val = struct.unpack('<f', data[i:i+4])[0]
        if 0.5 <= val <= 90.0:
            # check if next 4 bytes are also float
            try:
                val2 = struct.unpack('<f', data[i+4:i+8])[0]
                if 0 <= val2 <= 5.0:  # step size
                    print(f"  Offset {i}: {val:.4f}, next: {val2:.4f}")
            except:
                pass
    except:
        pass

# Try to find counts data (usually at the end, unsigned int)
print("\n--- Searching for count ranges ---")
counts = []
for i in range(300, min(len(data)-4, 8192)):
    try:
        val = struct.unpack('<I', data[i:i+4])[0]
        if 0 <= val <= 100000:
            counts.append((i, val))
    except:
        pass

# Show unique-ish values
seen = set()
for i, v in counts:
    key = round(v / 100) * 100
    if key not in seen and v > 100:
        print(f"  Offset {i}: {v}")
        seen.add(key)
        if len(seen) > 20:
            break
