#!/usr/bin/env python3
"""Query eleven Zheng Case Sidereal transits; stdout only, no interpretation."""
import argparse
from datetime import datetime, timezone
from functools import lru_cache
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import sys


BODIES = ('sun', 'moon', 'venus', 'jupiter', 'mercury', 'mars', 'saturn', 'keti', 'rahu', 'qi', 'bei')
NAMES = tuple('日月金木水火土计罗炁孛')
BRANCHES = tuple('子丑寅卯辰巳午未申酉戌亥')
PALACE_NAMES = ('命宫', '财帛', '兄弟', '田宅', '男女', '奴仆', '夫妻', '疾厄', '迁移', '官禄', '福德', '相貌')
PROFILES = {
    'moira_sidereal': ('SIDEREAL_STELLAR_BOUNDARIES', '郑案原脚本默认宿界'),
    'xhcl_original': ('XHCL_ORIG_BOUNDARIES', '备选宿界A宿界'),
    'xhcl_revised': ('XHCL_REVISED_BOUNDARIES', '备选宿界B宿界'),
}
ENGINE_PATH = Path(__file__).resolve().parent / 'vendor/equatorial_stellar.py'


@lru_cache(maxsize=1)
def load_engine():
    spec = importlib.util.spec_from_file_location('_qz_transit_engine', ENGINE_PATH)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except ModuleNotFoundError as exc:
        raise RuntimeError('缺少排盘依赖，请在专用 Python 环境安装 scripts/transit_requirements.txt。') from exc
    return module


def parse_instant(value):
    if not isinstance(value, str) or not re.match(r'^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?=[:+Z-]|$)', value):
        raise ValueError('请给完整日期、时分与时区，例如 2026-10-09T01:16:00+08:00。')
    try:
        instant = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError('日期或时区无效，请使用 ISO 日期时间。') from exc
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError('必须明确时区；北京时间在末尾加 +08:00。')
    try:
        utc = instant.astimezone(timezone.utc)
    except OverflowError as exc:
        raise ValueError('转换 UTC 后超出日期范围。') from exc
    if not 1583 <= utc.year <= 2999:
        raise ValueError('此流曜入口仅接受公历 1583–2999 年；历史历法须另行核验。')
    return instant, utc


def palace_position(longitude):
    if not math.isfinite(longitude):
        raise ValueError('星位必须是有限数值。')
    longitude %= 360.0
    engine = load_engine()
    return {'branch': engine.get_zodiac(longitude), 'palace_degree': engine.degree_in_zodiac(longitude)}


def validate_natal(natal):
    if natal is None:
        return {b: {'name': None, 'natal_stars': None} for b in BRANCHES}
    if not isinstance(natal, dict) or not isinstance(natal.get('palaces'), dict):
        raise ValueError('本命映射须为含 palaces 对象的 JSON。')
    if set(natal['palaces']) != set(BRANCHES):
        raise ValueError('本命映射须包含十二地支各一次，不从流年重新安命。')
    result, seen_names, seen_stars = {}, set(), set()
    for branch in BRANCHES:
        item = natal['palaces'][branch]
        if not isinstance(item, dict):
            raise ValueError(f'{branch}宫须包含 name，可另给 natal_stars。')
        name = item.get('name')
        if name not in PALACE_NAMES or name in seen_names:
            raise ValueError(f'{branch}宫人事宫名无效或重复；须使用十二宫规范名称。')
        seen_names.add(name)
        stars = item.get('natal_stars')
        if stars is not None:
            if not isinstance(stars, list) or any(not isinstance(s, str) for s in stars):
                raise ValueError(f'{branch}宫 natal_stars 须为星曜简称数组；未知时省略或 null。')
            stars = ['炁' if s == '气' else s for s in stars]
            if any(s not in NAMES or s in seen_stars for s in stars) or len(set(stars)) != len(stars):
                raise ValueError('本命宫内星含非十一曜或重复星曜。')
            seen_stars.update(stars)
        result[branch] = {'name': name, 'natal_stars': stars}
    if all(p['natal_stars'] is not None for p in result.values()) and seen_stars != set(NAMES):
        raise ValueError('十二宫均已明示宫内星时，十一曜须齐全；未提供的宫内星请用 null。')
    return result


def resolve_focus(focus, palaces):
    result = []
    for value in focus:
        if value in BRANCHES:
            branch = value
        else:
            found = [b for b, p in palaces.items() if p['name'] == value]
            if not found:
                raise ValueError(f'无法定位重点宫位：{value}。人事宫名需要完整本命映射。')
            branch = found[0]
        if branch not in result:
            result.append(branch)
    return result


def calculate_snapshot(at, *, natal=None, focus=(), mansion_profile='moira_sidereal', apogee='mean'):
    instant, utc = parse_instant(at)
    if mansion_profile not in PROFILES:
        raise ValueError('未知宿界方案。')
    if apogee not in ('mean', 'true'):
        raise ValueError('月孛口径只能是 mean 或 true。')
    palaces = validate_natal(natal)
    focus_branches = resolve_focus(focus, palaces)
    engine = load_engine()
    profile_constant, profile_label = PROFILES[mansion_profile]
    chart = engine.ZhengCaseSidereal(boundaries=getattr(engine, profile_constant), use_true_apog=apogee == 'true')
    hour = utc.hour + utc.minute / 60 + (utc.second + utc.microsecond / 1e6) / 3600
    jd = engine.swe_julday(utc.year, utc.month, utc.day, hour, tz=0)
    stars = []
    for palace in palaces.values():
        palace['transit_stars'] = []
    for body, name in zip(BODIES, NAMES):
        longitude = engine._engine_pos(body, jd, chart)[0] % 360.0
        # All eleven use the same sidereal-position derivative, including qi.
        # Do not reuse the legacy API that labels every auxiliary body direct.
        before = engine._engine_pos(body, jd - 0.005, chart)[0]
        after = engine._engine_pos(body, jd + 0.005, chart)[0]
        speed = ((after - before + 180.0) % 360.0 - 180.0) / 0.01
        if not all(math.isfinite(x) for x in (longitude, speed)):
            raise RuntimeError(f'{name}星计算返回非有限数值。')
        location = palace_position(longitude)
        branch = location['branch']
        star = {
            'name': name, 'body': body, 'sidereal_longitude': longitude,
            **location, 'natal_palace': palaces[branch]['name'],
            'mansion': chart.get_mansion(longitude, full=True),
            'mansion_element': chart.get_mansion_element(longitude),
            'mansion_degree': chart.degree_within_mansion(longitude),
            'speed_deg_per_day': speed, 'is_retrograde': speed < 0,
        }
        stars.append(star)
        palaces[branch]['transit_stars'].append(name)
    return {
        'meta': {
            'schema_version': 1, 'system': '郑氏星案恒星制', 'coordinate': 'sidereal_ecliptic_longitude',
            'scope': 'instant_snapshot', 'at': instant.isoformat(), 'at_utc': utc.isoformat(), 'jd_ut': jd,
            'calendar': 'Gregorian', 'mansion_profile': mansion_profile, 'mansion_profile_label': profile_label,
            'apogee': apogee, 'node_definition': '计=真北交点，罗=对点（沿用来源引擎）',
            'engine_sha256': hashlib.sha256(ENGINE_PATH.read_bytes()).hexdigest(),
            'ephemeris_version': str(engine._swe.version),
            'motion_basis': '恒星黄经中心差分；仅给速度与逆行，不推断迟留伏蚀或旺衰',
        },
        'stars': stars, 'palaces': palaces, 'focus_branches': focus_branches,
    }


def to_markdown(snapshot):
    meta = snapshot['meta']
    lines = ['# 郑氏星案恒星制｜流曜快照', '',
             f"时刻：{meta['at']}；宿界：{meta['mansion_profile_label']}；月孛：{meta['apogee']}。",
             '本表仅对应所列时刻；人事宫位沿用本命，不重新安命。', '',
             '| 流曜 | 地支 | 本命人事宫 | 宫内度 | 躔宿 | 宿内度 | 恒星黄经速度（度/日） | 方向 |',
             '|---|---|---|---:|---|---:|---:|---|']
    for s in snapshot['stars']:
        # Fixed decimals can display 30.00000 at a boundary; labels always use raw coordinates.
        degree = f"{s['palace_degree']:.5f}"
        if degree == '30.00000':
            degree = '<30.00000'
        lines.append(f"| {s['name']} | {s['branch']} | {s['natal_palace'] or '未映射'} | {degree} | "
                     f"{s['mansion']} | {s['mansion_degree']:.5f} | {s['speed_deg_per_day']:.6f} | "
                     f"{'逆' if s['is_retrograde'] else '顺'} |")
    focus = snapshot['focus_branches'] or list(BRANCHES)
    lines += ['', '## 重点本命宫位叠入' if snapshot['focus_branches'] else '## 十二宫叠入', '',
              '| 地支 | 本命人事宫 | 本命宫内星 | 该时刻流曜 |', '|---|---|---|---|']
    for branch in focus:
        p = snapshot['palaces'][branch]
        natal = '未知' if p['natal_stars'] is None else ('、'.join(p['natal_stars']) or '无')
        lines.append(f"| {branch} | {p['name'] or '未映射'} | {natal} | {'、'.join(p['transit_stars']) or '无'} |")
    lines += ['', '运动方向来自该时刻计算；迟留伏、垣殿旺衰、交感、神煞及吉凶由后续模块另行核验。', '']
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description='只查询郑氏星案恒星制十一曜，并叠入本命十二宫；默认只输出到终端。')
    parser.add_argument('--at', required=True, help='带时区的日期时间，如 2026-10-09T01:16:00+08:00')
    parser.add_argument('--natal', help='本命宫位映射 JSON；- 表示从标准输入读取，不保存案例')
    parser.add_argument('--focus', action='append', default=[], help='重点地支或本命人事宫，可重复指定')
    parser.add_argument('--mansion-profile', choices=PROFILES, default='moira_sidereal')
    parser.add_argument('--apogee', choices=('mean', 'true'), default='mean')
    parser.add_argument('--format', choices=('json', 'md'), default='json')
    args = parser.parse_args(argv)
    try:
        natal = None
        if args.natal == '-':
            natal = json.load(sys.stdin)
        elif args.natal:
            natal = json.loads(Path(args.natal).read_text(encoding='utf-8'))
        snapshot = calculate_snapshot(args.at, natal=natal, focus=args.focus,
                                      mansion_profile=args.mansion_profile, apogee=args.apogee)
        print(json.dumps(snapshot, ensure_ascii=False, indent=2, allow_nan=False) if args.format == 'json'
              else to_markdown(snapshot))
    except (ValueError, OSError, RuntimeError) as exc:
        parser.exit(2, f'流曜查询失败：{exc}\n')


if __name__ == '__main__':
    sys.dont_write_bytecode = True
    main()
