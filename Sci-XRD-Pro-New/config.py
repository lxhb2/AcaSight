"""
Sci-XRD Pro - 全局配置
"""

import os
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent

# 数据目录
DATA_DIR = PROJECT_ROOT / "resources" / "samples"
LOGS_DIR = PROJECT_ROOT / "logs"
EXPORT_DIR = PROJECT_ROOT / "exports"

# 确保目录存在
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

# X射线波长
WAVELENGTH_CU_KALPHA = 1.5406  # Cu K-alpha (Å)
WAVELENGTH_CO_KALPHA = 1.7890  # Co K-alpha (Å)
WAVELENGTH_MO_KALPHA = 0.7107  # Mo K-alpha (Å)

DEFAULT_WAVELENGTH = WAVELENGTH_CU_KALPHA

# 峰检测参数
PEAK_DETECTION = {
    'method': 'auto',           # 'auto', 'derivative', 'threshold', 'wavelet'
    'sensitivity': 0.1,          # 灵敏度 0-1
    'min_prominence': 0.02,     # 最小突出度
    'min_distance': 0.5,         # 最小峰间距 (°)
    'max_peaks': 20,            # 最大峰数
}

# 物相匹配参数
PHASE_MATCHING = {
    'method': 'fom',             # 'fom' 或 'hanawalt'
    'top_n': 10,                # 返回前N个结果
    'score_threshold': 30,       # 最低分数阈值
}

# AI参数
AI = {
    'enabled': True,
    'provider': 'ollama',
    'base_url': 'http://localhost:11434',
    'model': 'llama3.2:latest',
    'timeout': 60,
}

# 图表参数
CHART = {
    'figure_size': (12, 6),
    'dpi': 100,
    'style': 'seaborn-v0_8-darkgrid',
    'colors': {
        'raw_data': '#1f77b4',       # 蓝色
        'analyzed': '#ff7f0e',        # 橙色
        'baseline': '#2ca02c',        # 绿色
        'peaks': '#d62728',           # 红色
        'matched': '#9467bd',         # 紫色
    }
}

# UI参数
UI = {
    'window_size': (1400, 800),
    'theme': 'dark',              # 'dark' 或 'light'
    'font_size': 10,
    'language': 'zh_CN',         # 'zh_CN' 或 'en_US'
}

# 日志配置
LOGGING = {
    'level': 'INFO',              # DEBUG, INFO, WARNING, ERROR
    'file': LOGS_DIR / 'sci_xrd.log',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'max_bytes': 10 * 1024 * 1024,  # 10MB
    'backup_count': 3,
}


class Config:
    """配置管理类"""
    
    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.data_dir = DATA_DIR
        self.logs_dir = LOGS_DIR
        self.export_dir = EXPORT_DIR
        self.wavelength = DEFAULT_WAVELENGTH
        self.peak_detection = PEAK_DETECTION.copy()
        self.phase_matching = PHASE_MATCHING.copy()
        self.ai = AI.copy()
        self.chart = CHART.copy()
        self.ui = UI.copy()
        self.logging = LOGGING.copy()
    
    def update(self, **kwargs):
        """更新配置"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            elif key in self.peak_detection:
                self.peak_detection[key] = value
            elif key in self.phase_matching:
                self.phase_matching[key] = value
            elif key in self.ai:
                self.ai[key] = value
            elif key in self.chart:
                self.chart[key] = value
            elif key in self.ui:
                self.ui[key] = value
    
    def save(self, filepath: str = None):
        """保存配置到文件"""
        import json
        
        if filepath is None:
            filepath = self.project_root / "config.json"
        
        config_data = {
            'wavelength': self.wavelength,
            'peak_detection': self.peak_detection,
            'phase_matching': self.phase_matching,
            'ai': self.ai,
            'chart': self.chart,
            'ui': self.ui,
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
    
    def load(self, filepath: str = None):
        """从文件加载配置"""
        import json
        
        if filepath is None:
            filepath = self.project_root / "config.json"
        
        filepath = Path(filepath)
        if not filepath.exists():
            return
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            self.update(**config_data)
        except Exception as e:
            print(f"加载配置失败: {e}")


# 全局配置实例
config = Config()
