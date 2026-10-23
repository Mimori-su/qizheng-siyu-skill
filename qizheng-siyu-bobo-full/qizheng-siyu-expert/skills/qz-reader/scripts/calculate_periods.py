#!/usr/bin/env python3
"""Calculate teacher-defined annual/flying/solar-month limits, stdout only."""
import argparse
import copy
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import importlib.util
import json
import math
from pathlib import Path
import sys

sys.dont_write_bytecode = True
_spec = importlib.util.spec_from_file_location(
    '_qz_period_transits', Path(__file__).with_name('calculate_transits.py'))
transits = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(transits)

BRANCHES = transits.BRANCHES
MONTH_BRANCHES = tuple('寅卯辰巳午未申酉戌亥子丑')
TERMS = ('立春', '惊蛰', '清明', '立夏', '芒种', '小暑', '立秋', '白露', '寒露', '立冬', '大雪', '小寒')
LORDS = dict(zip(BRANCHES, '土土木火金水日月水金火木'))
MANSIONS = dict(zip('角亢氐房心尾箕斗牛女虚危室壁奎娄胃昴毕觜参井鬼柳星张翼轸',
                    '木金土日月火水木金土日月火水木金土日月火水木金土日月火水'))
CST = timezone(timedelta(hours=8))
FLIGHT_CONVENTION = '交宫当下为第1年，下一立春第2年；六年循环。此起算边界为程序约定。'


def integer(value, name, low, high):
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ValueError(f'{name}须为{low}–{high}之间的整数。')
    return value


def branch_index(branch):
    if branch not in BRANCHES:
        raise ValueError('须提供有效地支。')
    return BRANCHES.index(branch)


def instant(value):
    return transits.parse_instant(value)[0].astimezone(CST)


@lru_cache(maxsize=2048)
def term_time(solar_year, month_number):
    """Apparent tropical solar longitude; canonical boundaries at 1s resolution."""
    integer(solar_year, '立春年度', 1584, 2999)
    integer(month_number, '节气月序', 1, 12)
    year, month = (solar_year, month_number + 1) if month_number < 12 else (solar_year + 1, 1)
    engine = transits.load_engine()
    lo = engine.swe_julday(year, month, 1, 0, tz=8)
    hi = engine.swe_julday(year, month, 12, 0, tz=8)
    target = (315 + (month_number - 1) * 30) % 360

    def delta(jd):
        return (engine._swe.calc_ut(jd, engine._swe.SUN, 0)[0][0] - target + 540) % 360 - 180

    if not delta(lo) < 0 < delta(hi):
        raise RuntimeError('节气搜索窗口未包住交节点，不能输出推测月份。')
    for _ in range(50):
        mid = (lo + hi) / 2
        if delta(mid) < 0:
            lo = mid
        else:
            hi = mid
    # The displayed boundary is also the exact program boundary, never a
    # rounded display that would classify itself back into the preceding month.
    seconds = math.ceil((((lo + hi) / 2) - 2440587.5) * 86400)
    return (datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=seconds)).astimezone(CST)


def solar_month(at):
    dt = instant(at)
    if not 1584 <= dt.year <= 2999:
        raise ValueError('节气入口仅支持1584–2998立春年度。')
    year = dt.year if dt >= term_time(dt.year, 1) else dt.year - 1
    integer(year, '立春年度', 1584, 2998)
    bounds = [term_time(year, n) for n in range(1, 13)] + [term_time(year + 1, 1)]
    n = next(i for i in range(12) if bounds[i] <= dt < bounds[i + 1])
    return {'solar_year': year, 'month_number': n + 1, 'month_branch': MONTH_BRANCHES[n],
            'start': bounds[n].isoformat(), 'end': bounds[n + 1].isoformat(),
            'start_term': TERMS[n], 'end_term': TERMS[(n + 1) % 12]}


def xiaoxian_branch(ming_branch, birth_solar_year, target_solar_year):
    idx = branch_index(ming_branch)
    integer(birth_solar_year, '出生立春年度', 1584, 2998)
    integer(target_solar_year, '目标立春年度', 1584, 2998)
    if target_solar_year < birth_solar_year:
        raise ValueError('目标年度不能早于出生年度。')
    return BRANCHES[(idx - (target_solar_year - birth_solar_year)) % 12]


def yuexian_branch(xiao_branch, birth_month_number, target_month_number):
    idx = branch_index(xiao_branch)
    integer(birth_month_number, '出生节气月序', 1, 12)
    integer(target_month_number, '目标节气月序', 1, 12)
    return BRANCHES[(idx - (target_month_number - birth_month_number)) % 12]


def feixian_branch(base_branch, year_number):
    idx = branch_index(base_branch)
    integer(year_number, '飞限年序', 1, 10000)
    cycle = (year_number - 1) % 6 + 1
    if cycle <= 2:
        offset = 0
    elif cycle <= 4:
        offset = 6
    else:
        offset = (4 if cycle == 5 else 8) * (1 if idx % 2 == 0 else -1)
    return BRANCHES[(idx + offset) % 12]


def prepare_chart(chart):
    if not isinstance(chart, dict):
        raise ValueError('输入须为本命资料对象。')
    birth = instant(chart.get('birth_at'))
    birth_month = solar_month(birth.isoformat())
    if chart.get('birth_month_branch') is not None and chart['birth_month_branch'] != birth_month['month_branch']:
        raise ValueError('给定出生月支与交节计算不一致，请核对出生时间和月柱来源。')
    palaces = transits.validate_natal(chart)
    ming = next(b for b, p in palaces.items() if p['name'] == '命宫')
    for i, name in enumerate(transits.PALACE_NAMES):
        b = BRANCHES[(branch_index(ming) - i) % 12]
        if palaces[b]['name'] != name:
            raise ValueError('本命十二宫宫序不一致；须由命宫按命财兄田等宫序逐支逆行。')
    for b, p in palaces.items():
        raw = chart['palaces'][b]
        for field in ('shensha', 'annual_shensha', 'source'):
            p[field] = copy.deepcopy(raw.get(field))
        if p['shensha'] is not None and (not isinstance(p['shensha'], list) or any(not isinstance(x, str) for x in p['shensha'])):
            raise ValueError('本命神煞须为字符串列表或null。')
        annual = p['annual_shensha']
        if annual is not None and (not isinstance(annual, dict) or any(
                not isinstance(k, str) or not k.isdigit() or not isinstance(v, list)
                or any(not isinstance(x, str) for x in v) for k, v in annual.items())):
            raise ValueError('流年神煞须为年份字符串到字符串列表的映射。')
    schedules = {}
    for key, field in (('palace_limits', 'branch'), ('degree_limits', 'mansion')):
        rows = chart.get(key, [])
        if not isinstance(rows, list):
            raise ValueError(f'{key}须为按起始时间递增的列表。')
        parsed, previous = [], None
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError(f'{key}条目须为对象。')
            start = instant(row.get('start'))
            solar_month(start.isoformat())
            data = copy.deepcopy(row)
            if (start < birth and key == 'palace_limits' and not parsed
                    and row.get('branch') == ming and row.get('start_precision') == 'hour'
                    and start == birth.replace(minute=0, second=0, microsecond=0)):
                data['source_start'] = row['start']
                data['normalization'] = '首命宫限原文仅精确至小时，同出生小时；补齐为出生时刻。'
                start = birth
            if start < birth or (previous is not None and start <= previous):
                raise ValueError('限表不可早于出生，且须严格递增；不自动重排。')
            value = row.get(field)
            if field == 'branch':
                branch_index(value)
            elif not isinstance(value, str) or value[:1] not in MANSIONS or value not in (value[:1], value[:1] + MANSIONS[value[:1]]):
                raise ValueError('度限须为合法宿名或带属性全名，如斗或斗木。')
            parsed.append({'start_dt': start, 'data': {**data, 'start': start.isoformat()}})
            previous = start
        schedules[key] = parsed
    cutoff = instant(chart['limits_valid_until']) if chart.get('limits_valid_until') is not None else None
    if cutoff is not None and (cutoff <= birth or any(r['start_dt'] >= cutoff for rows in schedules.values() for r in rows)):
        raise ValueError('限表有效截止须晚于出生及所有已给起限时刻。')
    details = copy.deepcopy(chart.get('natal_star_details', {}))
    if not isinstance(details, dict) or any(k not in transits.NAMES or not isinstance(v, dict) for k, v in details.items()):
        raise ValueError('逐星原始资料须为十一曜简称到资料对象的映射。')
    return {'birth': birth, 'birth_month': birth_month, 'ming': ming, 'palaces': palaces,
            **schedules, 'cutoff': cutoff, 'details': details}


def active_limit(dt, rows, cutoff):
    if cutoff is not None and dt >= cutoff:
        return None
    index = next((i for i in range(len(rows) - 1, -1, -1) if rows[i]['start_dt'] <= dt), None)
    if index is None:
        return None
    end = rows[index + 1]['start_dt'] if index + 1 < len(rows) else cutoff
    return {**copy.deepcopy(rows[index]['data']), 'end': end.isoformat() if end else None,
            'coverage': '有明确截止' if end else '未提供下一交限，按已给末项延续',
            'source_type': 'user_supplied_schedule'}


def at_prepared(at, prepared, include_transits, mansion_profile, apogee):
    dt = instant(at)
    if dt < prepared['birth']:
        raise ValueError('查询时刻不能早于出生。')
    month = solar_month(dt.isoformat())
    year = month['solar_year']
    xiao = xiaoxian_branch(prepared['ming'], prepared['birth_month']['solar_year'], year)
    yue = yuexian_branch(xiao, prepared['birth_month']['month_number'], month['month_number'])

    def location(branch, lord=False):
        p = prepared['palaces'][branch]
        out = {'branch': branch, 'name': p['name'], 'natal_stars': copy.deepcopy(p['natal_stars']),
               'shensha': copy.deepcopy(p['shensha']),
               'annual_shensha': copy.deepcopy((p['annual_shensha'] or {}).get(str(year))),
               'source': copy.deepcopy(p['source']), 'transit_stars': None}
        if lord:
            out['lord'] = LORDS[branch]
        return out

    palace = active_limit(dt, prepared['palace_limits'], prepared['cutoff'])
    degree = active_limit(dt, prepared['degree_limits'], prepared['cutoff'])
    flight = None
    if palace:
        palace['name'] = prepared['palaces'][palace['branch']]['name']
        number = year - solar_month(palace['start'])['solar_year'] + 1
        flight = {**location(feixian_branch(palace['branch'], number)), 'year_number': number,
                  'cycle_year': (number - 1) % 6 + 1, 'base_branch': palace['branch']}
    out = {'meta': {'schema_version': 1, 'at': dt.isoformat(), 'timezone': 'UTC+08:00',
                    'scope': 'instant_limits', 'solar_year': year, 'birth_solar_month': prepared['birth_month'],
                    'source': '老师确认的小限／月限公式与飞限六年循环',
                    'flight_entry_convention': FLIGHT_CONVENTION,
                    'term_method': '太阳回归黄经315°起每30°；Swiss Ephemeris；向上取整到秒作为计算及显示边界',
                    'interval_convention': '左闭右开；出生之前不计算',
                    'missing': [label for label, data in (('宫限', palace), ('度限', degree)) if data is None]},
           'solar_month': month, 'palace_limit': palace, 'degree_limit': degree,
           'xiaoxian': location(xiao, lord=True), 'yuexian': location(yue), 'feixian': flight,
           'natal_star_details': copy.deepcopy(prepared['details']), 'transit_snapshot': None}
    if include_transits:
        focus = list(dict.fromkeys(p['branch'] for p in (out['xiaoxian'], out['yuexian'], flight) if p))
        snapshot = transits.calculate_snapshot(dt.isoformat(), natal={'palaces': prepared['palaces']},
                                             focus=focus, mansion_profile=mansion_profile, apogee=apogee)
        out['transit_snapshot'] = snapshot
        for key in ('xiaoxian', 'yuexian', 'feixian'):
            if out[key]:
                out[key]['transit_stars'] = list(snapshot['palaces'][out[key]['branch']]['transit_stars'])
                out[key]['transit_at'] = dt.isoformat()
    return out


def validate_options(mansion_profile, apogee):
    if mansion_profile not in transits.PROFILES or apogee not in ('mean', 'true'):
        raise ValueError('未知宿界或月孛口径。')


def calculate_at(at, chart, *, include_transits=False, mansion_profile='moira_sidereal', apogee='mean'):
    validate_options(mansion_profile, apogee)
    if not isinstance(include_transits, bool):
        raise ValueError('include_transits须为布尔值。')
    return at_prepared(at, prepare_chart(chart), include_transits, mansion_profile, apogee)


def calculate_year(year, chart, *, sample_times=(), mansion_profile='moira_sidereal', apogee='mean'):
    integer(year, '立春年度', 1584, 2998)
    validate_options(mansion_profile, apogee)
    prepared = prepare_chart(chart)
    start, end = term_time(year, 1), term_time(year + 1, 1)
    if prepared['birth'] >= end:
        raise ValueError('查询年度早于出生。')
    start = max(start, prepared['birth'])
    bounds = {start, end}
    bounds.update(term_time(year, n) for n in range(1, 13) if start < term_time(year, n) < end)
    for key in ('palace_limits', 'degree_limits'):
        bounds.update(r['start_dt'] for r in prepared[key] if start < r['start_dt'] < end)
    if prepared['cutoff'] is not None and start < prepared['cutoff'] < end:
        bounds.add(prepared['cutoff'])
    boundaries = sorted(bounds)
    segments = [{**at_prepared(a.isoformat(), prepared, False, mansion_profile, apogee),
                 'start': a.isoformat(), 'end': b.isoformat()}
                for a, b in zip(boundaries, boundaries[1:])]
    if not isinstance(sample_times, (list, tuple)):
        raise ValueError('sample_times须为时刻列表。')
    snapshots = []
    for at in sample_times:
        if not start <= instant(at) < end:
            raise ValueError('流曜样本须落在该立春年度且不早于出生。')
        snapshots.append(at_prepared(at, prepared, True, mansion_profile, apogee))
    return {'meta': {'schema_version': 1, 'scope': 'solar_year_segments', 'solar_year': year,
                     'start': start.isoformat(), 'end': end.isoformat(), 'timezone': 'UTC+08:00',
                     'flight_entry_convention': FLIGHT_CONVENTION,
                     'transit_scope': '仅显式采样时刻；不将快照视作全年／整月常驻星'},
            'segments': segments, 'snapshots': snapshots}


def _stars(stars):
    return '未知' if stars is None else ('、'.join(stars) or '无')


def _place(p):
    return '未提供' if p is None else f"{p['branch']}·{p['name']}（{_stars(p['natal_stars'])}）"


def _escape(value):
    return str(value).replace('|', '\\|').replace('\n', '<br>')


def to_markdown(result):
    lines = ['# 小限、飞限与节气月限', '', '日期均为北京时间（UTC+08:00）；区间含起点，不含终点，交节切换。',
             '节气边界统一向上取整至秒；星位仍使用郑氏星案恒星制。', '', FLIGHT_CONVENTION, '']
    if 'segments' in result:
        lines += [f"## {result['meta']['solar_year']}立春年度", '',
                  '| 起始日期时间 | 截止日期时间 | 节气月 | 宫限／度限 | 小限·本命星 | 飞限·本命星 | 月限·本命星 |',
                  '|---|---|---|---|---|---|---|']
        for s in result['segments']:
            p, d = s['palace_limit'], s['degree_limit']
            limits = (p['branch'] + '·' + p['name'] if p else '宫限未提供') + '／' + (d['mansion'] if d else '度限未提供')
            vals = [s['start'], s['end'], s['solar_month']['month_branch'] + '月·' + s['solar_month']['start_term'],
                    limits, _place(s['xiaoxian']), _place(s['feixian']), _place(s['yuexian'])]
            lines.append('| ' + ' | '.join(_escape(v) for v in vals) + ' |')
        lines += ['', '本表宫内星为本命守星；流曜只见下列明确采样时刻。神煞及逐星资料见结构化输出。']
        for snapshot in result['snapshots']:
            lines += ['', to_markdown(snapshot)]
    else:
        month = result['solar_month']
        lines += [f"时点：{result['meta']['at']}",
                  f"{month['month_branch']}月：{month['start_term']} {month['start']} → {month['end_term']} {month['end']}", '',
                  '| 限别 | 本命宫位与守星 | 宫主／飞限年序 | 本命神煞 | 本年神煞 | 该时刻流曜 |', '|---|---|---|---|---|---|']
        for key, label in (('xiaoxian', '小限'), ('feixian', '飞限'), ('yuexian', '月限')):
            p = result[key]
            qualifier = p.get('lord', f"第{p['year_number']}年／循环第{p['cycle_year']}年" if key == 'feixian' else '—') if p else '—'
            vals = [label, _place(p), qualifier, _stars(p['shensha']) if p else '未知',
                    _stars(p['annual_shensha']) if p else '未知', _stars(p['transit_stars']) if p else '未知']
            lines.append('| ' + ' | '.join(_escape(v) for v in vals) + ' |')
        if result['transit_snapshot']:
            lines += ['', transits.to_markdown(result['transit_snapshot'])]
    lines += ['', '只补定位与星曜资料，不由此直接作吉凶判断；按原局、宫限、度限及交感继续解读。', '']
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description='补算小限、飞限、节气月限；仅读取输入并输出，不保存客户命盘。')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--at', help='带时区的公历查询时刻')
    group.add_argument('--year', type=int, help='立春年度')
    parser.add_argument('--input', default='-', help='资料JSON；默认-从标准输入读取')
    parser.add_argument('--transits', action='store_true', help='仅--at：附该时刻十一曜')
    parser.add_argument('--sample', action='append', default=[], help='仅--year：附指定时刻流曜，可重复')
    parser.add_argument('--mansion-profile', choices=transits.PROFILES, default='moira_sidereal')
    parser.add_argument('--apogee', choices=('mean', 'true'), default='mean')
    parser.add_argument('--format', choices=('json', 'md'), default='json')
    args = parser.parse_args(argv)
    if (args.transits and args.at is None) or (args.sample and args.year is None):
        parser.error('--transits仅配--at，--sample仅配--year。')
    try:
        chart = json.load(sys.stdin) if args.input == '-' else json.loads(Path(args.input).read_text(encoding='utf-8'))
        options = {'mansion_profile': args.mansion_profile, 'apogee': args.apogee}
        result = calculate_at(args.at, chart, include_transits=args.transits, **options) if args.at else calculate_year(
            args.year, chart, sample_times=args.sample, **options)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) if args.format == 'json' else to_markdown(result))
    except (ValueError, TypeError, OSError, RuntimeError) as exc:
        parser.exit(2, f'三限计算失败：{exc}\n')


if __name__ == '__main__':
    main()
