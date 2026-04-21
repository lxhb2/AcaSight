#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sci-XRD Web服务配置
"""

import os
from pathlib import Path
from typing import Dict, Any

# 基础路径
BASE_DIR = Path(__file__).parent
PROJECT_ROOT = BASE_DIR.parent

# 数据库配置
DATABASE_CONFIG = {
    "path": str(PROJECT_ROOT / "pdf2_final_complete.db"),
    "read_only": False,
    "timeout": 30,
    "check_same_thread": False
}

# Web服务配置
WEB_CONFIG = {
    "host": os.getenv("HOST", "0.0.0.0"),
    "port": int(os.getenv("PORT", 8000)),
    "debug": os.getenv("DEBUG", "true").lower() == "true",
    "reload": os.getenv("RELOAD", "true").lower() == "true",
    "workers": int(os.getenv("WORKERS", 4)),
    "log_level": os.getenv("LOG_LEVEL", "info"),
    
    # CORS配置
    "cors": {
        "allow_origins": ["*"],  # 生产环境应限制
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    }
}

# 文件上传配置
UPLOAD_CONFIG = {
    "max_size": 100 * 1024 * 1024,  # 100MB
    "allowed_extensions": [".txt", ".csv", ".dat", ".xrd", ".xy", ".ras"],
    "temp_dir": "/tmp/sci_xrd_uploads",
    "keep_temp_files": False,
    "cleanup_interval": 3600  # 1小时清理一次
}

# 分析配置
ANALYSIS_CONFIG = {
    "default_params": {
        "smooth_window": 5,
        "background_lambda": 1000.0,
        "peak_height_threshold": 2.0,
        "peak_prominence": 1.0,
        "min_peak_distance": 0.3,
        "search_tolerance": 0.02,
        "min_matched_peaks": 3,
        "enable_ai": True
    },
    
    "presets": {
        "high_quality": {
            "smooth_window": 7,
            "background_lambda": 5000.0,
            "peak_height_threshold": 1.0,
            "peak_prominence": 0.8,
            "min_peak_distance": 0.2
        },
        "fast_analysis": {
            "smooth_window": 3,
            "background_lambda": 100.0,
            "peak_height_threshold": 3.0,
            "peak_prominence": 1.5,
            "min_peak_distance": 0.5
        },
        "noisy_data": {
            "smooth_window": 9,
            "background_lambda": 10000.0,
            "peak_height_threshold": 2.5,
            "peak_prominence": 2.0,
            "min_peak_distance": 0.4
        }
    }
}

# AI配置
AI_CONFIG = {
    "enabled": True,
    "model": "qwen3.5:0.8b",
    "timeout": 30,
    "max_retries": 3,
    "temperature": 0.3,
    "max_tokens": 1000,
    
    "cache": {
        "enabled": True,
        "max_size": 1000,
        "ttl_seconds": 3600
    }
}

# 图表配置
PLOT_CONFIG = {
    "style": "publication",
    "dpi": 300,
    "figure_size": [10, 6],
    "color_scheme": "black_white",
    "font_size": 10,
    
    "export_formats": ["png", "pdf", "svg"],
    "export_dpi": 600,
    
    "templates": {
        "publication": {
            "font_family": "Arial",
            "font_size": 10,
            "line_width": 1.2,
            "grid_alpha": 0.3
        },
        "presentation": {
            "font_family": "Arial",
            "font_size": 12,
            "line_width": 2.0,
            "grid_alpha": 0.5
        }
    }
}

# 批处理配置
BATCH_CONFIG = {
    "max_workers": 4,
    "max_files_per_batch": 100,
    "timeout_per_file": 300,  # 5分钟
    "result_retention_days": 7,
    
    "concurrency": {
        "max_concurrent_analyses": 4,
        "queue_size": 100,
        "worker_timeout": 30
    }
}

# 性能优化配置
PERFORMANCE_CONFIG = {
    "monitoring": {
        "enabled": True,
        "interval": 5,
        "log_file": "performance.log",
        "metrics_retention_hours": 24
    },
    
    "memory": {
        "gc_threshold": (700, 10, 10),
        "enable_auto_gc": True,
        "memory_limit_mb": 1024,
        "cache_size": 1000
    },
    
    "caching": {
        "enabled": True,
        "strategy": "lru",
        "max_size": 1000,
        "ttl_seconds": 3600
    }
}

# 安全配置
SECURITY_CONFIG = {
    "rate_limiting": {
        "enabled": False,  # 生产环境应启用
        "requests_per_minute": 60,
        "burst_limit": 10
    },
    
    "authentication": {
        "enabled": False,  # 生产环境应启用
        "jwt_secret": os.getenv("JWT_SECRET", "change_this_in_production"),
        "token_expiry_hours": 24
    },
    
    "input_validation": {
        "enabled": True,
        "max_string_length": 10000,
        "max_array_size": 1000
    }
}

# 日志配置
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        },
        "detailed": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(pathname)s:%(lineno)d - %(message)s"
        }
    },
    
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "level": "INFO"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "sci_xrd.log",
            "formatter": "detailed",
            "level": "DEBUG",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5
        }
    },
    
    "loggers": {
        "": {  # 根日志器
            "handlers": ["console", "file"],
            "level": "INFO"
        },
        "uvicorn": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False
        },
        "fastapi": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False
        }
    }
}

# 导出配置
EXPORT_CONFIG = {
    "formats": {
        "json": {
            "enabled": True,
            "indent": 2,
            "ensure_ascii": False
        },
        "csv": {
            "enabled": True,
            "delimiter": ",",
            "encoding": "utf-8"
        },
        "excel": {
            "enabled": True,
            "engine": "openpyxl"
        },
        "origin": {
            "enabled": True,
            "version": "2024",
            "template": "default.opj"
        },
        "word": {
            "enabled": True,
            "template": "report_template.docx"
        }
    },
    
    "templates": {
        "report": {
            "title": "XRD分析报告",
            "author": "Sci-XRD系统",
            "company": "智能材料分析实验室",
            "include_charts": True,
            "include_tables": True,
            "include_summary": True
        }
    }
}

# 将所有配置合并
CONFIG = {
    "database": DATABASE_CONFIG,
    "web": WEB_CONFIG,
    "upload": UPLOAD_CONFIG,
    "analysis": ANALYSIS_CONFIG,
    "ai": AI_CONFIG,
    "plot": PLOT_CONFIG,
    "batch": BATCH_CONFIG,
    "performance": PERFORMANCE_CONFIG,
    "security": SECURITY_CONFIG,
    "logging": LOGGING_CONFIG,
    "export": EXPORT_CONFIG,
    
    # 元数据
    "metadata": {
        "version": "2.0.0",
        "name": "Sci-XRD Web Interface",
        "description": "智能XRD分析平台",
        "author": "QClaw AI Assistant",
        "license": "MIT",
        "repository": "https://github.com/example/sci-xrd"
    }
}

def get_config() -> Dict[str, Any]:
    """获取配置"""
    return CONFIG

def update_config(updates: Dict[str, Any]):
    """更新配置"""
    global CONFIG
    
    def deep_update(target, source):
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                deep_update(target[key], value)
            else:
                target[key] = value
    
    deep_update(CONFIG, updates)

if __name__ == "__main__":
    # 打印配置摘要
    import json
    print("Sci-XRD 配置摘要:")
    print("=" * 60)
    
    for section, config in CONFIG.items():
        if section != "metadata":
            print(f"{section.upper()}:")
            if isinstance(config, dict):
                for key, value in config.items():
                    if isinstance(value, dict):
                        print(f"  {key}: {{...}}")
                    else:
                        print(f"  {key}: {value}")
            else:
                print(f"  {config}")
            print()
    
    print("=" * 60)
    print(f"版本: {CONFIG['metadata']['version']}")
    print(f"数据库: {CONFIG['database']['path']}")
    print(f"服务地址: {CONFIG['web']['host']}:{CONFIG['web']['port']}")
    print("=" * 60)