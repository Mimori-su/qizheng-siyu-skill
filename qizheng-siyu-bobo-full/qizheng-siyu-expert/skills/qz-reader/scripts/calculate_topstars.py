#!/usr/bin/env python3
"""Evaluate supplied coordinates using the adopted top-star method.

JSON in on stdin, JSON out on stdout; no ephemeris, limit interpolation or files.
The input and the meaning of the 29/1 exception are in topstar_query.md.
"""
import copy
from datetime import datetime
from fractions import Fraction
import json
import math
import sys

STARS = tuple('日月金木水火土计罗炁孛')
METHOD = 'palace-degree-29-1-v1'


def text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{label}须为非空字符串。')
    return value


def number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{label}须为有限数值。')
    return value


def instant(value, label):
    raw = text(value, label)
    try:
        dt = datetime.fromisoformat(raw.replace('Z', '+00:00'))
    except ValueError:
        raise ValueError(f'{label}须为带时区的ISO日期时间。') from None
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(f'{label}必须明确时区偏移。')
    return dt


def scan(group, label, at, center_degree, width):
    if group is None:
        return {'status': 'not_provided', 'checked': [], 'hits': [], 'missing_stars': list(STARS)}
    text(group['source'], f'{label}.source')
    if label == 'transit' and instant(group['at'], 'transit.at') != at:
        raise ValueError('流曜时刻必须与查询时刻一致。')
    if not isinstance(group['stars'], list):
        raise ValueError(f'{label}.stars须为列表。')
    checked, seen = [], set()
    for star in group['stars']:
        name = star['name']
        if name not in STARS:
            raise ValueError('只接受日月金木水火土计罗炁孛十一曜；本命／流曜由分栏区分。')
        if name in seen:
            raise ValueError(f'{label}中星名重复。')
        seen.add(name)
        longitude = Fraction(str(number(star['longitude_deg'], f'{label}.longitude_deg'))) % 360
        degree = longitude % 30
        delta = degree - center_degree
        regular = abs(delta) <= width
        boundary = ((center_degree >= 29.0 and degree < 1.0)
                    or (degree >= 29.0 and center_degree < 1.0))
        reasons = (['regular_window'] if regular else []) + (['boundary_29_1'] if boundary else [])
        checked.append({'name': name, 'longitude_deg': float(longitude), 'palace_degree': float(degree),
                        'delta_deg': float(delta), 'hit': bool(reasons), 'hit_reasons': reasons,
                        'boundary_only': boundary and not regular})
    checked.sort(key=lambda item: item['longitude_deg'])
    return {'status': 'complete' if len(seen) == len(STARS) else 'partial',
            'checked': checked, 'hits': [item for item in checked if item['hit']],
            'missing_stars': [name for name in STARS if name not in seen]}


def calculate_topstars(data):
    """Return candidates for this instant; preserve all supplied provenance."""
    text(data['chart_version'], 'chart_version')
    text(data['coordinate_profile'], 'coordinate_profile')
    if data['coordinate_system'] != '郑氏星案恒星制':
        raise ValueError('本入口只接受同一坐标基准的郑氏星案恒星制黄经。')
    at = instant(data['at'], 'at')
    center, limit = data['center'], data['limit']
    text(center['source'], 'center.source')
    text(limit['source'], 'limit.source')
    if instant(center['at'], 'center.at') != at:
        raise ValueError('行度中心必须来自查询时刻；不能用年初或别时点中心代替。')
    # Rational arithmetic preserves decimal endpoints under 30-degree shifts;
    # no extra tolerance is added to either the window or the 29/1 exception.
    center_degree = Fraction(str(number(center['longitude_deg'], 'center.longitude_deg'))) % 360 % 30
    years = number(limit['years'], 'limit.years')
    if years <= 0:
        raise ValueError('限年数必须大于0。')
    width = Fraction(15) / Fraction(str(years))
    if not math.isfinite(width):
        raise ValueError('限年数过小，不能产生有限半宽。')
    return {
        'meta': {'method': METHOD, 'scope': 'instant_candidates',
                 'basis': '宫内度比较；半宽15/限年数；29/1边界独立判断'},
        'input': copy.deepcopy(data),
        'half_width_deg': float(width),
        'center_palace_degree': float(center_degree),
        'natal': scan(data.get('natal'), 'natal', at, center_degree, width),
        'transit': scan(data.get('transit'), 'transit', at, center_degree, width),
    }


def main():
    try:
        result = calculate_topstars(json.load(sys.stdin))
        print(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2))
    except (ValueError, KeyError, TypeError, OverflowError) as exc:
        print(f'topstars: 输入不完整或不一致（{exc}）', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
