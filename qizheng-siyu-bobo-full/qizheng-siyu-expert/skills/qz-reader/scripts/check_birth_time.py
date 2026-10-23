#!/usr/bin/env python3
"""Inspect a local birth clock time using IANA data; never choose/correct it silently."""
from datetime import datetime, timezone
import json
import re
import sys
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def check_birth_time(data):
    if not isinstance(data, dict):
        raise ValueError('输入须为 JSON 对象')
    local_text, zone_key = data.get('local_time'), data.get('timezone')
    basis = data.get('time_basis', 'unknown')
    if not isinstance(local_text, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?', local_text):
        raise ValueError('local_time 须为无UTC偏移的当地日期时间，至少精确到分钟')
    local = datetime.fromisoformat(local_text)
    if not isinstance(zone_key, str) or not zone_key:
        raise ValueError('timezone 须为明确的 IANA 时区名')
    if basis not in ('unknown', 'civil', 'standard', 'mean_solar', 'apparent_solar'):
        raise ValueError('未知 time_basis')
    result = dict(local_time=local_text, timezone=zone_key, time_basis=basis,
                  source='Python zoneinfo / installed IANA timezone data',
                  status=None, dst_active=None, confirmation_required=True,
                  candidates=[], prompt=None)
    if basis not in ('unknown', 'civil'):
        result.update(status='basis_requires_review', prompt='这是已校正时间。请核对原始钟表时间，以及是否已处理夏令时、经度差和均时差；不要重复校正。')
        return result
    try:
        zone = ZoneInfo(zone_key)
    except (ZoneInfoNotFoundError, ValueError):
        result.update(status='timezone_unknown', prompt='无法核验该出生地的历史时区，请确认地点与时制资料；不能据此认定没有夏令时。')
        return result

    candidates = {}
    for fold in (0, 1):
        aware = local.replace(tzinfo=zone, fold=fold)
        utc = aware.astimezone(timezone.utc)
        back = utc.astimezone(zone)
        # A gap maps back to another wall time; a fold has two distinct UTCs.
        if back.replace(tzinfo=None) != local:
            continue
        candidates[utc] = dict(local=back.isoformat(), utc=utc.isoformat(),
                               utc_offset_seconds=int(back.utcoffset().total_seconds()),
                               dst_seconds=int(back.dst().total_seconds()),
                               fold=back.fold, abbreviation=back.tzname())
    result['candidates'] = [candidates[k] for k in sorted(candidates)]
    count = len(candidates)
    result['status'] = 'nonexistent' if count == 0 else 'ambiguous' if count == 2 else 'unique'
    result['dst_active'] = any(x['dst_seconds'] != 0 for x in candidates.values()) if count else None
    result['confirmation_required'] = count != 1 or result['dst_active'] or basis == 'unknown'
    if count == 0:
        result['prompt'] = '这个当地钟表时间处于拨快后的缺口，按该历史时区没有对应时刻。请核对原始出生记录和是否已作时间校正。'
    elif count == 2:
        result['prompt'] = '这个当地钟表时间在换表时出现了两次，请确认是换表前还是换表后，并确认记录是否已扣除夏令时；不确定时保留两个候选。'
    elif result['dst_active']:
        result['prompt'] = '出生地当时存在夏令时或季节性时制调整。请确认所填时间是当时钟表显示的时间，还是已经扣除夏令时／换算为太阳时的时间；不确定也请说明。确认后再定时辰。'
    elif basis == 'unknown':
        result['prompt'] = '请确认所填时间是当时出生地的钟表时间，还是已经调整过的标准时间／太阳时；当前UTC仅是按钟表时间计算的待确认候选。'
    # For unknown basis these are conditional civil-clock candidates, not a confirmed birth instant.
    result['interpretation'] = '按当地钟表时间核验；time_basis=unknown 时仅为待确认假设。'
    return result


def main():
    try:
        result = check_birth_time(json.load(sys.stdin))
    except (ValueError, TypeError, OverflowError) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
