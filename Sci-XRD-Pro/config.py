"""
Sci-XRD Pro 配置文件

包含：
1. 应用程序配置
2. 默认参数
3. 路径配置
4. 数据库配置
5. AI配置
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import json


class Config:
    """配置管理器"""
    
    # 默认配置
    DEFAULT_CONFIG = {
        # 应用程序
        'app': {
            'name': 'Sci-XRD Pro',
            'version': '1.0.0',
            'author': 'QClaw AI',
            'description': '专业XRD分析平台',
            'debug': False,
            'log_level': 'INFO'
        },
        
        # 路径配置
        'paths': {
            'data_dir': 'data',
            'export_dir': 'exports',
            'log_dir': 'logs',
            'temp_dir': 'temp',
            'config_dir': 'config',
            'database_dir': 'database'
        },
        
        # 图表配置
        'chart': {
            'figure_size': [10, 6],
            'dpi': 100,
            'line_width': 1.5,
            'marker_size': 5,
            'font_size': 12,
            'title_font_size': 14,
            'grid_alpha': 0.3,
            'colors': {
                'original': '#000000',      # 黑色
                'analysis': '#1f77b4',      # 蓝色
                'peak_marker': '#d62728',   # 红色
                'peak_label': '#2ca02c',    # 绿色
                'background': '#f0f0f0'     # 浅灰色
            }
        },
        
        # 峰检测配置
        'peak_detection': {
            'default_method': 'wavelet',
            'min_snr': 2.0,
            'min_prominence': 0.01,
            'min_width': 0.1,
            'max_width': 5.0,
            'wavelet_scales': [0.5, 1.0, 2.0, 3.0, 5.0, 8.0, 12.0],
            'savgol_window': 11,
            'savgol_polyorder': 3
        },
        
        # 物相匹配配置
        'phase_matching': {
            'database_path': 'database/pdf2.db',
            'match_tolerance': 0.02,
            'min_matched_peaks': 3,
            'intensity_weight': 0.3,
            'position_weight': 0.7,
            'min_confidence': 0.4,
            'good_confidence': 0.7,
            'excellent_confidence': 0.9,
            'max_phases': 5
        },
        
        # 算法配置
        'algorithms': {
            'background_method': 'tophat',
            'tophat_window': 101,
            'snip_iterations': 100,
            'kalpha2_intensity_ratio': 0.5,
            'kalpha1_wavelength': 1.54056,
            'kalpha2_wavelength': 1.54439,
            'scherrer_shape_factor': 0.94,
            'default_wavelength': 1.5406
        },
        
        # 导出配置
        'export': {
            'default_preset': 'origin_standard',
            'default_separator': '\t',
            'default_precision': 6,
            'include_header': True,
            'include_metadata': True,
            'create_origin_script': True,
            'auto_open_export': False
        },
        
        # AI配置
        'ai': {
            'enabled': True,
            'model': 'qwen3.5:0.8b',
            'base_url': 'http://localhost:11434',
            'timeout': 30,
            'temperature': 0.7,
            'max_tokens': 2000,
            'use_cache': True,
            'cache_ttl': 3600
        },
        
        # 界面配置
        'ui': {
            'language': 'zh_CN',
            'theme': 'light',
            'font_family': 'Microsoft YaHei',
            'font_size': 10,
            'toolbar_visible': True,
            'statusbar_visible': True,
            'dock_windows': True,
            'auto_save_layout': True,
            'recent_files_limit': 10
        },
        
        # 性能配置
        'performance': {
            'max_data_points': 100000,
            'cache_enabled': True,
            'cache_size': 100,
            'parallel_processing': True,
            'max_workers': 4,
            'memory_limit_mb': 1024
        }
    }
    
    def __init__(self, config_file: Optional[str] = None):
        """
        初始化配置
        
        Args:
            config_file: 配置文件路径（可选）
        """
        self.config_file = config_file
        self.config = self.DEFAULT_CONFIG.copy()
        
        # 加载用户配置
        if config_file and Path(config_file).exists():
            self.load_config(config_file)
        
        # 确保目录存在
        self._ensure_directories()
    
    def load_config(self, config_file: str):
        """加载配置文件"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
            
            # 深度合并配置
            self._deep_merge(self.config, user_config)
            
        except Exception as e:
            print(f"加载配置文件失败: {e}")
    
    def save_config(self, config_file: Optional[str] = None):
        """保存配置文件"""
        if config_file is None:
            config_file = self.config_file
        
        if config_file:
            try:
                # 确保目录存在
                Path(config_file).parent.mkdir(parents=True, exist_ok=True)
                
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(self.config, f, ensure_ascii=False, indent=2)
                    
            except Exception as e:
                print(f"保存配置文件失败: {e}")
    
    def _deep_merge(self, base: Dict, update: Dict):
        """深度合并字典"""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def _ensure_directories(self):
        """确保所有配置的目录存在"""
        paths = self.config['paths']
        
        for key, path in paths.items():
            if isinstance(path, str):
                full_path = Path(path)
                if not full_path.is_absolute():
                    # 相对于应用程序目录
                    full_path = Path.cwd() / path
                
                full_path.mkdir(parents=True, exist_ok=True)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键（支持点分隔符，如 'app.name'）
            default: 默认值
            
        Returns:
            配置值
        """
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any):
        """
        设置配置值
        
        Args:
            key: 配置键（支持点分隔符）
            value: 配置值
        """
        keys = key.split('.')
        config = self.config
        
        # 导航到最后一个字典
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # 设置值
        config[keys[-1]] = value
    
    def update(self, updates: Dict[str, Any]):
        """
        批量更新配置
        
        Args:
            updates: 更新字典
        """
        for key, value in updates.items():
            self.set(key, value)
    
    def get_path(self, path_key: str, absolute: bool = True) -> Path:
        """
        获取路径
        
        Args:
            path_key: 路径键（如 'data_dir'）
            absolute: 是否返回绝对路径
            
        Returns:
            路径对象
        """
        relative_path = self.get(f'paths.{path_key}')
        if not relative_path:
            raise KeyError(f"路径键不存在: {path_key}")
        
        path = Path(relative_path)
        
        if absolute and not path.is_absolute():
            path = Path.cwd() / path
        
        return path
    
    def get_chart_color(self, color_key: str) -> str:
        """
        获取图表颜色
        
        Args:
            color_key: 颜色键
            
        Returns:
            颜色代码
        """
        return self.get(f'chart.colors.{color_key}', '#000000')
    
    def get_export_preset(self, preset_name: str) -> Dict:
        """
        获取导出预设
        
        Args:
            preset_name: 预设名称
            
        Returns:
            导出预设配置
        """
        # 这里可以扩展为从文件加载预设
        presets = {
            'origin_standard': {
                'name': 'Origin标准格式',
                'data_format': 'ascii_xy',
                'separator': '\t',
                'header': True,
                'precision': 6,
                'include_metadata': True,
                'include_peaks': False,
                'include_phases': False
            },
            'origin_advanced': {
                'name': 'Origin高级格式',
                'data_format': 'multi_file',
                'separator': '\t',
                'header': True,
                'precision': 8,
                'include_metadata': True,
                'include_peaks': True,
                'include_phases': True,
                'create_script': True
            },
            'excel_friendly': {
                'name': 'Excel友好格式',
                'data_format': 'csv',
                'separator': ',',
                'header': True,
                'precision': 4,
                'include_metadata': False,
                'include_peaks': True,
                'include_phases': True
            }
        }
        
        return presets.get(preset_name, presets['origin_standard'])
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return self.config.copy()
    
    def __getitem__(self, key: str) -> Any:
        """支持字典式访问"""
        return self.get(key)
    
    def __setitem__(self, key: str, value: Any):
        """支持字典式设置"""
        self.set(key, value)
    
    def __contains__(self, key: str) -> bool:
        """检查键是否存在"""
        try:
            self.get(key)
            return True
        except KeyError:
            return False


# 全局配置实例
_config_instance: Optional[Config] = None


def get_config(config_file: Optional[str] = None) -> Config:
    """
    获取全局配置实例
    
    Args:
        config_file: 配置文件路径
        
    Returns:
        配置实例
    """
    global _config_instance
    
    if _config_instance is None:
        _config_instance = Config(config_file)
    
    return _config_instance


def save_config():
    """保存全局配置"""
    global _config_instance
    
    if _config_instance:
        _config_instance.save_config()


# 测试函数
def test_config():
    """测试配置管理器"""
    config = Config()
    
    # 测试获取配置
    print("应用程序名称:", config.get('app.name'))
    print("图表DPI:", config.get('chart.dpi'))
    print("峰检测方法:", config.get('peak_detection.default_method'))
    
    # 测试设置配置
    config.set('app.debug', True)
    print("调试模式:", config.get('app.debug'))
    
    # 测试路径获取
    data_path = config.get_path('data_dir')
    print("数据目录:", data_path)
    
    # 测试颜色获取
    color = config.get_chart_color('original')
    print("原始数据颜色:", color)
    
    # 测试导出预设
    preset = config.get_export_preset('origin_standard')
    print("Origin标准预设:", preset['name'])
    
    return config


if __name__ == '__main__':
    test_config()