---
name: code-cleaner
description: 审查项目结构、未使用的导入与定义、重复代码及代码坏味道。用于代码体检、code review、清理冗余和经授权的代码整理；默认只读报告，支持 Python、JavaScript/TypeScript 和 Java。
license: MIT
metadata:
  version: "1.1.0"
---

# Code Cleaner

默认先做只读筛查，输出可定位、可复核的候选问题。只有用户要求修改时，才在授权范围内整理代码。脚本不执行修复，也不联网或上传源码。

## 选择工作模式

- **只读筛查**：检查、体检、review、找问题。读取项目约定并确认项目根目录，运行相关检测，复核候选结果后报告。
- **代码整理**：用户明确要求修改、清理或重构。沿用已有授权；先准备具体改动清单，区分可确定的格式调整与影响行为的改动。对授权范围外或语义不确定的删除、重命名和公开 API 变更先澄清。

不要因为脚本说“未使用”就删除代码。导入可能有副作用；空的 `__init__.py`、框架入口、反射、插件注册、公开导出都可能有用途。

## 执行筛查

脚本要求 Python 3.10+，仅使用标准库。把 `<skill-dir>` 替换为本 Skill 所在目录；Windows 上可以用 `python` 替代 `python3`。

```bash
python3 <skill-dir>/scripts/run_review.py <项目目录> --format markdown
```

按需缩小范围并保存报告：

```bash
python3 <skill-dir>/scripts/run_review.py <项目目录> --checks structure,dead --exclude "tests/*" --format markdown --output review.md
```

也可以分别运行 `scripts/analyze_structure.py`、`scripts/detect_dead_code.py`、`scripts/find_duplicates.py`，它们默认输出 JSON。独立脚本只读取 `.codecleanerignore` 和自身命令参数；项目 JSON 配置由统一入口读取。

- 自定义阈值、忽略文件、退出码、输出格式和限制：读 [references/cli.md](references/cli.md)。
- 判断长函数、耦合和重复职责：按需读 [references/code-smells.md](references/code-smells.md)。
- 用户要求安全/性能审查：按需读 [references/security-checklist.md](references/security-checklist.md)，结合业务上下文检查；内置脚本不代替安全审计。
- 需要改命名、格式或语言习惯：按需读 [references/language-rules.md](references/language-rules.md)，优先遵循项目已有约定。

## 复核与报告

先检查 `complete` 和 `diagnostics`。文件读取失败、语法错误或比较数量达到上限时，扫描不完整；不能把空结果解释成“项目无问题”。

Python 使用 AST 和符号表检查导入及顶层定义；类方法、嵌套函数和装饰器入口不作为未使用定义候选。JS/TS/Java 使用启发式词法与引用统计，不具备完整的类型、模块或框架解析能力。重复检测会归一化字符串与数字，近似匹配仅筛选共享相邻代码行的窗口，结果需要上下文复核。

报告以 [assets/report-template.md](assets/report-template.md) 为参考，每项包含：相对路径、原始行号、规则、严重级别、置信度、具体影响与建议。区分已验证的问题与不确定的候选；附扫描范围、未覆盖内容、问题统计和处理顺序。

## 经授权整理

1. 修改前查看工作区状态，保留用户已有改动；备份将要修改的文件，包括未跟踪文件，并告知备份位置及恢复方式。不要自动执行 `git stash`。
2. 在已有授权范围内实施具体改动。删除未使用导入前确认副作用与导出；删除空文件前确认包结构与工具约定。
3. 删除或重命名小批量进行，每批不超过 10 项；运行与行为相关的测试或编译检查。
4. 汇报实际改动、验证结果、剩余限制及回滚方法。不要为了减少告警而压低阈值或隐藏问题。

## 范围保护

- 只处理用户指定的项目与文件，不扩大到无关目录。
- 不扫描或整理 `.workbuddy/` 项目数据、第三方依赖、虚拟环境和构建产物。扫描器不跟随符号链接或目录联接。
- 未明确要求写报告时输出到对话或标准输出；不在项目中自动写入配置、报告或缓存。
- 不执行未经授权的源码删除、公开 API 重命名、发布、提交或推送。
