# CLI 参考

要求 Python 3.10+，无第三方运行依赖。所有扫描器只读，不执行项目代码。以下命令在 Skill 根目录运行。

## 统一扫描

```bash
python scripts/run_review.py PROJECT [选项]
```

| 选项 | 默认值 | 含义 |
|---|---|---|
| `--checks` | `structure,dead,duplicates` | 逗号分隔的检测维度 |
| `--format` | `json` | `json` / `markdown` |
| `--output PATH` | 标准输出 | 显式写入报告；父目录需已存在 |
| `--config PATH` | 项目根目录 `.codecleaner.json`（若存在） | JSON 配置；未知字段或错误类型会报错 |
| `--exclude GLOB` | 无额外规则 | 可重复；追加到配置中的 exclude |
| `--max-lines` | `500` | 单文件行数阈值，正整数 |
| `--max-depth` | `6` | 相对目录深度阈值，非负整数 |
| `--min-lines` | `6` | 重复窗口的归一化代码行数，至少 2 |
| `--threshold` | `0.85` | 有序窗口匹配阈值，范围 `[0.5, 1]` |
| `--max-comparisons` | `50000` | 重复候选比较上限，正整数 |
| `--max-findings` | `200` | 重复检测结果上限，正整数 |
| `--fail-on` | `none` | `none` / `info` / `warning` / `error` |
| `--version` | — | 显示工具版本 |

JSON 配置使用对应下划线字段，例如 `max_lines`；`checks`、`exclude` 均为字符串数组。配置仅由统一入口读取。

## 忽略规则

所有检测器读取项目根目录 `.codecleanerignore`：每行一个相对路径 glob，路径分隔符统一为 `/`。使用 Python `fnmatch` 语义，`*` 可以匹配路径分隔符；目录前缀也参与匹配。`generated/` 跳过该目录，`tests/*` 跳过测试文件，`*.min.js` 跳过任意深度的匹配文件。`#` 开头为注释；不实现 Git 的反选、转义或完整 `.gitignore` 语义。

内置跳过规则不可通过配置取消：第三方目录、虚拟环境、构建产物、隐藏目录、`.workbuddy/` 和符号链接/目录联接。根目录应指向真正要扫描的项目，不要把依赖目录本身作为根目录。

## JSON 格式（schema_version 1）

顶层含 `schema_version`、`version`、`root`、`complete`、`total_findings`、`counts`、`diagnostics`、`findings`。

每个 finding 含 `rule_id`、`type`、`path`、`line`、`severity`、`confidence`、`detail`、`suggestion`。路径相对于项目根目录，行号从 1 开始。重复代码还含 `path_b`、`line_b`、`end_line`、`end_line_b`、`similarity`。位置覆盖原始源码，归一化不会改变报告行号。

- `severity`：`error` / `warning` / `info`；按影响定级，规则结果不等同已确认 bug。
- `confidence`：`high` / `medium` / `low`；表示静态推断把握，不代替人工复核。
- `diagnostics`：读取、解析或上限信息，每项含 `path` 和 `message`。非空时 `complete` 为 false。
- 退出码：0 = 完整且未达失败级别；1 = 完整且触发级别；2 = 参数、配置、I/O 错误或扫描不完整。不要忽略退出码 2。

规则 ID：`structure.depth`、`structure.lines`、`structure.definitions`、`structure.empty`、`structure.naming`、`dead.import`、`dead.definition`、`duplicates.window`。

## 独立检测器

```bash
python scripts/analyze_structure.py PROJECT --max-lines 600 --max-depth 6
python scripts/detect_dead_code.py PROJECT --exclude "generated/*"
python scripts/find_duplicates.py PROJECT --min-lines 8 --threshold 0.9
```

它们直接输出相同 schema 的 JSON，但不应用 JSON 配置，也不提供 CI 级别判定；扫描诊断请检查 `complete`。CI 使用 `run_review.py`。

## 安装器

```bash
python install.py codex --dry-run
python install.py claude workbuddy --no-symlink
python install.py --all --force
python install.py --target ./local-skills --no-symlink
```

`--target` 是父目录，会在其下创建 `code-cleaner/`；它与平台名、`--all` 不混用。`--force` 显式替换并保留旧版本；无覆盖授权时拒绝已有目标。暂存失败时旧安装不变；发布重命名失败时尝试恢复旧安装，保留下来的备份可用于手工恢复。`--dry-run` 不创建目录、不安装。成功返回 0，任一目标失败返回 1，参数错误返回 2。
