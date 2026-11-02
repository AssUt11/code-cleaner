# 代码审查报告

- 项目：{{project_root}}
- 模式：{{mode}}
- 范围与排除项：{{scope}}
- 扫描状态与诊断：{{completeness}}
- 验证方式及未覆盖内容：{{validation}}

## 问题统计

| 严重 | 警告 | 建议 | 合计 |
|---:|---:|---:|---:|
| {{error_count}} | {{warning_count}} | {{info_count}} | {{total_count}} |

## 经复核的问题

| 级别 | 路径与行号 | 规则 / 置信度 | 影响与证据 | 建议 |
|---|---|---|---|---|
| {{severity}} | {{location}} | {{rule_and_confidence}} | {{impact_and_evidence}} | {{suggestion}} |

将不确定的候选单独说明，解释动态调用、公开 API 或副作用为何尚不能确定。扫描不完整时不可写“项目无问题”。自动生成报告是脚本候选，AI 报告应补充复核结论。

## 处理顺序

{{priorities}}

## 仅在已授权修改时填写

- 实际改动及原因：{{changes}}
- 备份位置与恢复方式：{{backup_and_restore}}
- 验证结果及限制：{{checks_and_limits}}
