import struct
import numpy as np

files = [
    r"F:\xwechat_files\wxid_02k0z8c1gb8i22_115d\msg\file\2026-04\tongliukuang yuankuang.raw",
    r"F:\xwechat_files\wxid_02k0z8c1gb8i22_115d\msg\file\2026-04\2cu2jing jingkuang tongliukuang.raw",
    r"F:\xwechat_files\wxid_02k0z8c1gb8i22_115d\msg\file\2026-04\2cu2jing weikuang tongliukuang.raw",
]

for filepath in files:
    with open(filepath, 'rb') as fh:
        data = fh.read()
    name = filepath.split("\\")[-1]
    print(f"\nFile: {name}")
    print(f"  Size: {len(data)} bytes")

    # Try float32 from position 892
    chunk = data[892:892+4000]
    vals = struct.unpack(f'<{len(chunk)//4}f', chunk)
    valid = [v for v in vals if 0 <= v <= 5000]
    print(f"  Float32 from 892: {len(valid)} valid, max={max(vals):.1f}, non-zero={sum(1 for v in vals if v > 0.1)}")
    if valid:
        print(f"  First 40 values: {[round(v,1) for v in vals[:40]]}")

    # Try uint16 from position 892
    chunk2 = data[892:892+8000]
    vals2 = struct.unpack(f'<{len(chunk2)//2}H', chunk2)
    valid2 = [v for v in vals2 if 0 <= v <= 10000]
    print(f"  Uint16 from 892: {len(valid2)} valid, max={max(vals2)}")
    if valid2:
        print(f"  First 40 values: {list(vals2[:40])}")
