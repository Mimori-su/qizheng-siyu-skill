---
name: qz-children
description: Use this skill for 七政四余 children, fertility symbolism, parent-child relationship, 男女宫, and offspring-topic questions after qz-core. It avoids medical or fetal-sex conclusions.
---

# qz-children

## Purpose

子女、生育取象和亲子关系专题。本 Skill 输出以中文为主，所有结论都要区分“已确认规则”“整理后的分析框架”“模型推理”“不确定项”。

## When to use this skill

当用户请求与本 Skill 定位一致的学习、读盘、核心分析、专题分析、校时或报告整合任务时使用。若用户请求超出本 Skill 边界，先说明边界并交给对应上游或下游 Skill。

## Required inputs

qz_structured_data.md、qz_core_report.md 和用户专题问题。

## Output files

`children_report.md` 是记录契约名称，输入、内部记录与客户正文均可在本轮对话／内存中完成；不存档时不生成文件。

## Workflow

1. 检查必要盘面与原局分析内容，可由本轮记录或已有文件承载；不以实体文件作为门槛。
2. 读取本 Skill 的 resources，只加载与问题相关的文件。
3. 按数据契约或专题框架整理证据。
4. 输出支持因素、制约因素、缺失数据、不确定项和谨慎结论。
5. 专题 Skill 必须继承 `qz_core_report.md`，不能独立乱断。

## Rules

- Reader 只读盘，不解读。
- Core 只基于 `qz_structured_data.md` 分析，不绕开数据契约。
- 专题 Skill 必须继承 `qz_core_report.md`，不能各自独立乱断。
- 不使用确定性、恐吓式、绝对化语言。
- 客户正文即使只问单项，也读取 `../qz-report/resources/report_style.md`；下方技术提纲仅作内部记录，不替代客户表达。
- 区分已确认规则、整理框架、推演与待核项；未明确的判法直接说明。

## Safety rules

- 疾病问题：只作传统术数取象参考，提醒咨询医生。
- 法律问题：只作传统术数取象参考，提醒咨询律师。
- 投资问题：不提供投资建议或收益预测，提醒咨询持牌专业人士。
- 心理危机或现实危险：建议寻求现实专业帮助或紧急服务。

## Reference resources

- `resources/children_framework.md`
- `resources/children_report_rules.md`

## Output format

```markdown
## 问题

## 数据基础

## 支持因素

## 制约因素

## 规则依据与待核项

## 谨慎结论

## 需要继续确认
```

## Handoff to other skills

缺读盘数据交给 qz-reader；缺原局分析交给 qz-core；需要整合交给 qz-report。
