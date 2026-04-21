import warnings
warnings.filterwarnings('error')

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

CHINESE_FONTS = ["SimHei", "Microsoft YaHei", "SimSun", "Arial"]
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = CHINESE_FONTS
plt.rcParams['axes.unicode_minus'] = False

# Test annotate with Chinese + subscript 2
fig, ax = plt.subplots(figsize=(6, 4))
ax.set_xlim(0, 10)
ax.set_ylim(0, 10)

# Test 1: Chinese text
ax.annotate("石英 SiO2", xy=(5, 5), fontsize=14)

# Test 2: Check what happens with a plain annotate
ax.annotate("Test 2 - subscript in arrow", xy=(5, 8), xytext=(2, 8),
            arrowprops=dict(arrowstyle='->', color='black'),
            fontsize=10)

plt.tight_layout()
plt.savefig('F:/桌面/王铨毕业论文/xrd数据/_test_font.png', dpi=100)
plt.close()
print("Test complete")
