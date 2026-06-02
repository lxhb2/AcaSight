"""
AcaSight 配置管理
"""

from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用信息
    APP_NAME: str = "AcaSight"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, env="DEBUG")
    
    # 服务器
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    
    # 数据库
    DATABASE_URL: str = Field(
        default="sqlite:///./data/acasight.db",
        env="DATABASE_URL"
    )

    TEST_DATABASE_URL: str = Field(
        default="sqlite:///./data/test_acasight.db",
        env="TEST_DATABASE_URL"
    )
    
    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    
    # Qdrant
    QDRANT_HOST: str = Field(default="localhost", env="QDRANT_HOST")
    QDRANT_PORT: int = Field(default=6333, env="QDRANT_PORT")
    
    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000"],
        env="CORS_ORIGINS"
    )
    
    # AI 模型
    OPENAI_API_KEY: str = Field(default="", env="OPENAI_API_KEY")
    OPENAI_BASE_URL: str = Field(default="https://api.openai.com/v1", env="OPENAI_BASE_URL")
    
    DEEPSEEK_API_KEY: str = Field(default="", env="DEEPSEEK_API_KEY")
    DEEPSEEK_BASE_URL: str = Field(default="https://api.deepseek.com/v1", env="DEEPSEEK_BASE_URL")
    
    CLAUDE_API_KEY: str = Field(default="", env="CLAUDE_API_KEY")
    
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434", env="OLLAMA_BASE_URL")
    
    # 默认模型
    DEFAULT_AI_PROVIDER: str = Field(default="openai", env="DEFAULT_AI_PROVIDER")
    DEFAULT_AI_MODEL: str = Field(default="gpt-4", env="DEFAULT_AI_MODEL")
    
    # 搜索
    SEMANTIC_SCHOLAR_API_KEY: str = Field(default="", env="SEMANTIC_SCHOLAR_API_KEY")
    CORE_API_KEY: str = Field(default="kSbRLqWtrlBE4uaNsQMjpAO2gD8nz569", env="CORE_API_KEY")
    
    # 文件存储
    UPLOAD_DIR: str = Field(default="./data/uploads", env="UPLOAD_DIR")
    MAX_FILE_SIZE: int = Field(default=100 * 1024 * 1024, env="MAX_FILE_SIZE")  # 100MB
    
    # Zotero
    ZOTERO_DB_PATH: str = Field(default="", env="ZOTERO_DB_PATH")
    
    # JWT
    JWT_SECRET: str = Field(default="your-secret-key", env="JWT_SECRET")
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    JWT_EXPIRE_DAYS: int = Field(default=7, env="JWT_EXPIRE_DAYS")
    
    # 日志
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# 全局配置实例
settings = Settings()
