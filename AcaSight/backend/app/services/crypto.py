"""
AcaSight 加密工具
- AES-256-GCM 加密 API Key 存储
- PBKDF2 密钥派生
"""

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# ─── 密钥派生 ───

SALT = b'Ac@Sight_2025_salt_v1'

def _get_key() -> bytes:
    """从环境变量 ACASIGHT_AES_KEY 或 JWT_SECRET 派生 256-bit AES 密钥"""
    raw = (os.environ.get('ACASIGHT_AES_KEY', '') or 'acasight-default-key').encode()
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=SALT, iterations=100_000)
    return kdf.derive(raw)


def encrypt_key(plain: str) -> str:
    """AES-256-GCM 加密 → url-safe base64 字符串"""
    if not plain:
        return ''
    key = _get_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    cipher = aesgcm.encrypt(nonce, plain.encode(), None)
    return base64.urlsafe_b64encode(nonce + cipher).decode()


def decrypt_key(encrypted: str) -> str:
    """AES-256-GCM 解密 → 明文"""
    if not encrypted:
        return ''
    try:
        key = _get_key()
        raw = base64.urlsafe_b64decode(encrypted)
        nonce, cipher = raw[:12], raw[12:]
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, cipher, None).decode()
    except Exception:
        return ''


def mask_key(key: str) -> str:
    """脱敏显示：sk-a***c123"""
    if not key:
        return ''
    if len(key) <= 8:
        return key[:1] + '****' + key[-1:]
    return key[:4] + '****' + key[-4:]