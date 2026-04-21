# LEARNINGS.md

This file tracks corrections, knowledge gaps, and best practices discovered during sessions.

---

## [LRN-20260421-001] windows_path_handling

**Logged**: 2026-04-21T14:30:00+08:00
**Priority**: high
**Status**: resolved
**Area**: backend

### Summary
Windows 短路径名 (ADMINI~1) 和长路径名 (Administrator) 不一致，导致路径比较失败

### Details
在 Windows 上，`os.path.realpath()` 返回长路径名，而 `os.path.normpath(os.path.abspath())` 返回短路径名。这导致路径边界检查失败。

**错误示例**:
```python
# realpath 返回长路径
base = os.path.realpath("C:\\Users\\ADMINI~1\\...")  # -> C:\Users\Administrator\...

# normpath + abspath 返回短路径
target = os.path.normpath(os.path.abspath("C:\\Users\\ADMINI~1\\...\\file.txt"))  # -> C:\Users\ADMINI~1\...\file.txt

# 比较失败！
target.startswith(base + os.sep)  # -> False
```

**解决方案**:
统一使用 `os.path.normpath(os.path.abspath())` 处理所有路径。

### Suggested Action
在所有路径比较场景中，统一使用相同的路径规范化方法。

### Metadata
- Source: debugging
- Related Files: src/utils/safe_file_ops.py
- Tags: windows, path-handling, bug

---

## [LRN-20260421-002] function_parameter_order

**Logged**: 2026-04-21T14:35:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: backend

### Summary
函数参数顺序应遵循直觉：检查函数应该是 `check(target, base)` 而非 `check(base, target)`

### Details
`_is_path_inside(base_dir, target_path)` 的参数顺序违反直觉，导致所有调用都传反了参数。

**错误示例**:
```python
def _is_path_inside(base_dir, target_path):  # 参数顺序反直觉
    ...

_is_path_inside(workspace_root, resolved)  # 调用也反了！
```

**正确设计**:
```python
def _is_path_inside(target_path, base_dir):  # target 在前，符合直觉
    ...

_is_path_inside(resolved, workspace_root)  # 检查 resolved 是否在 workspace_root 内
```

### Suggested Action
设计检查类函数时，把被检查对象放在第一个参数。

### Metadata
- Source: code-review
- Related Files: src/utils/safe_file_ops.py
- Tags: api-design, parameter-order

---

