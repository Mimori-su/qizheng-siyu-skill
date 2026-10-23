#!/usr/bin/env python3
"""按立命和月柱排阳九限、月限。立春用太阳黄经 315° 定日。"""
import math
import sys
from datetime import datetime, timedelta, timezone

BRANCHES = "子丑寅卯辰巳午未申酉戌亥"
MONTHS = "寅卯辰巳午未申酉戌亥子丑"
MONTH_NAMES = ["正月", "二月", "三月", "四月", "五月", "六月", "七月", "八月", "九月", "十月", "十一月", "十二月"]
CST = timezone(timedelta(hours=8))


def sun_apparent_lon(jd):
    t = (jd - 2451545.0) / 36525.0
    l0 = (280.46646 + 36000.76983 * t + 0.0003032 * t * t) % 360.0
    m = math.radians((357.52911 + 35999.05029 * t - 0.0001537 * t * t) % 360.0)
    c = ((1.914602 - 0.004817 * t - 0.000014 * t * t) * math.sin(m)
         + (0.019993 - 0.000101 * t) * math.sin(2 * m)
         + 0.000289 * math.sin(3 * m))
    return (l0 + c) % 360.0


def julian_day(dt):
    dt = dt.astimezone(timezone.utc)
    y, m = dt.year, dt.month
    d = dt.day + (dt.hour + dt.minute / 60 + dt.second / 3600) / 24
    if m <= 2:
        y -= 1
        m += 12
    a = y // 100
    b = 2 - a + a // 4
    return int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + b - 1524.5


def lichun(year):
    """立春当日 0 时（北京时间）之前最近的交节日。返回 date。"""
    start = datetime(year, 2, 1, tzinfo=CST)
    lo = julian_day(start)
    hi = julian_day(start + timedelta(days=8))
    target = 315.0
    for _ in range(50):
        mid = (lo + hi) / 2
        lon = sun_apparent_lon(mid)
        # 二月上旬太阳黄经从约 310 增到 320，过 315 即立春
        if lon < 180:
            lon += 360
        if lon < target:
            lo = mid
        else:
            hi = mid
    moment = datetime(2000, 1, 1, 12, tzinfo=timezone.utc) + timedelta(days=hi - 2451545.0)
    return moment.astimezone(CST).date()


def branch_of_palace(text):
    # 子宫 / 辰宫
    for ch in text:
        if ch in BRANCHES:
            return ch
    raise ValueError("认不出宫支: " + text)


def lichun_year(d):
    """所在立春年。立春当天起算入当年。"""
    if d < lichun(d.year):
        return d.year - 1
    return d.year


def age_on(birth, query):
    return lichun_year(query) - lichun_year(birth) + 1


def yangjiu(ming, age):
    i = BRANCHES.index(ming)
    return BRANCHES[(i - (age - 1)) % 12]


def month_table(xiaoxian, birth_month):
    start = MONTHS.index(birth_month)
    base = BRANCHES.index(xiaoxian)
    rows = []
    for i, month_branch in enumerate(MONTHS):
        k = (i - start) % 12
        palace = BRANCHES[(base - k) % 12]
        rows.append((MONTH_NAMES[i], month_branch, palace))
    return rows


def solar_month(query):
    """节气月。立春315°起寅，每30°一位。"""
    moment = datetime(query.year, query.month, query.day, 12, tzinfo=CST)
    lon = sun_apparent_lon(julian_day(moment))
    idx = int(((lon - 315.0) % 360.0) // 30.0) % 12
    return MONTHS[idx], MONTH_NAMES[idx]


def main():
    # 立命宫支 月支 出生YYYY-MM-DD 所问YYYY-MM-DD
    ming, birth_month, birth_s, query_s = sys.argv[1:5]
    birth = datetime.strptime(birth_s, "%Y-%m-%d").date()
    query = datetime.strptime(query_s, "%Y-%m-%d").date()
    age = age_on(birth, query)
    palace = yangjiu(branch_of_palace(ming), age)
    q_branch, q_name = solar_month(query)
    print("阳九限: 立春后虚岁%d  小限在%s宫（一岁%s宫，逐年逆行，立春换宫）" % (
        age, palace, branch_of_palace(ming)))
    print("立春: 出生年界 %s  所问年界 %s" % (lichun(lichun_year(birth)), lichun(lichun_year(query))))
    print("月限（小限宫起生月%s，逐月逆退，正月起排）:" % birth_month)
    hit = None
    for name, branch, pal in month_table(palace, birth_month):
        mark = ""
        if branch == q_branch:
            mark = "  ← 所问日在此月"
            hit = pal
        print("  %s（%s月） %s宫%s" % (name, branch, pal, mark))
    print("所问 %s 在%s月（%s），这一月的月限在%s宫" % (query.isoformat(), q_branch, q_name, hit))


if __name__ == "__main__":
    main()
