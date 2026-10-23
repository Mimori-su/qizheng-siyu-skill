---
name: qz-rectifier
description: Use this skill when the user is unsure of birth time, wants 生时校正,
  compares candidate 时辰, or asks which birth time fits life events. It compares
  candidate charts and never claims perfect certainty.
disable: true
---

# qz-rectifier

## Purpose

生时校正专题。本 Skill 输出以中文为主，所有结论都要区分“已确认规则”“整理后的分析框架”“模型推理”“不确定项”。

## When to use this skill

当用户请求与本 Skill 定位一致的学习、读盘、核心分析、专题分析、校时或报告整合任务时使用。若用户请求超出本 Skill 边界，先说明边界并交给对应上游或下游 Skill。

## Required inputs

候选出生时间范围及各候选的真实排盘数据。可先正常分析候选差异让用户核对，或接收带年月、确定度的真实事件反查；不强制至少5件事件。资料不能区分候选时，保留多个结果并明确最需要补的反馈。

## Output files

允许归档时为 rectification_report.md；“不存档”时在对话中交付，分析记录也不为流程强制落盘。

## Workflow

1. 读 `resources/birth_time_rectification.md`，确定“先读候选再反馈”或“已有事件反查”路径，核出生时间范围、历法与排盘来源，不擅自扩大搜索范围。
2. 每个候选分别完成 qz-reader → qz-wangshuai → qz-core；相关事件按正常专题与限运方法分析，不能把一个候选的喜忌复用给所有盘。
3. 有真实事件时，按 `resources/event_mapping_rules.md` 用同一清单公平比较所有候选，列支持、矛盾和未知；没有事件时先比较候选差异。区分事先推断与已知事件后的解释。
4. 客户输出读取 `../qz-report/resources/report_style.md` 和 `resources/rectification_report_rules.md`；给可区分的差异与下一步核对，不编匹配分、百分比或确定到分钟的结论。
5. 旧关键词计分脚本已移至包内 retired，仅作历史资料，不调用。分析不自动改用户出生资料或客户档案。

## Rules

- Reader 只读盘，不解读。
- Core 只基于 `qz_structured_data.md` 分析，不绕开数据契约。
- 专题 Skill 必须继承 `qz_core_report.md`，不能各自独立乱断。
- 不使用确定性、恐吓式、绝对化语言。
- 区分已确认规则、整理框架、推演与待核项；未明确的判法直接说明。

## Safety rules

- 疾病问题：只作传统术数取象参考，提醒咨询医生。
- 法律问题：只作传统术数取象参考，提醒咨询律师。
- 投资问题：不提供投资建议或收益预测，提醒咨询持牌专业人士。
- 心理危机或现实危险：建议寻求现实专业帮助或紧急服务。

## Reference resources

- `resources/birth_time_rectification.md`
- `resources/event_collection_form.md`
- `resources/event_mapping_rules.md`
- `resources/rectification_report_rules.md`

## Output format

客户版按 `resources/rectification_report_rules.md`；以下仅为内部证据提纲，不覆盖客户结论先行顺序。

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
