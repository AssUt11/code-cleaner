# Code Cleaner

[English](README.md) | **简体中文** | [日本語](README.ja.md)

让 AI 帮你审查代码，同时保留人的判断：**默认只读，给出证据，经授权后再修改。**

Code Cleaner 是一个可安装的 Agent Skill，也是一组可独立运行的 Python 命令行工具。支持 Python、JavaScript / TypeScript（含 JSX、TSX）和 Java；运行时仅依赖 Python 3.10+ 标准库。

[使用说明](references/cli.zh-CN.md) · [贡献指南](CONTRIBUTING.zh-CN.md) · [更新记录](CHANGELOG.zh-CN.md) · [MIT 许可证](LICENSE)

## 能做什么

- **项目结构检查**：文件行数、目录深度、定义数量、空文件及含空格的文件名；保留 Java / React 的大写命名约定和空的 `__init__.py`。
- **未使用代码候选**：Python AST + 符号表检查导入的作用域和顶层定义；JS/TS/Java 使用启发式导入与引用统计。
- **重复代码候选**：按有序归一化代码行生成滑动窗口，识别嵌在更长代码段中的重复片段；索引筛选候选，支持比较次数与结果数量上限。
- **统一报告**：JSON / Markdown，包含原始行号、规则 ID、严重级别、置信度和修复建议。
- **项目定制**：`.codecleaner.json` 配置、`.codecleanerignore` 忽略规则、CLI 参数覆盖。
- **CI 集成**：可设置失败级别；读取失败、语法错误和结果截断均明确标记为不完整。
- **安全安装**：源/目标重合保护、预演、显式覆盖、暂存安装、保留旧版本和失败恢复。

结构、死代码和重复代码由脚本辅助；坏味道、安全和性能问题需要 AI 阅读上下文后判断。扫描脚本不修改源码、不执行被扫描代码，也不联网。

## 快速试用

克隆仓库并进入项目目录后运行：

```bash
git clone https://github.com/AssUt11/code-cleaner.git
cd code-cleaner
python scripts/run_review.py /path/to/project --format markdown
python scripts/run_review.py /path/to/project --format json --output report.json
```

Windows 路径有空格时加引号：

```powershell
python scripts/run_review.py "D:\My Project" --format markdown
```

AI 对话示例：

```text
使用 code-cleaner 检查这个项目，先只读报告，按影响给出修复顺序。
筛查死代码和重复代码，排除 generated 目录。
修复报告中已确认的问题，保留公开 API，并运行相关测试。
```

## 安装为 Skill

```bash
python install.py codex --dry-run
python install.py codex
python install.py claude workbuddy
python install.py --all
```

| 目标 | 默认父目录 |
|---|---|
| Codex | `~/.agents/skills/` |
| Claude Code | `~/.claude/skills/` |
| WorkBuddy | `~/.workbuddy/skills/` |

安装到父目录下的 `code-cleaner/`。目标布局供对应客户端发现 Skill；实际加载方式以客户端支持为准。Skill 的 `name`、`description`、`license`、`metadata` 使用 [Agent Skills 标准字段](https://agentskills.io/specification)，不再假定各客户端都会忽略任意扩展字段。

默认优先符号链接，权限不允许时复制。符号链接安装会随源目录更新；复制安装需重新安装。已有目标不会被静默覆盖：

```bash
python install.py codex --force
python install.py --target /custom/skills --no-symlink --dry-run
```

`--force` 会保留同级 `.code-cleaner.backup-时间-随机值` 备份。恢复时先移走当前 `code-cleaner`，再把备份重命名为 `code-cleaner`；备份为符号链接时保留它所指向的旧源目录。自安装、父子目录重合会被拒绝。

## 项目配置与忽略规则

将 `.codecleaner.example.json` 复制为被扫描项目根目录的 `.codecleaner.json`，按需调整；统一入口自动读取该配置。示例：

```json
{
  "checks": ["structure", "dead", "duplicates"],
  "exclude": ["generated/*", "*.min.js"],
  "max_lines": 500,
  "max_depth": 6,
  "min_lines": 6,
  "threshold": 0.85,
  "max_comparisons": 50000,
  "max_findings": 200
}
```

也可在 `.codecleanerignore` 中每行写一个相对路径 glob；`#` 开头为注释，不支持 `!` 反选，不自动读取 `.gitignore`。CLI 标量覆盖 JSON 配置，`--exclude` 则追加到配置。第三方依赖、隐藏目录、`.workbuddy/`、虚拟环境、构建产物和链接默认跳过。

## CI 与退出码

```bash
python scripts/run_review.py /path/to/project --checks structure,dead --fail-on warning
```

| 退出码 | 含义 |
|---|---|
| `0` | 完整扫描，未达到失败级别；默认 `--fail-on none` 允许存在候选项 |
| `1` | 完整扫描，存在达到 `--fail-on` 级别的问题 |
| `2` | 参数/配置/写入错误，或扫描不完整，包括解析失败与结果截断 |

`--fail-on info` 包含所有级别；`warning` 包含 warning / error；`error` 只包含 error。当前内置规则主要输出 warning / info，安全严重问题需人工或 AI 复核。三个独立检测脚本用于查看候选 JSON，CI 应使用统一入口。

仓库自带 GitHub Actions，覆盖 Ubuntu / Windows 与 Python 3.10 / 3.14。[查看 CI 运行结果](https://github.com/AssUt11/code-cleaner/actions)。

## 能力边界

- 结果是候选问题，**没有自动修复或自动删除命令**。导入副作用、公开 API、反射、插件注册、跨仓库调用不能仅凭静态计数判定。
- Python 不报告类方法、嵌套定义和装饰器入口为死代码；动态导出和字符串中的动态引用仍可能误判。
- JS/TS/Java 不是完整编译器分析，不解析模块别名、完整作用域或框架约定；CommonJS、动态导入等复杂语法覆盖有限。
- 重复检测保留代码行顺序，但会归一化字符串与数字；近似匹配要求窗口共享相邻归一化代码行，不保证召回所有语义相似片段。
- 索引无法消除高重复项目的最坏情况；达到上限会返回已有结果、`complete: false` 和退出码 `2`，请缩小范围或调高限制。
- 所有支持文件应可读取；Python 支持编码声明及 UTF-8 BOM，其他语言按 UTF-8 读取。读取失败会报告诊断。

## 开发与发布

```bash
python -B -m unittest discover -s tests -v
python -B tools/validate_skill.py
python -B tools/package_release.py --output ../code-cleaner.zip
```

验证器检查元数据、版本一致性和 Skill 本地引用；打包器校验后生成带 `code-cleaner/` 顶层目录的 ZIP，跳过 Git、缓存、依赖、已有 ZIP 和 `.workbuddy/`。完整源码、测试和 `.github/` 都包含在发布包内。

上传 GitHub 时，建议把**本目录中的文件和文件夹**作为仓库根目录内容，保留 `.github/`、`.gitignore` 等隐藏项；ZIP 可作为 Release 附件，单独上传 ZIP 不会触发源码 CI。



## 目录

```text
code-cleaner/
├── README*.md               # 英文、简体中文和日文说明
├── SKILL.md                 # AI 工作流与范围保护
├── install.py               # 跨平台目标安装器
├── scripts/                 # 统一入口、三个检测器、共享辅助模块
├── references/              # CLI、代码坏味道、语言习惯、安全/性能清单
├── assets/                  # 报告模板
├── agents/openai.yaml       # Codex UI 元数据
├── tests/                   # 行为回归测试
├── tools/                   # 发布校验与打包
└── .github/                 # CI、问题模板、PR 模板
```

## License

MIT，见 [LICENSE](LICENSE)。
