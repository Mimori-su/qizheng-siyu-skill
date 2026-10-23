---
name: qz-love
description: Use this skill for 单人七政四余 relationship, marriage, romance, 桃花, breakup, reunion, partner traits, and timing questions after natal analysis. Actual two-person synastry routes to qz-compatibility and inherits each person's natal relationship model.
---

# qz-love

## Purpose

单人感情、婚姻、桃花专题；为双人合盘提供双方各自的婚恋模式。本 Skill 输出以中文为主，所有结论都要区分“已确认规则”“整理后的分析框架”“模型推理”“不确定项”。

## When to use this skill

当用户请求与本 Skill 定位一致的学习、读盘、核心分析、专题分析、校时或报告整合任务时使用。若用户请求超出本 Skill 边界，先说明边界并交给对应上游或下游 Skill。

实际两人匹配、婚恋合盘转到 `../qz-compatibility/SKILL.md`；先分别继承两人的原局与本专题需求，不把单人对象画像当作另一位现实对象的事实。本 Skill 的八板块客户模板不变，双人合盘使用该模块专用模板。

## Required inputs

qz_structured_data.md、qz_core_report.md 和用户专题问题。

上述名称表示输入数据契约，可由本轮对话／内存记录承载；报告名称也不强制落盘。用户不存档时不创建内部档或客户报告文件。

## Output files

`love_report.md`（内部证据与谨慎结论）。正式客户交付另生成独立的 `love_client_report.md`，与内部档结论同源，不把技术审计混入客户正文。完整婚恋客户报告按 `resources/client_report_template.md` 的八板块输出；只问窄问题时选取相关板块，不强行补齐八节。

## Workflow

1. 检查结构化盘面与原局分析内容是否具备，不以实体文件是否存在作为前置。
2. 读取本 Skill 的 resources，只加载与问题相关的文件。
3. 按数据契约或专题框架整理证据。
4. 输出支持因素、制约因素、缺失数据、不确定项和谨慎结论。
5. 专题 Skill 必须继承 `qz_core_report.md`，不能独立乱断。
6. 先完成内部档，再读取 `resources/client_report_template.md` 和 `resources/cautious_language.md` 生成客户版；两份报告的事实、风险程度和结论方向必须一致。

## Rules

- Reader 只读盘，不解读。
- Core 只基于 `qz_structured_data.md` 分析，不绕开数据契约。
- 专题 Skill 必须继承 `qz_core_report.md`，不能各自独立乱断。
- 桃花或恋爱对象的性格以男女宫主星定位，正式伴侣或配偶的性格以夫妻宫主星定位；宫内星曜主要描述关系氛围、活动与事件。详见 `resources/relationship_palace_rules.md`。
- 婚恋问题同时审查男女主和夫妻主，先分清接触机会与关系成立；宫主受克须有实际作用证据。多桃花、余奴或第三方风险均不能单点定案；时机按原局、洞微大限、度限、流年引动顺序。详见 `resources/relationship_palace_rules.md`。
- 不使用确定性、恐吓式、绝对化语言。
- 客户正文同时读取 `../qz-report/resources/report_style.md`，单项也执行“语言的艺术”，保持婚恋专用八节模板及按需裁剪规则。
- 不利婚恋线索须如实说明证据强弱、成立条件和现实影响，再给客户可选择的沟通、边界或保护行动；正向语气不得把风险说成好事。现实中的威胁、暴力或强迫不得淡化为“磨合”。
- 区分已确认规则、整理框架、推演与待核项；未明确的判法直接说明。

## Safety rules

- 疾病问题：只作传统术数取象参考，提醒咨询医生。
- 法律问题：只作传统术数取象参考，提醒咨询律师。
- 投资问题：不提供投资建议或收益预测，提醒咨询持牌专业人士。
- 心理危机或现实危险：建议寻求现实专业帮助或紧急服务。

## Reference resources

- `resources/love_framework.md`
- `resources/relationship_palace_rules.md`
- `resources/compatibility_rules.md`
- `resources/cautious_language.md`
- `resources/client_report_template.md`（完整婚恋客户报告时必读）

## 内部档 Output format

以下七项仅用于 `love_report.md` 的内部审查，不是客户版章节；客户版遵循 `resources/client_report_template.md`。

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
