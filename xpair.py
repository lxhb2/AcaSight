import struct, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

data = open(r'F:\xwechat_files\wxid_02k0z8c1gb8i22_115d\msg\file\2026-04\Y-2(1).raw', 'rb').read()

# Check big-endian (>) interpretation of 2-byte pairs
print('=== Big-endian ushort (BE) from 0x0C58 ===')
vals_be = []
for i in range(0x0C58, 0x0C58+200, 2):
    val = struct.unpack('>H', data[i:i+2])[0]
    vals_be.append(val)

print('First 50 BE-ushort values:')
for i, v in enumerate(vals_be[:50]):
    angle = 5.0 + i * 0.02
    print(f'  i={i}: raw={v:5d}  angle={angle:.2f}')

# Also check: maybe the alternating zeros are from byte alignment
# What if data starts 1 byte offset?
print('\n=== Checking byte offset 1 from 0x0C58 ===')
vals_offset1 = []
for i in range(1, 0x0C58+200, 2):
    if i + 1 < len(data):
        val_le = struct.unpack('<H', data[i:i+2])[0]
        val_be = struct.unpack('>H', data[i:i+2])[0]
        vals_offset1.append((i, val_le, val_be))

print('First 30 LE/BE at byte offset 1:')
for i, (pos, le, be) in enumerate(vals_offset1[:30]):
    print(f'  pos={pos}: LE={le:6d}  BE={be:6d}')

# Try to identify data by looking for sequences of non-zero values
print('\n=== Looking for contiguous non-zero sequences ===')
all_vals = []
for i in range(0x0C58, min(0x0C58+10000, len(data)-1), 2):
    val = struct.unpack('<H', data[i:i+2])[0]
    all_vals.append(val)

# Find sequences of non-zero
in_seq = False
seq_start = 0
seqs = []
for i, v in enumerate(all_vals):
    if v != 0 and not in_seq:
        seq_start = i
        in_seq = True
    elif v == 0 and in_seq:
        seqs.append((seq_start, i-1, i-seq_start))
        in_seq = False
if in_seq:
    seqs.append((seq_start, len(all_vals)-1, len(all_vals)-seq_start))

print(f'Found {len(seqs)} non-zero sequences:')
for s, e, l in seqs[:20]:
    angle_s = 5.0 + s * 0.02
    angle_e = 5.0 + e * 0.02
    print(f'  indices {s}-{e} (len={l}), angles {angle_s:.2f}-{angle_e:.2f}')

# Check: maybe the data uses 4-byte floats for both angle and count?
# Let's look at the raw bytes as they appear
print('\n=== Raw bytes at 0x0C58-0x0C80 ===')
for i in range(0x0C58, 0x0C80, 1):
    print(f'0x{i:04X}: 0x{data[i]:02X} ({data[i]:3d})')
