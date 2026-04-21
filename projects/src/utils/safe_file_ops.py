"""
安全文件操作模块 — 脉冲学习系统

借鉴 OpenClaw (fs-safe.ts, path-guards.ts) 和 HermesAgent (file_operations.py, file_tools.py)
的安全机制，为脉冲学习系统提供安全的文件读写能力。

核心安全机制：
1. 路径边界检查 — 防止逃逸 workspace
2. 敏感路径黑名单 — 阻止读写 ~/.ssh、/etc/passwd 等
3. 设备路径黑名单 — 阻止读取 /dev/zero 等无限输出设备
4. 符号链接检测 — 防止 symlink 攻击
5. 写入大小限制 — 防止意外写入超大文件
"""

import os
import stat
import errno
import json
from pathlib import Path
from typing import Optional, Tuple, Union, Any
from dataclasses import dataclass


# =============================================================================
# 安全配置
# =============================================================================

# 默认最大读取字符数 (100K chars ≈ 25-35K tokens)
DEFAULT_MAX_READ_CHARS = 100_000

# 默认最大写入字节数 (10 MB)
DEFAULT_MAX_WRITE_BYTES = 10 * 1024 * 1024

# 大文件提示阈值 (512 KB)
LARGE_FILE_HINT_BYTES = 512_000


# =============================================================================
# 黑名单
# =============================================================================

_HOME = str(Path.home())

# 禁止写入的敏感路径 (精确匹配)
WRITE_DENIED_PATHS = {
    os.path.realpath(p) for p in [
        os.path.join(_HOME, ".ssh", "authorized_keys"),
        os.path.join(_HOME, ".ssh", "id_rsa"),
        os.path.join(_HOME, ".ssh", "id_ed25519"),
        os.path.join(_HOME, ".ssh", "config"),
        os.path.join(_HOME, ".bashrc"),
        os.path.join(_HOME, ".zshrc"),
        os.path.join(_HOME, ".profile"),
        os.path.join(_HOME, ".bash_profile"),
        os.path.join(_HOME, ".netrc"),
        os.path.join(_HOME, ".pgpass"),
        os.path.join(_HOME, ".npmrc"),
        os.path.join(_HOME, ".pypirc"),
        "/etc/sudoers",
        "/etc/passwd",
        "/etc/shadow",
    ] if os.path.exists(os.path.dirname(p))
}

# 禁止写入的敏感路径前缀
WRITE_DENIED_PREFIXES = [
    os.path.realpath(p) + os.sep for p in [
        os.path.join(_HOME, ".ssh"),
        os.path.join(_HOME, ".aws"),
        os.path.join(_HOME, ".gnupg"),
        os.path.join(_HOME, ".kube"),
        "/etc/sudoers.d",
        "/etc/systemd",
        os.path.join(_HOME, ".docker"),
        os.path.join(_HOME, ".azure"),
        os.path.join(_HOME, ".config", "gh"),
    ] if os.path.exists(p)
]

# 禁止读取的设备路径 (无限输出或阻塞)
BLOCKED_DEVICE_PATHS = frozenset({
    "/dev/zero", "/dev/random", "/dev/urandom", "/dev/full",
    "/dev/stdin", "/dev/tty", "/dev/console",
    "/dev/stdout", "/dev/stderr",
    "/dev/fd/0", "/dev/fd/1", "/dev/fd/2",
})

# 禁止读写的敏感路径前缀
SENSITIVE_PATH_PREFIXES = (
    "/etc/", "/boot/", "/usr/lib/systemd/",
    "/private/etc/", "/private/var/",
)


# =============================================================================
# 结果数据类
# =============================================================================

@dataclass
class ReadResult:
    """读取结果"""
    success: bool
    content: str = ""
    error: str = ""
    path: str = ""
    size: int = 0
    is_symlink: bool = False
    symlink_target: str = ""


@dataclass
class WriteResult:
    """写入结果"""
    success: bool
    error: str = ""
    path: str = ""
    bytes_written: int = 0


# =============================================================================
# 安全检查函数
# =============================================================================

def _resolve_path(filepath: str) -> str:
    """解析路径 (展开 ~ 和环境变量)

    Windows 短路径名和长路径名不一致，统一使用 normpath + abspath
    """
    expanded = os.path.expanduser(os.path.expandvars(filepath))
    return os.path.normpath(os.path.abspath(expanded))


def _is_path_inside(target_path: str, base_dir: str) -> bool:
    """检查 target_path 是否在 base_dir 内

    Args:
        target_path: 要检查的目标路径
        base_dir: 基准目录
    """
    try:
        # Windows 短路径名和长路径名不一致，统一使用 normpath + abspath
        base = os.path.normpath(os.path.abspath(base_dir))
        target = os.path.normpath(os.path.abspath(target_path))
        return target == base or target.startswith(base + os.sep)
    except Exception:
        return False


def _is_blocked_device(filepath: str) -> bool:
    """检查是否为阻塞设备路径"""
    normalized = os.path.expanduser(filepath)
    if normalized in BLOCKED_DEVICE_PATHS:
        return True
    # /proc/self/fd/0-2 和 /proc/<pid>/fd/0-2 是 Linux stdio 别名
    if normalized.startswith("/proc/") and normalized.endswith(("/fd/0", "/fd/1", "/fd/2")):
        return True
    return False


def _is_write_denied(filepath: str) -> Tuple[bool, str]:
    """检查路径是否在写入黑名单中"""
    try:
        resolved = _resolve_path(filepath)
    except Exception:
        resolved = filepath

    # 1. 精确匹配
    if resolved in WRITE_DENIED_PATHS:
        return True, f"写入被拒绝: 敏感文件 {filepath}"

    # 2. 前缀匹配
    for prefix in WRITE_DENIED_PREFIXES:
        if resolved.startswith(prefix):
            return True, f"写入被拒绝: 敏感目录 {filepath}"

    # 3. 系统路径前缀
    for prefix in SENSITIVE_PATH_PREFIXES:
        if resolved.startswith(prefix):
            return True, f"写入被拒绝: 系统路径 {filepath}"

    return False, ""


def _is_sensitive_path(filepath: str) -> Tuple[bool, str]:
    """检查是否为敏感路径"""
    try:
        resolved = _resolve_path(filepath)
    except Exception:
        resolved = filepath

    normalized = os.path.normpath(os.path.expanduser(filepath))

    for prefix in SENSITIVE_PATH_PREFIXES:
        if resolved.startswith(prefix) or normalized.startswith(prefix):
            return True, f"访问被拒绝: 敏感系统路径 {filepath}"

    return False, ""


def _check_symlink(filepath: str) -> Tuple[bool, str]:
    """检查是否为符号链接"""
    try:
        if os.path.islink(filepath):
            target = os.readlink(filepath)
            return True, target
    except Exception:
        pass
    return False, ""


# =============================================================================
# 主 API
# =============================================================================

def safe_read_file(
    filepath: str,
    workspace_root: str,
    max_chars: int = DEFAULT_MAX_READ_CHARS,
    offset: int = 0,
    limit: int = 0,
) -> ReadResult:
    """
    安全读取文件

    Args:
        filepath: 文件路径
        workspace_root: workspace 根目录 (路径边界)
        max_chars: 最大读取字符数
        offset: 起始行号 (1-indexed)
        limit: 最大行数 (0 = 无限制)

    Returns:
        ReadResult
    """
    # 1. 设备路径检查
    if _is_blocked_device(filepath):
        return ReadResult(
            success=False,
            error=f"读取被拒绝: 设备路径 {filepath} (无限输出或阻塞)",
            path=filepath,
        )

    # 2. 敏感路径检查
    is_sensitive, sensitive_msg = _is_sensitive_path(filepath)
    if is_sensitive:
        return ReadResult(
            success=False,
            error=sensitive_msg,
            path=filepath,
        )

    # 3. 路径边界检查
    try:
        resolved = _resolve_path(filepath)
        if not _is_path_inside(resolved, workspace_root):
            return ReadResult(
                success=False,
                error=f"读取被拒绝: 路径逃逸 workspace ({filepath})",
                path=filepath,
            )
    except Exception as e:
        return ReadResult(
            success=False,
            error=f"路径解析失败: {e}",
            path=filepath,
        )

    # 4. 符号链接检测
    is_symlink, symlink_target = _check_symlink(filepath)

    # 5. 读取文件
    try:
        file_stat = os.stat(filepath)
        file_size = file_stat.st_size

        # 大文件提示
        hint = ""
        if file_size > LARGE_FILE_HINT_BYTES and limit <= 200:
            hint = f"\n[提示: 文件较大 ({file_size // 1024}KB)，建议使用 offset/limit 分段读取]"

        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            if offset > 0 or limit > 0:
                # 分段读取
                lines = f.readlines()
                start = max(0, offset - 1) if offset > 0 else 0
                end = start + limit if limit > 0 else len(lines)
                content = ''.join(lines[start:end])
            else:
                content = f.read()

        # 截断超长内容
        if len(content) > max_chars:
            content = content[:max_chars] + f"\n... [截断: 文件超过 {max_chars} 字符]"

        return ReadResult(
            success=True,
            content=content + hint,
            path=filepath,
            size=len(content),
            is_symlink=is_symlink,
            symlink_target=symlink_target,
        )

    except FileNotFoundError:
        return ReadResult(
            success=False,
            error=f"文件不存在: {filepath}",
            path=filepath,
        )
    except PermissionError:
        return ReadResult(
            success=False,
            error=f"权限不足: {filepath}",
            path=filepath,
        )
    except Exception as e:
        return ReadResult(
            success=False,
            error=f"读取失败: {e}",
            path=filepath,
        )


def safe_write_file(
    filepath: str,
    content: Union[str, bytes],
    workspace_root: str,
    max_bytes: int = DEFAULT_MAX_WRITE_BYTES,
    mkdir: bool = True,
) -> WriteResult:
    """
    安全写入文件

    Args:
        filepath: 文件路径
        content: 写入内容 (str 或 bytes)
        workspace_root: workspace 根目录 (路径边界)
        max_bytes: 最大写入字节数
        mkdir: 是否自动创建父目录

    Returns:
        WriteResult
    """
    # 1. 写入黑名单检查
    is_denied, deny_msg = _is_write_denied(filepath)
    if is_denied:
        return WriteResult(
            success=False,
            error=deny_msg,
            path=filepath,
        )

    # 2. 敏感路径检查
    is_sensitive, sensitive_msg = _is_sensitive_path(filepath)
    if is_sensitive:
        return WriteResult(
            success=False,
            error=sensitive_msg,
            path=filepath,
        )

    # 3. 路径边界检查
    try:
        resolved = _resolve_path(filepath)
        if not _is_path_inside(resolved, workspace_root):
            return WriteResult(
                success=False,
                error=f"写入被拒绝: 路径逃逸 workspace ({filepath})",
                path=filepath,
            )
    except Exception as e:
        return WriteResult(
            success=False,
            error=f"路径解析失败: {e}",
            path=filepath,
        )

    # 4. 写入大小检查
    content_bytes = content.encode('utf-8') if isinstance(content, str) else content
    if len(content_bytes) > max_bytes:
        return WriteResult(
            success=False,
            error=f"写入被拒绝: 内容超过 {max_bytes} 字节",
            path=filepath,
        )

    # 5. 写入文件
    try:
        if mkdir:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, 'wb') as f:
            f.write(content_bytes)

        return WriteResult(
            success=True,
            path=filepath,
            bytes_written=len(content_bytes),
        )

    except PermissionError:
        return WriteResult(
            success=False,
            error=f"权限不足: {filepath}",
            path=filepath,
        )
    except Exception as e:
        return WriteResult(
            success=False,
            error=f"写入失败: {e}",
            path=filepath,
        )


def safe_delete_file(
    filepath: str,
    workspace_root: str,
) -> Tuple[bool, str]:
    """
    安全删除文件

    Args:
        filepath: 文件路径
        workspace_root: workspace 根目录

    Returns:
        (success, error_message)
    """
    # 1. 写入黑名单检查 (删除也需要写入权限)
    is_denied, deny_msg = _is_write_denied(filepath)
    if is_denied:
        return False, deny_msg

    # 2. 路径边界检查
    try:
        resolved = _resolve_path(filepath)
        if not _is_path_inside(resolved, workspace_root):
            return False, f"删除被拒绝: 路径逃逸 workspace ({filepath})"
    except Exception as e:
        return False, f"路径解析失败: {e}"

    # 3. 删除文件
    try:
        if os.path.isfile(filepath):
            os.remove(filepath)
            return True, ""
        elif os.path.isdir(filepath):
            # 目录需要显式确认，防止意外删除
            return False, f"拒绝删除目录: {filepath} (需要显式确认)"
        else:
            return False, f"路径不存在: {filepath}"
    except Exception as e:
        return False, f"删除失败: {e}"


# =============================================================================
# 便捷函数 (向后兼容 pulse_tools.py)
# =============================================================================

def read_file(
    filepath: str,
    workspace_root: Optional[str] = None,
) -> str:
    """
    读取文件内容 (简化版 API)

    Args:
        filepath: 文件路径
        workspace_root: workspace 根目录 (可选，默认使用 filepath 的父目录)

    Returns:
        文件内容 (失败返回空字符串)
    """
    if workspace_root is None:
        workspace_root = os.path.dirname(filepath) or "."

    result = safe_read_file(filepath, workspace_root)
    if not result.success:
        print(f"[safe_file_ops] 读取失败: {result.error}")
        return ""
    return result.content


def write_file(
    filepath: str,
    content: str,
    workspace_root: Optional[str] = None,
) -> bool:
    """
    写入文件内容 (简化版 API)

    Args:
        filepath: 文件路径
        content: 写入内容
        workspace_root: workspace 根目录 (可选，默认使用 filepath 的父目录)

    Returns:
        是否成功
    """
    if workspace_root is None:
        workspace_root = os.path.dirname(filepath) or "."

    result = safe_write_file(filepath, content, workspace_root)
    if not result.success:
        print(f"[safe_file_ops] 写入失败: {result.error}")
        return False
    return True


# =============================================================================
# JSON 安全读写函数
# =============================================================================


def safe_read_json(
    filepath: str,
    workspace_root: str,
    default: Any = None,
) -> Tuple[Any, Optional[str]]:
    """
    安全读取 JSON 文件

    Args:
        filepath: JSON 文件路径
        workspace_root: workspace 根目录
        default: 文件不存在或解析失败时的默认返回值

    Returns:
        (data, error) — data 为解析后的数据，error 为错误信息（None 表示成功）
    """
    result = safe_read_file(filepath, workspace_root)
    
    if not result.success:
        # 文件不存在返回默认值
        if "不存在" in result.error or "not found" in result.error.lower():
            return default, None
        return default, result.error
    
    try:
        data = json.loads(result.content)
        return data, None
    except json.JSONDecodeError as e:
        return default, f"JSON 解析失败: {e}"


def safe_write_json(
    filepath: str,
    data: Any,
    workspace_root: str,
    indent: int = 2,
    ensure_ascii: bool = False,
    max_bytes: int = DEFAULT_MAX_WRITE_BYTES,
) -> WriteResult:
    """
    安全写入 JSON 文件

    Args:
        filepath: JSON 文件路径
        data: 要写入的数据
        workspace_root: workspace 根目录
        indent: 缩进空格数
        ensure_ascii: 是否转义非 ASCII 字符
        max_bytes: 最大写入字节数

    Returns:
        WriteResult
    """
    try:
        content = json.dumps(
            data,
            indent=indent,
            ensure_ascii=ensure_ascii,
        )
    except (TypeError, ValueError) as e:
        return WriteResult(
            success=False,
            error=f"JSON 序列化失败: {e}",
            path=filepath,
        )
    
    return safe_write_file(
        filepath=filepath,
        content=content,
        workspace_root=workspace_root,
        max_bytes=max_bytes,
        mkdir=True,
    )
