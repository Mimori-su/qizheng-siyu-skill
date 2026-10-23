---
name: qz-reader
description: Extract and validate 七政四余 chart data; calculate 小限、飞限、节气月限 with dated intervals, and query eleven 郑氏星案恒星制 transit stars mapped to natal palaces. Data only, no fortune interpretation.
---

# qz-reader

## Purpose

七政四余盘面数据入口，负责提取、校验、小限／飞限／节气月限计算与指定时刻流曜查询，不作命理解读。本 Skill 输出以中文为主，所有结论都要区分“教材明确内容”“整理后的分析框架”“模型推理”“不确定项”。

## When to use this skill

当用户请求与本 Skill 定位一致的学习、读盘、核心分析、专题分析、校时或报告整合任务时使用。若用户请求超出本 Skill 边界，先说明边界并交给对应上游或下游 Skill。

## Required inputs

用户上传盘面 PDF、截图、OCR 文本或粘贴盘面。

流曜查询另需明确日期时间和时区；若要映射本命人事宫，须有已经核对的十二宫地支映射。仅有出生资料时，本入口不计算本命命宫。需要使用计算入口时完整读取 `resources/transit_star_query.md`。

年运／月运请求须完整读取 `resources/annual_period_query.md`，按已给出生时间、本命十二宫和宫限表调用 `scripts/calculate_periods.py` 自动补小限、飞限、月限。出生节气月由交节时刻计算，与已给月柱核对；缺宫限表只留缺飞限，不妨碍小限／月限。不要再因原盘未附这三项而要求用户手工排出。

## Output files

`qz_structured_data.md` 是数据契约名称，可由本轮结构化记录承载，不强制存在实体文件。用户不存档时全链路留在对话／内存。

## Workflow

1. 检查输入内容与必要资料是否具备；文本可直接来自本轮对话，不为满足文件名而强制落盘。
2. 读取本 Skill 的 resources，只加载与问题相关的文件。
3. 按 `resources/data_contract.md` 整理原局与流年数据；自动脚本输出须人工复核和补全新增字段。
   - 指定时刻流曜可调用 `scripts/calculate_transits.py`，只用郑氏星案恒星制与十一曜白名单。本命原盘保持不变，计算结果进入契约第 9 节。
   - 年运默认程序补算三限及节气日期表；月运定位具体时点。流曜须指定查询时刻，独立叠入小限／月限等本命宫位，不能把月初快照当成整月驻留。
4. 输出原始值、来源与可信度、缺失数据和可疑项；不输出支持／制约因素或命理结论。
5. 严格遵守本 Skill 的职责边界。

## Rules

- Reader 只提取／计算数据，不解读。三限由 `calculate_periods.py` 生成；流曜由 `calculate_transits.py` 生成。均不补算顶星、神煞、化曜或喜忌。
- 小限按出生立春年度起命宫、逐年逆行；月限以出生节气月起当年小限宫，交节换月。飞限六年一轮，实际交宫即第1年、下一立春第2年是本次公开的程序起算约定。飞限只列守星，不生成宫主星分析入口。输出具体公历起止时间和时区，年中换宫／度分段。
- 流曜叠本命使用普通三十度地支宫，不用来源程序的量天尺字段。必须标明时刻、时区、宿界、月孛口径与计算来源；默认宿界沿用来源引擎，已给流盘使用其他内置宿界时显式选取，不能静默改动星位或跨宿修正。
- 若用户已有流盘，保留原值及来源；重算不覆盖原值。星位或宿度不一致时查时间、时区和计算口径，未解决则标差异。一次快照不外推全年；用户不存档时标准输入／输出或内存传递，不写案例文件。
- 完整保留原始相位表及逐星化曜、管库、职衔标签，按本命／流年分栏；自动初提脚本未覆盖的字段须人工补齐，缺失与明确无项分开。
- 旧 `parse_chart_text.py` 的输出只是初稿；交给 Core 前须按 `resources/data_contract.md` 人工补全四柱地支、月令／农历日／昼夜月相线索、十一曜落宫地支与躔宿曜类、十二宫本命宫内星／宫主星，以及四阶段和 A／B 两条四宿观察入口。缺项标未知，不从宿度地支或流年关系推断填实；Reader 不判交感与喜忌。
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

- `resources/data_contract.md`
- `resources/extraction_rules.md`
- `resources/validation_rules.md`
- `resources/chart_reading_rules.md`
- `resources/missing_data_rules.md`
- `resources/transit_star_query.md`（仅需要查询流曜时加载）
- `resources/annual_period_query.md`（年运／月运自动补算三限时加载）

## Output format

`qz_structured_data.md` 须遵循 `resources/data_contract.md` 的十节结构。Reader 仅交付结构化盘面与校验结果，不生成客户断语。

## Handoff to other skills

缺读盘数据交给 qz-reader；缺原局分析交给 qz-core；需要整合交给 qz-report。
