# -*- coding: utf-8 -*-
"""
恒星制双模式（Equatorial + Zheng Case Sidereal）— Python 实现 v4

基于 Moira (moira_pack20240319赤道恒星) 反编译源码逐行复现，
同时支持：
  1) 郑氏星案恒星制（黄道恒星制）: 行星位置用恒星黄经直接落宿；
  2) 赤道恒星制: 同一 ayanamsa、同一套二十八宿宿界数值，
     但行星位置从【恒星黄道经度】转为【赤道赤经】后再落宿。

v2: 加入四余 —— 计都 / 罗睺 / 紫炁 / 月孛。
v3: 合并郑氏星案恒星制引擎 ZhengCaseSidereal，与赤道制共用
    宿界/格式化/导出/GUI，--test 输出两制对照。
v4 (2026-08-16): 对照 zip 内 moira_proj.jar 逐方法字节码复核 + 用打包 JRE
    实跑 Moira 管线产出黄金参照值, 修复:
    1) 迟逆留速伏阈值错位: Moira 的 stationary/invisible/slow/fast 数组
       按【金木水火土】(行星号 2..6) 索引, 旧映射 金水火木土 导致
       水/火/木 三颗行星阈值互相错位;
    2) 「留」判定整体重写: 判态顺序改为 留→伏→逆→速→迟→顺, 删除自创的
       |speed|<0.5 门控, 对冲日验证条件与 Moira 对齐(冲日在留点之外才判留),
       速度过境搜索半径 120→1000 天;
    3) 日/月「蚀」状态补全 (getEclipseState: 日 ±1h / 月 ±0.5d 窗口,
       地点可见口径, 北京);
    4) 星象日历行星对方向与 Moira 对齐 (过境星体 = swe 行星号大者, 即
       k_body; 参照 = 小者 i_body), 四余不再进入相对过境;
    5) 环境兼容: 精简 swisseph 兼容层(swisseph-ffi)未暴露 revjul 与日月食
       API —— generate_time_points 改用内置 _jd_to_date(修复生成时间点即崩溃),
       日月食检测/蚀状态增加几何近似回退(朔/望+黄纬+地平可见性); 完整
       pyswisseph 路径同时修正 sol_eclipse_when_glob 三元组解包错误;
    6) 历法边界: _jd_to_date 的 Z 与分钟提取改 floor+浮点容差, 修复
       -4712 年附近差一天/一分钟; 儒略 1582-10-05~14 重叠窗按文档化口径
       以格里历显示;
    7) 性能 (全功能导出 51s→2.4s, 逐行 58ms→2.7ms):
       a) 留判定方向修复 (牛顿梯度不分方向, 向后/向前常收敛到同一留点;
          改为方向不符时 15 天步线性扫描+二分, 15 天<最短逆行窗口 23 天);
       b) 留点/冲日过境按日缓存 (同一天 24 个导出行共享搜索结果);
       c) 冲日搜索 0.5 天线性扫描 → 指数扩展括号+二分 (~30 倍);
       d) _engine_pos 回归黄经懒计算 (热路径省一半 calc_ut);
       e) openpyxl 懒加载 (CSV 导出省 ~0.5s); f) 可选 SWIEPH 星历开关。
v5 (2026-08-16): 新增【占星子功能模块】moira_astro (西方占星, 从 moira_proj.jar
    反编译源码提炼): 星座(黄道十二宫, 资源表 ch_house_name)落座、逆行开始/
    结束时刻(computeSpeedTransit→SEFLG_TRANSIT_SPEED 速度过零)、西方相位、
    分宫制接口。文件暂时独立(可单独运行), 本文件经 get_astro() 懒加载,
    并封装 astro_zodiac / astro_retrograde_periods / astro_stations /
    astro_next_station 统一调用; 与主引擎共用 swisseph, sid_mode 由
    _ensure_sid_mode 守卫保证互不污染。
v6 (2026-09-13): 新增【星海词林·量天尺】流年星官模块 (§3b): 360 格
    (12 宫 × 30 区) 逐度星官表嵌入, 子宫第一区锚定天圈 299.0°
    (= 星海词林原版女宿一度整), 星官跟宫度走、与宿界选择无关;
    两制 get_planet_mansion 结果新增 palace/palace_deg/xingguan 字段
    (赤道制按赤经、郑案制按恒星黄经查表); Excel/CSV 导出与 GUI 新增
    「星官(量天尺)」开关; lichun_jd 求立春交节 (太阳回归黄经 315°),
    liunian_xingguan(年) 出立春快照两制对照; CLI 新增 --liunian 年份。

----------------------------------------------------------------------
核心算法（对应 Java 反编译代码）：

  赤道恒星制
    ModeDialog "赤道恒星制" 选项
        → ChartData.use_equ = true  (ChartData.java:463, 4019-4027)
    Calculate.getPlanetEquPos()  (Calculate.java:1122-1126)
        → SwissEph.swe_polar_ecl_to_equ()  (SwissEph.java:272-278)
        用当日【平黄赤交角】(swed.oec.eps, 不含章动) 做坐标旋转:
            RA/Dec = cotrans((恒星黄经, 恒星黄纬), -eps_mean)
        旋转经 swe_cotrans → swi_polcart → swi_coortrf → swi_cartpol
        (SwissLib.java:129-148), 输出赤经自动归化到 [0, 360)。

  郑氏星案恒星制
    直接用 swe.calc_ut(FLG_SIDEREAL) 得到恒星黄经，
    以恒星黄经在 sidereal_stellar_names 宿界中落宿。

  共同宿界 (ChartData.java:4152-4159):
      恒星制模式下宿界 = prop 的 sidereal_stellar_names 数值
      (15.9, 26.3, ..., 358.3)。赤道模式下该数值解释为【赤经度数】
      (中国传统二十八宿距度本为赤道度)；郑氏制下解释为恒星黄道度数。
      落宿查找 getStarSign / 格式化 formatDegree 逻辑完全一致。
      ★ 这组刻度 = 28 颗距星在【锁定校准历元】钉在天球的位置, 每颗距星即
        所在宿的宿度 0; 宿界一旦锁定便永不随历元重算/移动(同圈同刻度,
        两制只是坐标口径不同: 赤道制=赤经, 郑案制=恒星黄经)。

依赖:
    pip install swisseph   (Anaconda 已预装)

用法:
    zcs = ZhengCaseSidereal()
    r = zcs.get_planet_mansion("moon", 2026, 7, 10, 12)
    print(r["mansion_formatted"])   # → 黄道恒星落宿

    eqs = EquatorialStellar()
    r = eqs.get_planet_mansion("moon", 2026, 7, 10, 12)
    print(r["mansion_formatted"])   # → 赤经落宿
    print(r["ra"], r["dec"])        # 赤经 / 赤纬

作者: 基于 Moira (At Home Projects, 2004-2015) Java 反编译源码
"""

import math
import threading
import queue

# =====================================================================
# 1. Swiss Ephemeris 引擎
# =====================================================================

import swisseph as _swe

# J2000 平黄赤交角：从 quasi_ecliptic 取（IAU 2006 规范值，单一真源）。
# 本文件其余地方一律用 swe_mean_obliquity(jd) 取"当日"值，不必再存常数。
try:
    from quasi_ecliptic import J2000_OBLIQUITY as _J2000_OBLIQUITY
except ImportError:      # 单独拷走本文件运行时兜底
    _J2000_OBLIQUITY = 23.439281339

# ★性能/精度开关 (2026-08-16): 内置 .se1 星历 (SWIEPH)。
# 默认 False = 与旧环境行为完全一致 (Moshier 历表);
# True 时启用兼容层自带的官方 .se1 文件:
#   - 月亮等重扫描提速 ~3.6× (月亮 20 年 4.2s → 1.2s; 入宿/落宿数据逐条一致);
#   - 位置与 Moira 的 .se1 口径一致 (与 Moshier 相差 ~14″ 内, 只影响宿内度末位)。
USE_BUNDLED_EPHE = False
if USE_BUNDLED_EPHE and hasattr(_swe, "set_ephe_path"):
    import os as _os
    _EPHE_DIR = _os.path.join(_os.path.dirname(_os.path.abspath(_swe.__file__)), "ephe")
    _swe.set_ephe_path(_EPHE_DIR)

# 恒星制参数（与郑氏星案恒星制相同, 来自 moira_s.prop:
#   ayanamsha_base_degree=4.0 / ayanamsha_base_date=1300,1,1,0,0）
# ★2026-08-20 修正: 旧值 2195875.5 是用【格里历】公式手算的
#   (= _swe.julday(1300,1,1,0,0,GREG_CAL) = date(1300,1,1).toordinal()+1721424.5),
#   但 Moira 与本文件的口径都是 1582-10-15 之前按【儒略历】(见下方 swe_julday)。
#   Moira 实跑 Calculate.getJulianDayUT([1300,1,1,0,0]) = 2195882.5;
#   getDateFromJulianDayUT(2195875.5) 回读 = 1299-12-25 —— 正好差 7 天。
#   影响: ayanamsa@J2000 偏 +0.000267°(+0.96″), 小于守卫容差 0.001°, 故长期未被发现。
#   现改为直接调儒略历换算, 与 swe_julday(1300,1,1,0,0) 恒等, 杜绝再次手算漂移。
AYAN_T0_JD = _swe.julday(1300, 1, 1, 0.0, _swe.JUL_CAL)   # = 2195882.5
AYAN_T0_DEG = 4.0

# 初始化恒星制 ayanamsa（SIDM_USER = 255, 对应 Java swe_set_sid_mode(255,...)）
_swe.set_sid_mode(_swe.SIDM_USER, AYAN_T0_JD, AYAN_T0_DEG)

# ---- sid_mode 守卫: 其他模块/环境可能覆盖 swisseph 的全局 sid_mode ----
# 表现为 ayanamsa 偏离预期 ~11°(默认模式 24.75° vs SIDM_USER 13.76°@2000),
# 导致所有行星恒星坐标整体平移 ~11°, 入宿事件整体错位(典型事故:
# 1800 年太阳"进入柳土"从 07-28 01:17 漂移到 08-08 12:27)。
# ★2026-08-08 修复: swisseph 的 sid_mode 是【进程级全局 C 状态】, 任何其他
# 代码(Jupyter/IDE 同内核混跑、旧脚本、第三方库)调用过 set_sid_mode 都会污染
# 它; 旧守卫只检查一次, 污染发生在首次检查之后便不再拦截, 静默产出错误结果。
# 现改为:
#   1) _ensure_sid_mode(): 每次恒星坐标计算前【无条件】强制恢复 SIDM_USER
#      (set_sid_mode 只设几个全局变量, 微秒级开销, 可放心每次调用);
#   2) _verify_sid_mode(): 导入时启动自检, 若 SIDM_USER 在当前 swisseph 环境
#      无法生效(如版本不支持), 直接抛错终止, 不再静默偏移 ~11°。
_J2000_JD = 2451545.0
_AYAN_J2000_EXPECTED = 13.7627263  # SIDM_USER(儒略历 1300-01-01, 4.0°) @ J2000 实测值

# Moira 侧实测基准 (交叉来源, 非本文件推导所得):
#   Calculate.getJulianDayUT([1300,1,1,0,0]) = 2195882.5
#   依据: 反汇编中 year<1582 时传入 false → 纯儒略历; 并用 bundled JRE 实跑确认,
#   且 getDateFromJulianDayUT(2195882.5) 回读 = 1300-01-01 00:00。
_AYAN_T0_JD_MOIRA = 2195882.5

def _verify_ayan_t0():
    """t0 与 Moira 实测基准交叉校验。

    上面的 0.001° ayanamsa 守卫只能拦住 ~11° 级别的 sid_mode 失效
    (Fagan-Bradley 回退), 拦不住 t0 差 7 天这种 0.000267° 的偏差; 而且一旦
    _AYAN_J2000_EXPECTED 被"照着实测值"一起改写, 守卫就自证通过 —— 这正是
    2026-08-20 那个旧值 2195875.5(格里历口径) 能长期潜伏的原因。
    这里把常量与【Moira 实跑得到的独立字面值】对齐, 与本地换算表达式互证:
    只要日历口径写错(如 JUL_CAL 误写成 GREG_CAL)、日期写错, 立即报警。
    """
    if AYAN_T0_JD != _AYAN_T0_JD_MOIRA:
        raise RuntimeError(
            f"[致命] AYAN_T0_JD={AYAN_T0_JD} != Moira 实跑基准 "
            f"{_AYAN_T0_JD_MOIRA} (Calculate.getJulianDayUT([1300,1,1,0,0]), 儒略历)。"
            "恒星制基准时刻错误会使 ayanamsa 整体偏移(7 天 ≈ 0.000267°), "
            "请用 _swe.julday(1300,1,1,0.0,_swe.JUL_CAL) 生成该常量。")


def _ensure_sid_mode():
    """每次恒星坐标计算前强制 swisseph 处于 SIDM_USER(1300-01-01, 4.0°) 模式。

    无论之前谁把全局 sid_mode 改成什么(默认 Fagan-Bradley 24.75°@J2000 等),
    这里都恢复为本脚本的 SIDM_USER 口径, 保证坐标恒定正确。
    """
    _swe.set_sid_mode(_swe.SIDM_USER, AYAN_T0_JD, AYAN_T0_DEG)

def _verify_sid_mode():
    """导入时自检: SIDM_USER 若在当前 swisseph 环境无法生效, 立即报错。

    否则所有恒星坐标会整体偏移 ~11°(回退到默认 Fagan-Bradley 岁差),
    入宿/落宿结果全部错误且自校仍通过, 极难察觉。
    """
    _ensure_sid_mode()
    a = _swe.get_ayanamsa_ut(_J2000_JD)
    if abs(a - _AYAN_J2000_EXPECTED) > 0.001:
        raise RuntimeError(
            "[致命] swisseph 无法生效 SIDM_USER: ayanamsa@J2000 = "
            f"{a:.4f}° (预期 {_AYAN_J2000_EXPECTED:.4f}°)。所有恒星坐标将整体偏移 ~11°, "
            "入宿/落宿全部错误。请执行 pip install pyswisseph==2.10.3.2 重装 swisseph, "
            "并重启 Python 解释器(勿与其它改过 sid_mode 的代码共用进程)。")

_verify_ayan_t0()
_verify_sid_mode()

# 行星映射（Swiss Ephemeris 可直接计算的天体）
_PLANET_IDS = {
    "sun": _swe.SUN, "moon": _swe.MOON,
    "mercury": _swe.MERCURY, "venus": _swe.VENUS,
    "mars": _swe.MARS, "jupiter": _swe.JUPITER,
    "saturn": _swe.SATURN, "uranus": _swe.URANUS,
    "neptune": _swe.NEPTUNE, "pluto": _swe.PLUTO,
    # 四余中可直接由 swe 计算的两个（ChartData.java:69 planets 数组）:
    "keti": _swe.TRUE_NODE,      # 计都 = 真北交点 (swe body 11; Moira 用 TRUE_NODE)
    "bei":  _swe.MEAN_APOG,      # 月孛 = 平均远地点 (swe body 12;
                                 #   use_true_apog 时改 OSCU_APOG 真远地点)
}

# 全部 14 星曜（含特殊计算路径的罗睺/紫炁）
_ALL_BODIES = ["sun","moon","mercury","venus","mars",
               "jupiter","saturn","uranus","neptune","pluto",
               "keti","rahu","qi","bei"]

PLANET_NAMES = {
    "sun":"日","moon":"月","mercury":"水","venus":"金",
    "mars":"火","jupiter":"木","saturn":"土",
    "uranus":"天","neptune":"海","pluto":"冥",
    "keti":"计","rahu":"罗","qi":"炁","bei":"孛",
}

# ---------------------------------------------------------------------
# 四余定义（来自 moira_s.prop 与反编译代码）
#
#  计都 keti = 真北交点 (ChartData planets[10] = swe body 11 = TRUE_NODE)
#  罗睺 rahu = 计都对冲点 (prop: inverse_opposite=true;
#             ChartData.computeOpposite: 罗 = 计 - 180°。
#             赤道模式下对冲施加在【赤经转换之后】:
#             sign_pos[计] 已被 getPlanetEquPos 覆写为赤经,
#             故 罗_ra = (计_ra + 180°) mod 360,
#             而非对黄道经度取冲后再转换。—— 即 罗睺 = 南交点)
#  紫炁 qi   = 匀速圆周轨道 (sign_computation_type[12]=1,
#             prop: purple_period=10227.1792 日/周,
#                   purple_base_date=1975,3,13,16,0 (GMT/UT),
#                   purple_base_degree=230.5° (回归黄经);
#             Calculate.computeOrbit: deg = 230.5 + 360/10227.1792×(jd-base),
#             恒星制下再减当日 ayanamsa, 黄纬=0)
#  月孛 bei  = 平均远地点 (ChartData planets[13] = swe body 12 = MEAN_APOG;
#             pref use_true_apog=1 时改 body 13 = OSCU_APOG 真远地点,
#             Calculate.compute: body==12 && useTrueApog → body=13)
# ---------------------------------------------------------------------
QI_PERIOD       = 10227.1792                # 紫炁周期（日/周）
QI_SPEED        = 360.0 / QI_PERIOD         # 紫炁速度（°/日）
QI_BASE_JD      = _swe.julday(1975, 3, 13, 16.0, _swe.GREG_CAL)  # 16:00 GMT
QI_BASE_DEG     = 230.5                     # 基准回归黄经


# ★历法分界线: 1582-10-15 00:00 UT (格里历生效; 儒略日 2299160.5 / 整数部 Z 2299161)
# 用户 2026-08-07 决策: 分界线之前按儒略历, 之后按格里历 (历史历法, 与 Moira 显示一致)
_CAL_SPLIT_JD = 2299160.5


def bc_year_to_astro(bc_year: int) -> int:
    """历史纪年(公元前 N 年) → 天文纪年。公元前 N 年 = 天文 (1-N) 年。
    例: bc_year=1 (公元前1年) → 0; bc_year=2100 (公元前2100年) → -2099。
    天文纪年含 0 年(0=公元前1年), 历史纪年无 0 年——换算差 1。"""
    return 1 - int(bc_year)


def astro_year_to_bc(year: int):
    """天文纪年 → 历史纪年。天文 0 = 公元前 1 年; 天文 -1 = 公元前 2 年;
    天文 N>0 = 公元 N 年。返回 (era, year): ('BC', n) 或 ('AD', n)。"""
    if year >= 1:
        return "AD", year
    return "BC", 1 - year


def swe_julday(year, month, day, hour=12.0, tz=8.0):
    """本地时间→儒略日(UT)。
    ★历史历法: 分界线(1582-10-15)之前按儒略历解析(JUL_CAL), 之后按格里历
    (GREG_CAL)——与 _jd_to_date 显示口径一致 (用户 2026-08-07 要求)。
    ★分界用日期级判断 (year,month,day) < (1582,10,15), 不能用工时偏移后的
    jd 判断——否则北京时间 1582-10-15 00:00 (UTC 尚在 10-14) 会被误判为
    儒略段而差 10 天。"""
    use_jul = (year, month, day) < (1582, 10, 15)
    cal = _swe.JUL_CAL if use_jul else _swe.GREG_CAL
    return _swe.julday(year, month, day, hour - tz, cal)


def swe_get_ayanamsa(jd_ut):
    """获取当前恒星制 ayanamsa。
    ★2026-08-16: 先经 _ensure_sid_mode 恢复 SIDM_USER 再取值 ——
    占星子模块(moira_astro)或任何第三方代码可能把进程级 sid_mode 切到
    Lahiri 等标准模式, 直接 get_ayanamsa_ut 会取到错误岁差 (如 24.23°
    而非郑案 14.13°)。"""
    _ensure_sid_mode()
    return _swe.get_ayanamsa_ut(jd_ut)


def swe_mean_obliquity(jd_ut):
    """
    当日【平黄赤交角】（度），不含章动。
    等同 Moira swed.oec.eps —— Swiss Ephemeris ECL_NUT 的 x[1]。
    (Java SwissEph.java:794-795: x[0]=真交角=eps+nut, x[1]=平交角=eps)
    """
    xx, _ = _swe.calc_ut(jd_ut, _swe.ECL_NUT, 0)
    return xx[1]


def swe_ecl_to_equ(lon, lat, jd_ut):
    """
    黄道坐标 → 赤道坐标，等同 swe_polar_ecl_to_equ。
    eps 取负值: ecliptic → equator (swe_cotrans 约定 eps<0 为黄转赤)。
    返回 (赤经 RA[0,360), 赤纬 Dec)。
    """
    eps = swe_mean_obliquity(jd_ut)
    ra, dec, _ = _swe.cotrans((lon, lat, 1.0), -eps)
    return _norm(ra), dec


def ziqi_sidereal(jd_ut):
    """
    紫炁恒星黄经（Calculate.computeOrbit 复现）:
      回归黄经 = 230.5 + (360/10227.1792) × (jd_ut - 基准JD)
      恒星黄经 = 回归黄经 - 当日 ayanamsa   (黄纬恒为 0)
    """
    deg = QI_BASE_DEG + QI_SPEED * (jd_ut - QI_BASE_JD)
    return _norm(deg - swe_get_ayanamsa(jd_ut))


def _body_sidereal(name, jd_ut, use_true_apog=False):
    """
    任意星曜的恒星黄道坐标 (恒星黄经, 黄纬)。
    罗睺返回计都对冲的黄道位置（黄纬取 0，与节点在黄道上同理）；
    赤道制真正的罗睺位置在 _equatorial_coords 中按 Moira 方式取。
    """
    _ensure_sid_mode()   # ★sid_mode 守卫: 确保 ayanamsa 未被其他代码覆盖
    n = name.lower()
    if n == "qi":
        return ziqi_sidereal(jd_ut), 0.0
    if n == "rahu":
        lon, _ = _body_sidereal("keti", jd_ut)
        return _norm(lon + 180.0), 0.0
    pid = _PLANET_IDS.get(n)
    if pid is None:
        return None
    if n == "bei" and use_true_apog:
        pid = _swe.OSCU_APOG
    xx, _ = _swe.calc_ut(jd_ut, pid, _swe.FLG_SIDEREAL)
    return _norm(xx[0]), xx[1]


def _equatorial_coords(name, jd_ut, use_true_apog=False):
    """
    任意星曜的赤道恒星制坐标。
    返回 (ra, dec, sidereal_lon, sidereal_lat)。

    罗睺按 Moira 赤道路径处理（ChartData.java:4293-4317 + 5822）:
      计都先做 黄→赤 转换得 计_ra, 罗_ra = (计_ra + 180°) mod 360,
      赤纬镜像取负 (Moira 中 sign_alt 取负, 仅影响高度角, 此处延伸至赤纬)。
    """
    n = name.lower()
    if n == "rahu":
        ra_k, dec_k, sid_k, lat_k = _equatorial_coords("keti", jd_ut)
        return _norm(ra_k + 180.0), -dec_k, _norm(sid_k + 180.0), 0.0
    res = _body_sidereal(n, jd_ut, use_true_apog)
    if res is None:
        return None
    sid_lon, sid_lat = res
    ra, dec = swe_ecl_to_equ(sid_lon, sid_lat, jd_ut)
    return ra, dec, sid_lon, sid_lat


def swe_planet_equatorial(planet, jd_ut):
    """
    赤道恒星制核心：星曜【恒星】黄道位置 → 赤道赤经/赤纬。

    步骤（等同 Moira compute + getPlanetEquPos 调用链）:
      1) swe.calc_ut(FLG_SIDEREAL) → 恒星黄经/黄纬
         （紫炁走匀速轨道公式; 罗睺取计都赤经对冲）
      2) 按当日平黄赤交角旋转 → 赤经/赤纬

    返回 (ra, dec, sidereal_lon, sidereal_lat)，失败返回 None
    """
    return _equatorial_coords(planet, jd_ut)


def swe_planet_sidereal(planet, jd_ut):
    """获取天体恒星黄经（Swiss Ephemeris SEFLG_SIDEREAL）"""
    pid = _PLANET_IDS.get(planet.lower())
    if pid is None:
        return None
    xx, _ = _swe.calc_ut(jd_ut, pid, _swe.FLG_SIDEREAL)
    return xx[0]


def swe_planet_tropical(planet, jd_ut):
    """获取天体回归黄经"""
    pid = _PLANET_IDS.get(planet.lower())
    if pid is None:
        return None
    xx, _ = _swe.calc_ut(jd_ut, pid, 0)
    return xx[0]


# =====================================================================
# 2. 二十八宿数据
# =====================================================================

# 赤道恒星制宿界（默认）
# 数值与郑氏四十星案恒星盘相同 (moira_s.prop: sidereal_stellar_names)——
# Moira 的"赤道恒星制"选项只设 use_equ=true 而不切换宿界
# (ModeDialog/ChartData:4152), 与郑氏制唯一区别是坐标系:
# 该数值在郑氏制下解释为恒星黄道度数, 在本制下解释为【赤经度数】。
SIDEREAL_STELLAR_BOUNDARIES = [
    15.9, 26.3, 41.1, 53.2, 69.0, 70.0, 81.8, 112.3,
    115.2, 130.5, 136.4, 151.4, 170.1, 187.2, 200.0, 208.9,
    225.2, 230.6, 237.0, 255.6, 266.3, 290.1, 298.0, 308.9,
    318.3, 333.6, 349.4, 358.3
]

# 备选宿界（ChartData.java:3934-3939, ancient_sidereal_mode）
#   星海词林原版 (ancient_sidereal_mode=1)
XHCL_ORIG_BOUNDARIES = [
    15.0, 27.0, 42.0, 53.0, 70.0, 71.0, 81.0, 112.0,
    116.0, 129.0, 136.0, 152.0, 171.0, 188.0, 200.0, 209.0,
    225.0, 231.0, 237.0, 256.0, 266.0, 291.0, 298.0, 309.0,
    318.0, 333.0, 350.0, 359.0
]
#   星海词林改版 (ancient_sidereal_mode=2, 整体 -0.8°)
XHCL_REVISED_BOUNDARIES = [
    14.2, 26.2, 41.2, 52.2, 69.2, 70.2, 80.2, 111.2,
    115.2, 128.2, 135.2, 151.2, 170.2, 187.2, 199.2, 208.2,
    224.2, 230.2, 236.2, 255.2, 265.2, 290.2, 297.2, 308.2,
    317.2, 332.2, 349.2, 358.2
]

# =====================================================================
# 二十八宿距星 (determinative stars) —— J2000 赤道坐标 (RA°, Dec°)
# 顺序与 FULL_STELLAR_SIGNS 一致:
#   娄,胃,昴,毕,觜,参,井,鬼,柳,星,张,翼,轸,
#   角,亢,氐,房,心,尾,箕,斗,牛,女,虚,危,室,壁,奎
#
# ★ 数组的本质（已复原, 与用户一致）:
#   SIDEREAL_STELLAR_BOUNDARIES = 这 28 颗距星在【锁定校准历元】钉在天球
#   360° 圈上的位置。每一颗距星就是它所在宿的【宿度 0】, 数组即"距星画在
#   圈上的刻度"。天区是固定的 360°, 28 宿就是固定的刻度, 一旦锁定便永不
#   随历元重算或移动 —— 绝不是"时间对应关系", 而是钉死的"空间刻度"。
#   赤道恒星制把刻度当【赤经】用, 郑案恒星制把刻度当【恒星黄经】用, 两套
#   都是 Moira 原本设计, 都"绝对正确", 只是坐标口径不同。
# =====================================================================
STELLAR_MANSION_STARS = [
    (28.66, 20.81), (40.80, 27.26), (56.87, 24.10), (68.98, 16.51),
    (83.78, 9.93), (85.19, -1.94), (95.74, 22.51), (128.13, 18.15),
    (129.40, 5.70), (141.90, -8.66), (147.80, -14.85), (164.90, -18.30),
    (183.90, -17.54), (201.30, -11.16), (213.00, -10.27), (222.70, -16.04),
    (239.70, -26.11), (245.30, -25.59), (253.00, -38.05), (271.40, -30.42),
    (276.60, -26.99), (305.20, -14.78), (312.20, -9.49), (322.90, -5.57),
    (331.40, -0.32), (346.20, 15.21), (3.31, 15.18), (14.40, 23.25),
]


def _radec_to_ecl(ra_deg, dec_deg, eps_deg=None):
    """J2000 赤道(RA,Dec) → 黄道(经,纬)。

    eps 默认取 J2000 平黄赤交角的 **IAU 2006 规范值**，由 quasi_ecliptic 提供
    （单一真源，避免本文件再复制一份常数）。注意这只是 J2000 参考黄道；
    若要做"当日"换算，请改用本文件已有的 swe_mean_obliquity(jd) +
    swe_ecl_to_equ()，那条路走 Swiss Ephemeris 的 ECL_NUT，是更好的做法。
    """
    if eps_deg is None:
        eps_deg = _J2000_OBLIQUITY
    ra = math.radians(ra_deg); dec = math.radians(dec_deg)
    eps = math.radians(eps_deg)
    x = math.cos(dec) * math.cos(ra); y = math.cos(dec) * math.sin(ra)
    z = math.sin(dec)
    xe = x
    ye = y * math.cos(eps) + z * math.sin(eps)
    ze = -y * math.sin(eps) + z * math.cos(eps)
    return math.degrees(math.atan2(ye, xe)), math.degrees(math.asin(ze))


def _precess_ecl(lon_deg, lat_deg, jd):
    """黄道坐标从 J2000 岁差到 jd (IAU 1976 / Lieske)。"""
    T = (jd - 2451545.0) / 36525.0
    z = math.radians((2306.2181 * T + 1.09468 * T * T + 0.018203 * T ** 3) / 3600.0)
    th = math.radians((2004.3109 * T - 0.42665 * T * T - 0.041833 * T ** 3) / 3600.0)
    ze = math.radians((2306.2181 * T + 0.30188 * T * T + 0.017998 * T ** 3) / 3600.0)
    lon = math.radians(lon_deg); lat = math.radians(lat_deg)
    A = math.cos(lat) * math.sin(lon + ze)
    B = math.cos(th) * math.cos(lat) * math.cos(lon + ze) - math.sin(th) * math.sin(lat)
    C = math.sin(th) * math.cos(lat) * math.cos(lon + ze) + math.cos(th) * math.sin(lat)
    return (math.degrees(math.atan2(A, B)) + math.degrees(z)) % 360.0, \
           math.degrees(math.asin(C))


def determinative_star_boundaries(jd_ut=None, system="equatorial"):
    """
    【校验/溯源用, 非运算用】按指定历元、指定恒星制, 计算 28 颗距星的【恒星
    坐标】, 用以说明 SIDEREAL_STELLAR_BOUNDARIES 的来源：

      数组 = 28 颗距星（距星即其宿的宿度 0）的恒星坐标, 钉在天球 360° 圈上。
      二十八宿是恒星制, 恒星坐标不随岁差变, 故数组与时间无关(现代星表重建,
      最佳吻合 ~1955 年, RMS≈1.5°)。
        system="equatorial": 距星恒星赤经（以恒星春分点为基准, 赤道恒星制刻度）
        system="zheng":      距星恒星黄经（郑氏星案恒星制刻度）

    jd_ut 仅为求值参考历元(取 ayanamsa 把回归坐标转恒星坐标), 不是刻度锁定
    时间点——固定恒星的恒星坐标本身是常数。算出的距星坐标 ≈ 数组值(每宿自
    距星起算、宿度 0 = 距星)。运算落宿永远使用【固定数组】, 绝不在此按历元
    重算/替换宿界。
    """
    if jd_ut is None:
        jd_ut = SCALE_LOCK_EPOCH_JD  # 求值参考历元(非刻度锁定时间点)
    # 与固定恒星共用同一坐标变换 star_coord_at_epoch —— 距星与恒星都用同一套
    # 恒星坐标换算投到刻度(但距星钉在刻度起点=宿度0, 固定恒星只是落在刻度上)
    return [round(star_coord_at_epoch(ra0, dec0, system, jd_ut), 3)
            for ra0, dec0 in STELLAR_MANSION_STARS]

FULL_STELLAR_SIGNS = [
    "娄金","胃土","昴日","毕月","觜火","参水","井木",
    "鬼金","柳土","星日","张月","翼火","轸水","角木",
    "亢金","氐土","房日","心月","尾火","箕水","斗木",
    "牛金","女土","虚日","危月","室火","壁水","奎木",
]

HALF_STELLAR_SIGNS = [
    "娄","胃","昴","毕","觜","参","井",
    "鬼","柳","星","张","翼","轸","角",
    "亢","氐","房","心","尾","箕","斗",
    "牛","女","虚","危","室","壁","奎",
]

STELLAR_ELEMENTS = [
    "金","土","日","月","火","水","木",
    "金","土","日","月","火","水","木",
    "金","土","日","月","火","水","木",
    "金","土","日","月","火","水","木",
]


# =====================================================================
# 固定恒星 → 二十八宿（投到固定刻度，落宿固定、历元无关）
#
# ★ 概念（用户纠正，务必分清）:
#   "距星 = 宿度 0" 只针对 28 宿本身: 28 颗距星各自坐在自己那一宿的起点,
#   把 360° 圈钉成 28 段固定刻度(数组 SIDEREAL_STELLAR_BOUNDARIES)。
#   这句话与【其他固定恒星无关】——固定恒星不是距星, 不参与"宿度 0"。
#
#   固定恒星只是天球上的另一个点: 用【与距星定义刻度完全相同的换算】
#   把它投到这条已经钉死的刻度上, 看它落在哪一段、离该段起点(距星)差几度
#   (即入宿度)。
#
# ★ 刻度到底是什么口径 / 为什么历元无关（关键，破除"J2000 锁定"误解）:
#   二十八宿是【恒星(sidereal)制】——刻度钉在恒星背景上, 不随岁差漂移。
#   固定恒星的"恒星坐标"(恒星赤经 / 恒星黄经)对固定恒星而言是【常数】
#   (只差极小的自行, 千年级 <1°), 因此:
#     · 数组 = 28 距星的【恒星坐标】, 由现代星表重建(最佳吻合 ~1955 年,
#       RMS≈1.5°, 残差来自自行+距星认星+取整, 不是历元误差);
#     · 固定恒星的恒星坐标同样是常数 → 落入数组的宿判定【历元无关】。
#   J2000 只是用来"求值"的参考历元(在此取 ayanamsa 把回归坐标转成恒星坐标),
#   它【不是】刻度锁定的时间点——因为恒星坐标本身不随历元变, 换成任何现代
#   历元结果都一样。此即用户所言"空间关系, 不是时间对应关系"。
#   两套恒星制只是坐标口径不同(同一组恒星坐标):
#     · 赤道恒星制: 刻度 = 恒星赤经(恒星黄道经→赤经, 以恒星春分点为基准)
#     · 郑氏星案恒星制: 刻度 = 恒星黄经(回归黄经 − ayanamsa)
# =====================================================================

# 求值参考历元(非"刻度锁定时间点"!): 固定恒星的恒星坐标与历元无关, 此处
# 只是取 ayanamsa 把回归黄经转成恒星坐标; 换任何现代历元结果相同。
# 校验: 28 距星恒星坐标(现代星表重建)与数组残差 RMS≈1.5°、26/28 落 3° 内,
# 印证数组=距星恒星坐标(恒星制), 而非"距星@J2000 回归赤经"(后者残差 14°)。
SCALE_LOCK_EPOCH_JD = 2451545.0  # J2000, 仅作求值参考历元

# 著名恒星(非二十八宿距星)的 J2000 赤道坐标 (RA°, Dec°) —— 求其【恒星坐标】
# 后投到固定刻度(恒星坐标与历元无关, 固定不随岁差改变)。这些恒星不是距星,
# 落点即其入宿度, 与"宿度 0"无关。
NOTABLE_STARS = {
    "天狼(大犬α)":         (101.287, -16.716),
    "参宿四(猎户α)":       (88.793,   7.407),
    "参宿七(猎户β)":       (78.634,  -8.202),
    "五车二(御夫α)":       (79.172,  45.998),
    "北河二(双子α)":       (113.650, 31.888),
    "北河三(双子β)":       (116.329, 28.026),
    "南河三(小犬α)":       (114.825,  5.225),
    "大角(牧夫α)":         (213.915, 19.182),
    "轩辕十四(狮子α)":     (152.093, 11.967),
    "五帝座一(狮子β)":     (177.265, 14.572),
    "织女(天琴α)":         (279.234, 38.784),
    "河鼓二/牛郎(天鹰α)":  (297.696,  8.868),
    "天津四(天鹅α)":       (310.358, 45.280),
    "北落师门(南鱼α)":     (344.413, -29.622),
    "北极星(小熊α)":       (37.954,  89.264),
}


def star_coord_at_epoch(ra0, dec0, system, jd_ut=SCALE_LOCK_EPOCH_JD):
    """
    固定恒星(给定 J2000 RA,Dec)的【恒星坐标】—— 与历元无关(空间常数)。

    ★ 关键(用户结论, 已验证): 固定恒星的恒星坐标(恒星赤经 / 恒星黄经)是
      空间常数, 不随岁差变。因此【随便选哪个历元求值结果都相同】——这正是
      "特定历元下的恒星赤经在数千年内几乎不变"。jd_ut 形参仅为 API 对称保留,
      对固定恒星坐标无影响(只有行星才需要历元)。

    ★ 旧 bug 修正: 不能写 lon0 − ayanamsa(jd_ut)(lon0 是 J2000 回归黄经,
      却减了目标历元 ayanamsa, 历元≠J2000 即漂移 ~14°)。固定恒星坐标应直接
      取常数 S = J2000 回归黄经 − ayanamsa@J2000, 与历元无关。
      · zheng      → 恒星黄经 S (常数)
      · equatorial → 把 S 按 J2000 黄赤交角转成恒星赤经(亦为常数)

    注意: 固定恒星【不是距星】, 与"距星=宿度0"无关。只是用与距星定义刻度
    同一套恒星坐标口径, 把恒星投到已钉死的刻度上得到入宿度。
    """
    lon0, lat0 = _radec_to_ecl(ra0, dec0)                  # J2000 回归黄经(常数)
    ayan0 = swe_get_ayanamsa(SCALE_LOCK_EPOCH_JD)          # ayanamsa@J2000 (常数)
    sid_lon = _norm(lon0 - ayan0)                          # 恒星黄经(与历元无关)
    if system == "zheng":
        return sid_lon
    eps0 = swe_mean_obliquity(SCALE_LOCK_EPOCH_JD)
    ra, _, _ = _swe.cotrans((sid_lon, lat0, 1.0), -eps0)   # 恒星赤经(与历元无关)
    return _norm(ra)


def fixed_slon_to_mansion(slon_deg: float):
    """把【已算好的落宿坐标】落入固定宿界 SIDEREAL_STELLAR_BOUNDARIES,
    返回 (宿序号, 宿全名, 入宿度)。宿界是锁定在 360° 圈上的固定刻度
    （距星=宿度0）, 永不随历元重算或移动; 此函数只做"落入固定刻度"的查找。"""
    s = (slon_deg % 360.0 + 360.0) % 360.0
    b = SIDEREAL_STELLAR_BOUNDARIES
    n = len(b)
    for i in range(n):
        lo = b[i]
        if i < n - 1:
            if lo <= s < b[i + 1]:
                return i, FULL_STELLAR_SIGNS[i], s - lo
        else:  # 奎: 跨 0°, 区间 [b[-1], b[0]+360)
            if s >= lo or s < b[0]:
                d = s - lo if s >= lo else s + 360.0 - lo
                return i, FULL_STELLAR_SIGNS[i], d
    return 0, FULL_STELLAR_SIGNS[0], 0.0


def star_mansion(name: str, system: str = "zheng", jd_ut=None):
    """
    固定恒星的宿与入宿度 —— 落宿与历元无关(固定恒星坐标 = 空间常数, 随便选
    哪个历元求值结果都相同)。jd_ut 仅为 API 对称保留, 不影响结果。

    固定恒星不是距星, 不参与"宿度 0"; 它只是用与距星定义刻度相同的恒星坐标
    换算, 求得一个固定的刻度坐标, 落入固定数组 SIDEREAL_STELLAR_BOUNDARIES
    (距星钉死的 28 段)得到所属宿与入宿度(距星起算的差值)。
      star_mansion("天狼(大犬α)")                # 默认郑案恒星制
      star_mansion("天狼(大犬α)", "equatorial")   # 赤道恒星制
    返回 (宿全名, 宿序号, 入宿度°)。
    """
    if name not in NOTABLE_STARS:
        raise KeyError(f"恒星 {name!r} 不在 NOTABLE_STARS 表")
    ra0, dec0 = NOTABLE_STARS[name]
    pos = star_coord_at_epoch(ra0, dec0, system, jd_ut)
    idx, full, deg = fixed_slon_to_mansion(pos)
    return full, idx, round(deg, 3)


def body_mansion_at(body_key: str, jd_ut: float, engine=None):
    """
    天体在某时刻、按指定恒星制的落宿（与行星落宿同逻辑, 复用引擎）。
    等价于 engine.get_planet_mansion(body, ...); 此处便捷封装为 (宿全名,序号,入宿度°)。
    """
    if engine is None:
        engine = ZhengCaseSidereal()
    pos, _slon, _aux, _trop = _engine_pos(body_key, jd_ut, engine)
    idx, full, deg = fixed_slon_to_mansion(pos)
    return full, idx, round(deg, 3)


# 十二宫（地支）, 等分 30°: index = (int)(degree / 30)
ZODIAC_SIGNS = ["戌","酉","申","未","午","巳","辰","卯","寅","丑","子","亥"]
ZODIAC_FULL  = ["戌火","酉金","申水","未月","午日","巳水","辰金","卯火","寅木","丑土","子土","亥木"]

def get_zodiac(degree: float, full: bool = False) -> str:
    idx = int(degree / 30.0) % 12
    return ZODIAC_FULL[idx] if full else ZODIAC_SIGNS[idx]

def degree_in_zodiac(degree: float) -> float:
    return degree % 30.0


def format_zodiac(degree: float, show_second: bool = True) -> str:
    """
    格式化黄道十二宫位置，如 00子土36。
    地支 + 五行 + 宫内分秒。
    """
    idx = int(degree / 30.0) % 12
    name = ZODIAC_FULL[idx]
    deg_in = degree % 30.0
    d = int(deg_in)
    f = deg_in - d
    return f"{d:02d}{name}{_to_dms(f, show_second)}"


# =====================================================================
# 3. 宿度查找 — 严格还原 Java Calculate 逻辑（与黄道恒星制完全同构，
#    仅输入从恒星黄经换成赤经）
# =====================================================================

def _norm(deg):
    """归化到 [0, 360)"""
    d = deg % 360.0
    return d + 360.0 if d < 0 else d


def _to_dms(decimal_degree, show_second=True):
    """City.toMinuteSeconds"""
    total = round(3600.0 * abs(decimal_degree))
    m, s = divmod(total, 60)
    if show_second:
        return f"{m:02d}'{s:02d}\""
    return f"{m + (1 if s >= 30 else 0):02d}'"


def get_sign_index(degree, sign_positions, start=0):
    """Calculate.getSignIndex(degree, sign_pos, start)"""
    if not (0 <= degree < 360):
        return -1
    n = len(sign_positions)
    last = sign_positions[n - 1]
    for i in range(start, n):
        v, p = degree, sign_positions[i]
        if p < last:
            p += 360.0
            if v < last:
                v += 360.0
        if last <= v < p:
            return (i - 1) if i > start else (n - 1)
        last = sign_positions[i]
    return -1


def get_star_sign(degree, sign_positions, signs):
    """Calculate.getStarSign(degree, sign_pos, signs)"""
    if not (0 <= degree < 360):
        return "?invalid?"
    n = len(signs)
    last = sign_positions[n - 1]
    for i in range(n):
        v, p = degree, sign_positions[i]
        if p < last:
            p += 360.0
            if v < last:
                v += 360.0
        if last <= v < p:
            return signs[(i - 1) if i > 0 else (n - 1)]
        last = sign_positions[i]
    return "?invalid?"


def format_degree(degree, sign_positions, signs, show_second=True):
    """Calculate.formatDegree(degree, sign_pos, signs, show_second)"""
    if not (0 <= degree < 360):
        return "?invalid?"
    n = len(signs)
    last = sign_positions[n - 1]
    for i in range(n):
        v, p = degree, sign_positions[i]
        if p < last:
            p += 360.0
            if v < last:
                v += 360.0
        if last <= v < p:
            v -= last
            d = int(v)
            f = v - d
            name = signs[(i - 1) if i > 0 else (n - 1)]
            return f"{d:02d}{name}{_to_dms(f, show_second)}"
        last = sign_positions[i]
    return "?invalid?"


# =====================================================================
# 3b. 星海词林·量天尺 (360 格星官表, ★2026-09-13 新增)
# =====================================================================
#
# 量天尺 = 星海词林体系的逐度星官表: 12 宫 × 30 区 (每区 1°) = 360 格,
# 每格挂一个星官。宫位是天圈上均分的 30° 宫段, 星官跟着【宫度】走,
# 与所选宿界无关 (宿界只影响落宿/宿度显示, 不影响星官查表)。
#
# 锚定 (由量天尺表自身结构复原, 并与文档例题互验通过):
#   子宫第一区 (0°42′–1°41′) = 女1 → 起点 = 女宿一度整 = 天圈 299.0°
#   (星海词林原版与默认宿界的女宿界均为 298°)。
#   宫位随度数增加方向为 子→亥→戌→…→丑 (地支逆序), 每宫恰 30°:
#     子宫 [299,329), 亥 [329,359), 戌 [359,29), ..., 丑 [269,299)。
#   结构验证: 360 格逐格复检 —— 每格中点用星海词林原版宿界落宿,
#   所得宿名与该行星宿度数标签 360/360 全部吻合。
#   文档"0°00′–0°41′ 归下一宫末区"规则由向下取整自动满足
#   (例: 辰宫 0°20′ → 巳末区·轸8 器府; 子宫 0°20′ → 丑末区·女0 郑越)。
#
# 坐标口径: 赤道恒星制用【赤经】查表, 郑氏星案恒星制用【恒星黄经】查表,
#   即与该制落宿所用度数同圈同刻度。
#
# 数据校订 (2026-09-13, 用户确认): 氐4 = 骑官（东上一座）(原表重"东上第二座"),
#   毕15 = 五车（之次）(原表重"之舍")。

LIANGTIANCHI = {
    "辰": [("轸9", "轸宿土司空"), ("轸10", "青丘（之次）"), ("轸11", "青丘（之舍）"), ("轸12", "右辖"), ("轸13", "轸（东左二星）"), ("轸14", "长沙子"), ("轸15", "轸（西右二星）"), ("轸16", "左辖"), ("轸17", "周鼎"), ("角1", "南门"), ("角2", "库楼（之首）"), ("角3", "（库中）衡星"), ("角4", "柱星（南柱二座）"), ("角5", "柱星（中柱）"), ("角6", "柱星（北座）"), ("角7", "天库"), ("角8", "平星"), ("角9", "天门"), ("角10", "进贤"), ("角11", "角（正度）"), ("角12", "天田"), ("亢1", "阳门"), ("亢2", "颉颃"), ("亢3", "折威（之首）"), ("亢4", "折威（之末）"), ("亢5", "亢（四星）"), ("亢6", "平道"), ("亢7", "右摄提"), ("亢8", "大角"), ("亢9", "左摄提")],
    "巳": [("张14", "天庙（西下三星）"), ("张15", "天庙（中舍三星）"), ("张16", "天庙（中西舍三星）"), ("翼1", "军门"), ("翼2", "翼（东上一星）"), ("翼3", "翼（东上第二珠）"), ("翼4", "翼（上中一星）"), ("翼5", "翼（西上第二珠）"), ("翼6", "翼（西上第一星）"), ("翼7", "翼（中上三星）"), ("翼8", "翼（东南中第一珠）"), ("翼9", "翼（中东第二珠）"), ("翼10", "翼（中央二星）"), ("翼11", "翼（中西第二星）"), ("翼12", "翼（中西第一星）"), ("翼13", "翼（下中三星）"), ("翼14", "翼（东下二珠）"), ("翼15", "翼（下中一星）"), ("翼16", "翼（西下二星）"), ("翼17", "翼（下末一星）"), ("翼18", "东瓯（之次）"), ("翼19", "东瓯（之舍）"), ("轸1", "器府（东南第一座）"), ("轸2", "器府（东南第二座）"), ("轸3", "器府（中座四星）"), ("轸4", "器府（中央二座）"), ("轸5", "器府（中下一座）"), ("轸6", "器府（中上二座）"), ("轸7", "器府（西南一座）"), ("轸8", "器府（西上末座）")],
    "午": [("柳3", "柳（黄道之间）"), ("柳4", "柳（东二星）"), ("柳5", "柳（次二星）"), ("柳6", "柳（第五珠）"), ("柳7", "柳（第六珠）"), ("柳8", "柳（第七珠）"), ("柳9", "柳（末一星）"), ("柳10", "天稷（之次）"), ("柳11", "天稷（之舍）"), ("柳12", "酒帘"), ("星0", "星（正度）"), ("星1", "天相"), ("星2", "御女"), ("星3", "轩辕（之首）"), ("星4", "轩辕（中舍）"), ("星5", "轩辕（中座）"), ("星6", "轩辕（之尾）"), ("张1", "内屏"), ("张2", "长垣"), ("张3", "少微（之次）"), ("张4", "少微（之舍）"), ("张5", "太尊"), ("张6", "灵台"), ("张7", "张（东第一珠）"), ("张8", "张（东第二珠）"), ("张9", "张（正度）"), ("张10", "张（西第二星）"), ("张11", "张（末一星）"), ("张12", "天庙（东下三星）"), ("张13", "天庙（东上二星）")],
    "未": [("井8", "军市（之次）"), ("井9", "军市（之舍）"), ("井10", "野鸡"), ("井11", "阙丘"), ("井12", "南河"), ("井13", "四渎"), ("井14", "水府"), ("井15", "钺"), ("井16", "井（正度）"), ("井17", "井（东舍）"), ("井18", "井（下含）"), ("井19", "水位"), ("井20", "天樽"), ("井21", "积薪"), ("井22", "五诸侯（中一星）"), ("井23", "五诸侯（左第二珠）"), ("井24", "五诸侯（左第一星）"), ("井25", "五诸侯（右第二珠）"), ("井26", "五诸侯（右第一珠）"), ("井27", "北河"), ("井28", "井宿积水"), ("井29", "天社"), ("井30", "天狗"), ("鬼0", "鬼（东左二星）"), ("鬼1", "积尸气"), ("鬼2", "鬼（西右二星）"), ("鬼3", "燿星"), ("柳0", "天记"), ("柳1", "外厨（之次）"), ("柳2", "外厨（之舍）")],
    "申": [("毕6", "天节"), ("毕7", "九斿"), ("毕8", "参旗"), ("毕9", "天街"), ("毕10", "天高"), ("毕11", "诸王（前三星）"), ("毕12", "诸王（下三星）"), ("毕13", "天潢咸池"), ("毕14", "天关（柱星之间）"), ("毕15", "五车（之次）"), ("毕16", "五车（之舍）"), ("觜1", "觜宿"), ("参0", "参（上舍）"), ("参1", "座旗"), ("参2", "司怪"), ("参3", "参（外舍）"), ("参4", "伐星"), ("参5", "玉井"), ("参6", "军井"), ("参7", "天厕"), ("参8", "天屎"), ("参9", "屏星"), ("井0", "丈人"), ("井1", "子星"), ("井2", "孙"), ("井3", "老人"), ("井4", "白狼"), ("井5", "弧矢（东首）"), ("井6", "弧矢（中舍）"), ("井7", "孤矢（之末）")],
    "酉": [("胃3", "天囷（之首）"), ("胃4", "天廪"), ("胃5", "胃（正三星）"), ("胃6", "大陵（之首）"), ("胃7", "大陵（中舍）"), ("胃8", "大陵（之末）"), ("胃9", "胃宿积尸"), ("胃10", "天船（之首）"), ("胃11", "天船（中舍）"), ("胃12", "天船（之末）"), ("胃13", "胃宿积水"), ("胃14", "天阴（之旁）"), ("胃15", "天阿（之侧）"), ("昴0", "天苑（之首）"), ("昴1", "天苑（之中）"), ("昴2", "天苑（之末）"), ("昴3", "刍藁营"), ("昴4", "天阴"), ("昴5", "天阿"), ("昴6", "昴（正度）"), ("昴7", "月星"), ("昴8", "卷舌"), ("昴9", "天谗"), ("昴10", "砺石"), ("毕0", "天园（之首）"), ("毕1", "天园（之末）"), ("毕2", "九州"), ("毕3", "毕（正度）"), ("毕4", "毕（西右四星）"), ("毕5", "附耳")],
    "戌": [("奎1", "奎宿土司空"), ("奎2", "天溷（之次）"), ("奎3", "天溷（之舍）"), ("奎4", "外屏（之次）"), ("奎5", "外屏（之中）"), ("奎6", "外屏（之末）"), ("奎7", "奎（南下八星）"), ("奎8", "奎（北上八星）"), ("奎9", "军南门"), ("奎10", "附路"), ("奎11", "王良"), ("奎12", "天策"), ("奎13", "天驷"), ("奎14", "阁道（东上二星）"), ("奎15", "阁道（中二星）"), ("奎16", "阁道（末二星）"), ("娄1", "天仓（之次）"), ("娄2", "天仓（中舍）"), ("娄3", "天仓（之末）"), ("娄4", "天庾"), ("娄5", "左更"), ("娄6", "娄（正度）"), ("娄7", "右更"), ("娄8", "天大将军"), ("娄9", "天大将军（东南吏士）"), ("娄10", "天大将军（西北一星）"), ("娄11", "天大将军（中央大星曰大将军）"), ("娄12", "天大将军（东北一星）"), ("胃1", "天囷（之末）"), ("胃2", "天囷（之中）")],
    "亥": [("危12", "车府（之杓）"), ("危13", "造父"), ("危14", "天钩（之首）"), ("危15", "天钧（之尾）"), ("室1", "螣蛇（之首）"), ("室2", "塍蛇（之中）"), ("室3", "离宫（西二座）"), ("室4", "离宫（东一座）"), ("室5", "室（正度）"), ("室6", "雷电（六星）"), ("室7", "土公吏"), ("室8", "垒壁阵（东首）"), ("室9", "垒壁阵（西首六星）"), ("室10", "羽林军（东南隅）"), ("室11", "羽林军（东北隅）"), ("室12", "羽林军（西北隅）"), ("室13", "羽林军（西南隅）"), ("室14", "八魁"), ("室15", "𫓧钺"), ("室16", "北洛师门"), ("室17", "天网"), ("壁1", "铁锧"), ("壁2", "云雨"), ("壁3", "霹雳（东二星）"), ("壁4", "霹雳（西三星）"), ("壁5", "土工"), ("壁6", "璧（南下一星）"), ("壁7", "璧（北上一星为正度）"), ("壁8", "天厩（之次）"), ("壁9", "天廐（之舍）")],
    "子": [("女1", "齐楚"), ("女2", "周魏秦"), ("女3", "燕代"), ("女4", "韩晋赵"), ("女5", "女（正度）"), ("女6", "骊珠"), ("女7", "败瓜"), ("女8", "天津"), ("女9", "扶筐"), ("女10", "奚仲"), ("虚1", "败臼"), ("虚2", "离瑜"), ("虚3", "垒城"), ("虚4", "哭泣"), ("虚5", "虚（正度）"), ("虚6", "司命"), ("虚7", "司禄"), ("虚8", "司危"), ("虚9", "司非"), ("危1", "天钱"), ("危2", "盖屋"), ("危3", "虚梁"), ("危4", "坟墓"), ("危5", "危（南第一星）"), ("危6", "危（中一星为正度）"), ("危7", "危（上一星）"), ("危8", "人星"), ("危9", "臼星"), ("危10", "危宿杵星"), ("危11", "车府（之魁）")],
    "丑": [("斗3", "天渊（之舍）"), ("斗4", "天籥（之次）"), ("斗5", "天籥（之舍）"), ("斗6", "农丈人"), ("斗7", "斗（魁南二星）"), ("斗8", "斗（中魁星）"), ("斗9", "斗（北二星）"), ("斗10", "司昏（狗星）"), ("斗11", "天鸡"), ("斗12", "狗国"), ("斗13", "天建（南二珠）"), ("斗14", "天建（中二星）"), ("斗15", "天建（末二星）"), ("斗16", "天弁（之首）"), ("斗17", "天弁（中舍）"), ("斗18", "天弁（之末）"), ("斗19", "牛左旗"), ("斗20", "牛右旗"), ("斗21", "渐台"), ("斗22", "辇道（南二星）"), ("斗23", "辇道（中一星）"), ("斗24", "辇道（北二星）"), ("牛1", "九坎"), ("牛2", "九田"), ("牛3", "牛（正度）"), ("牛4", "罗堰"), ("牛5", "天桴"), ("牛6", "河鼓"), ("牛7", "织女"), ("女0", "郑越")],
    "寅": [("尾2", "元武（之末）"), ("尾3", "尾（第一珠）"), ("尾4", "尾（第二珠）"), ("尾5", "尾（第三珠）"), ("尾6", "尾（第四星）"), ("尾7", "神宫"), ("尾8", "尾（第五珠）"), ("尾9", "尾（第六珠）"), ("尾10", "尾（第七珠）"), ("尾11", "尾（末二星）"), ("尾12", "尾（末一星）"), ("尾13", "傅说"), ("尾14", "鱼子"), ("尾15", "天江"), ("尾16", "七公"), ("尾17", "贯索"), ("尾18", "天纪"), ("箕1", "箕宿杵（下一星）"), ("箕2", "箕宿杵（第二珠）"), ("箕3", "箕宿杵（第三珠）"), ("箕4", "箕（南下一星）"), ("箕5", "箕艮一星"), ("箕6", "箕巽一星"), ("箕7", "箕（东北一星）"), ("箕8", "糠粃"), ("箕9", "箕（黄道之间）"), ("箕10", "箕（黄道）"), ("斗0", "太阴（之次）"), ("斗1", "太阴（之舍）"), ("斗2", "天渊（之次）")],
    "卯": [("氐1", "阵车"), ("氐2", "骑官（东南一座）"), ("氐3", "骑官（东南第二座）"), ("氐4", "骑官（东上一座）"), ("氐5", "骑官（东上第二座）"), ("氐6", "骑将军"), ("氐7", "骑官（西南一座）"), ("氐8", "骑官（西中道二星）"), ("氐9", "骑官（东北中三座）"), ("氐10", "骑官（西上二座）"), ("氐11", "天辐"), ("氐12", "氐（正度）"), ("氐13", "亢池"), ("氐14", "帝席"), ("氐15", "招摇梗河"), ("氐16", "天乳"), ("房0", "从官"), ("房1", "日星"), ("房2", "房（正度）"), ("房3", "罚星"), ("房4", "东咸"), ("房5", "西咸"), ("心0", "积卒（东南一座）"), ("心1", "积卒（西南三星）"), ("心2", "积卒（西北三星）"), ("心3", "心（第三珠）"), ("心4", "中央大星（心正度）"), ("心5", "前星（震星）"), ("尾0", "元武（之首）"), ("尾1", "元武（之中）")],
}

# 宫位序 (度数增加方向, 地支逆序): 子宫第一区起点 = 299.0°, 每宫 30°
_LTC_ANCHOR = 299.0
_LTC_SEQ = ("子", "亥", "戌", "酉", "申", "未", "午", "巳", "辰", "卯", "寅", "丑")


def liangtianchi_lookup(deg):
    """量天尺查表: 天圈度数 → 宫位 / 宫度 / 星宿度数 / 星官。

    deg: 赤道恒星制传【赤经】, 郑氏星案恒星制传【恒星黄经】
         (与该制落宿所用度数同圈同刻度, 星官跟宫度走, 与宿界选择无关)。
    返回 dict:
      palace          宫位 (子/丑/.../亥)
      palace_deg      宫度浮点 (宫度 0°42′ = 宫首区起点)
      palace_deg_text 宫度格式化 "15°23′"
      zone            区内序号 1-30
      zone_range      区间文字 "0°42′–1°41′"
      star_deg        星宿度数标签 ("轸9")
      xingguan        星官名
    """
    p = (deg - _LTC_ANCHOR) % 360.0
    seq = int(p // 30.0)
    zone = int(p % 30.0)                    # 0..29
    palace = _LTC_SEQ[seq]
    star_deg, xingguan = LIANGTIANCHI[palace][zone]
    gong_du = p % 30.0 + 0.7                # 区 k (1起) = (k-1)°42′–k°41′
    gd_d = int(gong_du)
    gd_m = int(round((gong_du - gd_d) * 60.0))
    if gd_m >= 60:
        gd_d, gd_m = gd_d + 1, 0
    return {
        "palace": palace,
        "palace_deg": round(gong_du, 4),
        "palace_deg_text": f"{gd_d}°{gd_m:02d}′",
        "zone": zone + 1,
        "zone_range": f"{zone}°42′–{zone + 1}°41′",
        "star_deg": star_deg,
        "xingguan": xingguan,
    }


def lichun_jd(year, tz=8.0):
    """立春交节时刻 (儒略日 UT): 太阳回归黄经 = 315°。

    流年换年口径 = 立春。搜索窗为该年(天文纪年) 1/28–2/10,
    太阳黄经在此窗内单调递增 (~1°/天), 二分收敛。
    """
    target = 315.0
    jd_lo = swe_julday(year, 1, 28, 0.0, tz)
    jd_hi = swe_julday(year, 2, 10, 0.0, tz)

    def _diff(jd):
        return (_swe.calc_ut(jd, _swe.SUN, 0)[0][0] - target + 540.0) % 360.0 - 180.0

    for _ in range(60):
        mid = 0.5 * (jd_lo + jd_hi)
        if _diff(mid) < 0:
            jd_lo = mid
        else:
            jd_hi = mid
    return 0.5 * (jd_lo + jd_hi)


def liunian_xingguan(year, tz=8.0, boundaries=None, use_true_apog=False):
    """流年星官: 该年立春交节时刻, 14 星曜的两制落宿 + 宫位/星官对照。

    返回 dict:
      year, lichun_jd, lichun_text (本地时间),
      zheng       郑氏星案恒星制结果列表 (get_planet_mansion, 含 palace/xingguan)
      equatorial  赤道恒星制结果列表 (同上)
    """
    jd = lichun_jd(year, tz)
    y, m, d, hh, mm = _jd_to_date(jd + tz / 24.0)   # → (年,月,日,时,分) 本地
    h = hh + mm / 60.0
    zcs = ZhengCaseSidereal(boundaries=boundaries, use_true_apog=use_true_apog)
    eqs = EquatorialStellar(boundaries=boundaries, use_true_apog=use_true_apog)
    return {
        "year": year,
        "lichun_jd": round(jd, 6),
        "lichun_text": f"{y:04d}-{m:02d}-{d:02d} {hh:02d}:{mm:02d}",
        "zheng": [r for p in _ALL_BODIES
                  if (r := zcs.get_planet_mansion(p, y, m, d, h, tz))],
        "equatorial": [r for p in _ALL_BODIES
                       if (r := eqs.get_planet_mansion(p, y, m, d, h, tz))],
    }


# =====================================================================
# 4. EquatorialStellar 引擎（swisseph 后端，赤道恒星制）
# =====================================================================

class EquatorialStellar:
    """
    赤道恒星制引擎。

    与郑氏星案恒星制的唯一区别：
      落宿所用的"度数"是行星恒星位置经当日平黄赤交角旋转后的【赤经】，
      而不是恒星黄经。宿界数值、查找与格式化逻辑完全一致。

    参数:
      boundaries: 宿界数组，默认郑氏四十星案恒星盘 (prop sidereal_stellar_names)；
                  可选 XHCL_ORIG_BOUNDARIES / XHCL_REVISED_BOUNDARIES
                  (对应 ModeDialog 星海词林原版/改版)。
      use_true_apog: 月孛是否用真远地点 (pref use_true_apog;
                     默认 False = 平均远地点 MEAN_APOG)。
    """

    def __init__(self, boundaries=None, use_true_apog=False):
        self.b = boundaries if boundaries is not None else SIDEREAL_STELLAR_BOUNDARIES
        self.fs = FULL_STELLAR_SIGNS
        self.hs = HALF_STELLAR_SIGNS
        self.el = STELLAR_ELEMENTS
        self.use_true_apog = use_true_apog
        self._is_equatorial = True  # 统一接口标记

    # ---- 基本查询（入参 ra 为赤经度数） ----

    def julday(self, year, month, day, hour=12.0, tz=8.0):
        return swe_julday(year, month, day, hour, tz)

    def get_ayanamsa(self, jd_ut):
        return swe_get_ayanamsa(jd_ut)

    def get_mean_obliquity(self, jd_ut):
        return swe_mean_obliquity(jd_ut)

    def get_mansion_index(self, ra):
        return get_sign_index(ra, self.b)

    def get_mansion(self, ra, full=False):
        s = self.fs if full else self.hs
        return get_star_sign(ra, self.b, s)

    def get_mansion_element(self, ra):
        i = self.get_mansion_index(ra)
        return self.el[i] if 0 <= i < 28 else "?"

    def format_mansion(self, ra, show_second=True):
        return format_degree(ra, self.b, self.hs, show_second)

    def format_mansion_full(self, ra, show_second=True):
        return format_degree(ra, self.b, self.fs, show_second)

    def degree_within_mansion(self, ra):
        i = self.get_mansion_index(ra)
        if i < 0:
            return None
        s = self.b[i]
        return (ra + 360.0 - s) if ra < s else (ra - s)

    def mansion_boundaries(self):
        r = []
        n = len(self.b)
        for i in range(n):
            s, e = self.b[i], self.b[(i + 1) % n]
            w = e - s + (360.0 if e < s else 0)
            r.append({
                'index': i, 'name': self.hs[i],
                'full_name': self.fs[i], 'element': self.el[i],
                'start': s, 'end': e, 'width': round(w, 2),
            })
        return r

    # ---- 行星赤经落宿（swisseph 直接计算） ----

    def get_planet_mansion(self, planet, year, month, day,
                           hour=12.0, tz=8.0):
        """完整星曜赤道落宿信息（含 计/罗/炁/孛）"""
        n = planet.lower()
        if n not in _ALL_BODIES:
            return None

        jd_ut = swe_julday(year, month, day, hour, tz)
        ayan = swe_get_ayanamsa(jd_ut)
        eps = swe_mean_obliquity(jd_ut)

        # 赤道恒星制关键一步：恒星黄经/黄纬 → 赤经/赤纬
        # （罗睺 = 计都赤经+180°, 见 _equatorial_coords）
        res = _equatorial_coords(n, jd_ut, self.use_true_apog)
        if res is None:
            return None
        ra, dec, sid_lon, sid_lat = res

        # 回归黄经（信息列；紫炁由轨道公式反推, 罗睺取计都+180°）
        if n == "qi":
            trop_lon = _norm(QI_BASE_DEG + QI_SPEED * (jd_ut - QI_BASE_JD))
        elif n == "rahu":
            kt, _ = _swe.calc_ut(jd_ut, _swe.TRUE_NODE, 0)
            trop_lon = _norm(kt[0] + 180.0)
        else:
            pid = _PLANET_IDS[n]
            if n == "bei" and self.use_true_apog:
                pid = _swe.OSCU_APOG
            trop, _ = _swe.calc_ut(jd_ut, pid, 0)
            trop_lon = trop[0]

        # 量天尺: 星官跟宫度走 —— 赤道制以赤经查表 (与落宿同圈同刻度)
        ltc = liangtianchi_lookup(ra)

        return {
            'planet': n,
            'date': (year, month, day, hour),
            'tz': tz,
            'jd_ut': jd_ut,
            'ayanamsa': round(ayan, 6),
            'eps_mean': round(eps, 6),
            'tropical_lon': round(trop_lon, 6),
            'sidereal_lon': round(sid_lon, 6),
            'ra': round(ra, 6),               # 赤经（落宿依据）
            'dec': round(dec, 6),             # 赤纬
            'mansion_index': self.get_mansion_index(ra),
            'mansion': self.get_mansion(ra),
            'mansion_full': self.get_mansion(ra, full=True),
            'mansion_element': self.get_mansion_element(ra),
            'mansion_formatted': self.format_mansion(ra),
            'degree_in_mansion': round(self.degree_within_mansion(ra), 4),
            'palace': ltc['palace'],                    # 量天尺宫位
            'palace_deg': ltc['palace_deg_text'],       # 宫度 (0°42′起算)
            'xingguan': ltc['xingguan'],                # 星官
            'xingguan_star_deg': ltc['star_deg'],       # 量天尺星宿度数标签
        }

    def get_all_planets_mansion(self, year, month, day,
                                hour=12.0, tz=8.0, include_siyu=True):
        planets = list(_ALL_BODIES) if include_siyu else _ALL_BODIES[:10]
        return [r for p in planets
                if (r := self.get_planet_mansion(p, year, month, day, hour, tz))]


# =====================================================================
# 4b. ZhengCaseSidereal 引擎（郑氏星案恒星制，黄道恒星制）
# =====================================================================

class ZhengCaseSidereal:
    """
    郑氏星案恒星制引擎（黄道恒星制）。

    与赤道恒星制的区别：
      落宿所用的"度数"直接是行星恒星黄经，不再经黄赤交角旋转为赤经。
      其余宿界、查找、格式化、四余定义完全一致。

    参数:
      boundaries: 宿界数组，默认 sidereal_stellar_names；
                  可选 XHCL_ORIG_BOUNDARIES / XHCL_REVISED_BOUNDARIES。
      use_true_apog: 月孛是否用真远地点（默认 False = 平均远地点）。
    """

    def __init__(self, boundaries=None, use_true_apog=False):
        self.b = boundaries if boundaries is not None else SIDEREAL_STELLAR_BOUNDARIES
        self.fs = FULL_STELLAR_SIGNS
        self.hs = HALF_STELLAR_SIGNS
        self.el = STELLAR_ELEMENTS
        self.use_true_apog = use_true_apog
        self._is_equatorial = False  # 统一接口标记

    # ---- 基本查询（入参 slon 为恒星黄经） ----

    def julday(self, year, month, day, hour=12.0, tz=8.0):
        return swe_julday(year, month, day, hour, tz)

    def get_ayanamsa(self, jd_ut):
        return swe_get_ayanamsa(jd_ut)

    def get_mean_obliquity(self, jd_ut):
        return swe_mean_obliquity(jd_ut)

    def get_mansion_index(self, slon):
        return get_sign_index(slon, self.b)

    def get_mansion(self, slon, full=False):
        s = self.fs if full else self.hs
        return get_star_sign(slon, self.b, s)

    def get_mansion_element(self, slon):
        i = self.get_mansion_index(slon)
        return self.el[i] if 0 <= i < 28 else "?"

    def format_mansion(self, slon, show_second=True):
        return format_degree(slon, self.b, self.hs, show_second)

    def format_mansion_full(self, slon, show_second=True):
        return format_degree(slon, self.b, self.fs, show_second)

    def degree_within_mansion(self, slon):
        i = self.get_mansion_index(slon)
        if i < 0:
            return None
        s = self.b[i]
        return (slon + 360.0 - s) if slon < s else (slon - s)

    def mansion_boundaries(self):
        r = []
        n = len(self.b)
        for i in range(n):
            s, e = self.b[i], self.b[(i + 1) % n]
            w = e - s + (360.0 if e < s else 0)
            r.append({
                'index': i, 'name': self.hs[i],
                'full_name': self.fs[i], 'element': self.el[i],
                'start': s, 'end': e, 'width': round(w, 2),
            })
        return r

    # ---- 行星落宿（恒星黄经直接落宿） ----

    def get_planet_mansion(self, planet, year, month, day,
                           hour=12.0, tz=8.0):
        """完整星曜郑氏恒星落宿信息（含 计/罗/炁/孛）"""
        n = planet.lower()
        if n not in _ALL_BODIES:
            return None

        jd_ut = swe_julday(year, month, day, hour, tz)
        ayan = swe_get_ayanamsa(jd_ut)

        # 恒星黄经（罗睺 = 计都 + 180°）
        sid_lon, sid_lat = _body_sidereal(n, jd_ut, self.use_true_apog)
        sid_lon = _norm(sid_lon)

        # 回归黄经（信息列）
        if n == "qi":
            trop_lon = _norm(QI_BASE_DEG + QI_SPEED * (jd_ut - QI_BASE_JD))
        elif n == "rahu":
            kt, _ = _swe.calc_ut(jd_ut, _swe.TRUE_NODE, 0)
            trop_lon = _norm(kt[0] + 180.0)
        else:
            pid = _PLANET_IDS[n]
            if n == "bei" and self.use_true_apog:
                pid = _swe.OSCU_APOG
            trop, _ = _swe.calc_ut(jd_ut, pid, 0)
            trop_lon = trop[0]

        # 量天尺: 星官跟宫度走 —— 郑案制以恒星黄经查表 (与落宿同圈同刻度)
        ltc = liangtianchi_lookup(sid_lon)

        return {
            'planet': n,
            'date': (year, month, day, hour),
            'tz': tz,
            'jd_ut': jd_ut,
            'ayanamsa': round(ayan, 6),
            'tropical_lon': round(trop_lon, 6),
            'sidereal_lon': round(sid_lon, 6),
            'sidereal_lat': round(sid_lat, 6),
            'mansion_index': self.get_mansion_index(sid_lon),
            'mansion': self.get_mansion(sid_lon),
            'mansion_full': self.get_mansion(sid_lon, full=True),
            'mansion_element': self.get_mansion_element(sid_lon),
            'mansion_formatted': self.format_mansion(sid_lon),
            'degree_in_mansion': round(self.degree_within_mansion(sid_lon), 4),
            'palace': ltc['palace'],                    # 量天尺宫位
            'palace_deg': ltc['palace_deg_text'],       # 宫度 (0°42′起算)
            'xingguan': ltc['xingguan'],                # 星官
            'xingguan_star_deg': ltc['star_deg'],       # 量天尺星宿度数标签
        }

    def get_all_planets_mansion(self, year, month, day,
                                hour=12.0, tz=8.0, include_siyu=True):
        planets = list(_ALL_BODIES) if include_siyu else _ALL_BODIES[:10]
        return [r for p in planets
                if (r := self.get_planet_mansion(p, year, month, day, hour, tz))]


# -----------------------------------------------------------------
# 4c. 统一坐标接口（赤道 / 郑案 两制共用）
# -----------------------------------------------------------------

def _engine_pos(body: str, jd: float, engine, need_tropical: bool = False) -> tuple:
    """
    返回某星曜在某时刻、按指定恒星制引擎解释的"落宿位置"及辅助坐标。

    返回 (pos, sidereal_lon, aux, tropical_lon):
      - 赤道恒星制: pos = 赤经 RA,  aux = 赤纬 Dec
      - 郑氏星案恒星制: pos = 恒星黄经,  aux = 恒星黄纬
    sidereal_lon 始终为该星曜的恒星黄经（信息列）;
    tropical_lon 始终为该星曜的回归黄经（信息列）。

    ★2026-08-16 性能优化: need_tropical=False 时跳过回归黄经计算
    (一次额外的 calc_ut)。入宿扫描/星象日历显示等热路径均不需要该列,
    实际调用方无一使用 trop_lon —— 仅当显式 need_tropical=True 才计算。
    """
    n = body.lower()
    if getattr(engine, '_is_equatorial', False):
        ra, dec, sid_lon, sid_lat = _equatorial_coords(n, jd, engine.use_true_apog)
        if not need_tropical:
            return ra, sid_lon, dec, 0.0
        # 回归黄经
        if n == "qi":
            trop_lon = _norm(QI_BASE_DEG + QI_SPEED * (jd - QI_BASE_JD))
        elif n == "rahu":
            kt, _ = _swe.calc_ut(jd, _swe.TRUE_NODE, 0)
            trop_lon = _norm(kt[0] + 180.0)
        else:
            pid = _PLANET_IDS[n]
            if n == "bei" and engine.use_true_apog:
                pid = _swe.OSCU_APOG
            trop, _ = _swe.calc_ut(jd, pid, 0)
            trop_lon = trop[0]
        return ra, sid_lon, dec, trop_lon
    else:
        sid_lon, sid_lat = _body_sidereal(n, jd, engine.use_true_apog)
        sid_lon = _norm(sid_lon)
        if not need_tropical:
            return sid_lon, sid_lon, sid_lat, 0.0
        if n == "qi":
            trop_lon = _norm(QI_BASE_DEG + QI_SPEED * (jd - QI_BASE_JD))
        elif n == "rahu":
            kt, _ = _swe.calc_ut(jd, _swe.TRUE_NODE, 0)
            trop_lon = _norm(kt[0] + 180.0)
        else:
            pid = _PLANET_IDS[n]
            if n == "bei" and engine.use_true_apog:
                pid = _swe.OSCU_APOG
            trop, _ = _swe.calc_ut(jd, pid, 0)
            trop_lon = trop[0]
        return sid_lon, sid_lon, sid_lat, trop_lon


def _engine_pos_speed(body: str, jd: float, engine) -> float:
    """指定引擎下某星曜的落宿位置数值速度（度/日），中心差分。"""
    n = body.lower()
    if n == "qi":
        return QI_SPEED
    h = 0.005
    p1 = _engine_pos(n, jd + h, engine)[0]
    p0 = _engine_pos(n, jd - h, engine)[0]
    d = p1 - p0
    if d > 180: d -= 360
    elif d < -180: d += 360
    return d / (2 * h)


# =====================================================================
# 5. 批量时间范围 & Excel 输出
# =====================================================================


# ---- 5a. 行星速度状态 ----

# 速度状态常量（等同 Moira Calculate.SPEED_*）
SPEED_NORMAL    = 0  # 顺
SPEED_REVERSE   = 1  # 逆
SPEED_ECLIPSE   = 2  # 蚀
SPEED_STATIONARY = 3 # 留
SPEED_INVISIBLE  = 4 # 伏
SPEED_SLOW      = 5  # 迟
SPEED_FAST      = 6  # 速

SPEED_NAMES = ["顺", "逆", "蚀", "留", "伏", "迟", "速"]

# 速度阈值（来自 moira_s.prop）：金/木/水/火/土
_STATIONARY_GAP = [0.15, 0.07, 0.1, 0.2, 0.05]   # 留的间隙（度）
_INVISIBLE_GAP  = [3.0, 3.0, 3.0, 3.0, 3.0]       # 伏的日距（度）
_SLOW_SPEED     = [0.71, 0.05, 0.88, 0.4, 0.02]    # 慢速阈值（度/日）
_FAST_SPEED     = [1.245, 0.23, 1.50, 0.70, 0.13]  # 快速阈值（度/日）

# 经典行星索引映射
# ★2026-08-16 修复（对照 moira_proj.jar 字节码 ChartData.getSpeedState + Calculate.getSpeedState(II)）:
#   Moira 的数组按【金星(2), 木星(3), 水星(4), 火星(5), 土星(6)】的行星号-2 索引
#   （即 prop 注释的 金, 木, 水, 火, 土 顺序）。旧映射为 金, 水, 火, 木, 土,
#   导致 水/火/木 三颗行星的留/伏/迟/速阈值互相错位
#   （如火星用 1.50°/日 判“速”几乎永不可能, 木星用 0.4°/日 判“迟”等）。
_CLASSICAL_INDEX = {"venus": 0, "jupiter": 1, "mercury": 2, "mars": 3, "saturn": 4}


def get_planet_speed_state(planet: str, jd_ut: float, engine=None) -> dict:
    """
    获取星曜速度状态（迟逆留速伏蚀），★2026-08-16 起与 Moira 字节码逐行对齐。

    判态顺序（Moira Calculate.getSpeedState(int,int) / ChartData.getSpeedState）:
      日/月   → 蚀状态 (getEclipseState: ±1h 日食 / ±0.5d 月食, 地点可见)
      金木水火土 → 留 → 伏 → 逆 → 速 → 迟 → 顺
      天海冥  → 逆/顺（仅按速度正负）
      四余（计/罗/炁/孛）→ 恒"顺"

    坐标口径（与 Moira 完全一致, 含其"混合口径"特性）:
      - 行星位置取 computation[0] = 恒星黄经
      - 太阳位置: 赤道恒星制 = 太阳赤经; 郑氏星案恒星制 = 太阳恒星黄经
      （Moira 在 use_equ 时 sign_pos[日] 已被 getPlanetEquPos 覆写为赤经,
      而 getSpeedState 里的行星 computation[0] 仍是恒星黄经 —— 伏的日距
      判定在赤道制下就是"行星恒星黄经 vs 太阳赤经"的混合口径, 逐条保留）
    engine 为 None 时默认按赤道恒星制处理（保持旧调用兼容）。
    """
    n = planet.lower()

    # 四余: 恒为"顺"（Moira 行为）, 速度仅作参考
    if n == "qi":
        return {'speed_deg_day': QI_SPEED, 'state': SPEED_NORMAL, 'state_name': '顺'}
    if n == "rahu":
        xx, _ = _swe.calc_ut(jd_ut, _swe.TRUE_NODE, _swe.FLG_SWIEPH | _swe.FLG_SPEED)
        return {'speed_deg_day': xx[3], 'state': SPEED_NORMAL, 'state_name': '顺'}
    if n in ("keti", "bei"):
        pid = _PLANET_IDS[n]
        xx, _ = _swe.calc_ut(jd_ut, pid, _swe.FLG_SWIEPH | _swe.FLG_SPEED)
        return {'speed_deg_day': xx[3], 'state': SPEED_NORMAL, 'state_name': '顺'}

    pid = _PLANET_IDS.get(n)
    if pid is None:
        return None
    xx, _ = _swe.calc_ut(jd_ut, pid, _swe.FLG_SWIEPH | _swe.FLG_SPEED)
    speed = xx[3]

    # 日/月: 蚀状态（★2026-08-16 补上 Moira 的 getEclipseState 路径）
    if n == "sun":
        state = _eclipse_state(jd_ut, solar=True)
        return {'speed_deg_day': speed, 'state': state, 'state_name': SPEED_NAMES[state]}
    if n == "moon":
        state = _eclipse_state(jd_ut, solar=False)
        return {'speed_deg_day': speed, 'state': state, 'state_name': SPEED_NAMES[state]}
    if n in ("uranus", "neptune", "pluto"):
        state = SPEED_REVERSE if speed < 0 else SPEED_NORMAL
        return {'speed_deg_day': speed, 'state': state, 'state_name': SPEED_NAMES[state]}

    idx = _CLASSICAL_INDEX.get(n)
    if idx is None:
        return {'speed_deg_day': speed, 'state': SPEED_NORMAL, 'state_name': '顺'}

    # 太阳位置: 赤道制取赤经，郑案制取恒星黄经（与 Moira 混合口径一致）
    sun_sid, _ = _swe.calc_ut(jd_ut, _swe.SUN, _swe.FLG_SIDEREAL)
    if getattr(engine, '_is_equatorial', False):
        eps = swe_mean_obliquity(jd_ut)
        sun_ra, _, _ = _swe.cotrans((_norm(sun_sid[0]), sun_sid[1], 1.0), -eps)
        sun_pos = _norm(sun_ra)
    else:
        sun_pos = _norm(sun_sid[0])

    planet_sid, _ = _swe.calc_ut(jd_ut, pid, _swe.FLG_SIDEREAL)
    planet_pos = _norm(planet_sid[0])   # computation[0], 恒星黄经

    # --- 留（Moira 最先判, 无速度门控; ★2026-08-16 重写, 字节码 1:1）---
    stop, state = _stationary_state(pid, planet_pos, idx, jd_ut, speed)
    if stop:
        return {'speed_deg_day': speed, 'state': state, 'state_name': SPEED_NAMES[state]}

    if _degree_gap(planet_pos, sun_pos) <= _INVISIBLE_GAP[idx]:
        return {'speed_deg_day': speed, 'state': SPEED_INVISIBLE, 'state_name': '伏'}
    if speed < 0:
        return {'speed_deg_day': speed, 'state': SPEED_REVERSE, 'state_name': '逆'}
    if speed >= _FAST_SPEED[idx]:
        return {'speed_deg_day': speed, 'state': SPEED_FAST, 'state_name': '速'}
    if speed <= _SLOW_SPEED[idx]:
        return {'speed_deg_day': speed, 'state': SPEED_SLOW, 'state_name': '迟'}
    return {'speed_deg_day': speed, 'state': SPEED_NORMAL, 'state_name': '顺'}


# ★留点搜索半径（日）。Moira 的 SEFLG_TRANSIT_SPEED 搜索本质无界,
# 1000 天已覆盖 金/水/火/木/土 任意时刻前后最近的留点(火星逆行周期 ~780 天)。
_STATIONARY_SEARCH_SPAN = 1000.0

# ★2026-08-16 性能优化: 冲日过境结果按日缓存。
# 触发留判定时(仅限留点附近几天)的冲日搜索, 同一天 24 行共享同一结果
# (冲日目标 = 当前恒星黄经+180°, 一天内漂移 ≤1°, 穿越时刻变化仅数小时,
# 与留点时刻相距数周的不等式判定不受影响)。
_OPP_CACHE = {}


def _opposition_transit(pid: int, sid_now: float, jd_ut: float,
                        backward: bool):
    """冲日过境时刻 (带日级缓存): 行星恒星黄经穿越 sid_now+180° 的时刻"""
    day = int(jd_ut)
    key = (pid, day, backward)
    if key not in _OPP_CACHE:
        _OPP_CACHE[key] = _sidereal_lon_transit(
            pid, _norm(sid_now + 180.0), day + 0.5, backward)
    return _OPP_CACHE[key]


def _stationary_state(pid: int, sid_now: float, idx: int,
                      jd_ut: float, speed: float):
    """
    Moira Calculate.getSpeedState(int,int) 留判定（对照 moira_proj.jar 字节码移植）。

    返回 (stop, state):
      stop=True 时 state 为最终判态（留 / 逆 / 顺）;
      stop=False 时 state=None, 继续后续 伏/逆/速/迟 判定。

    Java 逻辑:
      1) 向后搜 speed==0 时刻 jd_bwd; 搜不到 → 直接按速度正负返回 逆/顺。
      2) gap(当前恒星黄经, jd_bwd 处恒星黄经) <= stationary_gap[idx] 时:
         向后搜行星经过 (当前恒星黄经+180°) 的冲日时刻 jd_opp;
         若 jd_opp 无效 或 jd_opp < jd_bwd（冲日发生在向后留点之前）→ 留。
      3) 向前搜 speed==0 时刻 jd_fwd; 搜不到 → 按速度正负返回 逆/顺。
      4) gap(当前恒星黄经, jd_fwd 处恒星黄经) <= stationary_gap[idx] 时:
         向前搜冲日时刻 jd_opp2; 若无效 或 jd_opp2 > jd_fwd → 留。
    ★旧实现的门控 abs(speed)<0.5 与"冲日在 [留点, 当前] 内才判留"均为自创,
    与 Moira 恰好相反, 已删除。
    """
    gap_deg = _STATIONARY_GAP[idx]
    bwd = _speed_station(pid, jd_ut, backward=True)
    if bwd is None:
        return True, SPEED_REVERSE if speed < 0 else SPEED_NORMAL
    jd_bwd, pos_bwd = bwd
    if _degree_gap(sid_now, pos_bwd) <= gap_deg:
        jd_opp = _opposition_transit(pid, sid_now, jd_ut, backward=True)
        if jd_opp is None or jd_opp < jd_bwd:
            return True, SPEED_STATIONARY
    fwd = _speed_station(pid, jd_ut, backward=False)
    if fwd is None:
        return True, SPEED_REVERSE if speed < 0 else SPEED_NORMAL
    jd_fwd, pos_fwd = fwd
    if _degree_gap(sid_now, pos_fwd) <= gap_deg:
        jd_opp2 = _opposition_transit(pid, sid_now, jd_ut, backward=False)
        if jd_opp2 is None or jd_opp2 > jd_fwd:
            return True, SPEED_STATIONARY
    return False, None


def _sidereal_lon_at(pid: int, jd: float) -> float:
    """某时刻行星的恒星黄经（Moira compute() 口径: FLG_SIDEREAL）"""
    xx, _ = _swe.calc_ut(jd, pid, _swe.FLG_SIDEREAL)
    return _norm(xx[0])


def _sidereal_lon_unwrapped(pid: int, jd: float, target_T: float) -> float:
    """行星恒星黄经, 以 target_T 为中心解卷绕到 (target_T-180, target_T+180]"""
    lon = _sidereal_lon_at(pid, jd)
    while lon - target_T > 180.0:
        lon -= 360.0
    while lon - target_T <= -180.0:
        lon += 360.0
    return lon


def _bisect_lon_crossing(pid: int, target_T: float,
                         jd_lo: float, jd_hi: float) -> float:
    """在已知穿越区间 [jd_lo, jd_hi] 内二分细化恒星黄经穿越到 0.0001°"""
    lo, hi = jd_lo, jd_hi
    for _ in range(30):
        mid = (lo + hi) / 2.0
        pos_mid = _sidereal_lon_unwrapped(pid, mid, target_T)
        diff_mid = pos_mid - target_T
        if abs(diff_mid) < 0.0001:
            return mid
        pos_lo = _sidereal_lon_unwrapped(pid, lo, target_T)
        if (pos_lo - target_T) * diff_mid <= 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2.0


def _sidereal_lon_transit(pid: int, target: float, jd_start: float,
                          backward: bool = False,
                          max_span: float = _STATIONARY_SEARCH_SPAN):
    """
    搜索行星恒星黄经穿越 target 的时刻（等同 Moira getNextTransitUT,
    flags = SEFLG_TRANSIT_LONGITUDE | SEFLG_SIDEREAL）。

    ★2026-08-16 提速: 旧 0.5 天线性扫描(最坏 ±1000 天 ≈ 2000 步 ≈ 70ms/次,
    土星留点附近触发行每行两次 → 200ms/行) 改为指数扩展括号 + 二分:
    行星冲日/合日会合周期最短 ~116 天(水星), 5 天起步 ×2 扩展必能包住
    最近一次穿越, ~15 次采样 + 30 次二分 ≈ 50 次 calc_ut ≈ 2ms, 快 ~30 倍。
    本函数仅在留判定触发时使用, target ≈ 当前留点+180°(冲日点),
    该目标每个会合周期只穿越一次, 括号法无漏检。
    max_span 天内无穿越返回 None（等同 Moira 返回无效值 4.9e-324）。
    """

    def f_of(jd):
        lon = _sidereal_lon_at(pid, jd)
        while lon - target > 180.0:
            lon -= 360.0
        while lon - target <= -180.0:
            lon += 360.0
        return lon - target

    f0 = f_of(jd_start)
    if abs(f0) < 0.0001:
        return jd_start
    lo = jd_start
    hi = jd_start
    step = 5.0
    for _ in range(12):
        hi = hi - step if backward else hi + step
        if (backward and hi < jd_start - max_span) or (not backward and hi > jd_start + max_span):
            return None
        f_hi = f_of(hi)
        if f0 * f_hi <= 0:
            return _bisect_lon_crossing(pid, target, min(lo, hi), max(lo, hi))
        lo = hi
        f0 = f_hi
        step *= 2.0
    return None


def _eclipse_state(jd_ut: float, solar: bool) -> int:
    """
    Moira Calculate.getEclipseState 移植:
      日: [jd-1h, jd+1h] 窗口内存在【北京可见】的日食 → 蚀
          (Moira: computeSolarEclipse(jd-1/24, jd+1/24, ...) 走
           swe_sol_eclipse_when_loc(地点=星盘地点))
      月: [jd-0.5d, jd+0.5d] 窗口内存在【北京可见】的月食 → 蚀
          (Moira: swe_lun_eclipse_when + swe_lun_eclipse_how(地点) > 0)
    地点固定北京, 与导出表的 LOCATION_DESC 一致。

    ★2026-08-16: 完整 pyswisseph 提供上述 API 时与 Moira 完全同路;
    精简兼容层(swisseph-ffi)无日月食 API, 用朔/望 + 黄纬 + 地平可见性
    几何近似回退 (_eclipses_fallback), 保证"蚀"状态可用。
    """
    win = (1.0 / 24.0) if solar else 0.5
    try:
        if _HAS_SWE_ECLIPSES:
            if solar:
                ret, tret, _attr = _swe.sol_eclipse_when_loc(
                    jd_ut - win, _swe.FLG_SWIEPH, (116.4, 39.93, 0.0), False)
            else:
                ret, tret = _swe.lun_eclipse_when(jd_ut - win, _swe.FLG_SWIEPH, False)
            if ret == 0 or tret is None:
                return SPEED_NORMAL
            t0 = tret[0] if isinstance(tret, (tuple, list)) else tret
            if t0 > jd_ut + win:
                return SPEED_NORMAL
            if not solar:
                # 月食还需在星盘地点可见 (Moira: swe_lun_eclipse_how 返回 >0 才记录)
                how, _ah = _swe.lun_eclipse_how(t0, _swe.FLG_SWIEPH, (116.4, 39.93, 0.0))
                if how <= 0:
                    return SPEED_NORMAL
            return SPEED_ECLIPSE
        events = _eclipses_fallback(jd_ut - win, jd_ut + win,
                                    solar=solar, require_visible=True)
        return SPEED_ECLIPSE if events else SPEED_NORMAL
    except Exception:
        return SPEED_NORMAL


# ---- 无日月食 API 环境的几何近似回退（★2026-08-16 新增） ----


def _rel_moon_sun(jd):
    """日月相对黄经 (月-日) 归化到 [0,360)"""
    mo, _ = _swe.calc_ut(jd, _swe.MOON, _swe.FLG_SWIEPH)
    su, _ = _swe.calc_ut(jd, _swe.SUN, _swe.FLG_SWIEPH)
    return _norm(mo[0] - su[0])


def _rel_moon_sun_unwrapped(jd, target_T):
    r = _rel_moon_sun(jd)
    while r - target_T > 180.0:
        r -= 360.0
    while r - target_T <= -180.0:
        r += 360.0
    return r


def _bisect_moon_sun(jd_lo, jd_hi, target_T):
    lo, hi = jd_lo, jd_hi
    for _ in range(30):
        mid = (lo + hi) / 2.0
        diff_mid = _rel_moon_sun_unwrapped(mid, target_T) - target_T
        if abs(diff_mid) < 0.0001:
            return mid
        diff_lo = _rel_moon_sun_unwrapped(lo, target_T) - target_T
        if diff_lo * diff_mid <= 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2.0


def _moon_sun_crossings(start_jd, end_jd, target):
    """日月相对黄经穿越 target(0=朔, 180=望) 的时刻列表（1 天步进 + 二分）"""
    res = []
    if end_jd <= start_jd:
        return res
    step = 1.0
    jd_prev = start_jd
    r_prev = _rel_moon_sun(jd_prev)
    u_prev = r_prev
    jd = min(start_jd + step, end_jd)
    while jd_prev < end_jd - 1e-9:
        r = _rel_moon_sun(jd)
        d = r - r_prev
        if d > 180.0:
            d -= 360.0
        elif d < -180.0:
            d += 360.0
        u = u_prev + d
        if u != u_prev:
            if u > u_prev:
                k_min = math.ceil((u_prev - target) / 360.0)
                k_max = math.floor((u - target) / 360.0)
            else:
                k_min = math.ceil((u - target) / 360.0)
                k_max = math.floor((u_prev - target) / 360.0)
            if k_min <= k_max:
                res.append(_bisect_moon_sun(jd_prev, jd, target + 360.0 * k_min))
        jd_prev = jd
        r_prev = r
        u_prev = u
        jd = min(jd + step, end_jd)
    return res


def _gmst_deg(jd_ut):
    """格林尼治恒星时（度）。Meeus 12.4: GMST = 280.46061837 + 360.98564736629 * (jd-2451545)"""
    d = jd_ut - 2451545.0
    return (280.46061837 + 360.98564736629 * d) % 360.0


def _alt_deg(jd_ut, lon_deg, lat_deg, ra_deg, dec_deg):
    """天体高度角（度）。H = 地方恒星时 - 赤经"""
    lst = (_gmst_deg(jd_ut) + lon_deg) % 360.0
    h = math.radians(lst - ra_deg)
    dec = math.radians(dec_deg)
    lat = math.radians(lat_deg)
    return math.degrees(math.asin(math.sin(lat) * math.sin(dec)
                                  + math.cos(lat) * math.cos(dec) * math.cos(h)))


def _body_ra_dec(jd_ut, pid):
    xx, _ = _swe.calc_ut(jd_ut, pid, _swe.FLG_SWIEPH)
    eps = swe_mean_obliquity(jd_ut)
    ra, dec, _ = _swe.cotrans((_norm(xx[0]), xx[1], 1.0), -eps)
    return _norm(ra), dec


def _eclipses_fallback(start_jd, end_jd, solar=True, require_visible=True):
    """
    无日月食 API 环境的几何近似回退（★2026-08-16）:
      日食: 朔(日月会) 且 |月球黄纬| < 1.573°(日食极限),
            require_visible 时还要求太阳在北京地平上;
      月食: 望(日月冲) 且 |月球黄纬| < 1.0°(本影),
            require_visible 时还要求月亮在北京地平上。
    类型按黄纬粗分（近似, 与 swe 精确类型可能有出入）。
    返回 [{'jd':, 'type_name':}, ...]。
    """
    events = []
    target = 0.0 if solar else 180.0
    for jd_c in _moon_sun_crossings(start_jd, end_jd, target):
        mo, _ = _swe.calc_ut(jd_c, _swe.MOON, _swe.FLG_SWIEPH)
        lat = abs(mo[1])
        if solar:
            if lat >= 1.573:
                continue
            tn = "日全食" if lat < 0.5 else "日偏食"
            if require_visible:
                ra, dec = _body_ra_dec(jd_c, _swe.SUN)
                if _alt_deg(jd_c, 116.4, 39.93, ra, dec) <= 0:
                    continue
        else:
            if lat >= 1.0:
                continue
            if lat < 0.35:
                tn = "月全食"
            elif lat < 0.8:
                tn = "月偏食"
            else:
                tn = "月半影食"
            if require_visible:
                ra, dec = _body_ra_dec(jd_c, _swe.MOON)
                if _alt_deg(jd_c, 116.4, 39.93, ra, dec) <= 0:
                    continue
        events.append({'jd': jd_c, 'type_name': tn})
    return events


# swisseph 兼容层能力探测（★2026-08-16）
# 完整 pyswisseph 提供日月食 API; 精简兼容层(swisseph-ffi)只提供核心计算,
# 日月食相关功能自动走上方几何近似回退。
_HAS_SWE_ECLIPSES = (hasattr(_swe, "sol_eclipse_when_glob")
                     and hasattr(_swe, "lun_eclipse_when"))


def _ra_at(body, jd: float, engine=None) -> float:
    """
    指定儒略日的星曜落宿位置（显示用）。
    未指定 engine 时默认赤道恒星制（保持旧调用兼容）。
    """
    if engine is None:
        return _equatorial_coords(body, jd)[0]
    return _engine_pos(body, jd, engine)[0]


def _aspect_position(body, jd: float, engine=None) -> float:
    """
    返回用于相位计算的位置。
    赤道恒星制下，相位以郑案恒星黄经为准；
    郑案制下则使用当前引擎位置（即恒星黄经）。
    """
    if engine is not None and getattr(engine, '_is_equatorial', False):
        sid_lon, _ = _body_sidereal(body.lower(), jd, getattr(engine, 'use_true_apog', False))
        return _norm(sid_lon)
    return _ra_at(body, jd, engine)


def _aspect_speed(body, jd: float, engine=None) -> float:
    """相位位置速度（度/日），中心差分；紫炁为恒定速度"""
    if body.lower() == "qi":
        return QI_SPEED
    h = 0.005
    r1 = _aspect_position(body, jd + h, engine)
    r0 = _aspect_position(body, jd - h, engine)
    d = r1 - r0
    if d > 180: d -= 360
    elif d < -180: d += 360
    return d / (2 * h)


def _ra_speed(body, jd: float, engine=None) -> float:
    """落宿位置数值速度（度/日），中心差分；紫炁为恒定速度"""
    if body.lower() == "qi":
        return QI_SPEED
    h = 0.005
    r1 = _ra_at(body, jd + h, engine)
    r0 = _ra_at(body, jd - h, engine)
    d = r1 - r0
    if d > 180: d -= 360
    elif d < -180: d += 360
    return d / (2 * h)


def _speed_at(pid: int, jd: float) -> tuple:
    """行星黄经速度 (度/日) 与加速度 (度/日²)"""
    xx, _ = _swe.calc_ut(jd, pid, _swe.FLG_SWIEPH | _swe.FLG_SPEED)
    spd = xx[3]
    xx2, _ = _swe.calc_ut(jd + 0.02, pid, _swe.FLG_SWIEPH | _swe.FLG_SPEED)
    return spd, (xx2[3] - spd) / 0.02


def _speed1(pid: int, jd: float) -> float:
    """行星黄经速度 (度/日), 单次计算 (线性扫描用)"""
    xx, _ = _swe.calc_ut(jd, pid, _swe.FLG_SWIEPH | _swe.FLG_SPEED)
    return xx[3]


def _newton_speed(pid: int, target_speed: float, jd_start: float,
                  max_iter: int = 30) -> float | None:
    """沿速度梯度的牛顿迭代(不设方向), 收敛到最近的速度目标点"""
    jd = jd_start
    for _ in range(max_iter):
        spd, accel = _speed_at(pid, jd)
        err = target_speed - spd
        if abs(err) < 0.0001:
            return jd
        if abs(accel) < 1e-12:
            return None
        dt = err / accel
        dt = max(-15.0, min(15.0, dt))
        jd += dt
        if abs(jd - jd_start) > _STATIONARY_SEARCH_SPAN:
            return None
    return None


def _bisect_speed(pid: int, target_speed: float,
                  jd_lo: float, jd_hi: float) -> float:
    """在已知符号变化区间内二分速度目标穿越 (35 次 → 0.0001° 级)"""
    lo, hi = jd_lo, jd_hi
    f_lo = _speed1(pid, lo) - target_speed
    for _ in range(35):
        mid = (lo + hi) / 2.0
        f_mid = _speed1(pid, mid) - target_speed
        if abs(f_mid) < 0.0001:
            return mid
        if f_lo * f_mid <= 0:
            hi = mid
        else:
            lo = mid
            f_lo = f_mid
    return (lo + hi) / 2.0


def compute_speed_transit(pid: int, target_speed: float,
                          jd_start: float, backward: bool = False) -> float | None:
    """速度目标过境搜索, 等同 Moira 的 SEFLG_TRANSIT_SPEED (getNextTransitUT)。

    ★2026-08-16 修复方向 bug: 旧实现沿速度梯度做牛顿迭代, 向后/向前请求
    常收敛到同一侧留点 (如水星 07-01 的 bwd/fwd 都落到 06-30 的留点),
    导致"留"判定双向重复触发并做昂贵冲日扫描。现改为:
      1) 牛顿梯度搜索; 若收敛点已在要求方向一侧 → 直接返回;
      2) 否则从该收敛点起, 按 15 天步在要求方向线性扫描速度符号变化
         (15 天 < 最短逆行窗口(水星 ~23 天), 任何留点必被采样到), 再二分。
    搜索半径 ±_STATIONARY_SEARCH_SPAN 天 (火星前后留点可相距 ~400 天)。
    """
    jd = _newton_speed(pid, target_speed, jd_start)
    if jd is not None:
        if backward and jd < jd_start - 1e-9:
            return jd
        if not backward and jd > jd_start + 1e-9:
            return jd
    # 方向不符(或牛顿失败): 线性扫描 + 二分
    span = _STATIONARY_SEARCH_SPAN
    anchor = jd if jd is not None else jd_start
    lo = anchor
    hi = anchor
    s_lo = _speed1(pid, lo) - target_speed
    step = 15.0
    max_steps = int(span / step) + 4
    for _ in range(max_steps):
        hi = hi - step if backward else hi + step
        if (backward and hi < jd_start - span) or (not backward and hi > jd_start + span):
            return None
        s_hi = _speed1(pid, hi) - target_speed
        if s_lo * s_hi <= 0:
            res = _bisect_speed(pid, target_speed, lo, hi)
            # 可能又收敛回刚越过的那颗留点(错侧), 方向校验后决定是否继续扫
            if (backward and res < jd_start - 1e-9) or (not backward and res > jd_start + 1e-9):
                return res
        lo = hi
        s_lo = s_hi
    return None


# ★2026-08-16 性能优化: 留点按日缓存。
# 留点时刻是星历属性(与查询行无关), 同一天内 24 个导出行共享同一搜索结果,
# 把每行星每行的 2 次速度过境搜索降到 每天每行星 2 次 (~24 倍)。
# 注意: 向后搜索锚定当日正午, 恰逢留点落在当天的极端情况(<1 天/年/行星)
# 判定可能与逐行精确搜索差一条留点 —— 影响仅限该日、且仅在留点附近,
# 判定容差 0.05~0.2° 下无实际差别。向前搜索不受此限(最近留点在正午之后)。
_STATION_CACHE = {}


def _speed_station(pid: int, jd_ut: float, backward: bool):
    """返回 (jd_station, pos_station) 或 None, 带日级缓存"""
    day = int(jd_ut)
    key = (pid, day, backward)
    if key not in _STATION_CACHE:
        jd0 = day + 0.5
        jd_s = compute_speed_transit(pid, 0.0, jd0, backward)
        if jd_s is not None:
            _STATION_CACHE[key] = (jd_s, _sidereal_lon_at(pid, jd_s))
        else:
            _STATION_CACHE[key] = None
    return _STATION_CACHE[key]


# ---- 5b. 日月食检测 ----

def find_eclipses(start_jd: float, end_jd: float, engine=None) -> dict:
    """
    搜索日月食（等同 Moira computeSolarEclipse/computeLunarEclipse），
    并对每次食相计算当时的日月落宿（赤道制用赤经，郑案制用恒星黄经）。

    返回: {'solar': [...], 'lunar': [...]}
          每项: {'jd':, 'type':, 'type_name':,
                  'sun_mansion':, 'sun_deg':, 'moon_mansion':, 'moon_deg':}

    ★2026-08-16 修复: 完整 pyswisseph 路径修正 sol_eclipse_when_glob 的三元组
    解包(pyswisseph 返回 (retflag, tret, attr), 旧二元解包被 except 吞掉,
    日食列表永远为空); 精简兼容层(swisseph-ffi)无日月食 API 时走
    _eclipses_fallback 几何近似(朔/望+黄纬), 类型为近似标注。
    """
    result = {'solar': [], 'lunar': []}

    if not _HAS_SWE_ECLIPSES:
        # ★2026-08-16 回退: 无日月食 API 环境用几何近似 (全局事件, 不过滤可见性)
        for ev in _eclipses_fallback(start_jd, end_jd, solar=True, require_visible=False):
            if engine is not None:
                _add_eclipse_mansions(ev, ev['jd'], engine)
            result['solar'].append(ev)
        for ev in _eclipses_fallback(start_jd, end_jd, solar=False, require_visible=False):
            if engine is not None:
                _add_eclipse_mansions(ev, ev['jd'], engine)
            result['lunar'].append(ev)
        return result

    # 日食
    ut = start_jd
    while ut < end_jd:
        try:
            # ★2026-08-16 修复: pyswisseph 的 sol_eclipse_when_glob 返回 3 元组
            # (retflag, tret, attr), 旧代码二元解包 → ValueError → 被 except 吞掉,
            # 日食列表永远为空。
            ret, tret, _attr = _swe.sol_eclipse_when_glob(ut, 0, 0, False)
            if ret == 0 or tret[0] > end_jd:
                break
            if ret & _swe.ECL_ANNULAR:
                tn = "日环食"
            elif ret & _swe.ECL_TOTAL:
                tn = "日全食"
            else:
                tn = "日偏食"
            entry = {'jd': tret[0], 'type': ret, 'type_name': tn}
            if engine is not None:
                _add_eclipse_mansions(entry, tret[0], engine)
            result['solar'].append(entry)
            ut = tret[0] + 1.0
        except Exception:
            break

    # 月食
    ut = start_jd
    while ut < end_jd:
        try:
            ret, tret = _swe.lun_eclipse_when(ut, 0, 0, False)
            if ret == 0 or tret[0] > end_jd:
                break
            if ret & _swe.ECL_TOTAL:
                tn = "月全食"
            elif ret & _swe.ECL_PARTIAL:
                tn = "月偏食"
            else:
                tn = "月半影食"
            entry = {'jd': tret[0], 'type': ret, 'type_name': tn}
            if engine is not None:
                _add_eclipse_mansions(entry, tret[0], engine)
            result['lunar'].append(entry)
            ut = tret[0] + 1.0
        except Exception:
            break

    return result


def _add_eclipse_mansions(entry: dict, jd: float, engine):
    """在食相时刻计算日月落宿（按引擎类型：赤道=赤经，郑案=恒星黄经）"""
    pos_s, _, _, _ = _engine_pos("sun", jd, engine)
    pos_m, _, _, _ = _engine_pos("moon", jd, engine)
    entry['sun_mansion'] = engine.get_mansion(pos_s, full=True)
    entry['sun_deg'] = round(engine.degree_within_mansion(pos_s), 4)
    entry['moon_mansion'] = engine.get_mansion(pos_m, full=True)
    entry['moon_deg'] = round(engine.degree_within_mansion(pos_m), 4)


# ---- 5c. 相位计算（赤经角距，等同赤道模式下 Moira computeAspects
#           作用于 sign_pos 数组 —— 该数组在 use_equ 时存赤经） ----

def _degree_gap(a: float, b: float) -> float:
    """两角度间的最小距离（度），等同 Moira getDegreeGap"""
    d = abs(a - b) % 360.0
    return d if d <= 180.0 else 360.0 - d


def _jd_to_date(jd: float) -> tuple:
    """儒略日 → (年, 月, 日, 时, 分)
    ★历史历法 (用户 2026-08-07 决策): 分界线 Z 2299161 (1582-10-15) 之前按儒略历,
    之后按格里历——与 swe_julday 输入口径一致, 与 Moira 1582 前儒略显示一致。
    ★格里分支除法取整必须 math.floor (Meeus 算法要求向下取整; int() 对负 α 值
    向零截断会 off-by-one 1 天; 儒略分支全正数, int() 即可)。
    ★2026-08-16: Z 也改为 math.floor —— 对 jd+0.5 ∈ (-1, 0) (约 -4712 年开头)
    int() 向零截断得 Z=0、F<0, 反解出 -4712-01-00, 差一天; floor 得 Z=-1、F≥0,
    Meeus 公式恢复正确。对正 jd 与 int() 完全等价。
    注: 输入侧 swe_julday 按【日期】(1582,10,15) 选历, 输出侧按【JD】Z 2299161 选历,
    两者只在儒略历 1582-10-05~10-14 这段重叠窗存在 10 天差(输入儒略日期会以
    格里历显示, 标为格里历)——为历史纪年口径的固有歧义, 保留此约定。"""
    jd += 0.5
    # 浮点容差: julday 对远古负年有 ~1e-10 天量级残差, floor 前先吸收
    # (1e-9 天 ≈ 86 微秒, 远小于输出分钟分辨率)
    jd = round(jd, 9)
    Z = math.floor(jd)
    F = jd - Z
    if Z < 2299161:
        A = Z                                   # 儒略历 (1582-10-15 之前)
    else:
        alpha = math.floor((Z - 1867216.25) / 36524.25)
        A = Z + 1 + alpha - alpha // 4          # 格里历
    B = A + 1524
    C = math.floor((B - 122.1) / 365.25)
    D = math.floor(365.25 * C)
    E = math.floor((B - D) / 30.6001)
    day = B - D - math.floor(30.6001 * E) + F
    month = E - 1 if E < 14 else E - 13
    year = C - 4716 if month > 2 else C - 4715
    d = int(day)
    frac = day - d
    # ★2026-08-16: 总分钟数一次性提取 + 60µs 浮点容差。
    # 旧写法 h=int(frac*24), m=int((frac*24-h)*60) 在 23:00/06:00 等
    # 1/24 的二进制不可精确表示处会差 1 分钟 (如 -4711-12-31 23:00 → 22:59)。
    m_total = int(frac * 1440.0 + 1e-6)
    if m_total >= 1440:
        m_total = 1439   # 距子夜 60µs 内的浮点尾差, 钳到 23:59
    h = m_total // 60
    m = m_total % 60
    return (year, month, d, h, m)


def _calendar_of_jd(jd: float) -> str:
    """该儒略日使用的显示历法: 1582-10-15 (jd 2299161) 前儒略历, 之后格里历"""
    return "儒略历" if int(jd + 0.5) < 2299161 else "格里历"


# ★计算地点与时区 (用户 2026-08-07 晚要求: 日月食等导出注明地点与当地时区;
#   地点固定北京——GUI 无地点输入; 日月食极大时刻为全球同一时刻(物理基准
#   jd/UT), 但【呈现口径固定为地点当地时间】, 与 GUI 选择的时区/时间无关
#   (Moira 日月食计算逻辑都是当地时间, 用户 2026-08-07 晚确认))
LOCATION_NAME = "北京"
LOCATION_DESC = "北京 116°24'E 39°55'48\"N"
LOCATION_TZ   = 8.0                     # 当地时间时区 (北京 UTC+8, 日月食固定用)


def _fmt_datetime(jd: float, tz: float = 8.0, label_cal: bool = False) -> str:
    """格式化儒略日为日期时间字符串 (本地时间, 默认北京时间 tz=8)。
    ★时间值保持纯日期 (历法标注在导出列名/表头, 用户 2026-08-07 要求);
    label_cal=True 时附加 '0000-08-07 00:00(儒略历)' 形式标注。"""
    jd_loc = jd + tz / 24.0
    y, mo, d, h, mi = _jd_to_date(jd_loc)
    s = f"{y:04d}-{mo:02d}-{d:02d} {h:02d}:{mi:02d}"
    if label_cal:
        s += f"({_calendar_of_jd(jd_loc)})"
    return s

# 相位配置（来自 moira_s.prop；按用户要求 120° 改为「三合」，60° 保持「六合」）
_ASPECT_ANGLES = [0.0, 180.0, 90.0, 120.0, 60.0, 45.0, 135.0, 30.0, 150.0]
_ASPECT_ORBS   = [12.0, 6.0, 3.0, 4.0, 2.0, 1.5, 1.5, 1.0, 1.0]
_ASPECT_NAMES  = ["会", "冲", "刑", "三合", "六合", "半刑", "半刑", "四合", "四合"]

# 星象日历默认相位: 会/六合/刑/三合/冲（test3 五角口径, 在原有默认上多勾选六合 60°;
# 逻辑层默认, 非仅 GUI 勾选; 不传 aspect_indices 时生效）
_DEFAULT_ASPECT_INDICES = [i for i, a in enumerate(_ASPECT_ANGLES)
                           if a in (0.0, 60.0, 90.0, 120.0, 180.0)]


def compute_aspects(planet_ras: dict) -> list:
    """
    计算所有行星对之间的相位（赤经角距），等同 Moira computeAspects。

    参数:
        planet_ras: {'sun': ra1, 'moon': ra2, ...}  赤经度数

    返回: [(p1, p2, angle, orb, name), ...]
    """
    planets = list(planet_ras.keys())
    result = []
    for i in range(len(planets)):
        for j in range(i + 1, len(planets)):
            p1, p2 = planets[i], planets[j]
            gap = _degree_gap(planet_ras[p1], planet_ras[p2])
            for k in range(len(_ASPECT_ANGLES)):
                if abs(gap - _ASPECT_ANGLES[k]) <= _ASPECT_ORBS[k]:
                    result.append((p1, p2, round(gap, 4), _ASPECT_ORBS[k], _ASPECT_NAMES[k]))
                    break
    return result


def compute_transit_aspects(start_jd: float, end_jd: float,
                             selected_planets: list = None,
                             aspect_indices: list = None,
                             engine=None,
                             progress_callback=None,
                             tz: float = 8.0) -> list:
    """
    星象日历 (流年相位)。

    ★与 moira_pack 反编译源码同构 (ChartData.computeTransitData mode==0):
        for i_body < k_body:                    # 按 swe 行星号, 小号为过境星体
            for j in 相位角:
                for p in (±1;  对称角 0°/180° 仅 +1):
                    angle = normalize360(p * aspects_degree[j])
                    when = start_ut
                    while when < end_ut:
                        when = relativeTransitUT(k_body, i_body, angle, when)
                             # 求 (pos_k - pos_i) mod 360 = angle 的时刻
                             # (Moira 调 swisseph getRelativeTransitUT;
                             #  python 绑定未暴露该 API, 此处用等价求解器 _relative_transit_ut)
                        if 无效 or when >= end_ut: break
                        记录事件;  when += 1.0
    ★2026-08-16 核对（字节码 + 实跑 moira_proj.jar 金参照）:
    Moira 调用链 computeTransitData → computePlanetRelativeTransit(planets[i], planets[j], ...)
    → computeRelativeTransit → getRelativeTransitUT(k_body, i_body, angle, flags, start, ...),
    即 过境星体 t = swe 行星号【大】者, 参照星体 r = 行星号【小】者,
    方程 (大 - 小) mod 360 = angle。p1 = 过境星体(大号), p2 = 参照星体(小号),
    与 Moira 星象日历输出一致（实跑对照: 日月 off=60 事件 jd=2461240.4256,
    (月-日)=60°）。四余(计/罗/炁/孛)为非真实行星, Moira isRealPlanet 跳过, 此处同样跳过。
    相位基准 = 郑案恒星黄经 (赤道制相位以郑案为准)。
    tz: 事件时间戳时区 (默认北京时间 8)。
    """
    if selected_planets is None:
        selected_planets = list(_ALL_BODIES)
    if aspect_indices is None:
        aspect_indices = list(_DEFAULT_ASPECT_INDICES)   # 默认六合 60°

    sel = list(selected_planets)
    events = []
    total_units = 0
    for i in range(len(sel)):
        for j in range(i + 1, len(sel)):
            pa, pb = sel[i], sel[j]
            ta, tb = _BODY_SWE_IDX.get(pa), _BODY_SWE_IDX.get(pb)
            if ta is None or tb is None:
                continue   # 四余等: Moira isRealPlanet 不支持相对过境, 跳过
            for k in aspect_indices:
                ang = _ASPECT_ANGLES[k]
                sym = (abs(ang) < 0.1 or abs(ang - 180.0) < 0.1)
                total_units += 1 if sym else 2
    unit = 0
    for i in range(len(sel)):
        for j in range(i + 1, len(sel)):
            pa, pb = sel[i], sel[j]
            ta, tb = _BODY_SWE_IDX.get(pa), _BODY_SWE_IDX.get(pb)
            if ta is None or tb is None:
                continue   # 四余等: Moira isRealPlanet 不支持相对过境, 跳过
            # Moira: 过境星体 = swe 行星号大者 (k_body), 参照 = 小者 (i_body)
            if ta < tb:
                p1, p2 = pb, pa   # p1=过境(大号), p2=参照(小号)
            else:
                p1, p2 = pa, pb
            for k in aspect_indices:
                ang = _ASPECT_ANGLES[k]
                orb = _ASPECT_ORBS[k]
                sym = (abs(ang) < 0.1 or abs(ang - 180.0) < 0.1)
                dirs = [1] if sym else [-1, 1]
                for p_dir in dirs:
                    unit += 1
                    offset = (p_dir * ang) % 360.0
                    when = start_jd
                    while when < end_jd:
                        jd_tr = _relative_transit_ut(p1, p2, offset, when, end_jd, engine)
                        if jd_tr is None or jd_tr > end_jd:
                            break
                        _append_event(events, p1, p2, jd_tr, ang, orb, k, engine, tz)
                        when = jd_tr + 1.0   # Moira: 找到后跳 1 天继续搜下一个
                    if progress_callback and (unit % 5 == 0 or unit == total_units):
                        progress_callback(unit, total_units)

    events.sort(key=lambda x: x['jd'])
    deduped, seen = [], set()
    for e in events:
        key = (round(e['jd'], 3), e['p1'], e['p2'], e['name'])
        if key not in seen:
            seen.add(key); deduped.append(e)
    return deduped


# ---- Moira 内置 Swiss Ephemeris Java 版 移植常量 (SwephData.java) ----
# 行星黄经速度极值表 (°/天; 索引: 0日 1月 2水 3金 4火 5木 6土 7天 8海 9冥 10罗 11计)
_MOIRA_MAX_LON_SPEED = [1.025, 15.41, 2.23, 1.266, 0.794, 0.244, 0.13404, 0.067, 0.04, 0.041, -0.0528, 0.0328]
_MOIRA_MIN_LON_SPEED = [0.946, 11.75, -1.4, -0.65, -0.404, -0.1369, -0.084, -0.044, -0.0286, -0.0284, -0.0531, -0.261]
_MOIRA_MAX_BARY_DIST = [1.017261973, 1.019846623, 0.466604085, 0.728698831, 0.728698831,
                        4.955912195, 8.968685733, 19.893326756, 30.326750627, 41.499626899,
                        0.002569555, 0.002774851]
_BODY_SWE_IDX = {"sun": 0, "moon": 1, "mercury": 2, "venus": 3, "mars": 4,
                 "jupiter": 5, "saturn": 6, "uranus": 7, "neptune": 8, "pluto": 9}


def _relative_transit_ut(t_planet: str, r_planet: str, offset: float,
                         start_jd: float, end_jd: float,
                         engine=None) -> float | None:
    """
    ★1:1 移植 Moira 内置 Swiss Ephemeris Java 版 (org.athomeprojects.swisseph)
    Extensions.getRelativeTransit/relTransit —— 即 Moira 流年相位的原始算法
    (ChartData.computeTransitData mode==0 调 computeRelativeTransit → getRelativeTransitUT)。
    求最小的 jd >= start_jd 使 (黄经(t) - 黄经(r)) mod 360 = offset。
    - 速度用行星黄经速度极值表 (SwephData.minLonSpeed/maxLonSpeed) 保守外推,
      对逆行/停滞天然安全 (与 Moira 完全一致)。
    - 位置用回归黄经 (Moira getRelativeTransit 内 flags &= 0xFFFEFFFF 清 SIDEREAL;
      恒星黄经成相与之数学等价, ayanamsa 在差值中抵消)。
    - 只实现前向 (backward=false, 与 Moira 星象日历一致); idx=0 黄经模式。
    """
    ti = _BODY_SWE_IDX.get(t_planet)
    ri = _BODY_SWE_IDX.get(r_planet)
    if ti is None or ri is None:
        return None   # 四余: Moira isRealPlanet 同样不支持
    # --- getRelativeTransit 前置: offset 归一化 + idx=0 黄经 rollover ---
    rollover = True
    while offset < 0.0:
        offset += 360.0
    r_shift = offset % 360.0
    offset = 0.0
    tMax, tMin = _MOIRA_MAX_LON_SPEED[ti], _MOIRA_MIN_LON_SPEED[ti]
    rMax, rMin = _MOIRA_MAX_LON_SPEED[ri], _MOIRA_MIN_LON_SPEED[ri]
    deltaMax = tMax - rMin
    deltaMin = tMin - rMax
    xneg = deltaMax < 0.0
    mneg = deltaMin < 0.0
    degPrec = max(_moira_calc_precision(ti, start_jd), _moira_calc_precision(ri, start_jd)) / 2.0
    timePrec = _moira_calc_time_precision(degPrec,
                                          min(abs(tMin), abs(rMin)),
                                          min(abs(tMax), abs(rMax)))
    # --- 位置计算 (回归黄经, idx=0) ---
    def _lon(p_idx, jd):
        return _swe.calc_ut(jd, p_idx, 0)[0][0]
    def _rlon(jd):
        p = _lon(ri, jd)
        if rollover and r_shift > 0.0:
            p = (p + r_shift) % 360.0
        return p
    jd_ut = start_jd
    xxr = _rlon(jd_ut)
    xxt = _lon(ti, jd_ut)
    if abs(offset - (xxt - xxr)) == 0.0:
        return jd_ut
    if deltaMax == 0.0 and deltaMin == 0.0:
        return None
    # --- relTransit 迭代 (backward=false) ---
    while True:
        delta = xxt - xxr
        above = delta >= offset
        lastJD = jd_ut
        lastDelta = delta
        if rollover and delta < offset:
            delta += 360.0
        # 速度边界保守外推 (前向)
        jdPlus = (offset - delta + (0.0 if xneg else 360.0)) / deltaMax
        jdMinus = (offset - delta + (0.0 if mneg else 360.0)) / deltaMin
        jd_ut += min(jdPlus, jdMinus)
        if abs(jd_ut - lastJD) < timePrec:
            jd_ut = lastJD + timePrec
        if jd_ut > end_jd:
            return None   # 等价 Moira "Out of bound"
        xxr = _rlon(jd_ut)
        xxt = _lon(ti, jd_ut)
        delta = xxt - xxr
        if offset - delta == 0.0:
            return jd_ut
        pxway = True
        if rollover:
            if delta > offset and lastDelta < offset and delta - lastDelta > 360.0:
                delta -= 360.0
            elif delta < offset and lastDelta > offset and lastDelta - delta > 360.0:
                delta += 360.0
            deltadeg1 = delta - lastDelta
            if deltadeg1 < 0.0:
                deltadeg1 += 360.0
            deltadeg2 = lastDelta - delta
            if deltadeg2 < 0.0:
                deltadeg2 += 360.0
            if mneg and not xneg:
                pxway = abs(deltadeg1 / deltaMax) < abs(deltadeg2 / deltaMin)
            else:
                pxway = True   # !backward
            if mneg and xneg:
                pxway = not pxway
        else:
            pxway = lastDelta <= delta
        found = (abs(offset - delta) < degPrec
                 or (above and delta <= offset and not pxway)
                 or (not above and delta >= offset and pxway)
                 or (rollover and (
                     (offset < lastDelta and delta > 340.0 and lastDelta < 20.0 and not pxway)
                     or (offset > lastDelta and delta < 20.0 and lastDelta > 340.0 and pxway)
                     or (offset > delta and delta > 340.0 and lastDelta < 20.0 and not pxway)
                     or (offset < delta and delta < 20.0 and lastDelta > 340.0 and pxway))))
        if abs(offset - delta) < degPrec:
            return jd_ut
        if found:
            jdRet = lastJD + (jd_ut - lastJD) * (offset - lastDelta) / (delta - lastDelta)
            return max(jdRet, jd_ut)
    return None


def _moira_calc_precision(planet_idx: int, jd_ut: float, what: int = 0) -> float:
    """★Moira Extensions.calcPrecision 移植 (idx=0 黄经模式)"""
    degPrec = 0.005
    if what > 2:
        degPrec = 0.002
    elif 0 <= planet_idx <= 5:
        if jd_ut < 1980.0 or jd_ut > 2099.0:
            degPrec = 0.08
    elif 1900.0 <= jd_ut < 1980.0:
        degPrec = 0.08
    elif jd_ut < 1900.0 or jd_ut > 2099.0:
        degPrec = 1.0
    degPrec /= 3600.0
    degPrec *= 0.7
    if what in (2, 5):
        degPrec *= _MOIRA_MAX_BARY_DIST[planet_idx]
    return degPrec


def _moira_calc_time_precision(deg_prec: float, vmin: float, vmax: float) -> float:
    """★Moira Extensions.calcTimePrecision 移植"""
    return deg_prec / max(abs(vmin), abs(vmax))


def _refine_quick_equ(jd_lo: float, jd_hi: float,
                   p1: str, p2: str, target: float,
                   engine=None) -> float | None:
    """相位穿越区间内 3~5 次牛顿迭代细化（以郑案黄经为相位基准）"""
    jd = (jd_lo + jd_hi) / 2
    gap = 0.0
    h = 0.005
    for _ in range(8):
        gap = _degree_gap(_aspect_position(p1, jd, engine), _aspect_position(p2, jd, engine))
        # 数值导数 d(gap)/dt: 短弧方向自动正确(递减为负/递增为正)。
        # 不能用 speed 差(p2-p1): 恒正, 短弧递减方向发散→漏检约 2/3 相位事件
        # (实证: 2026-08-06 日月刑 gap 递减, d(gap)/dt=-12.99 vs rel=+12.99)。
        g_p = _degree_gap(_aspect_position(p1, jd + h, engine), _aspect_position(p2, jd + h, engine))
        g_m = _degree_gap(_aspect_position(p1, jd - h, engine), _aspect_position(p2, jd - h, engine))
        rel = (g_p - g_m) / (2 * h)
        err = target - gap
        if abs(err) < 0.0005:
            return jd
        if abs(rel) < 1e-9:
            break
        dt = err / rel
        dt = max(-0.5, min(0.5, dt))
        jd += dt
        if jd < jd_lo or jd > jd_hi:
            break
    # 牛顿失败(短弧极值点 0°/180° 导数翻转振荡, 或慢速星对长区间):
    # 三分搜索 min|gap-target|。事件区间保证 gap 穿过 target(两端在容许度外),
    # 故 |gap-target| 在区间内单谷, 三分收敛到解, 不依赖导数。
    def _gap(x):
        return _degree_gap(_aspect_position(p1, x, engine), _aspect_position(p2, x, engine))
    lo, hi = jd_lo, jd_hi
    for _ in range(50):
        m1 = lo + (hi - lo) / 3.0
        m2 = hi - (hi - lo) / 3.0
        if abs(_gap(m1) - target) < abs(_gap(m2) - target):
            hi = m2
        else:
            lo = m1
    jd_best = (lo + hi) / 2.0
    return jd_best if abs(_gap(jd_best) - target) < 0.01 else None


def _append_event(events: list, p1_key: str, p2_key: str,
                   jd: float, angle: float, orb: float,
                   k: int, engine, tz: float = 8.0):
    # 显示位置：赤道制下为赤经，郑案制下为恒星黄经
    pos1 = _ra_at(p1_key, jd, engine)
    pos2 = _ra_at(p2_key, jd, engine)
    # 相位位置：赤道制下以郑案恒星黄经为准，郑案制下与显示位置相同
    asp1 = _aspect_position(p1_key, jd, engine)
    asp2 = _aspect_position(p2_key, jd, engine)
    gap = _degree_gap(asp1, asp2)
    if abs(gap - angle) > orb:
        return
    ev = {
        'jd': jd, 'date': _fmt_datetime(jd, tz),
        'p1': PLANET_NAMES.get(p1_key, p1_key),
        'p2': PLANET_NAMES.get(p2_key, p2_key),
        'angle': angle, 'name': _ASPECT_NAMES[k],
        'orb': orb,
    }
    # 宿（按显示位置）
    if engine is not None:
        ev['p1_mansion'] = engine.get_mansion(pos1, full=True)
        ev['p1_mansion_deg'] = round(engine.degree_within_mansion(pos1), 4)
        ev['p2_mansion'] = engine.get_mansion(pos2, full=True)
        ev['p2_mansion_deg'] = round(engine.degree_within_mansion(pos2), 4)
    # 宫（地支, 等分30°；按显示位置）
    ev['p1_zodiac'] = get_zodiac(pos1, full=True)
    ev['p1_zodiac_deg'] = round(degree_in_zodiac(pos1), 4)
    ev['p1_zodiac_text'] = format_zodiac(pos1, show_second=False)
    ev['p2_zodiac'] = get_zodiac(pos2, full=True)
    ev['p2_zodiac_deg'] = round(degree_in_zodiac(pos2), 4)
    ev['p2_zodiac_text'] = format_zodiac(pos2, show_second=False)
    events.append(ev)


# ---- 5d. 入宿检测 (赤经精确穿越宿界) ----

def compute_mansion_entries(start_jd: float, end_jd: float,
                            selected_planets: list = None,
                            engine=None, tz: float = 8.0,
                            progress_callback=None,
                            fixed_node_speed: bool = False) -> list:
    """
    检测星曜精确穿越二十八宿边界的时刻 (入宿)。
    步进采样 + 穿越检测 + 二分/牛顿细化。支持 计/罗/炁/孛。

    赤道制下穿越的是赤经；郑案制下穿越的是恒星黄经。
    注意: 某些位置可能短时回退, 算法对每个方向的穿越都可检出。

    ★ 内部实现 = compute_mansion_entries_fast (速度预估跳跃版, 边扫边推进):
    输入只有开始/结束两个时刻; 从开始点出发, 用「宿界与位置的差值 ÷ 速度」
    估算到达下一个宿界的时间, 跳到穿越窗口, 窗口内细扫 + 二分细化出精确时刻,
    记录后从穿越点继续推进 —— 大段无事件区间直接跳过, 扫描量∝事件数,
    不随区间长度增长(4200 年月亮 ≈ 57 分钟), 内存 O(1)。
    进度按「推进到的时刻」(=年份) 报告, 每推进 0.5% 报一次, 长区间平滑推进。
    """
    return compute_mansion_entries_fast(start_jd, end_jd,
                                        selected_planets, engine, tz,
                                        progress_callback,
                                        fixed_node_speed=fixed_node_speed)


# 入宿搜索步长（按星体典型移动速度设定，确保不跳过最近仅 1° 的宿界）
_MANSION_STEP_BY_BODY = {
    "moon": 0.03,
    "sun": 0.2,
    "mercury": 0.2,
    "venus": 0.2,
    "mars": 0.2,
    "jupiter": 2.0,
    "saturn": 2.0,
    "uranus": 5.0,
    "neptune": 5.0,
    "pluto": 5.0,
    "keti": 5.0,
    "rahu": 5.0,
    "bei": 5.0,
    "qi": 5.0,
}

# ★自校正原则容差: 入宿事件时刻反算的星体位置与该宿起点(宿度0)的偏差上限。
# 二分细化精度 0.0001° → 实际偏差 ~1e-4~1e-5°; 容差取 0.01°(36″) 远大于
# 数值尾差、远小于最近宿界间距(觜参 1°), 超差即判定事件异常。
_SELF_CHECK_TOL = 0.01


def compute_mansion_entries_fast(start_jd: float, end_jd: float,
                                 selected_planets: list = None,
                                 engine=None, tz: float = 8.0,
                                 progress_callback=None,
                                 fixed_node_speed: bool = False) -> list:
    """
    速度预估跳跃版入宿检测（与 compute_mansion_entries 结果逐条一致, 更快）。

    思路: 每轮取当前位置 u(解卷绕) 与速度 v(度/天, 差分估算),
    找「速度方向上的最近宿界」得距离 d;
    窗口起点一律取当前位置 t(实际穿越必然在未来, 永不晚于穿越),
    窗口终点 = t + 1.5×(d/|v|) + 0.5 (停滞段 |v|<0.05 用小窗口细扫);
    窗口内以大步进(无逆行星)/原步进(逆行星)扫描, 对全部 28 宿界做
    解卷绕 k_min/k_max 穿越检测 + _bisect_crossing 二分细化 ——
    窗口可跨多个宿界, 全宿界检测保证窗口内事件一个不漏;
    检出后跳过 max(0.02, 0.002/|v|) 天(防二分尾差导致重复检出),
    未检出则从窗口末尾继续重新定位。结果与轨迹版 1/2 年全星、
    月亮 100 年、逆行段全量比对 0 漏 0 多, 提速约 1.4~1.8 倍。
    """
    if selected_planets is None:
        selected_planets = list(_ALL_BODIES)
    boundaries = (engine.b if engine else SIDEREAL_STELLAR_BOUNDARIES)
    mansions = FULL_STELLAR_SIGNS
    n = len(boundaries)
    events = []
    # 进度: 按「推进到的时刻」报告(=年份比例)。边扫边推进下, 每处理完一个
    # 窗口 t 就前进一段(穿越点或窗口末尾), 进度 = (t-start)/(end-start)。
    # 每推进 0.5% 报一次, 长区间(4200 年)平滑推进, 不再卡 0%。
    span = max(end_jd - start_jd, 1e-9)
    n_stars = max(len(selected_planets), 1)
    last_pct = -1.0   # ★跨星累计进度: 第 k 颗星扫描时总进度 = (k + 星内比例)/n_stars,
                      #   14 颗星依次推进 0→100%(太阳段→月亮段→…→孛段), 全程平滑, 不再卡段
    for si, p in enumerate(selected_planets):
        pk = p.lower()
        step = _MANSION_STEP_BY_BODY.get(pk, 1.0)
        t = start_jd

        # ★Moira 兼容分支: 罗/计用固定平均速度推进, 避免 fast 算法与真实速度混用导致重复/漂移
        if fixed_node_speed and pk in ("rahu", "keti"):
            prev_u = _ra_at(pk, t, engine)
            last_found_jd = None
            last_found_bi = None
            while t < end_jd - 1e-9:
                local = min((t - start_jd) / span, 1.0)
                pct = (si + local) / n_stars
                if progress_callback and (pct - last_pct >= 0.005 / n_stars or t >= end_jd - 1e-9):
                    progress_callback(round(pct * 10000) / 100.0, 100.0)
                    last_pct = pct

                pos = _ra_at(pk, t, engine)
                dlt = pos - prev_u
                if dlt > 180.0:
                    dlt -= 360.0
                elif dlt < -180.0:
                    dlt += 360.0
                u = prev_u + dlt
                prev_u = u

                # 逆行方向最近的宿界
                best = None
                for bi in range(n):
                    bv = boundaries[bi]
                    k = math.floor((u - bv) / 360.0 + 0.5)
                    target_T = bv + 360.0 * k
                    dd = target_T - u
                    if dd < 0.0 and (best is None or -dd < best[0]):
                        best = (-dd, target_T, bi)
                if best is None:
                    t += step
                    continue
                d, target_T, bi = best
                dt = d / abs(_FIXED_NODE_SPEED_DEG_DAY)
                if dt <= 0 or t + dt > end_jd:
                    break
                jd_tr = t + dt

                # 固定速度估算后, 用真实位置验证是否确实已越过该边界
                # (真交点速度会波动, 固定速度可能给出虚假穿越)
                pos_chk = _ra_at(pk, jd_tr, engine)
                dist_chk = abs(pos_chk - target_T)
                if dist_chk > 180.0:
                    dist_chk = 360.0 - dist_chk
                # 逆行越过: 真实位置应在 target_T 之后(数值更小)
                if dist_chk > 5.0:
                    t += step
                    prev_u = _ra_at(pk, t, engine)
                    continue

                # 去重: 同一宿界不可能在 30 天内穿越两次
                if last_found_bi == bi and last_found_jd is not None and abs(jd_tr - last_found_jd) < 30.0:
                    t += step
                    prev_u = _ra_at(pk, t, engine)
                    continue

                # 逆行: 退出 mansions[bi], 进入 mansions[bi-1]
                new_mansion = mansions[(bi - 1) % n]
                from_mansion = mansions[bi]
                events.append({
                    'jd': jd_tr,
                    'date': _fmt_datetime(jd_tr, tz),
                    'planet': PLANET_NAMES.get(p, p),
                    'pk': pk,
                    'mansion': new_mansion,
                    'from_mansion': from_mansion,
                    'boundary_deg': boundaries[bi],
                    'self_check_ok': dist_chk <= _SELF_CHECK_TOL,
                    'self_check_deg': round(dist_chk, 6),
                    'speed_deg_day': round(_FIXED_NODE_SPEED_DEG_DAY, 6),
                })
                last_found_jd = jd_tr
                last_found_bi = bi
                # 跳到事件后, 继续下一宿
                t = jd_tr + max(0.02, 0.002 / abs(_FIXED_NODE_SPEED_DEG_DAY))
                prev_u = _ra_at(pk, t, engine)
            end_pct = (si + 1) / n_stars
            if progress_callback and last_pct < end_pct:
                progress_callback(round(end_pct * 10000) / 100.0, 100.0)
                last_pct = end_pct
            continue

        prev_u = _ra_at(pk, t, engine)
        while t < end_jd - 1e-9:
            # 进度: 星内按「推进到的时刻」(=年份比例)上报, 再平移到跨星累计刻度上。
            # 每处理完一个窗口 t 就前进一段; 每推进 0.5% 报一次, 长区间平滑推进。
            local = min((t - start_jd) / span, 1.0)
            pct = (si + local) / n_stars
            if progress_callback and (pct - last_pct >= 0.005 / n_stars or t >= end_jd - 1e-9):
                progress_callback(round(pct * 10000) / 100.0, 100.0)
                last_pct = pct
            # --- 当前位置(解卷绕) ---
            pos = _ra_at(pk, t, engine)
            dlt = pos - prev_u
            if dlt > 180.0:
                dlt -= 360.0
            elif dlt < -180.0:
                dlt += 360.0
            u = prev_u + dlt
            prev_u = u
            # --- 速度(度/天): 差分窗口取 min(step,5) 天, 慢星用长差分更稳 ---
            sp = min(step, 5.0)
            sp = max(sp, 1e-4)
            t1 = min(t + sp, end_jd)
            if t1 <= t:
                break
            pos1 = _ra_at(pk, t1, engine)
            d1 = pos1 - pos
            if d1 > 180.0:
                d1 -= 360.0
            elif d1 < -180.0:
                d1 += 360.0
            v = d1 / (t1 - t)
            # --- 速度方向上的最近宿界 ---
            best = None  # (距离 d, target_T, bi)
            for bi in range(n):
                bv = boundaries[bi]
                k = math.floor((u - bv) / 360.0 + 0.5)
                target_T = bv + 360.0 * k
                dd = target_T - u
                if v >= 0.0:
                    if dd > 0.0 and (best is None or dd < best[0]):
                        best = (dd, target_T, bi)
                else:
                    if dd < 0.0 and (best is None or -dd < best[0]):
                        best = (-dd, target_T, bi)
            if best is None:
                t += step
                continue
            d, _, _ = best
            # --- 窗口起点一律取当前位置 t: 实际穿越必然在未来, 永不晚于穿越 ---
            if abs(v) < 0.05:
                # 停滞/极慢(逆行转折附近): 小窗口细扫, 不做 t_est 跳跃
                t_win1 = min(t + max(step * 2, 2.0), end_jd)
                wstep = step
            elif pk in ("mercury", "venus", "mars") and abs(v) < 0.2:
                # ★2026-08-08 逆行三星接近留点(0.05~0.2°/天): t_est 窗口会拉得极长
                #   (火星 0.1°/天 → 窗口 ~190 天), 改用 2 天小窗细扫, 每窗 ≤10 步,
                #   更便宜且事件不漏(每个 2 天切片都被完整检测)
                t_win1 = min(t + max(step * 2, 2.0), end_jd)
                wstep = step
            else:
                t_est = d / abs(v)
                t_win1 = min(t + t_est * 1.5 + 0.5, end_jd)
                # 无逆行星(月/日/木土/四余)窗口内可用大步; 逆行星(水金火)按实时速度
                # 分配窗口步长 (★2026-08-08 优化: 每步角位移 ≤0.5° 且 ≥0.1 天,
                # 取代固定 0.2 天。旧固定步长对火星(0.5°/天)过细——每步只走 0.1°;
                # 0.5°/步 仍 < 觜参 1° 宿距, 不会跳宿)
                if pk in ("mercury", "venus", "mars"):
                    wstep = max(0.1, min(0.5 / max(abs(v), 1e-4), 1.5))
                else:
                    wstep = min(max(step, 1.0), 5.0)
            if t_win1 <= t:
                t = t_win1
                continue
            # ---- 窗口内全宿界穿越检测 (分段轨迹版) ----
            # 窗口内每步与全部 28 宿界做 k_min/k_max 穿越检测:
            # 窗口可能跨多个宿界(尤其大步长+快星), 只检最近宿界会漏;
            # 检出后推进 wt 继续扫窗口剩余, 保证窗口内事件一个不漏
            wpos_prev = pos
            wu_prev = pos
            wt = t
            last_found = None
            while wt < t_win1:
                wt2 = min(wt + wstep, t_win1)
                wpos = _ra_at(pk, wt2, engine)
                wd = wpos - wpos_prev
                if wd > 180.0:
                    wd -= 360.0
                elif wd < -180.0:
                    wd += 360.0
                wu2 = wu_prev + wd
                if wu2 != wu_prev:
                    for bi in range(n):
                        if wu2 > wu_prev:
                            k_min = math.ceil((wu_prev - boundaries[bi]) / 360.0)
                            k_max = math.floor((wu2 - boundaries[bi]) / 360.0)
                        else:
                            k_min = math.ceil((wu2 - boundaries[bi]) / 360.0)
                            k_max = math.floor((wu_prev - boundaries[bi]) / 360.0)
                        if k_min <= k_max:
                            # 区间位移 <360°, 同一宿界至多一个 360k 副本被跨过
                            target_T = boundaries[bi] + 360.0 * k_min
                            # ★Moira 兼容: 罗/计可选固定速度推进
                            if fixed_node_speed and pk in ("rahu", "keti"):
                                jd_tr = _bisect_crossing_fixed_speed(pk, target_T, wt, wt2, engine)
                            else:
                                jd_tr = _bisect_crossing_fast(pk, target_T, wt, wt2, engine)
                            if jd_tr is not None and wt - 1e-9 <= jd_tr <= min(wt2, end_jd) + 1e-9:
                                # ★2026-08-09 修复: 删除了这里曾加的 0.5 天去重 —— 它误杀了窄宿
                                #   (心宿仅 6.3° 宽, 月亮 0.48 天穿过) 的连续穿越事件。
                                #   防重复检出由下方 skip = max(0.02, 0.002/|v|) 跳过量保证,
                                #   原版轨迹算法即如此, 0 漏 0 多。
                                # ★方向判定 (2026-08-08 修复逆行标注颠倒):
                                #   顺行(wu2>wu_prev)跨边界 → 进入 mansions[bi](自 mansions[bi-1]);
                                #   逆行(wu2<wu_prev)跨边界 → 反向: 退出 mansions[bi], 进入 mansions[bi-1]。
                                #   旧代码不分方向一律按顺行标注 → 逆行事件原宿/新宿颠倒
                                #   (例: 1913-04-29 金星逆行, 实为娄金→奎木, 却标成奎木→娄金)。
                                if wu2 > wu_prev:
                                    new_mansion = mansions[bi]
                                    from_mansion = mansions[(bi - 1) % n]
                                else:
                                    new_mansion = mansions[(bi - 1) % n]
                                    from_mansion = mansions[bi]
                                # ★自校正原则: 用计算出的入宿时刻反算星体位置,
                                #   验证应落在该宿起点(宿度0)附近(容差 _SELF_CHECK_TOL)。
                                pos_chk = _ra_at(pk, jd_tr, engine)
                                dist_chk = abs(pos_chk - target_T)
                                if dist_chk > 180.0:
                                    dist_chk = 360.0 - dist_chk
                                if dist_chk > _SELF_CHECK_TOL and not (fixed_node_speed and pk in ("rahu", "keti")):
                                    print(f"[自校异常] {PLANET_NAMES.get(p, p)}→{new_mansion} "
                                          f"{_fmt_datetime(jd_tr, tz)} 反算位置偏差 {dist_chk:.4f}° "
                                          f"超容差 {_SELF_CHECK_TOL}°", flush=True)
                                # ★穿越时刻瞬时速度: 与宿界同口径的手写差分。
                                #   _ra_at 已按 engine 自动适配坐标(赤道制=赤经, 郑案制=恒星黄经);
                                #   复用自校位置 pos_chk, 只需再多算 1 个未来点, 比 _ra_speed 少一次调用。
                                #   正 = 顺行, 负 = 逆行, |值|极小 = 正好在留点附近跨越。
                                if fixed_node_speed and pk in ("rahu", "keti"):
                                    speed_at_cross = _FIXED_NODE_SPEED_DEG_DAY
                                else:
                                    dt = 0.05
                                    pos_future = _ra_at(pk, min(jd_tr + dt, end_jd), engine)
                                    dchk = pos_future - pos_chk
                                    if dchk > 180.0:
                                        dchk -= 360.0
                                    elif dchk < -180.0:
                                        dchk += 360.0
                                    speed_at_cross = dchk / dt
                                events.append({
                                    'jd': jd_tr,
                                    'date': _fmt_datetime(jd_tr, tz),
                                    'planet': PLANET_NAMES.get(p, p),
                                    'pk': pk,
                                    'mansion': new_mansion,
                                    'from_mansion': from_mansion,
                                    'boundary_deg': boundaries[bi],
                                    'self_check_ok': dist_chk <= _SELF_CHECK_TOL,
                                    'self_check_deg': round(dist_chk, 6),
                                    'speed_deg_day': round(speed_at_cross, 6),
                                })
                                last_found = jd_tr
                wpos_prev = wpos
                wu_prev = wu2
                wt = wt2
            if last_found is not None:
                # 跳过量必须大于二分尾差(0.0001°→停滞段可达 ~0.02 天)折合的行程,
                # 否则位置还在宿界另一侧, 同一穿越会被重复检出;
                # 正常速度段保持 0.02 天(< 觜参 1° 间距, 不破坏极近宿界连续穿越)
                skip = max(0.02, 0.002 / max(abs(v), 1e-4))
                t = last_found + skip
                prev_u = _ra_at(pk, t, engine)
                continue
            # --- 窗口内未检出: 从窗口末尾继续, 重新定位 ---
            t = t_win1
            prev_u = _ra_at(pk, t, engine)
        end_pct = (si + 1) / n_stars
        if progress_callback and last_pct < end_pct:
            progress_callback(round(end_pct * 10000) / 100.0, 100.0)   # 该星扫完, 推进到其段尾
            last_pct = end_pct
    events.sort(key=lambda x: x['jd'])
    # ★2026-08-09 在宿停留区间: 每颗星按时间排序后, 事件 i 表示"从 jd 起进入该宿"(停留初始),
    #   停留结束 = 下一次穿越时刻(下一事件); 最后一事件停留结束 = 区间终点。
    #   逆行往返会形成 [进A, 退A][进B, 退B][再进A,...] 连续区间, 自然衔接。
    _by_pk = {}
    for _ev in events:
        _by_pk.setdefault(_ev.get('pk', _ev['planet']), []).append(_ev)
    for _evs in _by_pk.values():
        _evs.sort(key=lambda x: x['jd'])
        for _i, _ev in enumerate(_evs):
            if _i + 1 < len(_evs):
                _ev['leave_jd'] = _evs[_i + 1]['jd']
                _ev['leave_date'] = _evs[_i + 1]['date']
            else:
                _ev['leave_jd'] = end_jd
                _ev['leave_date'] = _fmt_datetime(end_jd, tz)
    return events


def _ra_unwrapped_near(body: str, jd: float, target_T: float,
                       engine=None) -> float:
    """返回星曜位置，以 target_T 为中心解卷绕到 (target_T-180, target_T+180]"""
    pos = _ra_at(body, jd, engine)
    while pos - target_T > 180.0:
        pos -= 360.0
    while pos - target_T <= -180.0:
        pos += 360.0
    return pos


def _bisect_crossing(body: str, target_T: float,
                     jd_lo: float, jd_hi: float,
                     engine=None) -> float | None:
    """在已知穿越区间内二分细化到 0.0001° 精度"""
    lo, hi = jd_lo, jd_hi
    for _ in range(25):
        mid = (lo + hi) / 2.0
        pos_mid = _ra_unwrapped_near(body, mid, target_T, engine)
        diff_mid = pos_mid - target_T
        if abs(diff_mid) < 0.0001:
            return mid
        pos_lo = _ra_unwrapped_near(body, lo, target_T, engine)
        diff_lo = pos_lo - target_T
        if diff_lo * diff_mid <= 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2.0


def _bisect_crossing_fast(body: str, target_T: float,
                          jd_lo: float, jd_hi: float,
                          engine=None) -> float | None:
    """
    ★加速版二分细化 (模仿星象日历 relTransit 的「外推收敛+插值」思路):
    线性插值预定位 → 牛顿细化 (速度差分) → 小窗二分兜底。
    收敛到 1e-6° 量级 (原版 _bisect_crossing 提前返回容差 1e-4°,
    慢速星上该容差折合数百秒时刻误差——加速版更接近真值)。
    事件集合/宿名与原版逐条一致 (0 漏 0 多), 每事件 swisseph 调用
    从 ~30 次降到 ~10 次, 月亮 3x / 全星 1.7x。
    """
    pos_lo = _ra_unwrapped_near(body, jd_lo, target_T, engine)
    pos_hi = _ra_unwrapped_near(body, jd_hi, target_T, engine)
    span = jd_hi - jd_lo
    if span <= 0:
        return None
    # 1) 线性插值预定位 (单调段几乎精确)
    denom = pos_hi - pos_lo
    t_est = jd_lo
    if abs(denom) > 1e-9:
        frac = (target_T - pos_lo) / denom
        t_est = jd_lo + span * frac
        t_est = max(jd_lo, min(jd_hi, t_est))
    # 2) 牛顿细化 (最多 4 次; 发散/停滞自动退出转二分)
    t = t_est
    for _ in range(4):
        pos = _ra_unwrapped_near(body, t, target_T, engine)
        diff = pos - target_T
        if abs(diff) < 1e-6:
            return t
        h = min(span, 0.02)
        p1 = _ra_unwrapped_near(body, min(t + h, jd_hi), target_T, engine)
        v = (p1 - pos) / h
        if abs(v) < 1e-6:
            break
        dt = -diff / v
        if abs(dt) > span:
            break
        t += dt
        if t < jd_lo or t > jd_hi:
            break
    # 3) 小窗二分兜底 (窗=span 的 1/4; 不含穿越则扩到全区间)
    win = max(span * 0.25, 2e-4)
    lo = max(jd_lo, t - win)
    hi = min(jd_hi, t + win)
    pl = _ra_unwrapped_near(body, lo, target_T, engine) - target_T
    ph = _ra_unwrapped_near(body, hi, target_T, engine) - target_T
    if pl * ph > 0:
        lo, hi = jd_lo, jd_hi
    for _ in range(25):
        mid = (lo + hi) / 2.0
        pos_mid = _ra_unwrapped_near(body, mid, target_T, engine)
        diff_mid = pos_mid - target_T
        if abs(diff_mid) < 1e-4:
            return mid
        pos_l = _ra_unwrapped_near(body, lo, target_T, engine)
        if (pos_l - target_T) * diff_mid <= 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2.0


# ★Moira 兼容: 罗/计用固定平均速度推进(ChartData.java 反编译中 transit 计算用 -0.05299°/天)
_FIXED_NODE_SPEED_DEG_DAY = -0.05299


def _bisect_crossing_fixed_speed(body: str, target_T: float,
                                 jd_lo: float, jd_hi: float,
                                 engine=None) -> float | None:
    """
    Moira 兼容模式下的罗/计入宿细化: 从窗口起点真实位置出发,
    用固定速度 _FIXED_NODE_SPEED_DEG_DAY 推到 target_T, 不再用真实瞬时速度二分。
    每次从窗口起点重新同步, 避免长期漂移累积。
    """
    pos_lo = _ra_unwrapped_near(body, jd_lo, target_T, engine)
    v = _FIXED_NODE_SPEED_DEG_DAY
    if abs(v) < 1e-12:
        return None
    # 确认方向: 罗/计逆行, target_T 应位于 pos_lo 的负方向
    dt = (target_T - pos_lo) / v
    if dt < 0 or dt > (jd_hi - jd_lo):
        return None
    jd_tr = jd_lo + dt
    return max(jd_lo, min(jd_hi, jd_tr))


def _transit_single(body: str, target: float,
                    jd_start: float, max_jd: float,
                    engine=None) -> float | None:
    """
    单星曜落宿位置过境搜索（鲁棒版）。

    不再使用大跳步 Newton 迭代（容易跳过 0° 卷绕处的宿界），
    改为小步采样 + 解卷绕穿越检测 + 二分细化。
    支持逆行、赤经回退、跨 0° 边界等所有情况。
    """
    if jd_start >= max_jd:
        return None
    step = _MANSION_STEP_BY_BODY.get(body.lower(), 1.0)

    jd_prev = jd_start
    pos_prev = _ra_at(body, jd_prev, engine)
    uprev = pos_prev

    jd = min(jd_prev + step, max_jd)
    while True:
        pos = _ra_at(body, jd, engine)
        # 解卷绕：与上一步的连续位置对齐
        delta = pos - pos_prev
        if delta > 180.0:
            delta -= 360.0
        elif delta < -180.0:
            delta += 360.0
        unow = uprev + delta

        # 检查 [uprev, unow] 是否跨越 target + 360*k（k 为任意整数）
        if unow != uprev:
            if unow > uprev:
                k_min = math.ceil((uprev - target) / 360.0)
                k_max = math.floor((unow - target) / 360.0)
            else:
                k_min = math.ceil((unow - target) / 360.0)
                k_max = math.floor((uprev - target) / 360.0)
            if k_min <= k_max:
                # 取第一个穿越
                target_T = target + 360.0 * k_min
                return _bisect_crossing(body, target_T, jd_prev, jd, engine)

        # 推进
        pos_prev = pos
        uprev = unow
        jd_prev = jd
        if jd >= max_jd:
            break
        jd = min(jd + step, max_jd)

    return None


# ---- 5e. 时间范围生成 ----

def generate_time_points(start: tuple, end: tuple,
                         interval_hours: float = 1.0,
                         tz: float = 8.0) -> list[tuple]:
    """
    生成时间范围内的所有时间点（JD 步进, 支持负年份/公元前）。

    参数:
        start: (y, m, d, h) 起始时间（本地时间）
        end:   (y, m, d, h) 结束时间（本地时间）
        interval_hours: 间隔（小时），支持小数（如 0.5 = 30 分钟）
        tz: 时区

    返回: [(y, m, d, h, jd_ut), ...] 列表
    """
    # 原实现用 datetime 步进, 仅支持 1~9999 年; 改用 JD 步进 + _jd_to_date 反解,
    # 任意年份（含公元前）都可生成时间点, 与 swe 计算范围一致。
    h0 = start[3] if len(start) > 3 else 0
    h1 = end[3] if len(end) > 3 else 0
    jd0 = swe_julday(start[0], start[1], start[2], h0, tz)
    jd1 = swe_julday(end[0], end[1], end[2], h1, tz)
    step = max(interval_hours, 1e-9) / 24.0

    points = []
    n = 0
    while True:
        jd = jd0 + n * step
        if jd > jd1 + 1e-9:
            break
        # JD → 本地日期时刻
        # ★显示口径与 _jd_to_date 完全一致: 分界线按【本地日】判断
        #   (jd_loc + 0.5 的整数部 ≥ 2299161 即北京 1582-10-15 00:00 起格里;
        #   此前儒略)——修复前用 jd(UT) 判断, 北京 1582-10-15 00:00 的 UTC
        #   尚在 10-14, 会误判为儒略段导致时间点显示 10-05 与事件 date 10-15 打架)
        # ★2026-08-16 修复: 原实现调用 _swe.revjul, 但当前环境的 swisseph
        #   精简兼容层(swisseph-ffi)未暴露该函数 → 生成时间点即崩溃;
        #   改用内置 _jd_to_date（同一套历法分界口径）, 分钟精度
        #   （GUI 时间间隔均为整分钟, 等价）。
        y, m, d, hh, mi = _jd_to_date(jd + tz / 24.0)
        points.append((y, m, d, hh + mi / 60.0, jd))
        n += 1
    return points


def export_to_excel(engine, start: tuple, end: tuple,
                    interval_hours: float = 1.0,
                    tz: float = 8.0,
                    output_path: str = "stellar_mansion_output.xlsx",
                    selected_planets: list = None,
                    show_lon: bool = True,
                    show_jd_ayan: bool = True,
                    show_deg_in_mansion: bool = True,
                    show_xingguan: bool = True,
                    detect_events: bool = True,
                    show_speed: bool = False,
                    show_aspects: bool = False,
                    detect_eclipses: bool = False,
                    show_transit_aspects: bool = False,
                    transit_planets: list = None,
                    aspect_indices: list = None,
                    generate_interval_rows: bool = True,  # ★独立开关: 按时间间隔周期生成落宿数据
                    file_format: str = "xlsx",
                    progress_callback=None,
                    fixed_node_speed: bool = False):
    """
    批量计算行星落宿并导出为 Excel。

    赤道恒星制输出赤经/赤纬；郑氏星案恒星制输出恒星黄经/黄纬。

    参数:
        show_speed: 是否输出行星速度状态（迟逆留速伏）
        show_aspects: 是否输出行星间相位
        detect_eclipses: 是否搜索日月食
    """
    planets = selected_planets or list(_ALL_BODIES)

    # CSV 流式直写: 不构建 openpyxl workbook, 每行直接写文件(内存 O(1))
    is_csv = (file_format == "csv" or str(output_path).lower().endswith(".csv"))
    base = str(output_path).replace(".csv", "").replace(".xlsx", "")
    # ★2026-08-16 性能优化: openpyxl 懒加载 —— CSV 导出不再支付 ~0.5s 导入开销
    if is_csv:
        import csv
        wb = None
    else:
        try:
            import openpyxl
            from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
        except ImportError:
            raise ImportError("需要 openpyxl，运行: pip install openpyxl")
        wb = openpyxl.Workbook()

    # 区间起止 JD(本地时间 → UT, 所有事件扫描共用; 与 generate_time_points 首尾一致)
    jd_start = swe_julday(start[0], start[1], start[2], start[3], tz)
    jd_end   = swe_julday(end[0], end[1], end[2], end[3], tz)
    # ★列名历法标注 (用户 2026-08-07 要求): 按区间所在历法标注日期/时间列
    # 2026-08-07 晚细化: 1582-10-15 前标"天文儒略历含公元零年"(天文纪年含 0 年);
    # 判断用日期级(与 swe_julday/_jd_to_date 分界语义一致, 不用 jd 阈值)
    _CAL_SPLIT_DATE = (1582, 10, 15)
    if (end[0], end[1], end[2]) < _CAL_SPLIT_DATE:
        cal_label = "天文儒略历含公元零年"
    elif (start[0], start[1], start[2]) >= _CAL_SPLIT_DATE:
        cal_label = "格里历"
    else:
        cal_label = "天文儒略历含公元零年/格里历"
    # 时间点序列: 仅落宿数据表需要全量(逐点生成);
    # 落宿周期关闭时不生成 points(内存 O(1)), total 按区间/间隔直接计算
    if generate_interval_rows:
        points = generate_time_points(start, end, interval_hours, tz)
        total = len(points)
    else:
        points = None
        total = max(int((jd_end - jd_start) * 24.0 / interval_hours) + 1, 1)

    # ---- 阶段化进度: 各功能独立计算, 统一按总量汇报进度 ----
    # 落宿逐点占主要权重(total); 其余各事件扫描各占一段(total//4)
    w_rows = total if generate_interval_rows else 0          # 落宿数据
    w_man  = (total // 4) if detect_events else 0            # 入宿事件
    w_ec   = (total // 4) if detect_eclipses else 0          # 日月食
    w_ta   = (total // 4) if show_transit_aspects else 0     # 星象日历
    W = max(w_rows + w_man + w_ec + w_ta, 1)
    _done = [0]
    def _report(step):
        _done[0] = min(_done[0] + step, W)
        if progress_callback:
            progress_callback(_done[0], W)

    def _scoped(weight):
        """把扫描函数内部的 (done,total) 映射到总进度 W 的某一段(weight 权重)"""
        base = _done[0]
        def cb(done, total):
            frac = done / total if total else 1.0
            target = base + int(weight * frac)
            step = target - _done[0]
            if step > 0:
                _report(step)
        return cb

    if not is_csv:
        bold_font = Font(bold=True)
        header_fill = PatternFill("solid", fgColor="D9E1F2")
        thin_border = Border(
            left=Side(style="thin"), right=Side(style="thin"),
            top=Side(style="thin"), bottom=Side(style="thin"))

    class _Tbl:
        """统一表写入: xlsx → openpyxl sheet; csv → 流式文件(内存 O(1))"""
        def __init__(self, name, header):
            self.is_csv = is_csv
            if is_csv:
                self.f = open(f"{base}_{name}.csv", "w", newline="", encoding="utf-8-sig")
                self.w = csv.writer(self.f)
                self.w.writerow(header)
            else:
                self.ws = wb.active if name == "落宿数据" else wb.create_sheet(name)
                if name == "落宿数据":
                    self.ws.title = name
                self.ws.append(header)
                for ci in range(1, len(header) + 1):
                    c = self.ws.cell(row=1, column=ci)
                    c.font = bold_font; c.fill = header_fill
                    c.border = thin_border; c.alignment = Alignment(horizontal="center")
        def append(self, row):
            if self.is_csv:
                self.w.writerow(row)
            else:
                self.ws.append(row)
        def finish(self):
            if self.is_csv:
                self.f.close()
            else:
                self.ws.freeze_panes = "A2"
                for col in self.ws.columns:
                    ml = 0
                    cl = col[0].column_letter
                    for cell in col:
                        try:
                            ml = max(ml, len(str(cell.value)))
                        except Exception:
                            pass
                    self.ws.column_dimensions[cl].width = min(ml + 3, 25)

    # ==== Sheet 1: 落宿数据（按时间间隔周期生成）====
    # 独立开关 generate_interval_rows: 关闭时不生成落宿数据表,
    # 不影响入宿事件/日月食/星象日历（它们各自独立扫描区间）
    if generate_interval_rows:
        is_equ = getattr(engine, '_is_equatorial', False)
        header = [f"日期({cal_label})", "时间(本地)"]
        if show_jd_ayan:
            header += ["儒略日(UT)", "Ayanamsa(°)"]
            if is_equ:
                header += ["平黄赤交角(°)"]
        for p in planets:
            cn = PLANET_NAMES.get(p, p)
            if show_lon:
                header += [f"{cn}_恒星黄经(°)"]
                if is_equ:
                    header += [f"{cn}_赤经(°)", f"{cn}_赤纬(°)"]
                else:
                    header += [f"{cn}_黄纬(°)"]
            header += [f"{cn}_落宿", f"{cn}_五行"]
            if show_deg_in_mansion:
                header += [f"{cn}_宿内度(°)"]
            if show_xingguan:
                header += [f"{cn}_宫位(宫度)", f"{cn}_星官"]
            if show_speed:
                header += [f"{cn}_状态"]
        if show_aspects:
            header += ["相位(赤经)"] if is_equ else ["相位(黄经)"]
        tbl1 = _Tbl("落宿数据", header)

        for idx, (y, m, d, h, jd) in enumerate(points):
            ayan = swe_get_ayanamsa(jd)
            eps = swe_mean_obliquity(jd)
            date_str = f"{y:04d}-{m:02d}-{d:02d}"
            hh = int(h)
            mm_part = int((h - hh) * 60)
            time_str = f"{hh:02d}:{mm_part:02d}"

            row = [date_str, time_str]
            if show_jd_ayan:
                row += [round(jd, 4), round(ayan, 6)]
                if is_equ:
                    row += [round(eps, 6)]

            aspect_pos = {} if show_aspects else None

            for p in planets:
                pos, slon, aux, _ = _engine_pos(p, jd, engine)
                if show_aspects:
                    aspect_pos[p] = pos
                mansion = engine.get_mansion(pos, full=True)
                element = engine.get_mansion_element(pos)
                deg_in = engine.degree_within_mansion(pos)

                if show_lon:
                    row += [round(slon, 6)]
                    if is_equ:
                        row += [round(pos, 6), round(aux, 6)]  # pos=RA, aux=Dec
                    else:
                        row += [round(aux, 6)]  # aux=恒星黄纬
                row += [mansion, element]
                if show_deg_in_mansion:
                    row += [round(deg_in, 4)]
                if show_xingguan:
                    ltc = liangtianchi_lookup(pos)
                    row += [f"{ltc['palace']} {ltc['palace_deg_text']}",
                            ltc['xingguan']]
                if show_speed:
                    sp = get_planet_speed_state(p, jd, engine)
                    row += [sp['state_name'] if sp else '-']

            if show_aspects:
                asp_list = compute_aspects(aspect_pos)
                row.append(" | ".join(f"{PLANET_NAMES.get(a, a)}{PLANET_NAMES.get(b, b)}{n}"
                                       for a, b, _, _, n in asp_list) if asp_list else "")

            tbl1.append(row)
            _report(1)   # 逐时间点汇报进度
        tbl1.finish()
    else:
        # 不生成落宿数据表
        if is_csv:
            pass  # CSV 流式: 无落宿文件
        else:
            wb.remove(wb.active)
            # 若最终没有任何数据表, 由函数末尾统一创建"无数据"占位 sheet

    # ==== Sheet 2: 入宿事件 (精确穿越宿界) ====
    events = []
    if detect_events:
        entries = compute_mansion_entries(jd_start, jd_end, planets, engine, tz,
                                          progress_callback=_scoped(w_man),
                                          fixed_node_speed=fixed_node_speed)
        events = entries
        # 注: 不再重复 _report(w_man) —— _scoped 已把入宿段进度走完,
        #     旧代码重复叠加导致进度跳两段(33→66)
        if events:
            tbl2 = _Tbl("入宿事件", [f"时间({cal_label})", "星体", "事件", "原宿", "新宿",
                                     "速度(°/天)", "自校(°)", f"停留结束({cal_label})"])
            for ev in events:
                spd = ev.get('speed_deg_day', '')
                tbl2.append([
                    ev['date'], ev['planet'],
                    f"{ev['planet']}进入{ev['mansion']}",
                    ev['from_mansion'], ev['mansion'],
                    spd,
                    ev.get('self_check_deg', ''),
                    ev.get('leave_date', ''),
                ])
            tbl2.finish()

    # ==== Sheet 3: 日月食 ====
    ec_count = 0
    if detect_eclipses:
        eclipses = find_eclipses(jd_start, jd_end, engine)
        _report(w_ec)   # 日月食扫描完成
        tbl3 = _Tbl("日月食", ["类型", f"日期({cal_label},北京时间)", "儒略日(JD)",
                               "地点", "发生地", "日_落宿", "日_宿内度", "月_落宿", "月_宿内度"])
        for kind, eclist in [("日食", eclipses['solar']), ("月食", eclipses['lunar'])]:
            for ec in eclist:
                # ★发生地 (Moira 源码 ChartData:8225-8250: 日食 anywhere 模式用
                #   swe_sol_eclipse_where 求发生地经纬度; 月食全球可见无单一发生地)
                where = ""
                if kind == "日食" and hasattr(_swe, "sol_eclipse_where"):
                    try:
                        _ret, _geo, _attr = _swe.sol_eclipse_where(ec['jd'], _swe.FLG_SWIEPH)
                        lon, lat = _geo[0], _geo[1]
                        where = (f"{abs(lon):.1f}°{'W' if lon < 0 else 'E'} "
                                 f"{abs(lat):.1f}°{'S' if lat < 0 else 'N'}")
                    except Exception:
                        where = ""
                else:
                    where = "全球可见"
                tbl3.append([
                    ec['type_name'],
                    _fmt_datetime(ec['jd'], LOCATION_TZ),   # ★发生地当地时间 → 换算北京时间(固定, 不随 GUI tz 变)
                    round(ec['jd'], 4),
                    LOCATION_DESC,
                    where,
                    ec.get('sun_mansion', ''),
                    ec.get('sun_deg', ''),
                    ec.get('moon_mansion', ''),
                    ec.get('moon_deg', ''),
                ])
                ec_count += 1
        tbl3.finish()

    # ==== Sheet 4: 星象日历 (赤经流年相位) ====
    ta_count = 0
    if show_transit_aspects:
        transits = compute_transit_aspects(jd_start, jd_end,
                                           transit_planets or planets,
                                           aspect_indices or list(_DEFAULT_ASPECT_INDICES),
                                           engine=engine,
                                           progress_callback=_scoped(w_ta),
                                           tz=tz)
        _report(w_ta)   # 星象日历扫描完成
        if transits:
            tbl4 = _Tbl("星象日历", [f"时间({cal_label})", "星体A", "星体B", "相位", "角度(°)", "容许度(°)",
                                     "A_位置", "A_宿", "A_宿度", "A_宫", "A_宫度",
                                     "B_位置", "B_宿", "B_宿度", "B_宫", "B_宫度"])
            for t in transits:
                tbl4.append([_fmt_datetime(t['jd'], tz), t['p1'], t['p2'], t['name'],
                             t['angle'], t['orb'],
                             t.get('p1_zodiac_text', ''),
                             t.get('p1_mansion', ''), t.get('p1_mansion_deg', ''),
                             t.get('p1_zodiac', ''), t.get('p1_zodiac_deg', ''),
                             t.get('p2_zodiac_text', ''),
                             t.get('p2_mansion', ''), t.get('p2_mansion_deg', ''),
                             t.get('p2_zodiac', ''), t.get('p2_zodiac_deg', '')])
                ta_count += 1
            tbl4.finish()

    if not is_csv:
        if not wb.sheetnames:
            # 落宿周期与所有事件都未勾选时, 保证 workbook 至少有一个可见 sheet 可保存
            ws_empty = wb.create_sheet("无数据")
            ws_empty.append(["未勾选任何数据表(落宿周期与事件均关闭)"])
        wb.save(output_path)
    return output_path, len(events) if detect_events else 0, ec_count, ta_count


# =====================================================================
# 6. 可视化界面 (tkinter)
# =====================================================================

def launch_gui():
    """启动可视化界面"""
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox

    root = tk.Tk()
    root.title("恒星制双模式 — 批量落宿导出")
    root.geometry("720x600")
    root.resizable(True, True)
    root.configure(bg="white")

    style = ttk.Style()
    style.theme_use("clam")
    style.configure(".", background="white")
    style.configure("TLabelframe", background="white")
    style.configure("TLabelframe.Label", background="white")
    style.configure("TLabel", background="white")
    style.configure("TCheckbutton", background="white")

    main = ttk.Frame(root, padding=12)
    main.pack(fill="both", expand=True)

    # ---- 日期范围 (一行) ----
    date_frame = ttk.LabelFrame(main, text="时间范围 (北京时间)", padding=8)
    date_frame.pack(fill="x", pady=(0, 8))
    for c in range(11):
        date_frame.columnconfigure(c, weight=1)

    # 起始: 天文纪年直接输入(含负年份=公元前; 0=公元前1年), 复原自 2026-08-07
    # 加"公元前"复选框之前的 GUI——该改动把 Spinbox 范围改成 1~5400 导致负数
    # 年份无法输入/输出, 用户要求复原
    ttk.Label(date_frame, text="起始").grid(row=0, column=0, sticky="e", padx=3)
    sy = ttk.Spinbox(date_frame, from_=-5400, to=5400, width=6); sy.set(2026)
    sy.grid(row=0, column=1)
    ttk.Label(date_frame, text="年").grid(row=0, column=2)
    sm = ttk.Spinbox(date_frame, from_=1, to=12, width=4); sm.set(7)
    sm.grid(row=0, column=3)
    ttk.Label(date_frame, text="月").grid(row=0, column=4)
    sd = ttk.Spinbox(date_frame, from_=1, to=31, width=4); sd.set(10)
    sd.grid(row=0, column=5)
    ttk.Label(date_frame, text="日").grid(row=0, column=6)
    sh = ttk.Spinbox(date_frame, from_=0, to=23, width=4); sh.set(0)
    sh.grid(row=0, column=7)
    ttk.Label(date_frame, text="时").grid(row=0, column=8)
    smin = ttk.Spinbox(date_frame, from_=0, to=59, width=4); smin.set(0)
    smin.grid(row=0, column=9)
    ttk.Label(date_frame, text="分").grid(row=0, column=10)

    ttk.Label(date_frame, text="结束").grid(row=1, column=0, sticky="e", padx=3, pady=3)
    ey = ttk.Spinbox(date_frame, from_=-5400, to=5400, width=6); ey.set(2026)
    ey.grid(row=1, column=1, pady=3)
    ttk.Label(date_frame, text="年").grid(row=1, column=2, pady=3)
    em = ttk.Spinbox(date_frame, from_=1, to=12, width=4); em.set(7)
    em.grid(row=1, column=3, pady=3)
    ttk.Label(date_frame, text="月").grid(row=1, column=4, pady=3)
    ed = ttk.Spinbox(date_frame, from_=1, to=31, width=4); ed.set(10)
    ed.grid(row=1, column=5, pady=3)
    ttk.Label(date_frame, text="日").grid(row=1, column=6, pady=3)
    eh = ttk.Spinbox(date_frame, from_=0, to=23, width=4); eh.set(23)
    eh.grid(row=1, column=7, pady=3)
    ttk.Label(date_frame, text="时").grid(row=1, column=8, pady=3)
    emin = ttk.Spinbox(date_frame, from_=0, to=59, width=4); emin.set(0)
    emin.grid(row=1, column=9, pady=3)
    ttk.Label(date_frame, text="分").grid(row=1, column=10, pady=3)

    # ---- 时区 & 恒星制 & 宿界 & 输出格式 ----
    # 注: 时间间隔已移入「输出字段」的落宿周期旁 —— 它只对落宿数据表有意义,
    # 入宿/日月食/星象日历仅取区间首尾, 不依赖间隔, 故不属于基本功能
    opts_frame = ttk.LabelFrame(main, text="基本设置", padding=8)
    opts_frame.pack(fill="x", pady=(0, 8))

    ttk.Label(opts_frame, text="UTC+").grid(row=0, column=0, padx=3)
    tz_var = tk.IntVar(value=8)
    ttk.Spinbox(opts_frame, from_=-12, to=14, width=4, textvariable=tz_var)\
        .grid(row=0, column=1)

    ttk.Label(opts_frame, text="恒星制:").grid(row=0, column=2, padx=(20, 3))
    mode_var = tk.StringVar(value="赤道恒星制")
    ttk.Combobox(opts_frame, textvariable=mode_var, width=12,
                  values=["赤道恒星制", "郑氏星案恒星制"],
                  state="readonly").grid(row=0, column=3)

    ttk.Label(opts_frame, text="宿界:").grid(row=0, column=4, padx=(20, 3))
    bound_var = tk.StringVar(value="默认")
    ttk.Combobox(opts_frame, textvariable=bound_var, width=10,
                  values=["默认", "星海词林原版", "星海词林改版"],
                  state="readonly").grid(row=0, column=5)

    ttk.Label(opts_frame, text="格式:").grid(row=0, column=6, padx=(20, 3))
    fmt_var = tk.StringVar(value="xlsx")
    ttk.Combobox(opts_frame, textvariable=fmt_var, width=6,
                  values=["xlsx", "csv"], state="readonly").grid(row=0, column=7)

    # ---- 行星选择 (一行) ----
    planet_frame = ttk.LabelFrame(main, text="选择星体", padding=8)
    planet_frame.pack(fill="x", pady=(0, 8))
    planet_vars = {}
    planets_ch = [("日", "sun"), ("月", "moon"), ("水", "mercury"), ("金", "venus"),
                  ("火", "mars"), ("木", "jupiter"), ("土", "saturn"),
                  ("天", "uranus"), ("海", "neptune"), ("冥", "pluto"),
                  ("计", "keti"), ("罗", "rahu"), ("炁", "qi"), ("孛", "bei")]
    for i, (label, key) in enumerate(planets_ch):
        v = tk.BooleanVar(value=True)
        planet_vars[key] = v
        tk.Checkbutton(planet_frame, text=label, variable=v)\
            .grid(row=0, column=i, sticky="w", padx=4, pady=2)

    # ---- 输出字段 (一行) ----
    field_frame = ttk.LabelFrame(main, text="输出字段", padding=8)
    field_frame.pack(fill="x", pady=(0, 8))

    show_lon_var = tk.BooleanVar(value=True)
    show_jd_var  = tk.BooleanVar(value=True)
    show_deg_var = tk.BooleanVar(value=True)
    show_xg_var = tk.BooleanVar(value=True)  # ★量天尺宫位/星官 (2026-09-13)
    detect_ev_var = tk.BooleanVar(value=True)
    show_speed_var = tk.BooleanVar(value=False)
    show_aspects_var = tk.BooleanVar(value=False)
    detect_ec_var = tk.BooleanVar(value=False)
    show_ta_var = tk.BooleanVar(value=False)
    interval_rows_var = tk.BooleanVar(value=True)  # ★按时间间隔周期生成落宿数据(独立开关, 默认开)
    fixed_node_speed_var = tk.BooleanVar(value=False)  # ★Moira 兼容: 罗/计用固定速度推进

    tk.Checkbutton(field_frame, text="经纬/赤经纬", variable=show_lon_var)\
        .grid(row=0, column=0, padx=3)
    tk.Checkbutton(field_frame, text="JD/岁差/交角", variable=show_jd_var)\
        .grid(row=0, column=1, padx=3)
    tk.Checkbutton(field_frame, text="宿内度", variable=show_deg_var)\
        .grid(row=0, column=2, padx=3)
    tk.Checkbutton(field_frame, text="入宿事件", variable=detect_ev_var)\
        .grid(row=0, column=3, padx=3)
    tk.Checkbutton(field_frame, text="迟逆留伏", variable=show_speed_var)\
        .grid(row=0, column=4, padx=3)
    tk.Checkbutton(field_frame, text="相位", variable=show_aspects_var)\
        .grid(row=0, column=5, padx=3)
    tk.Checkbutton(field_frame, text="日月食", variable=detect_ec_var)\
        .grid(row=0, column=6, padx=3)
    tk.Checkbutton(field_frame, text="星象日历", variable=show_ta_var)\
        .grid(row=0, column=7, padx=3)

    def _sync_interval_state():
        # 时间间隔只对落宿数据表有意义: 落宿周期未勾选时禁用
        intv_combo.config(state="readonly" if interval_rows_var.get() else "disabled")

    tk.Checkbutton(field_frame, text="落宿周期", variable=interval_rows_var,
                   command=_sync_interval_state)\
        .grid(row=0, column=8, padx=3)
    ttk.Label(field_frame, text="间隔(分):").grid(row=0, column=9, padx=(6, 0))
    interval_var = tk.DoubleVar(value=60)
    intv_combo = ttk.Combobox(field_frame, textvariable=interval_var, width=5,
                              values=[1, 5, 10, 15, 30, 60, 120, 360, 720, 1440],
                              state="readonly"); intv_combo.set(60)
    intv_combo.grid(row=0, column=10, padx=(0, 6))

    tk.Checkbutton(field_frame, text="Moira兼容: 罗/计固定速度(-0.05299°/天)",
                   variable=fixed_node_speed_var)\
        .grid(row=1, column=0, columnspan=4, sticky="w", padx=3, pady=(6, 0))
    tk.Checkbutton(field_frame, text="星官(量天尺)", variable=show_xg_var)\
        .grid(row=1, column=4, columnspan=3, sticky="w", padx=3, pady=(6, 0))

    # ---- 高级: 星象日历设置 (可折叠) ----
    ta_shown = tk.BooleanVar(value=False)
    ta_toggle = ttk.Checkbutton(main, text="▼ 星象日历设置 (相位 & 星体选择)",
                                 variable=ta_shown,
                                 command=lambda: toggle_frame(ta_frame, ta_shown))
    ta_toggle.pack(fill="x", pady=(0, 2))

    ta_frame = ttk.LabelFrame(main, text="", padding=8)

    def toggle_frame(frame, var):
        if var.get():
            frame.pack(fill="x", pady=(0, 8), before=out_frame)
        else:
            frame.pack_forget()

    aspect_vars = {}
    asp_row1 = ttk.Frame(ta_frame)
    asp_row1.pack(fill="x")
    ttk.Label(asp_row1, text="相位:").pack(side="left", padx=3)
    for i, (ang, name) in enumerate(zip(_ASPECT_ANGLES, _ASPECT_NAMES)):
        # 默认多勾选: 会/冲/刑/三合/六合 (原默认 + 六合60°)
        v = tk.BooleanVar(value=(ang in (0.0, 60.0, 90.0, 120.0, 180.0)))
        aspect_vars[i] = v
        tk.Checkbutton(asp_row1, text=f"{name}({ang}°)", variable=v)\
            .pack(side="left", padx=3)

    transit_frame = ttk.Frame(ta_frame)
    transit_frame.pack(fill="x", pady=(5, 0))
    ttk.Label(transit_frame, text="星体:").pack(side="left", padx=3)
    transit_planet_vars = {}
    for label, key in planets_ch:
        v = tk.BooleanVar(value=(key in ['sun','moon','mercury','venus','mars',
                                          'jupiter','saturn','uranus','neptune','pluto',
                                          'keti','rahu','qi','bei']))
        transit_planet_vars[key] = v
        tk.Checkbutton(transit_frame, text=label, variable=v).pack(side="left", padx=2)

    # ---- 输出路径 ----
    out_frame = ttk.LabelFrame(main, text="输出文件", padding=8)
    out_frame.pack(fill="x", pady=(0, 8))

    out_path_var = tk.StringVar(value="stellar_mansion_output")
    ttk.Entry(out_frame, textvariable=out_path_var, width=60)\
        .grid(row=0, column=0, padx=3)
    ttk.Button(out_frame, text="浏览...", width=8,
               command=lambda: out_path_var.set(
                   filedialog.asksaveasfilename(
                       defaultextension=".xlsx" if fmt_var.get()=="xlsx" else ".csv",
                       filetypes=[("Excel","*.xlsx"),("CSV","*.csv")],
                       initialfile=out_path_var.get()) or out_path_var.get()))\
        .grid(row=0, column=1, padx=3)

    # ---- 进度 & 运行 ----
    bottom = ttk.Frame(main)
    bottom.pack(fill="x", pady=(5, 0))
    progress = ttk.Progressbar(bottom, mode="determinate", length=400)
    progress.pack(side="left", padx=(0, 10))
    status_label = ttk.Label(bottom, text="就绪")
    status_label.pack(side="left")

    # ---- 后台线程 + 队列轮询: 计算在子线程, 进度/结果回主线程更新, 窗口不假死 ----
    progress_q = queue.Queue()

    def poll_progress():
        try:
            while True:
                msg = progress_q.get_nowait()
                kind = msg[0]
                if kind == "progress":
                    progress["maximum"] = msg[2]
                    progress["value"] = msg[1]
                    pct = round(msg[1] / msg[2] * 100) if msg[2] else 0
                    status_label.config(text=f"计算中... {pct}% ({msg[1]}/{msg[2]})")
                elif kind == "done":
                    total, ev, ec, ta, out = msg[1:]
                    progress["value"] = progress["maximum"]
                    msg_s = f"完成! {total} 个时间点"
                    if ev > 0:
                        msg_s += f", {ev} 次入宿事件"
                    if ec > 0:
                        msg_s += f", {ec} 次日/月食"
                    if ta > 0:
                        msg_s += f", {ta} 次流年相位"
                    msg_s += f"\n→ {out}"
                    status_label.config(text=msg_s.replace("\n", " | "))
                    messagebox.showinfo("完成", msg_s)
                elif kind == "error":
                    status_label.config(text="出错")
                    messagebox.showerror("错误", msg[1])
        except queue.Empty:
            pass
        root.after(100, poll_progress)

    def do_export():
        # ---- 参数收集与校验(主线程) ----
        try:
            # 天文纪年直接输入(含负年份=公元前; 0=公元前1年)
            sy_v = int(sy.get()); ey_v = int(ey.get())
            start = (sy_v, int(sm.get()), int(sd.get()),
                     int(sh.get()) + int(smin.get()) / 60.0)
            end   = (ey_v, int(em.get()), int(ed.get()),
                     int(eh.get()) + int(emin.get()) / 60.0)
            iv_min = interval_var.get()
            iv_hours = iv_min / 60.0
            tz = tz_var.get()
            out = out_path_var.get()
            sel = [k for k, v in planet_vars.items() if v.get()]
            ta_planets = [k for k, v in transit_planet_vars.items() if v.get()]
            ta_aspects = [i for i, v in aspect_vars.items() if v.get()]

            # 恒星制与宿界选择
            cls = EquatorialStellar if mode_var.get() == "赤道恒星制" else ZhengCaseSidereal
            bname = bound_var.get()
            if bname == "星海词林原版":
                engine_use = cls(XHCL_ORIG_BOUNDARIES)
            elif bname == "星海词林改版":
                engine_use = cls(XHCL_REVISED_BOUNDARIES)
            else:
                engine_use = cls()

            if not sel:
                messagebox.showwarning("提示", "请至少选择一个星体")
                return
            if show_ta_var.get() and not ta_planets:
                messagebox.showwarning("提示", "星象日历需要至少选择一个参与星体")
                return
            if show_ta_var.get() and not ta_aspects:
                messagebox.showwarning("提示", "星象日历需要至少选择一个相位角度")
                return

            fmt = fmt_var.get()
            if not (out.endswith(".xlsx") or out.endswith(".csv")):
                out = out + (".xlsx" if fmt == "xlsx" else ".csv")
            # 仅算时间点数用于进度条 maximum(不生成全量列表, 4200 年 × 1h 也会省下 GB 级内存)
            _jd0 = swe_julday(start[0], start[1], start[2], start[3], tz)
            _jd1 = swe_julday(end[0], end[1], end[2], end[3], tz)
            total = max(int((_jd1 - _jd0) * 24.0 / iv_hours) + 1, 1)
        except Exception as e:
            messagebox.showerror("错误", str(e))
            return

        # ---- 计算放后台线程, 进度队列更新, 窗口不假死 ----
        status_label.config(text="计算中... 0%")
        progress["value"] = 0
        root.update()

        def worker():
            try:
                def cb(cur, tot):
                    progress_q.put(("progress", cur, tot))
                _, ev_count, ec_count, ta_count = export_to_excel(
                    engine_use, start, end, iv_hours, tz, out, sel,
                    show_lon=show_lon_var.get(),
                    show_jd_ayan=show_jd_var.get(),
                    show_deg_in_mansion=show_deg_var.get(),
                    show_xingguan=show_xg_var.get(),
                    detect_events=detect_ev_var.get(),
                    show_speed=show_speed_var.get(),
                    show_aspects=show_aspects_var.get(),
                    detect_eclipses=detect_ec_var.get(),
                    show_transit_aspects=show_ta_var.get(),
                    generate_interval_rows=interval_rows_var.get(),
                    transit_planets=ta_planets,
                    aspect_indices=ta_aspects,
                    file_format=fmt,
                    progress_callback=cb,
                    fixed_node_speed=fixed_node_speed_var.get(),
                )
                progress_q.put(("done", total, ev_count, ec_count, ta_count, out))
            except Exception as e:
                progress_q.put(("error", str(e)))

        threading.Thread(target=worker, daemon=True).start()

    ttk.Button(bottom, text="开始导出", width=12, command=do_export)\
        .pack(side="right", padx=(10, 0))

    root.after(100, poll_progress)   # 启动后台进度轮询
    root.mainloop()


# =====================================================================
# 8. 占星子功能模块 moira_astro (★2026-08-16 新增, 文件暂时独立)
# =====================================================================
# 从 moira_proj.jar 反编译源码提炼的西方占星功能, 作为本文件的【子功能模块】,
# 文件 moira_astro.py 暂时独立维护 (可单独运行), 由本文件懒加载后统一调用:
#   星座(黄道十二宫)落座 / 逆行开始结束时刻 / 西方相位 / 分宫制(需完整 pyswisseph)
# 与主引擎共用 swisseph 进程; 恒星制 sid_mode 为进程级全局, 子模块设置其他
# 岁差模式后, 主引擎每次计算前的 _ensure_sid_mode 会自动恢复 SIDM_USER(255),
# 二者互不污染。
_ASTRO_MODULE = None


def get_astro():
    """懒加载占星子功能模块 moira_astro (与本文件同目录)。
    返回模块对象; 模块文件缺失时返回 None (主功能不受影响)。"""
    global _ASTRO_MODULE
    if _ASTRO_MODULE is None:
        try:
            import moira_astro as _m
        except ImportError:
            try:
                import importlib.util as _ilu
                import os as _os
                _path = _os.path.join(
                    _os.path.dirname(_os.path.abspath(__file__)), "moira_astro.py")
                _spec = _ilu.spec_from_file_location("moira_astro", _path)
                _m = _ilu.module_from_spec(_spec)
                _spec.loader.exec_module(_m)
            except Exception:
                return None
        _ASTRO_MODULE = _m
    return _ASTRO_MODULE


def astro_zodiac(body, year, month, day, hour=12.0, tz=8.0, sidereal=0):
    """星座落座 (经子功能模块): (序号, 星座名, 英文名, 宫内度数, 元素)。

    sidereal: 0 = 回归黄道 (西方标准); 255 = 郑案恒星黄道
    (SIDM_USER 1300-01-01 4.0°, 与本文件恒星制同口径); 其余为标准岁差模式 id。
    模块缺失时返回 None。
    """
    a = get_astro()
    if a is None:
        return None
    return a.zodiac_of_planet(body, a.julday(year, month, day, hour, tz), sidereal)


def astro_retrograde_periods(body, y1, y2, m1=1, d1=1, m2=1, d2=1, tz=8.0):
    """逆行起止区间 (经子功能模块): [(start_jd, end_jd, start_str, end_str), ...]

    逆行开始/结束 = 留点(速度过零, Moira computeSpeedTransit/SEFLG_TRANSIT_SPEED)。
    模块缺失时返回 []。
    """
    a = get_astro()
    if a is None:
        return []
    return a.retrograde_periods(body, y1, y2, m1, d1, m2, d2, tz)


def astro_stations(body, jd_start, jd_end):
    """区间内全部留点 (经子功能模块): [{'jd','kind','kind_name'}, ...]。
    模块缺失时返回 []。"""
    a = get_astro()
    if a is None:
        return []
    return a.stations_in_range(body, jd_start, jd_end)


def astro_next_station(body, jd_start, backward=False):
    """下一个(或上一个)留点时刻 = 逆行开始/结束 (经子功能模块)。
    模块缺失时返回 None。"""
    a = get_astro()
    if a is None:
        return None
    return a.next_station(body, jd_start, backward)


# =====================================================================
# 7. 测试
# =====================================================================

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        y, m, d, h, TZ = 2026, 7, 10, 12, 8.0
        print("=" * 80)
        print("  恒星制双模式 v4 — Swiss Ephemeris 原生引擎 (+量天尺星官)")
        print("=" * 80)
        print(f"  引擎: swisseph, 基准: 1300-01-01, ayanamsa(t0)=4.0°")
        print(f"  日期: {y}-{m:02d}-{d:02d} {h:02d}:00 北京时间\n")

        # 郑氏星案恒星制
        print("  【郑氏星案恒星制】恒星黄经直接落宿 | 星官按恒星黄经宫度查量天尺")
        print(f"  {'星体':<4} {'恒星黄经':>10} {'黄纬':>10}  落宿             宫位(宫度)     星官")
        print(f"  {'-'*76}")
        zcs = ZhengCaseSidereal()
        for p in zcs.get_all_planets_mansion(y, m, d, h, TZ):
            cn = PLANET_NAMES.get(p['planet'], p['planet'])
            print(f"  {cn:<4} {p['sidereal_lon']:>10.4f} {p['sidereal_lat']:>+10.4f}  "
                  f"{p['mansion_formatted']:<14}  {p['palace']} {p['palace_deg']:<8} "
                  f"{p['xingguan']}")

        print()

        # 赤道恒星制
        print("  【赤道恒星制】恒星黄道 → (当日平黄赤交角旋转) → 赤经落宿 | 星官按赤经宫度查表")
        print(f"  {'星体':<4} {'恒星黄经':>10} {'赤经':>10} {'赤纬':>10}  落宿             宫位(宫度)     星官")
        print(f"  {'-'*90}")
        eqs = EquatorialStellar()
        for p in eqs.get_all_planets_mansion(y, m, d, h, TZ):
            cn = PLANET_NAMES.get(p['planet'], p['planet'])
            print(f"  {cn:<4} {p['sidereal_lon']:>10.4f} {p['ra']:>10.4f} "
                  f"{p['dec']:>+10.4f}  {p['mansion_formatted']:<14}  "
                  f"{p['palace']} {p['palace_deg']:<8} {p['xingguan']}")
        print(f"\n{'=' * 80}")
    elif len(sys.argv) > 2 and sys.argv[1] == "--liunian":
        # 流年星官: 立春交节时刻快照, 两制对照
        year = int(sys.argv[2])
        res = liunian_xingguan(year)
        print("=" * 80)
        print(f"  流年星官 · {year} 年 (换年口径: 立春)")
        print("=" * 80)
        print(f"  立春交节: {res['lichun_text']} 北京时间 (JD {res['lichun_jd']})\n")

        print("  【郑氏星案恒星制】")
        print(f"  {'星体':<4} {'恒星黄经':>10}  落宿             宫位(宫度)     星官")
        print(f"  {'-'*64}")
        for p in res["zheng"]:
            cn = PLANET_NAMES.get(p['planet'], p['planet'])
            print(f"  {cn:<4} {p['sidereal_lon']:>10.4f}  "
                  f"{p['mansion_formatted']:<14}  {p['palace']} {p['palace_deg']:<8} "
                  f"{p['xingguan']}")

        print()
        print("  【赤道恒星制】")
        print(f"  {'星体':<4} {'赤经':>10} {'赤纬':>10}  落宿             宫位(宫度)     星官")
        print(f"  {'-'*78}")
        for p in res["equatorial"]:
            cn = PLANET_NAMES.get(p['planet'], p['planet'])
            print(f"  {cn:<4} {p['ra']:>10.4f} {p['dec']:>+10.4f}  "
                  f"{p['mansion_formatted']:<14}  {p['palace']} {p['palace_deg']:<8} "
                  f"{p['xingguan']}")
        print(f"\n{'=' * 80}")
    else:
        launch_gui()
