---
name: qz-study
description: Use this skill when the user wants to learn, review, summarize,
  query, or create study materials from the 七政四余 training material, including
  太极、阴阳、三才、四时、五行、体用、喜忌、气数、七政四余、二十八宿、十二宫、三方四正、尽三、神煞、十神 and course chapter
  summaries.
disable: true
---

# qz-study

## Purpose

教材学习助手，不负责正式断盘。本 Skill 输出以中文为主，所有结论都要区分“教材明确内容”“整理后的分析框架”“模型推理”“不确定项”。

## When to use this skill

当用户请求与本 Skill 定位一致的学习、读盘、核心分析、专题分析、校时或报告整合任务时使用。若用户请求超出本 Skill 边界，先说明边界并交给对应上游或下游 Skill。

## Required inputs

PDF 整理资料、shared references、用户术语或章节问题。

## Output files

学习摘要、术语卡或章节问答。

## Workflow

1. 检查问题与所需来源内容是否可读，可来自文件或本轮对话；纯方法学习不要求命盘或 Core 报告，不强制落盘。
2. 读取本 Skill 的 resources，只加载与问题相关的文件。
3. 按数据契约或专题框架整理证据。
4. 输出支持因素、制约因素、缺失数据、不确定项和谨慎结论。
5. 严格遵守本 Skill 的职责边界。

## Rules

- Reader 只读盘，不解读。
- Core 只基于 `qz_structured_data.md` 分析，不绕开数据契约。
- 专题 Skill 必须继承 `qz_core_report.md`，不能各自独立乱断。
- 不使用确定性、恐吓式、绝对化语言。
- 引用教材时给出章节或页码范围；教材未明确时直接说明。

## Safety rules

- 疾病问题：只作传统术数取象参考，提醒咨询医生。
- 法律问题：只作传统术数取象参考，提醒咨询律师。
- 投资问题：不提供投资建议或收益预测，提醒咨询持牌专业人士。
- 心理危机或现实危险：建议寻求现实专业帮助或紧急服务。

## Reference resources

- `resources/course_index.md`
- `resources/glossary.md`
- `resources/learning_routes.md`
- `resources/concept_cards.md`
- `resources/chapter_qa.md`

## Output format

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
