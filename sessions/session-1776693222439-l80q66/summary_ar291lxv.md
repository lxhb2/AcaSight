## 任务背景
调试脉冲学习系统的端到端测试：`create_module` 成功但 `finish_module` 失败。
## 执行过程
1. 添加调试信息到 `test_e2e.py`
2. 定位多个静默失败点
3. 发现 frontmatter 解析 bug
4. 追踪 `_write_file` 失败原因
5. 定位 `PROJECTS_DIR` 路径计算错误
6. 会话压缩前写入记忆文件
## 关键结果
- 修改 `projects/test_e2e.py` 添加调试输出
- 发现根因链：frontmatter 解析 bug → 模块文件未创建 → finish_module 失败
- `PROJECTS_DIR` 来自 `data_paths.py`，读取 `data_paths.json` 配置
- `create_project` 静默失败，目录未创建
- 生成 `memory/2026-04-21.md` 记录调试进展
## 结论建议
根因已明确：`workspace_root` 参数和 `PROJECTS_DIR` 路径不一致导致文件写入到错误位置。
下一步：检查 `data_paths.json` 实际配置；验证 `workspace_root` 传入 `_write_file` 的值。