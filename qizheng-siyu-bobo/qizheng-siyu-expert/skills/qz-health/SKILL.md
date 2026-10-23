---
name: qz-health
description: 七政四余健康与身心功能取象；继承原局，检查全盘受制、疾厄体系及相貌宫与相貌主的内心感受线索，纳入45°刑和135°对刑。仅作传统象义与现实反馈核对，不作医学或心理诊断。
---

# qz-health

## Purpose

健康与身心功能取象专题。本 Skill 输出以中文为主，区分老师规则、传统功能资料、模型推理与现实反馈；盘面不能确立身体疾病或心理障碍。

## When to use this skill

当用户请求与本 Skill 定位一致的学习、读盘、核心分析、专题分析、校时或报告整合任务时使用。若用户请求超出本 Skill 边界，先说明边界并交给对应上游或下游 Skill。

## Required inputs

qz_structured_data.md、qz_core_report.md 和用户专题问题。

## Output files

仅在允许存档时生成客户版 `health_report.md` 与内部档 `health_internal.md`；用户说“不存档／不入库”时只在对话交付，不写客户、咨询或案例文件。

## Workflow

1. 检查读盘、旺衰与原局记录；可使用本轮对话结果，不强制新建文件。单问健康也先读 `../qz-report/resources/report_style.md`。
2. 读取本 Skill 的 resources，只加载与问题相关的文件。
3. 按 `resources/health_framework.md` 逐星检查身体及心理线索，重点复核疾厄体系、相貌宫与相貌主，保留原始相位表中的刑与对刑。
4. 输出支持、制约、救应、缺项及现实核对；客户正文与内部证据按框架末尾的双层格式组织。
5. 专题 Skill 必须继承 `qz_core_report.md`，不能独立乱断。

## Rules

- Reader 只读盘，不解读。
- Core 只基于 `qz_structured_data.md` 分析，不绕开数据契约。
- 专题 Skill 必须继承 `qz_core_report.md`，不能各自独立乱断。
- 不使用确定性、恐吓式、绝对化语言。
- 引用教材时给出章节或页码范围；教材未明确时直接说明。
- 健康专题采用 2026-10-09 老师确认的交感补充：45°刑、135°对刑均可看，取象侧重持续、反复、慢性的牵制感；不是慢性病诊断，也不代表必然长期患病。具体记录和边界见 `resources/health_framework.md`。
- 身体、心理及身心联系均须检查；心理重点包括相貌宫、相貌主的受克与交战，并参照月亮、身度主。没有对应依据时明确不足，不强行输出两套病象。

## Safety rules

- 疾病问题：只作传统术数取象参考，提醒咨询医生。
- 法律问题：只作传统术数取象参考，提醒咨询律师。
- 投资问题：不提供投资建议或收益预测，提醒咨询持牌专业人士。
- 心理危机或现实危险：建议寻求现实专业帮助或紧急服务。

## Reference resources

- `resources/health_framework.md`
- `resources/medical_safety_rules.md`
- `resources/disease_symbolism_rules.md`

## Output format

客户版按 `health_framework.md` 末尾六部分择要组织；以下为内部记录骨架，不替代客户模板。无存档授权时两层均只在对话交付。

```markdown
## 问题

## 数据基础

## 支持因素

## 制约因素

## 教材依据

## 谨慎结论

## 需要继续确认
```

## Handoff to other skills

缺读盘数据交给 qz-reader；缺原局分析交给 qz-core；需要整合交给 qz-report。
