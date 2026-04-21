import numpy as np
from scipy.signal import find_peaks, savgol_filter
from pathlib import Path

D = Path(r'F:\桌面\王铨毕业论文\xrd数据')
def load(f):
    a, i = [], []
    with open(f, 'r', encoding='utf-8', errors='replace') as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith(';') or line.startswith('#'): continue
            parts = [p.strip() for p in line.split(',')] if ',' in line else line.split()
            if len(parts) >= 2:
                try: a.append(float(parts[0])); i.append(float(parts[1]))
                except: continue
    return np.array(a), np.array(i)

# 精矿峰检测 - 复现脚本实际逻辑
ac, ic = load(D / '2cu2jing jingkuang tongliukuang_converted.txt')
ac = ac[ic>=0]; ic = ic[ic>=0]
mask = (ac>=5)&(ac<=80); x,y = ac[mask], ic[mask]

m2 = (x>=20)&(x<=60)
ys_local = savgol_filter(y[m2], window_length=51, polyorder=3)
peaks, props = find_peaks(ys_local, height=ys_local.max()*0.30, prominence=ys_local.max()*0.08, distance=20)
px = x[m2][peaks]; py = y[m2][peaks]
if len(px)<3:
    m_low=(x>=5)&(x<=20); x_l,y_l=x[m_low],y[m_low]
    ys_l=savgol_filter(y_l,window_length=21,polyorder=3)
    pk,_=find_peaks(ys_l,height=ys_l.max()*0.5,prominence=ys_l.max()*0.2)
    if len(pk)>0:
        top=pk[np.argmax(ys_l[pk])]
        px=np.append(px,x_l[top]); py=np.append(py,y_l[top])

print('=== 精矿实际峰检测结果 ===')
for i,(bx,by) in enumerate(zip(px,py),1):
    print(f'  Peak{i}: 2theta={bx:.2f}deg, I={by:.0f}')
print(f'  Total: {len(px)} peaks')
print()

# Correct phase assignments based on actual peak positions vs PDF references
print('=== Recommended phase assignments ===')
# PDF references: SiO2(26.65,20.85,50.14), CuFeS2(29.42), Cu2S(31.18),
#                 CuS(33.05), FeS2(56.28)
pdf_ref = {
    'SiO2_1': (26.65, 'SiO2-Quartz'),
    'SiO2_2': (20.85, 'SiO2-Quartz'),
    'SiO2_3': (50.14, 'SiO2-Quartz'),
    'CuFeS2': (29.42, 'CuFeS2-Chalcopyrite'),
    'Cu2S':   (31.18, 'Cu2S-Chalcocite'),
    'CuS':    (33.05, 'CuS-Covellite'),
    'FeS2':   (56.28, 'FeS2-Pyrite'),
}
for i, p in enumerate(px):
    diffs = [(abs(p - ref), name) for ref, name in pdf_ref.values()]
    best = sorted(diffs)[0]
    print(f'  Peak{i+1}@{p:.2f}deg -> Best match: {best[1]} (delta={best[0]:.2f}deg)')

# Also check: what does the raw ore detect?
print()
print('=== Raw Ore peak detection ===')
ar, ir = load(D / 'tongliukuang yuankuang.txt')
ar = ar[ir>=0]; ir = ir[ir>=0]
mask = (ar>=5)&(ar<=80); xr,yr = ar[mask], ir[mask]
ys = savgol_filter(yr, window_length=15, polyorder=3)
peaks,_ = find_peaks(ys, height=ys.max()*0.10, prominence=ys.max()*0.05, distance=15)
px_r = xr[peaks]; py_r = yr[peaks]
if len(px_r) > 8:
    idx = np.argsort(py_r)[-8:]
    px_r = px_r[np.sort(idx)]
    py_r = py_r[np.sort(idx)]
print(f'  Detected {len(px_r)} peaks:')
for i,(bx,by) in enumerate(zip(px_r,py_r),1):
    print(f'  Peak{i}: 2theta={bx:.2f}deg, I={by:.0f}')

# Tailings
print()
print('=== Tailings peak detection ===')
at, it = load(D / '2cu2jing weikuang tongliukuang.txt')
at = at[it>=0]; it = it[it>=0]
mask = (at>=5)&(at<=80); xt,yt = at[mask], it[mask]
ys = savgol_filter(yt, window_length=15, polyorder=3)
peaks,_ = find_peaks(ys, height=ys.max()*0.10, prominence=ys.max()*0.05, distance=15)
px_t = xt[peaks]; py_t = yt[peaks]
if len(px_t) > 8:
    idx = np.argsort(py_t)[-8:]
    px_t = px_t[np.sort(idx)]
    py_t = py_t[np.sort(idx)]
print(f'  Detected {len(px_t)} peaks:')
for i,(bx,by) in enumerate(zip(px_t,py_t),1):
    print(f'  Peak{i}: 2theta={bx:.2f}deg, I={by:.0f}')
