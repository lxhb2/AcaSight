import struct, numpy as np, sys

filepath = sys.argv[1]
with open(filepath, 'rb') as f:
    data = f.read()

print(f"=== RAW1.01 Parser ===")
print(f"File: {filepath}")
print(f"Size: {len(data)} bytes")

# RAW1.01 format analysis
# Header size: 4096 bytes typically
# Let's look at specific known offset patterns

# Offset 0x00-0x07: signature "RAW1.01"
# Offset 0x08-0x0B: version (uint32 LE)
# Offset 0x0C-0x0F: unknown
# Offset 0x10-0x17: date/time
# Offset 0x18-0x27: operator
# Offset 0x28-0x47: site

# Let's look at bytes around offset 128-512 more carefully
print("\n--- Header bytes 0-256 (hex) ---")
for i in range(0, 256, 16):
    hex_str = ' '.join(f'{b:02X}' for b in data[i:i+16])
    ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[i:i+16])
    print(f"  {i:04X}: {hex_str}  {ascii_str}")

# Known parameters for XRD RAW1.01
# Offset 512-1024 often contains measurement parameters
print("\n--- Header bytes 512-768 (hex) ---")
for i in range(512, 768, 16):
    hex_str = ' '.join(f'{b:02X}' for b in data[i:i+16])
    ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[i:i+16])
    print(f"  {i:04X}: {hex_str}  {ascii_str}")

# Look for the binary data section
# RAW files typically store: header + parameter block + raw counts
# Count data usually starts after header

# Try to find where float data starts (angles)
print("\n--- All float values in header (512-1024) ---")
for i in range(512, min(1024, len(data)-4)):
    try:
        val = struct.unpack('<f', data[i:i+4])[0]
        if 0 <= val <= 200:
            print(f"  {i:04X}: {val:.6f}")
    except:
        pass

# The RAW1.01 format has parameter data
# Try to find the data offset
# Count how many bytes are in header
# Some RAW files have variable header size

# Search for Goniometer parameters
# Offset ~4000 area
print("\n--- Bytes 4000-4096 (hex) ---")
for i in range(4000, min(4096, len(data)), 16):
    hex_str = ' '.join(f'{b:02X}' for b in data[i:i+16])
    ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[i:i+16])
    print(f"  {i:04X}: {hex_str}  {ascii_str}")

# Look at specific offsets
for i in range(600, 800, 4):
    val_u32 = struct.unpack('<I', data[i:i+4])[0]
    val_i32 = struct.unpack('<i', data[i:i+4])[0]
    val_f = struct.unpack('<f', data[i:i+4])[0]
    if 0 < val_u32 < 100000 or 0 <= val_f <= 100:
        print(f"  {i:04X}: uint={val_u32}, int={val_i32}, float={val_f:.4f}")
