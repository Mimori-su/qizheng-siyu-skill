#!/usr/bin/env python3
from __future__ import annotations
import argparse, datetime as dt, sys
from pathlib import Path
def read(p):
    content = p.read_text(encoding='utf-8')
    if not content.strip():
        raise ValueError(f'Empty input file: {p}')
    return content
def main():
    p=argparse.ArgumentParser(); p.add_argument('--core', default=Path('qz_core_report.md'), type=Path); p.add_argument('--topics', nargs='*', type=Path, default=[]); p.add_argument('--out', default=Path('qz_full_report.md'), type=Path); a=p.parse_args()
    try:
        core = read(a.core)
        topics = [(path, read(path)) for path in a.topics]
    except (OSError, UnicodeError, ValueError) as exc:
        print(f'Cannot assemble report: {exc}', file=sys.stderr)
        return 2
    parts=['# 七政四余内部资料拼接草稿','',f'生成时间：{dt.datetime.now().isoformat(timespec="seconds")}','', '仅供内部整理原始资料，不是已完成的分析或客户报告。', '', '声明：本草稿为传统术数取象与学习辅助，不能替代医学、法律、财务或心理专业咨询。', '', '## Core 原局报告', '', core]
    for t, content in topics: parts += [f'## 专题报告：{t.stem}','',content]
    parts += ['## 总体不确定项','','- 请以各分报告中的缺失数据和不确定项为准。','- 若专题结论冲突，回到对应 Skill 复核。']
    a.out.write_text('\n'.join(parts), encoding='utf-8'); print(f'wrote {a.out}'); return 0
if __name__ == '__main__': raise SystemExit(main())
