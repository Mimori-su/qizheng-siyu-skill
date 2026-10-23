# 七政四余命理分析师 · 完整技能包

## 这是什么

这是**七政四余命理分析师**的完整技能包，一个基于**既定恒星制**的七政四余命理分析全栈工具包。

版本：2026-10-17。安装与能力边界见 `开始使用.md`。

## 总览

| 项目 | 内容 |
|------|------|
| 入口数量 | **1 个总控 + 13 个子技能，共 14 个 Skill 入口** |
| 子技能 | 读盘、旺衰、原局、事业、财运、婚恋、通用合盘、子女、健康、学习整理、择日、校时、报告整合 |
| 参考资源 | 星曜类象库、二十八宿类象（含分类目录）、五行体用喜忌、十二宫框架、度层框架等 |
| 示例报告 | 原局核心、事业、财运、感情、子女、健康、校时、择日、完整报告 |
| 类象资料 | lodge_symbolism.md、star_symbolism.md，以及 shared-resources 内置类象页 |
| 自动化脚本 | Python 辅助脚本：PDF 文本提取与页面渲染、文本初提、基础字段校验、核心框架生成、内部旧报告拼接；不代替断法推理，不提供自动校时评分 |

## 使用方法

### 方式一：兼容宿主的 Agent / 插件加载

Agent 定义与现有插件配置位于 `qizheng-siyu-expert/`。按目标宿主实际支持的本地插件流程加载；本包不含自动注册工具，也未验证所有宿主版本。使用实际安装目录下的相对路径。

### 方式二：手动加载 SKILL.md

在对话中直接引用本包根目录的 `SKILL.md` 作为系统提示，配合子技能使用。

### 方式三：单独加载子技能

子技能入口位于 `qizheng-siyu-expert/skills/qz-*/SKILL.md`。健康已启用；学习整理、择日、校时仍保留原有 `disable: true`，加载状态以这些标记为准。入口文件存在不代表所有功能都已启用或完成。官非并入事业、财运，旧独立入口不随包提供，也不参与注册。

新手先看 `qizheng-siyu-expert/skills/qz-report/resources/usage_guide.md`；完整盘面而未指定问题时，输出同目录 `qizheng-siyu-expert/skills/qz-report/resources/quick_overview_template.md` 的六节简析。首次问候只邀请查看说明，不强制阅读；已有问题直接分析。

## 分析流程总览

```
用户提供盘面数据
       ↓
  ┌── qz-reader ──┐  读盘结构化（只读不解读）
  │  ↓             │
  │ qz-wangshuai   │  星曜旺衰判断（必须预先执行）
  │  ↓             │
  │ qz-core        │  原局核心分析（太极·喜忌·尽三·限运）——唯一地基
  │  ↓             │
  │ qz-career      │  事业与学历专题（继承 core 结论）
  │ qz-wealth      │  财运专题
  │ qz-love        │  感情婚姻专题
  │ qz-compatibility│ 通用合盘（双方分别完成读盘、旺衰、原局）
  │ qz-children    │  子女家庭专题
  │ qz-health      │  健康专题
  │ qz-study       │  教材学习整理（原加载标记保留）
  │ ...            │
  │  ↓             │
  └── qz-report ──┘  报告整合输出
```

## 核心资源索引

### 星曜类象（取象与旧说回查）
- `skills/qz-core/resources/star_symbolism.md` — 星曜力量与类象、关系类象、健康类象

四时判断以总控指定的现行《十一曜四时喜忌-条件分支》为先；旧教材类象库不覆盖老师已确认的条件规则。

### 星宿类象
- `skills/qz-core/resources/lodge_symbolism.md` — 二十八宿类象（Markdown 版）：每宿定义、性格、职业、象征物、五行、人体、场所、星度、现代引申、吉凶

### 分析框架
- `skills/qz-core/resources/taiji_rules.md` — 太极点判定规则
- `skills/qz-core/resources/palace_framework.md` — 十二宫框架
- `skills/qz-core/resources/degree_framework.md` — 度层四度相通规则
- `skills/qz-core/resources/wuxing_tiyong_xiji.md` — 五行体用喜忌
- `skills/qz-core/resources/core_concepts.md` — 核心概念
- `skills/qz-core/resources/original_vs_transit.md` — 原局与流年关系
- `skills/qz-core/resources/method_boundaries.md` — 已采用规则、候选技法与冲突边界
- `skills/qz-wangshuai/SKILL.md` — 旺衰判断框架（含生克口诀适用条件、四季喜忌）

### 读盘规则
- `skills/qz-reader/resources/natal_chart_input.md` — 出生资料、时间基准与本命引擎接入验收；完整本命引擎待适配和校准，未随包提供
- `skills/qz-reader/scripts/check_birth_time.py` — 按出生地历史时区检查夏令时及重复／不存在的钟表时间，提醒确认后定时辰
- `skills/qz-reader/resources/topstar_query.md` — 已采用的顶星公式及独立计算工具，需提供真实行度中心、限年数与同口径星位
- `skills/qz-reader/resources/data_contract.md` — 数据契约
- `skills/qz-reader/resources/extraction_rules.md` — 提取规则
- `skills/qz-reader/resources/validation_rules.md` — 校验规则
- `skills/qz-reader/resources/chart_reading_rules.md` — 读盘规则
- `skills/qz-reader/resources/missing_data_rules.md` — 缺数据规则

### 专题框架
- `skills/qz-career/resources/` — 事业与学历框架
- `skills/qz-career/resources/education_framework.md` — 学业、学历、升学与资格证分析；个人求学问题不交 qz-study
- `skills/qz-wealth/resources/` — 财运框架
- `skills/qz-love/resources/` — 单人感情框架；双盘交给 qz-compatibility
- `skills/qz-compatibility/resources/` — 同地支双向叠盘、婚恋/合作/上下属、客户版与内部档模板
- `skills/qz-children/resources/` — 子女框架
- `skills/qz-health/resources/` — 健康框架
- `skills/qz-core/resources/dispute_risk_rules.md` — 事业、财运共用的官非与纠纷规则
- `skills/qz-election/resources/` — 择日框架
- `skills/qz-rectifier/resources/` — 校时框架
- `skills/qz-study/resources/` — 学习资源（课程索引、概念卡、词汇表、学习路线）

### 示例报告
- `skills/qz-core/examples/core_report.sample.md` — 原局核心分析示例
- `skills/qz-report/examples/full_report.sample.md` — 完整报告示例
- 各专题 `examples/` 目录下均有示例报告

以上 `skills/` 资源路径均相对 `qizheng-siyu-expert/`。简析、使用指南、“语言的艺术”和各专题输出调度由 qz-report 管理；性格、人际、本命格局、洞微大限与流年是内部模块，不另算独立 Skill。

## 注意事项

- 必要知识页已内置在 `shared-resources/`，通过相对路径读取，无需原电脑的 Obsidian 库。可选脚本依赖与完整本命引擎边界见 `开始使用.md`；未提供的专门资料按缺失处理。
- 回归测试：在本包根目录执行 `python3 -m unittest discover -s tests -v`。此测试验证辅助脚本，不验证术数结论或宿主加载。

- 本技能包纯为术数研究学习使用
- 所有分析结论需区分教材明确 / 框架整理 / 模型推理 / 不确定项
- 健康/法律/投资类问题强制免责声明
- 日月是光体，不参与五行生克
