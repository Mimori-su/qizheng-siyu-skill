#!/usr/bin/env python3
from __future__ import annotations
import argparse, re
from pathlib import Path
HEADINGS=['## 1. 元信息','## 2. 数据完整性','## 3. 太极与命身','## 4. 七政四余星曜位置','## 5. 十二宫','## 6. 二十八宿','## 7. 神煞','## 8. 原局初步标记','## 9. 运势资料','## 10. 校验结果']
STARS=['日','月','金','木','水','火','土','罗','气','计','孛']
def missing(value):
    return not value.strip() or bool(re.match(r'^(?:未知|不详|未提供|未核|待|缺失|无$|[-—]+$|N/?A$|unknown$)', value.strip(), re.I))
def section(text, heading):
    return text.split(heading, 1)[1].split('\n## ', 1)[0] if heading in text else ''
def rows(text):
    return [line.strip().strip('|').split('|') for line in text.splitlines() if line.strip().startswith('|')]
def main():
    p=argparse.ArgumentParser(); p.add_argument('file', type=Path); a=p.parse_args(); text=a.file.read_text(encoding='utf-8')
    errors=[]
    for h in HEADINGS:
        if h not in text: errors.append(f'missing heading: {h}')
    star_rows = rows(section(text, HEADINGS[3]))
    for s in STARS:
        found = [row for row in star_rows if len(row) == 9 and row[0].strip() == s]
        if len(found) != 1 or len(found[0]) < 5 or any(missing(v) for v in found[0][3:5]):
            errors.append(f'missing or ambiguous natal star position: {s}')
    core_rows = rows(section(text, HEADINGS[2]))
    for key in ['命宫','命度','命度主','身宫','身度','身度主']:
        found = [row for row in core_rows if row[0].strip() == key]
        if len(found) != 1 or len(found[0]) < 2 or missing(found[0][1]):
            errors.append(f'missing or ambiguous field value: {key}')
    for key in ['可信度','来源']:
        if key not in text: errors.append(f'missing field: {key}')
    print('# qz_structured_data validation report')
    if errors:
        print('\n## Errors'); [print('- '+e) for e in errors]
    else: print('\nOK: basic natal fields and table structure only; source and chart consistency still require review.')
    return 1 if errors else 0
if __name__ == '__main__': raise SystemExit(main())
