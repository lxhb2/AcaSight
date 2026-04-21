import sys, warnings, os
warnings.filterwarnings('ignore')
sys.path.insert(0, os.path.dirname(__file__))

import XRD_Analysis_combined as xrd

data_file = r'F:\xwechat_files\wxid_02k0z8c1gb8i22_115d\msg\file\2026-04\Y-2.txt'
output_dir = r'C:\Users\Administrator\.qclaw\workspace\xrd_analysis\results'
sample_name = 'Y-2'

report = xrd.analyze_xrd(
    data_path=data_file,
    output_dir=output_dir,
    sample_name=sample_name,
    journal='Minerals Engineering',
    dpi=600,
    smooth_window=9,
    smooth_poly=3,
    background_method='rolling',
    peak_height_ratio=0.025,
    peak_prominence=0.006,
    peak_tolerance=0.30,
    run_quantification=True,
    verbose=True,
)

print('\n=== TOP MATCHED PHASES ===')
for p in report['phases_identified'][:8]:
    print('  {} | n_peaks: {} | score: {:.4f}'.format(p['name'], p['n_matched_peaks'], p['score']))

print('\n=== QUANTIFICATION (wt%) ===')
for k, v in report['quantification'].items():
    print('  {}: {:.2f}%'.format(k, v))

print('\n=== TOP PEAKS DETECTED ===')
for pk in report['peaks'][:15]:
    print('  2theta={:.2f}  I={:.0f}  prom={:.3f}'.format(pk['two_theta'], pk['intensity'], pk['prominence']))

print('\n=== OUTPUT FILES ===')
for k, v in report['output_files'].items():
    print('  {}: {}'.format(k, v))
