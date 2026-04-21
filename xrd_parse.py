import struct, sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
data = open(r'F:\xwechat_files\wxid_02k0z8c1gb8i22_115d\msg\file\2026-04\Y-2(1).raw', 'rb').read()

print('=== Full header analysis (0x0000 to 0x00D0) ===')
for i in range(0, 0x00D0, 16):
    chunk = data[i:i+16]
    hex_str = ' '.join(f'{b:02X}' for b in chunk)
    ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
    print(f'0x{i:04X}: {hex_str:<48}  {ascii_str}')

print('\n=== Scan parameters section (0x0070 to 0x00C0) ===')
for i in range(0x0070, 0x00C0, 8):
    le_f = struct.unpack('<f', data[i:i+4])[0]
    be_f = struct.unpack('>f', data[i:i+4])[0]
    le_i = struct.unpack('<I', data[i:i+4])[0]
    be_i = struct.unpack('>I', data[i:i+4])[0]
    le_s = struct.unpack('<h', data[i:i+2])[0]
    be_s = struct.unpack('>h', data[i:i+2])[0]
    le_us = struct.unpack('<H', data[i:i+2])[0]
    print(f'0x{i:04X}: LE-f={le_f:12.4f}  BE-f={be_f:12.4f}  LE-uI={le_i:10d}  LE-s={le_s:6d}  BE-uI={be_i:10d}')

print('\n=== Data section starts at 0x0C58 ===')
print('First 20 LE-ushort values (×0.01 = cps):')
for i in range(0x0C58, 0x0C58+40, 2):
    val = struct.unpack('<H', data[i:i+2])[0]
    print(f'  0x{i:04X}: {val:6d} ({val/100:.2f} cps)')

print('\n=== Try: Is there an angle table somewhere? ===')
# Check 0x0C00-0x0C58
for i in range(0x0C00, 0x0C58, 4):
    be_f = struct.unpack('>f', data[i:i+4])[0]
    le_f = struct.unpack('<f', data[i:i+4])[0]
    if 5 < be_f < 80:
        print(f'  BE-f at 0x{i:04X}: {be_f:.4f}')
    if 5 < le_f < 80:
        print(f'  LE-f at 0x{i:04X}: {le_f:.4f}')
