"""
API 密钥加密增强 (方向V.1)

功能:
1. 密钥加密存储 (AES-256-GCM)
2. 密钥轮换 (rotate_master_key)
3. 环境变量隔离 (敏感变量不落盘)
4. 密钥掩码显示 (mask_api_key)
5. 安全审计日志
"""

import base64
import hashlib
import json
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import structlog
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

logger = structlog.get_logger()

# ── 常量 ──

NONCE_SIZE = 12  # AES-GCM nonce
KEY_SIZE = 32    # AES-256
SALT_SIZE = 16
KDF_ITERATIONS = 600_000  # OWASP 推荐 PBKDF2 迭代次数

# 需要加密的密钥环境变量
SENSITIVE_ENV_VARS = [
    "OPENAI_API_KEY",
    "DEEPSEEK_API_KEY",
    "CLAUDE_API_KEY",
    "SEMANTIC_SCHOLAR_API_KEY",
    "CORE_API_KEY",
    "NCBI_API_KEY",
    "TAVILY_API_KEY",
    "SAM3_API_KEY",
    "ROBOFLOW_API_KEY",
]


class KeyManager:
    """
    API 密钥管理器
    
    功能:
    - AES-256-GCM 加密存储
    - PBKDF2 密钥派生
    - 密钥轮换
    - 掩码显示
    - 安全审计
    """
    
    def __init__(self, master_key: Optional[str] = None):
        self._master_key = master_key or os.environ.get("ACASIGHT_MASTER_KEY", "")
        if not self._master_key:
            # 自动生成并持久化 master key
            self._master_key = self._auto_generate_master_key()
        self._audit_log: List[Dict] = []
        self._key_cache: Dict[str, str] = {}  # 解密后的密钥缓存

    @staticmethod
    def _auto_generate_master_key() -> str:
        """自动生成 master key 并保存到文件，避免每次重启都重新生成"""
        key_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', '.master_key')
        try:
            if os.path.exists(key_file):
                with open(key_file, 'r') as f:
                    key = f.read().strip()
                if key:
                    return key
        except Exception:
            pass
        # 生成新的 master key
        import secrets
        key = secrets.token_urlsafe(32)
        try:
            os.makedirs(os.path.dirname(key_file), exist_ok=True)
            with open(key_file, 'w') as f:
                f.write(key)
        except Exception:
            pass
        return key
    
    @staticmethod
    def mask_api_key(key: str) -> str:
        """
        掩码显示 API 密钥
        
        示例: sk-abc123xyz789 → sk-ab...789
        """
        if not key or len(key) < 8:
            return "***"
        return f"{key[:4]}...{key[-4:]}"
    
    def _derive_key(self, salt: bytes) -> bytes:
        """PBKDF2 密钥派生"""
        if not self._master_key:
            raise ValueError("Master key not configured. Set ACASIGHT_MASTER_KEY env var.")
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=KEY_SIZE,
            salt=salt,
            iterations=KDF_ITERATIONS,
        )
        return kdf.derive(self._master_key.encode("utf-8"))
    
    def encrypt(self, plaintext: str) -> str:
        """
        加密密钥
        
        Returns:
            base64(salt + nonce + ciphertext)
        """
        salt = os.urandom(SALT_SIZE)
        nonce = os.urandom(NONCE_SIZE)
        derived_key = self._derive_key(salt)
        
        aesgcm = AESGCM(derived_key)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        
        # 组合: salt + nonce + ciphertext
        encrypted = salt + nonce + ciphertext
        return base64.b64encode(encrypted).decode("ascii")
    
    def decrypt(self, encrypted_b64: str) -> str:
        """
        解密密钥
        
        Args:
            encrypted_b64: base64(salt + nonce + ciphertext)
        """
        encrypted = base64.b64decode(encrypted_b64)
        
        salt = encrypted[:SALT_SIZE]
        nonce = encrypted[SALT_SIZE:SALT_SIZE + NONCE_SIZE]
        ciphertext = encrypted[SALT_SIZE + NONCE_SIZE:]
        
        derived_key = self._derive_key(salt)
        aesgcm = AESGCM(derived_key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        
        return plaintext.decode("utf-8")
    
    def rotate_master_key(self, old_key: str, new_key: str, encrypted_keys: Dict[str, str]) -> Dict[str, str]:
        """
        轮换主密钥
        
        Args:
            old_key: 旧主密钥
            new_key: 新主密钥
            encrypted_keys: {var_name: encrypted_value}
        
        Returns:
            {var_name: re_encrypted_value} 用新密钥重新加密
        """
        self._audit("rotate_start", details="Master key rotation initiated")
        
        # 临时使用旧密钥解密
        old_manager = KeyManager(master_key=old_key)
        
        re_encrypted = {}
        for var_name, enc_value in encrypted_keys.items():
            try:
                plaintext = old_manager.decrypt(enc_value)
                # 用新密钥重新加密
                self._master_key = new_key
                re_encrypted[var_name] = self.encrypt(plaintext)
                self._audit("rotate_rekey", var_name=var_name)
            except Exception as e:
                self._audit("rotate_failed", var_name=var_name, error=str(e))
                logger.error("Key rotation failed", var_name=var_name, error=str(e))
        
        self._audit("rotate_complete", details=f"{len(re_encrypted)} keys rotated")
        return re_encrypted
    
    def get_sensitive_env_vars(self) -> Dict[str, str]:
        """获取所有敏感环境变量 (掩码显示)"""
        result = {}
        for var in SENSITIVE_ENV_VARS:
            value = os.environ.get(var, "")
            if value:
                result[var] = self.mask_api_key(value)
        return result
    
    def encrypt_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """加密配置中的敏感字段"""
        encrypted_config = {}
        for key, value in config.items():
            if any(s in key.lower() for s in ["api_key", "secret", "password", "token"]):
                if isinstance(value, str) and value:
                    encrypted_config[key] = self.encrypt(value)
                    self._audit("encrypt", var_name=key)
                else:
                    encrypted_config[key] = value
            else:
                encrypted_config[key] = value
        return encrypted_config
    
    def decrypt_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """解密配置中的敏感字段"""
        decrypted_config = {}
        for key, value in config.items():
            if any(s in key.lower() for s in ["api_key", "secret", "password", "token"]):
                if isinstance(value, str) and value and not value.startswith("sk-"):
                    try:
                        decrypted_config[key] = self.decrypt(value)
                    except Exception:
                        # 可能是未加密的明文值
                        decrypted_config[key] = value
                else:
                    decrypted_config[key] = value
            else:
                decrypted_config[key] = value
        return decrypted_config
    
    def _audit(self, action: str, **kwargs):
        """安全审计日志"""
        entry = {
            "timestamp": time.time(),
            "action": action,
            **kwargs,
        }
        self._audit_log.append(entry)
        logger.info("KeyManager audit", **entry)
    
    def get_audit_log(self) -> List[Dict]:
        """获取审计日志"""
        return self._audit_log.copy()


# Singleton
_key_manager: Optional[KeyManager] = None


def get_key_manager() -> KeyManager:
    """获取全局密钥管理器"""
    global _key_manager
    if _key_manager is None:
        _key_manager = KeyManager()
    return _key_manager


# ── 向后兼容函数 (旧代码使用) ──

def encrypt_key(plaintext: str) -> str:
    """向后兼容: 加密密钥"""
    return get_key_manager().encrypt(plaintext)


def decrypt_key(encrypted: str) -> str:
    """向后兼容: 解密密钥
    优先尝试新 AES-GCM 解密，失败时返回原文 (可能是明文或旧格式)
    """
    try:
        return get_key_manager().decrypt(encrypted)
    except Exception:
        # 解密失败 — 可能是明文值或旧加密格式
        # 如果看起来像明文 API key 直接返回
        if encrypted and len(encrypted) > 10 and not encrypted.startswith("eyJ"):
            return encrypted
        # 否则返回空字符串
        return encrypted if encrypted else ""


def mask_key(key: str) -> str:
    """向后兼容: 掩码密钥"""
    return KeyManager.mask_api_key(key)
