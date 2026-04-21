"""
测试 safe_file_ops.py 安全机制

验证目标:
1. 能安全读写项目数据文件
2. 阻止写入敏感路径
3. 阻止读取设备文件
4. 路径不逃逸 workspace
5. 支持符号链接检测
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.safe_file_ops import (
    safe_read_file,
    safe_write_file,
    safe_delete_file,
    read_file,
    write_file,
    ReadResult,
    WriteResult,
    _is_blocked_device,
    _is_write_denied,
    _is_path_inside,
)


class TestSafeFileOps(unittest.TestCase):
    """安全文件操作测试"""

    def setUp(self):
        """创建临时测试目录"""
        self.test_dir = tempfile.mkdtemp(prefix="pulse_test_")
        self.workspace_root = self.test_dir

    def tearDown(self):
        """清理临时目录"""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    # =========================================================================
    # 测试 1: 正常读写
    # =========================================================================

    def test_normal_read_write(self):
        """测试正常读写"""
        # 写入
        test_file = os.path.join(self.test_dir, "test.json")
        test_content = '{"key": "value"}'

        result = safe_write_file(test_file, test_content, self.workspace_root)
        self.assertTrue(result.success, f"写入失败: {result.error}")
        self.assertEqual(result.bytes_written, len(test_content.encode('utf-8')))

        # 读取
        read_result = safe_read_file(test_file, self.workspace_root)
        self.assertTrue(read_result.success, f"读取失败: {read_result.error}")
        self.assertEqual(read_result.content, test_content)

    def test_read_with_offset_limit(self):
        """测试分段读取"""
        test_file = os.path.join(self.test_dir, "large.txt")
        lines = [f"Line {i}\n" for i in range(100)]
        test_content = ''.join(lines)

        # 写入
        safe_write_file(test_file, test_content, self.workspace_root)

        # 读取第 10-20 行 (offset=10 表示从第 10 行开始)
        result = safe_read_file(test_file, self.workspace_root, offset=10, limit=10)
        self.assertTrue(result.success)
        # offset=10 (1-indexed) 从第 10 行开始，limit=10 读取 10 行
        # 所以应该包含 Line 9 到 Line 18 (0-indexed: 9-18)
        self.assertIn("Line 9", result.content)
        self.assertIn("Line 18", result.content)
        self.assertNotIn("Line 19", result.content)

    # =========================================================================
    # 测试 2: 阻止写入敏感路径
    # =========================================================================

    def test_write_denied_sensitive_path(self):
        """测试阻止写入敏感路径"""
        # ~/.ssh/id_rsa
        ssh_key = os.path.expanduser("~/.ssh/id_rsa")
        result = safe_write_file(ssh_key, "test", self.workspace_root)
        self.assertFalse(result.success)
        self.assertIn("拒绝", result.error)

    def test_write_denied_etc_passwd(self):
        """测试阻止写入 /etc/passwd"""
        result = safe_write_file("/etc/passwd", "test", self.workspace_root)
        self.assertFalse(result.success)
        self.assertIn("拒绝", result.error)

    # =========================================================================
    # 测试 3: 阻止读取设备文件
    # =========================================================================

    def test_blocked_device_path(self):
        """测试阻止读取设备文件"""
        # /dev/zero
        self.assertTrue(_is_blocked_device("/dev/zero"))
        self.assertTrue(_is_blocked_device("/dev/random"))
        self.assertTrue(_is_blocked_device("/dev/stdin"))

        # 正常路径
        self.assertFalse(_is_blocked_device("/home/user/test.txt"))

    def test_read_device_path_denied(self):
        """测试读取设备路径被拒绝"""
        result = safe_read_file("/dev/zero", self.workspace_root)
        self.assertFalse(result.success)
        self.assertIn("设备路径", result.error)

    # =========================================================================
    # 测试 4: 路径不逃逸 workspace
    # =========================================================================

    def test_path_escape_denied(self):
        """测试路径逃逸被拒绝"""
        # 创建一个测试文件
        test_file = os.path.join(self.test_dir, "test.txt")
        safe_write_file(test_file, "inside", self.workspace_root)

        # 尝试读取 workspace 外的文件
        outside_file = os.path.join(tempfile.gettempdir(), "outside_test.txt")
        with open(outside_file, 'w') as f:
            f.write("outside content")

        try:
            result = safe_read_file(outside_file, self.workspace_root)
            self.assertFalse(result.success)
            self.assertIn("逃逸", result.error)
        finally:
            os.remove(outside_file)

    def test_path_inside_check(self):
        """测试路径边界检查"""
        # 使用实际存在的路径测试
        workspace = self.test_dir
        file_inside = os.path.join(workspace, "file.txt")
        file_outside = os.path.join(tempfile.gettempdir(), "outside.txt")

        self.assertTrue(_is_path_inside(workspace, workspace))
        self.assertTrue(_is_path_inside(file_inside, workspace))
        self.assertFalse(_is_path_inside(file_outside, workspace))

    def test_path_traversal_denied(self):
        """测试路径遍历攻击被拒绝"""
        # 尝试使用 .. 逃逸
        test_file = os.path.join(self.test_dir, "test.txt")
        safe_write_file(test_file, "inside", self.workspace_root)

        escape_path = os.path.join(self.test_dir, "..", "..", "etc", "passwd")
        result = safe_read_file(escape_path, self.workspace_root)
        self.assertFalse(result.success)
        self.assertIn("逃逸", result.error)

    # =========================================================================
    # 测试 5: 符号链接检测
    # =========================================================================

    def test_symlink_detection(self):
        """测试符号链接检测"""
        # 创建目标文件
        target_file = os.path.join(self.test_dir, "target.txt")
        safe_write_file(target_file, "target content", self.workspace_root)

        # 创建符号链接
        link_file = os.path.join(self.test_dir, "link.txt")
        try:
            os.symlink(target_file, link_file)

            # 读取符号链接
            result = safe_read_file(link_file, self.workspace_root)
            self.assertTrue(result.success)
            self.assertTrue(result.is_symlink)
            self.assertEqual(result.symlink_target, target_file)
        except OSError:
            # Windows 可能需要管理员权限创建符号链接
            self.skipTest("创建符号链接需要管理员权限")

    # =========================================================================
    # 测试 6: 写入大小限制
    # =========================================================================

    def test_write_size_limit(self):
        """测试写入大小限制"""
        test_file = os.path.join(self.test_dir, "large.txt")
        large_content = "x" * (20 * 1024 * 1024)  # 20 MB

        result = safe_write_file(test_file, large_content, self.workspace_root, max_bytes=10*1024*1024)
        self.assertFalse(result.success)
        self.assertIn("超过", result.error)

    # =========================================================================
    # 测试 7: 读取大小限制
    # =========================================================================

    def test_read_truncation(self):
        """测试读取截断"""
        test_file = os.path.join(self.test_dir, "large.txt")
        large_content = "x" * 200_000  # 200K chars

        safe_write_file(test_file, large_content, self.workspace_root)

        result = safe_read_file(test_file, self.workspace_root, max_chars=100_000)
        self.assertTrue(result.success)
        self.assertIn("截断", result.content)

    # =========================================================================
    # 测试 8: 简化 API
    # =========================================================================

    def test_simple_api(self):
        """测试简化 API"""
        test_file = os.path.join(self.test_dir, "simple.txt")

        # 写入
        success = write_file(test_file, "simple content", self.workspace_root)
        self.assertTrue(success)

        # 读取
        content = read_file(test_file, self.workspace_root)
        self.assertEqual(content, "simple content")

    # =========================================================================
    # 测试 9: 删除
    # =========================================================================

    def test_safe_delete(self):
        """测试安全删除"""
        test_file = os.path.join(self.test_dir, "delete_me.txt")
        safe_write_file(test_file, "content", self.workspace_root)

        success, error = safe_delete_file(test_file, self.workspace_root)
        self.assertTrue(success)
        self.assertFalse(os.path.exists(test_file))

    def test_delete_directory_denied(self):
        """测试拒绝删除目录"""
        test_dir = os.path.join(self.test_dir, "subdir")
        os.makedirs(test_dir)

        success, error = safe_delete_file(test_dir, self.workspace_root)
        self.assertFalse(success)
        self.assertIn("目录", error)


if __name__ == "__main__":
    unittest.main(verbosity=2)
