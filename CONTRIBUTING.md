# 贡献指南

欢迎提交 bug 修复、减少误报的真实用例及有明确边界的检测能力。先保证结果可复核，再扩大覆盖范围。

## 本地验证

使用 Python 3.10+，无需安装运行依赖：

```bash
python -B -m unittest discover -s tests -v
python -B tools/validate_skill.py
```

测试在仓库同级创建并清理独立临时目录，不安装到个人平台目录。Windows 未授予符号链接权限时，相关真实链接测试会显示 skipped；复制回退仍会测试。

## 提交要求

- 修复检测问题时提供最小源码样例，并断言可观察行为：候选是否出现、原始行号、诊断和退出码。
- 不通过隐藏误报样例或放宽断言让测试通过。启发式检测的限制写进 README。
- 保持扫描只读，不执行被扫描代码，不引入源码上传或自动删除。
- 优先标准库；新依赖需要说明必要性、安装影响及许可证。
- JSON schema 的破坏性调整需要更新 schema_version、文档和回归测试。
- 修改版本时同步 `scripts/_common.py`、`SKILL.md` 和 `CHANGELOG.md`。
- PR 说明问题、修改后的行为和实际验证结果；不要提交缓存、扫描报告或真实密钥。

## 发布

1. 运行测试与 Skill 校验；检查版本和更新记录。
2. 运行 `python tools/package_release.py --output ../code-cleaner.zip`。
3. 在 GitHub 检查跨系统 CI 的真实结果，再创建标签 / Release 并附加 ZIP。

发布和推送由维护者明确执行；工具不会自动创建仓库、提交或上传文件。
