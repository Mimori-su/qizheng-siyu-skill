#!/usr/bin/env python3
from __future__ import annotations
import argparse, datetime as dt, re
from pathlib import Path
def v(text,key):
    values = re.findall(rf'^\|[ \t]*{re.escape(key)}[ \t]*\|[ \t]*([^|\n]*)\|', text, re.M)
    if len(values) != 1:
        return ''
    value = values[0].strip()
    return '' if re.match(r'^(?:未知|不详|未提供|未核|待|缺失|无$|[-—]+$|N/?A$|unknown$)', value, re.I) else value
def main():
    p=argparse.ArgumentParser(); p.add_argument('--structured', required=True, type=Path); p.add_argument('--out', default=Path('qz_core_report.md'), type=Path); a=p.parse_args(); text=a.structured.read_text(encoding='utf-8')
    heading = '## 3. 太极与命身'
    natal = text.split(heading, 1)[1].split('\n## ', 1)[0] if heading in text else ''
    fields={k:v(natal,k) for k in ['命宫','命度','命度主','身宫','身度','身度主']}; missing=[k for k,x in fields.items() if not x]
    lines=['# qz_core_report.md','', '## 1. 报告元信息','', '| 字段 | 内容 |','|---|---|', f'| 输入文件 | {a.structured} |', f'| 生成时间 | {dt.datetime.now().isoformat(timespec="seconds")} |', '| 分析 Skill | qz-core |', f'| 数据完整性结论 | {"缺失："+", ".join(missing) if missing else "命身关键字段已读取，仍需人工复核"} |', '| 不适用声明 | 传统术数分析，仅供学习与取象参考 |', '', '## 2. 数据完整性复核', '', f'- 缺失字段：{", ".join(missing) or "无"}', f'- 脚本范围：{"缺命身字段，需补全；" if missing else ""}仅生成框架；仍须完整盘面与旺衰复核', '', '## 3. 太极与命身', '', '| 项目 | 结论 | 依据 | 制约 |','|---|---|---|---|', f'| 命度主 | {fields.get("命度主","")} | Reader 字段 | 需复核命度 |', f'| 身度主 | {fields.get("身度主","")} | Reader 字段 | 需复核身度 |', '', '## 4. 原局核心结构', '', '- 月令与四时：待分析','- 先天气数：待分析','- 尽三第一步：待分析','- 命度/身度/命主星所在度：待分析', '', '## 5. 喜忌与用神', '', '| 项目 | 结论 | 为什么喜/忌 | 支持证据 | 制约证据 | 可信度 |','|---|---|---|---|---|---|', '', '## 8. 正反双审', '', '- 支持因素：待分析','- 制约因素：待分析', f'- 缺失数据：{", ".join(missing) or "待人工复核"}', '- 不确定项：自动脚本只生成框架，不替代 qz-core 推理','- 谨慎结论：仅可作为分析草稿']
    a.out.write_text('\n'.join(lines)+'\n', encoding='utf-8'); print(f'wrote {a.out}'); return 1 if missing else 0
if __name__ == '__main__': raise SystemExit(main())
