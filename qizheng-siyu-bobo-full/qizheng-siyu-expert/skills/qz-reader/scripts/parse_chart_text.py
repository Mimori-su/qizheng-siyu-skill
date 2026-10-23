#!/usr/bin/env python3
from __future__ import annotations
import argparse, re
from pathlib import Path
STARS=[('日','七政'),('月','七政'),('金','七政'),('木','七政'),('水','七政'),('火','七政'),('土','七政'),('罗','四余'),('气','四余'),('计','四余'),('孛','四余')]
ALIASES = {
    '日': ('太阳', '太陽', '日'), '月': ('月亮', '太阴', '太陰', '月'),
    '金': ('金星', '金'), '木': ('木星', '木'), '水': ('水星', '水'),
    '火': ('火星', '火'), '土': ('土星', '土'),
    '罗': ('罗喉', '羅喉', '羅睺', '罗', '羅'),
    '气': ('紫炁', '紫气', '紫氣', '炁', '气', '氣'),
    '计': ('计都', '計都', '计', '計'), '孛': ('月孛', '孛星', '孛'),
}
NAME_TO_STAR = {name: star for star, names in ALIASES.items() for name in names}
STAR_START = re.compile('^(' + '|'.join(re.escape(name) for name in sorted(NAME_TO_STAR, key=len, reverse=True)) + r')(.*)$')
PALACES=['命宫','财帛','兄弟','田宅','男女','奴仆','夫妻','疾病','迁移','官禄','福德','相貌']
TRANSIT = r'流年|行运|大限|小限|度限|飞限|推运'
def natal_lines(text):
    """Read only unscoped/natal records; an explicit transit section stays excluded."""
    transit_section = False
    for raw in text.splitlines():
        line = raw.strip()
        heading = line.lstrip('#').strip().strip('【】[]').rstrip('：:')
        if line.startswith('#') or re.fullmatch(
                rf'(?:本命|原局|{TRANSIT})(?:盘|星曜|星位|资料|数据|信息|位置)?', heading):
            if heading.startswith(('本命', '原局')):
                transit_section = False
            elif re.search(TRANSIT, heading):
                transit_section = True
            continue
        line = line.lstrip('-* \t')
        explicit_natal = line.startswith(('本命', '原局'))
        if re.search(TRANSIT, line) or (transit_section and not explicit_natal):
            continue
        yield re.sub(r'^(?:本命|原局)[ \t]*', '', line)

def missing(value):
    return not value.strip() or bool(re.match(r'^(?:未知|不详|未提供|未核|待|缺失|无$|[-—]+$|N/?A$|unknown$)', value.strip(), re.I))

def val(text,key):
    values = set()
    for line in natal_lines(text):
        match = re.match(rf'^{re.escape(key)}(?:[ \t]*[：:][ \t]*|[ \t]+)(.*)$', line)
        if match:
            first_value = re.split(r'[，,；;|]|[ \t]+[^ \t：:,，；;|]+[：:]', match.group(1), maxsplit=1)[0]
            values.add(first_value.strip())
    return values.pop() if len(values) == 1 else ''
def star_row(text, star, typ):
    candidates = set()
    original_names = set()
    for line in natal_lines(text):
        record = STAR_START.match(line)
        if not record or NAME_TO_STAR[record.group(1)] != star:
            continue
        body = record.group(2)
        if re.search(r'宫内星|宮內星|汇总|彙總|、', body) or body.lstrip().startswith(('和', '与', '及')):
            continue
        entered = re.search(r'(?:^|[ \t,，;；|：:])入[ \t]*([子丑寅卯辰巳午未申酉戌亥])', body)
        position = re.match(r'(命宫|财帛|兄弟|田宅|男女|奴仆|夫妻|疾病|迁移|官禄|福德|相貌|[子丑寅卯辰巳午未申酉戌亥]宫?)', body.lstrip(' \t：:|'))
        if not entered and not position:
            continue
        lodge = re.search(r'[角亢氐房心尾箕斗牛女虚危室璧壁奎娄胃昴毕觜参井鬼柳星张翼轸][日月火水木金土](?:[ \t]*\d+(?:\.\d+)?[ \t]*(?:度|°)(?:[ \t]*\d+(?:\.\d+)?[ \t]*(?:分|′|\x27))?(?:[ \t]*\d+(?:\.\d+)?[ \t]*(?:秒|″|\x22))?)?', body)
        palace = entered.group(1) if entered else position.group(0)
        if len(palace) == 1:
            palace += '宫'
        candidates.add((palace, lodge.group(0) if lodge else ''))
        original_names.add(record.group(1))
    palace, degree = candidates.pop() if len(candidates) == 1 else ('', '')
    conf='中' if palace and degree else '低'
    note = '自动初提，需复核'
    if original_names:
        note += '；原星名：' + '／'.join(sorted(original_names))
    return f'| {star} | {typ} |  | {palace} | {degree} |  | {note} | 输入文本 | {conf} |'
def build(text):
    missing_fields=[k for k in ['命宫','命度','命度主','身宫','身度','身度主'] if missing(val(text,k))]
    out=['# qz_structured_data.md','','## 1. 元信息','','| 字段 | 内容 | 可信度 | 来源 |','|---|---|---|---|']
    for k in ['出生日期','出生时间','出生地点','性别','排盘软件']:
        out.append(f'| {k} | {val(text,k)} | 低 | 输入文本 |')
    out += ['| 数据来源 | 文本 | 中 | 用户粘贴 |','| 读取方式 | 文本提取 | 中 | parse_chart_text.py |','','## 2. 数据完整性',f'- 缺失项：{", ".join(missing_fields) if missing_fields else "待人工复核"}','- 待用户确认项：所有低可信度字段','','## 3. 太极与命身','','| 项目 | 值 | 说明 | 来源 | 可信度 |','|---|---|---|---|---|']
    for k in ['命宫','命度','命度主','身宫','身度','身度主']:
        out.append(f'| {k} | {val(text,k)} | 自动初提 | 输入文本 | 低 |')
    out += ['| 男命/女命取法 |  | 待确认 | 输入文本 | 低 |','','## 4. 七政四余星曜位置','','| 星曜 | 类型 | 五行 | 宫位 | 星宿/度 | 状态 | 备注 | 来源 | 可信度 |','|---|---|---|---|---|---|---|---|---|']
    out += [star_row(text,s,t) for s,t in STARS]
    out += ['','## 5. 十二宫','','| 序号 | 宫名 | 宫位 | 宫五行 | 宫内星曜 | 神煞 | 备注 | 来源 | 可信度 |','|---|---|---|---|---|---|---|---|---|']
    out += [f'| {i} | {name} |  |  |  |  | 自动模板，待补充 | 输入文本 | 低 |' for i,name in enumerate(PALACES,1)]
    out += ['','## 6. 二十八宿','','| 星宿 | 五行 | 所在宫位 | 相关星曜 | 来源 | 可信度 |','|---|---|---|---|---|---|','','## 7. 神煞','','| 神煞 | 位置 | 作用领域 | 备注 | 来源 | 可信度 |','|---|---|---|---|---|---|','','## 8. 原局初步标记','','注意：本部分由 qz-reader 仅做数据标记，不做解读。','','- 五行明显偏性：待 qz-core 复核','- 命身关键星曜：待 qz-core 复核',f'- 明显缺失项：{", ".join(missing_fields) if missing_fields else "待人工复核"}','- 可交给 qz-core 复核的点：自动解析结果可信度偏低','','## 9. 运势资料','','| 类型 | 内容 | 来源 | 可信度 |','|---|---|---|---|','| 流年 |  |  |  |','| 限度 |  |  |  |','| 倒限 |  |  |  |','| 其他 |  |  |  |','','## 10. 校验结果','','- 七政四余完整性：待校验','- 宫度一致性：待校验','- 命身信息一致性：待校验','- OCR 可疑项：无 OCR；文本仍需人工复核','- 需要用户确认的字段：所有低可信度字段']
    return '\n'.join(out)+'\n'
def main():
    p=argparse.ArgumentParser(); p.add_argument('--input', required=True, type=Path); p.add_argument('--out', default=Path('qz_structured_data.md'), type=Path); a=p.parse_args()
    a.out.write_text(build(a.input.read_text(encoding='utf-8')), encoding='utf-8'); print(f'wrote {a.out}'); return 0
if __name__ == '__main__': raise SystemExit(main())
