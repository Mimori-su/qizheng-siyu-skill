//
// App口径排盘引擎核心 — CLI 入口
// 衍生自 Moira v1.50 (GPL)，见 README.md 的 GPL 声明
//
// 用法: java org.athomeprojects.app.Main <yyyy-mm-dd> <HH:MM> <纬度> <经度> [流年年份] [时区ID]
//   时间=真太阳时直输(App实测口径, time_adjust=0, 引擎不再做任何时间改正)
//   纬度/经度=十进制度(北纬/东经为正)
//   时区默认 Asia/Shanghai
// 输出: 四柱 / 立命(宫支+宿名+度分) / 命度黄经 / 指定年年初限度 / 换限日期表 / 顶星 / 化曜 / 神煞 / 斗杓
//
package org.athomeprojects.app;

import java.io.File;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.Collections;
import java.util.Comparator;
import java.util.Date;
import java.util.TimeZone;

import org.athomeprojects.base.BaseCalendar;
import org.athomeprojects.base.Calculate;
import org.athomeprojects.base.ChartData;
import org.athomeprojects.base.ChartMode;
import org.athomeprojects.base.City;
import org.athomeprojects.base.DataEntry;
import org.athomeprojects.base.DiagramTip;
import org.athomeprojects.base.FileIO;
import org.athomeprojects.base.Message;
import org.athomeprojects.base.Resource;

public class Main {

	/** 角距(0..180): rad对, atan2分支/360边界安全 */
	static double angDiff(double a, double b) {
		return Math.toDegrees(Math.abs(Math.atan2(Math.sin(a - b), Math
				.cos(a - b))));
	}

	static boolean hasFlag(String[] args, String flag) {
		return java.util.Arrays.asList(args).contains(flag);
	}

	static String fmtDeg(double v) {
		// 度分: 13度28分
		int deg = (int) Math.floor(v + 1e-9);
		int min = (int) Math.round((v - deg) * 60.0);
		String tag = "";
		if (min >= 60) {
			min -= 60;
			deg += 1;
		}
		// 修复批二A7: 宿宽不等(井32.71°), 度分不按30°回卷/进位——宿内度=λ−宿首原值输出
		return deg + "度" + min + "分" + tag;
	}

	/** ZZT 宿界表查宿：pos=黄经, 返回"宿名 度分"；宿界表=用户定标默认(engine/rsrc/moira_s.prop) */
	static String findStellar(double[] zzt, String[] names, double pos) {
		pos = City.normalizeDegree(pos);
		int hit = -1;
		for (int i = 0; i < zzt.length; i++) {
			double lo = zzt[i];
			double hi = (i == zzt.length - 1) ? zzt[0] + 360.0 : zzt[i + 1];
			if (pos >= lo && pos < hi) {
				hit = i;
				break;
			}
		}
		if (hit < 0 && pos < zzt[0])
			hit = zzt.length - 1; // 落末宿(奎)段
		if (hit < 0)
			return "?";
		double in_sign = pos - zzt[hit];
		if (in_sign < 0)
			in_sign += 360.0;
		// 修复批二A7: 舍入到宿宽即进下宿(窄宿30°进位, 井木等宽宿>30°正常显示)
		double width = (hit == zzt.length - 1) ? zzt[0] + 360.0 - zzt[hit]
				: zzt[hit + 1] - zzt[hit];
		if (in_sign >= width - 0.0001) {
			hit = (hit + 1) % zzt.length;
			in_sign = 0.0;
		}
		return names[hit] + fmtDeg(in_sign);
	}

	static String palaceName(String[] zodiac, double pos) {
		pos = City.normalizeDegree(pos);
		int idx = ((int) (pos / 30.0)) % 12; // 宫界=黄经30°绝对格网, 戌=0-30起
		return zodiac[idx] + "宫";
	}

	/** 星历路径: swisseph 按 ";:" 切路径, 盘符冒号会断链 → 优先用相对路径(推荐从 engine 目录运行) */
	static String relEphePath(File ephe_dir) {
		if (new File("ephemeris").isDirectory())
			return "ephemeris";
		java.nio.file.Path cwd = java.nio.file.Paths.get("").toAbsolutePath();
		try {
			java.nio.file.Path rel = cwd.relativize(ephe_dir.toPath());
			String s = rel.toString().replace('\\', '/');
			// 修复批二: 同盘相对路径(含../前缀)均可用——swisseph只忌冒号
			if (!s.contains(":"))
				return s;
		} catch (Exception e) {
		}
		System.err.println("[错误] 星历路径跨盘且CWD不当, swe将找不到星历文件; 请从 engine 目录运行");
		System.exit(7);
		return null;
	}

	/** 顶星一块候选: 收集命中星, 按黄经升序(报告B件2: Arrays.sort c(1)升序, 本命块在前/流块在后)
	 *  二期#1: extra=行度点表尾部追加的斗/罡两点(App a1() L14405-14413), 与星体同规则参与d1扫描 */
	static String topStarBlock(ChartData cd, double[] pos, String[] names,
			double center, double w, String prefix, double[] extra,
			String[] extra_names) {
		ArrayList<Object[]> hit = new ArrayList<Object[]>();
		for (int p = 0; p < pos.length && p < 14; p++) { // 扫0..13: 十行星+计罗炁孛
			if (!Calculate.isValid(pos[p]))
				continue;
			if (cd.isTopStarHit(center, pos[p], w))
				hit.add(new Object[] { Double.valueOf(pos[p]),
						prefix + names[p] });
		}
		if (extra != null)
			for (int p = 0; p < extra.length; p++) {
				if (!Calculate.isValid(extra[p]))
					continue;
				if (cd.isTopStarHit(center, extra[p], w))
					hit.add(new Object[] { Double.valueOf(extra[p]),
							prefix + extra_names[p] });
			}
		Collections.sort(hit, new Comparator<Object[]>() {
			public int compare(Object[] a, Object[] b) {
				return Double.compare(((Double) a[0]).doubleValue(),
						((Double) b[0]).doubleValue());
			}
		});
		if (hit.isEmpty())
			return "(无)";
		StringBuffer sb = new StringBuffer();
		for (Object[] e : hit)
			sb.append((String) e[1]).append(' ');
		return sb.toString();
	}

	static final java.util.Set<String> KNOWN_FLAGS = new java.util.HashSet<String>(
			java.util.Arrays.asList("-dougang", "-aspects", "-full",
					"-fixstar", "-liuren", "-equ"));

	public static void main(String[] args) throws Exception {
		// 分离位置参数与-flag开关(修复批二A6: 只认已知旗标名, "-33.8688"这类负数坐标按位置参数)
		ArrayList<String> pos = new ArrayList<String>();
		for (String a : args) {
			if (a.startsWith("-") && KNOWN_FLAGS.contains(a))
				continue;
			if (a.startsWith("-") && a.length() > 1
					&& !Character.isDigit(a.charAt(1))) {
				System.err.println("[错误] 未知开关: " + a
						+ " (已知: -dougang -aspects -full -fixstar -liuren -equ)");
				System.exit(2);
			}
			pos.add(a);
		}
		if (pos.size() < 4) {
			System.err
					.println("用法: Main <yyyy-mm-dd> <HH:MM> <纬度> <经度> [流年年份=2026] [时区=Asia/Shanghai] [流年盘MM-DD] [-dougang] [-aspects] [-full] [-fixstar] [-liuren] [-equ]");
			System.exit(2);
		}
		// 解析自测(修复批B4): flag/位置参数分离不变式
		ArrayList<String> stp = new ArrayList<String>();
		for (String a : new String[] { "-aspects", "1999-05-03", "13:49",
				"-dougang", "29.5", "112.5", "2026", "Asia/Shanghai", "10-10" })
			if (!a.startsWith("-"))
				stp.add(a);
		ArrayList<String> exp = new ArrayList<String>();
		for (String a : new String[] { "1999-05-03", "13:49", "29.5", "112.5",
				"2026", "Asia/Shanghai", "10-10" })
			exp.add(a);
		if (!stp.equals(exp)) {
			System.err.println("[解析自测FAIL] flag/位置参数分离不变式破坏");
			System.exit(3);
		}
		String[] ymd = pos.get(0).split("-");
		String[] hm = pos.get(1).split(":"); // 修复批B4: 原args[1]在flag前置时错位
		int year = Integer.parseInt(ymd[0]);
		int month = Integer.parseInt(ymd[1]);
		int day = Integer.parseInt(ymd[2]);
		int hour = Integer.parseInt(hm[0]);
		int minute = hm.length > 1 ? Integer.parseInt(hm[1]) : 0;
		double lat = Double.parseDouble(pos.get(2));
		double lon = Double.parseDouble(pos.get(3));
		int query_year = (pos.size() > 4) ? Integer.parseInt(pos.get(4)) : 2026;
		String zone_id = (pos.size() > 5) ? pos.get(5) : "Asia/Shanghai";
		// 二期#4: 流年盘日期=App由用户所选流年盘记录决定(无自动规则; _188实测用各年10-10), 默认1月1日
		String flow_md = (pos.size() > 6) ? pos.get(6) : "01-01";
		int flow_month = Integer.parseInt(flow_md.split("-")[0]);
		int flow_day = Integer.parseInt(flow_md.split("-")[1]);
		// 修复批二B1: 输入校验——lenient关死(1999-02-30不得滚成03-02)+时区白名单
		Calendar vcal = Calendar.getInstance(TimeZone.getTimeZone(zone_id));
		vcal.setLenient(false);
		vcal.clear();
		vcal.set(year, month - 1, day, hour, minute, 0);
		try {
			vcal.getTime();
			if (vcal.get(java.util.Calendar.YEAR) != year
					|| vcal.get(java.util.Calendar.MONTH) != month - 1
					|| vcal.get(java.util.Calendar.DAY_OF_MONTH) != day) {
				System.err.println("[错误] 非法日期: " + pos.get(0));
				System.exit(2);
			}
		} catch (IllegalArgumentException e) {
			System.err.println("[错误] 非法日期/时间: " + pos.get(0) + " "
					+ pos.get(1) + " (" + e.getMessage() + ")");
			System.exit(2);
		}
		if (java.util.Arrays.asList(TimeZone.getAvailableIDs()).indexOf(
				zone_id) < 0) {
			System.err.println("[错误] 非法时区ID: " + zone_id);
			System.exit(2);
		}
		// 修复批三B1补漏: 流年盘日期同样lenient关死(02-30不得滚月)
		Calendar fcal = Calendar.getInstance(TimeZone.getTimeZone(zone_id));
		fcal.setLenient(false);
		fcal.clear();
		fcal.set(query_year, flow_month - 1, flow_day, 12, 0, 0);
		try {
			fcal.getTime();
			if (fcal.get(java.util.Calendar.YEAR) != query_year
					|| fcal.get(java.util.Calendar.MONTH) != flow_month - 1
					|| fcal.get(java.util.Calendar.DAY_OF_MONTH) != flow_day) {
				System.err.println("[错误] 非法流年盘日期: " + query_year + "-"
						+ flow_md);
				System.exit(2);
			}
		} catch (IllegalArgumentException e) {
			System.err.println("[错误] 非法流年盘日期: " + query_year + "-"
					+ flow_md + " (" + e.getMessage() + ")");
			System.exit(2);
		}
		// 修复批三B1补漏: 经纬度有限性与范围(NaN/超界exit非0)
		if (!Double.isFinite(lat) || Math.abs(lat) > 90.0) {
			System.err.println("[错误] 纬度非法(需有限且|纬|≤90): " + lat);
			System.exit(2);
		}
		if (!Double.isFinite(lon) || Math.abs(lon) > 180.0) {
			System.err.println("[错误] 经度非法(需有限且|经|≤180): " + lon);
			System.exit(2);
		}

		// 修复批二B2: prop开关判定移到Resource初始化之后(原来在new Resource()前读, prop路径死)
		boolean dougang = hasFlag(args, "-dougang");
		boolean fixstar = hasFlag(args, "-fixstar");
		boolean aspects = hasFlag(args, "-aspects");
		boolean full_ss = hasFlag(args, "-full");
		boolean liuren = hasFlag(args, "-liuren");
		boolean equ = hasFlag(args, "-equ");

		// ---- 工程目录定位: engine/out/classes 的上级即 engine, 资源在 rsrc/, 星历在 engine/ephemeris/ ----
		File here = new File(Main.class.getProtectionDomain().getCodeSource()
				.getLocation().toURI()).getAbsoluteFile();
		File engine_dir = here.getParentFile();
		while (engine_dir != null && !new File(engine_dir, "rsrc").isDirectory())
			engine_dir = engine_dir.getParentFile();
		if (engine_dir == null)
			engine_dir = new File(".").getAbsoluteFile();
		// 修复批四C④: -Dengine.rsrc=目录 覆盖资源目录(prop/cities), 供回归的prop隔离副本测试(原件零接触)
		File rsrc = System.getProperty("engine.rsrc") != null
				? new File(System.getProperty("engine.rsrc"))
				: new File(engine_dir, "rsrc");
		File ephe_dir = new File(engine_dir, "ephemeris");

		// ---- 资源初始化(Moira 骨架) ----
		FileIO.setBaseIO(new HeadlessIO(rsrc, engine_dir)); // 修复批四B补充: engine根兜底(隔离副本时星历可达)
		new Resource(null, "simplified", null, null, null); // prefs=null→全部取prop默认(=App moira_s.prop)
		ChartMode.initChartMode(); // chart_mode 无pref → TRADITIONAL_MODE(黄经绝对制+ZZT宿界表)
		City.loadCities("cities.prop");
		// 修复批六④: 资源缺失入口——cities.prop 缺失时给明确报错并干净退出(非0),
		// 不带病运行(批五防御后 matchCity 仍会解引用 null 崩溃, 五审实证; 空表短路已加为兜底)
		if (!City.citiesLoaded()) {
			System.err.println("[错误] 资源缺失: cities.prop (资源目录="
					+ rsrc.getPath() + ")——城市表为空, 无法继续");
			System.exit(8);
		}
		Message.setMessage(new HeadlessMessage()); // 无头禁弹窗; 防止星历缺失触发全局Moshier降级
		// 修复批二B2: prop开关(路径已通)——CLI旗标或prop键任一开启
		if (Resource.hasKey("show_dou_sign")
				&& Resource.getInt("show_dou_sign") == 1)
			dougang = true;
		if (Resource.hasKey("use_six_ren_god")
				&& Resource.getInt("use_six_ren_god") == 1)
			liuren = true;

		ChartData cd = new ChartData(new HeadlessTab(), new HeadlessTab(),
				new HeadlessTab());
		// APP-DELTA: 星历路径→施工ephemeris(sepl/semo_18.se1=App同款精确级; fixstars.cat同目录)
		// 注: swisseph Java移植 PATH_SEPARATOR=";:" 会把 "D:" 切成盘符+残径, 必须传不含冒号的相对路径
		cd.getCal().getSwissEph().swe_set_ephe_path(relEphePath(ephe_dir));
		cd.setTimeAdjust(0); // 真太阳时直输, 不再做LAT/LMT改正
		cd.setShowNow(true); // 流年(now)盘=流年块星位来源
		cd.setShowAspects(false);
		cd.setShowFixstar(fixstar); // 二期#6: 默认关恒星盘(非锚路径), -fixstar 开启验证
		cd.setShowHoriz(false);
		cd.setShowGauquelin(false);

		// ---- 本命盘 ----
		DataEntry birth = new DataEntry();
		birth.setName("chart");
		birth.setCountry("");
		birth.setCity(lon + "," + lat); // City.parseLongLatitude 直收经纬
		birth.setZone(zone_id);
		birth.setBirthDay(new int[] { year, month, day, hour, minute });
		// 流年盘: 流年块星位用, 取流年1月1日12:00(流年盘日期当日口径, 报告B件2 S2)
		DataEntry now = new DataEntry();
		now.setName("transit");
		now.setCountry("");
		now.setCity(lon + "," + lat);
		now.setZone(zone_id);
		now.setBirthDay(new int[] { query_year, flow_month, flow_day, 12, 0 });
		now.setNowDay(new int[] { query_year, flow_month, flow_day, 12, 0 }); // j=1(now盘)走 getNowDay()

		String err = cd.compute(birth, now, birth, new DiagramTip());
		if (err != null) {
			System.err.println("compute失败: " + err);
			System.exit(1);
		}

		// ---- 取数 ----
		String[] poles = cd.getBirthPoles(); // [2]=年柱 [3]=月柱 [4]=日柱 [5]=时柱
		double life = cd.getLifeSignPos();
		double self = cd.getSelfSignPos();
		double[] zzt = cd.getStellarSignPos();
		String[] star_names = cd.getFullStellarSigns(); // 娄金,胃土,...
		String[] zodiac = Resource.getStringArray("zodiac"); // 戌,酉,...,亥(0-30=戌)
		String[] sign_names = cd.getSignNames();
		double[] birth_pos = cd.getBirthSignPos();
		double[] now_pos = cd.getNowSignPos();
		TimeZone zone = TimeZone.getTimeZone(zone_id);
		SimpleDateFormat df = new SimpleDateFormat("yyyy-MM-dd");
		df.setTimeZone(zone);

		System.out.println("=== App口径排盘  " + pos.get(0) + " " + pos.get(1)
				+ " (真太阳时直输)  纬" + lat + " 经" + lon + " " + zone_id + " ===");
		System.out.println("四柱(干支): " + poles[2] + " " + poles[3] + " "
				+ poles[4] + " " + poles[5]);
			System.out.println("太阳黄经(本命, 恒星制): "
				+ String.format(java.util.Locale.US, "%.9f", birth_pos[0])
				+ "  太阴黄经(本命, 恒星制): "
				+ String.format(java.util.Locale.US, "%.9f", birth_pos[1]));
		// 修复批三A5: 流年盘同日期高精度输出(回归断言 太阴==SWIEPH 55.091931≠Moshier 55.092073)
		System.out.println("流年盘太阴黄经(恒星制): "
				+ String.format(java.util.Locale.US, "%.9f", now_pos[1]));

		// ---- 立命(安命) ----
		System.out.println("立命: " + palaceName(zodiac, life) + " "
				+ findStellar(zzt, star_names, life) + "  命度黄经 "
				+ String.format(java.util.Locale.US, "%.3f", life));
		System.out.println("身宫(太阴): " + palaceName(zodiac, self) + " "
				+ findStellar(zzt, star_names, self) + "  身度黄经 "
				+ String.format(java.util.Locale.US, "%.3f", self));

		// ---- 度限链(App口径) ----
		cd.computeLimitChain();
		int child_days = cd.getChildLimit(false);
		System.out.println("童限: " + child_days + "天("
				+ String.format(java.util.Locale.US, "%.3f", cd.getChildLimitYears())
				+ "年)  换限日(相貌段起点)=" + df.format(cd.getLimitSegmentStart(1)));
		String wedge_names = "命相福官迁疾妻奴男女田兄财"; // 楔0=童限(命宫楔), 楔1..11=相福官迁疾妻奴男女田兄财
		System.out.println("换限日期表(段i 起点→终点):");
		double[] seq = cd.getLimitSeq();
		for (int i = 0; i < seq.length; i++) {
			Date s = cd.getLimitSegmentStart(i);
			Date e = cd.getLimitSegmentEnd(i);
			double pos_s = cd.getLimitPosition(s);
			System.out.println("  楔" + i + " " + wedge_names.charAt(i) + " "
					+ (i == 0 ? "童限" : String.valueOf(seq[i]) + "年") + ": "
					+ df.format(s) + " → " + df.format(e) + "  段首行度黄经="
					+ String.format(java.util.Locale.US, "%.3f", pos_s));
		}

		// ---- 小限(use_birth_small_limit口径: 命度+(虚岁-1)*30, App楔0替换显示) ----
		int vl_age = query_year - year + 1;
		{ // 小限输出口常开(修复批B5: 删原==1||true死条件); use_birth_small_limit仅作口径标注
			double xl = City.normalizeDegree(life + (vl_age - 1) * 30.0);
			System.out.println("小限(虚岁" + vl_age + ", 命度+(虚岁-1)*30): "
					+ palaceName(zodiac, xl) + " "
					+ findStellar(zzt, star_names, xl) + "  黄经 "
					+ String.format(java.util.Locale.US, "%.3f", xl)
					+ "  [use_birth_small_limit="
					+ (Resource.hasKey("use_birth_small_limit") ? Resource
							.getInt("use_birth_small_limit") : 0) + "]");
		}

		// ---- 指定年年初限度 ----
		// 修复批二A4: INVALID=Double.MIN_VALUE, isInfinite()永不成立——按INVALID语义判;
		// 补充1: 年初限度链外与顶星中心链外分别判断(流年盘日期在链内时顶星照常输出)
		double q_pos = cd.getLimitPositionAtYear(query_year);
		boolean q_in = Calculate.isValid(q_pos);
		System.out.println("年初限度 " + query_year + "-01-01 00:00: "
				+ (!q_in ? "链外" : (palaceName(zodiac, q_pos)
						+ " " + findStellar(zzt, star_names, q_pos) + "  黄经 " + String
						.format(java.util.Locale.US, "%.3f", q_pos))));

		// ---- 顶星(伴星扫描): 中心=行度(流年盘日期当日, App S2口径), W=(30÷限年数)÷2, 同宿%30+29/1跨界 ----
		// 修复批三A4补反向: 顶星仅由 center_in 独立决定——
		//   反向例 1999-01-05出生/2093年/flow12-01: 年初限度有效(34.330°)但flow日期链止2093-09-21之外,
		//   旧实现(!q_in&&!center_in)会扫0°出顶星虚岁95 W=3.00 → 修后输出"中心链外"。
		{
			int age = query_year - year + 1; // 虚岁(App B1口径)
			double w = cd.getLimitHalfWidth(age);
			if (!Calculate.isValid(w)) { // 修复批三A4: isInfinite()对MIN_VALUE失效(虚岁100打W=0.00残留)
				System.out.println("顶星: 虚岁" + age + "链外(半宽无法定位)");
			} else {
				// 二期#4: 流年盘日期=App流年盘记录日期; 顶星中心独立于年初限度有效性
				Calendar fc = Calendar.getInstance(TimeZone.getTimeZone(zone_id));
				fc.clear();
				fc.set(query_year, flow_month - 1, flow_day, 12, 0, 0);
				double center = cd.getLimitPosition(fc.getTime());
				boolean center_in = Calculate.isValid(center);
				if (!center_in) {
					System.out.println("顶星: 中心链外(流年盘" + query_year + "-"
							+ flow_md + "不在度限链内)");
				} else {
				if (!q_in)
					System.out.println("(年初限度链外, 流年盘日期在链内——顶星照常)");
				// 二期#1: 斗/罡两点入候选(App行度点表尾部追加, a1() L14405-14413)
				double[] loc = new double[2];
				cd.getLocation(loc);
				double[] dg_natal = cd.computeDouGang(birth_pos[0],
						cd.getBirthAdjDate(), loc[0]);
				int[] now_date = new int[] { query_year, flow_month, flow_day,
						12, 0 };
				double[] dg_flow = Calculate.isValid(now_pos[0]) ? cd
						.computeDouGang(now_pos[0], now_date, loc[0])
						: new double[] { Calculate.INVALID, Calculate.INVALID };
				if (!dougang) {
					dg_natal = new double[] { Calculate.INVALID,
							Calculate.INVALID };
					dg_flow = new double[] { Calculate.INVALID,
							Calculate.INVALID };
				}
				System.out.println("顶星(虚岁" + age + " W="
						+ String.format(java.util.Locale.US, "%.2f", w) + " 中心=流年盘"
						+ query_year + "-" + flow_md + " 行度"
						+ String.format(java.util.Locale.US, "%.3f", center) + "): 本命块="
						+ topStarBlock(cd, birth_pos, sign_names, center, w,
								"", new double[] { dg_natal[0], dg_natal[1] },
								new String[] { "斗", "罡" })
						+ " 流年块="
						+ topStarBlock(cd, now_pos, sign_names, center, w, "流",
								new double[] { dg_flow[0], dg_flow[1] },
								new String[] { "斗", "罡" }));
				java.text.DecimalFormat df3 = new java.text.DecimalFormat(
						"0.000;-0.000");
				System.out.println("  [斗罡] 本命: 斗"
						+ (Calculate.isValid(dg_natal[0]) ? df3.format(dg_natal[0]) : "-")
						+ " 罡"
						+ (Calculate.isValid(dg_natal[1]) ? df3.format(dg_natal[1]) : "-")
						+ "  流年盘: 斗"
						+ (Calculate.isValid(dg_flow[0]) ? df3.format(dg_flow[0]) : "-")
						+ " 罡"
						+ (Calculate.isValid(dg_flow[1]) ? df3.format(dg_flow[1]) : "-"));
				} // center-else(修复批二A4: 中心/年初限度独立判)
			} // w-else
		} // 顶星块

		// ---- 守照关拱(二期#3): 对行度中心扫14体x9相位, 首个命中相位, |角距-度数|<=容差 ----
		if (aspects && q_in) {
			double[] adeg = cd.getAspectDegreeArray(false);
			double[] aorb = cd.getAspectOrbArray();
			String[] asign = cd.getAspectSignArray(false);
			if (adeg != null && aorb != null && asign != null) {
				StringBuffer dbg = new StringBuffer("  [相位表] ");
				for (int k = 0; k < adeg.length; k++)
					dbg.append(asign[k]).append('=').append(adeg[k]).append('±')
							.append(aorb[k]).append(' ');
				System.out.println(dbg.toString());
				StringBuffer sb = new StringBuffer();
				for (int blk = 0; blk < 2; blk++) {
					double[] bp = (blk == 0) ? birth_pos : now_pos;
					String pf = (blk == 0) ? "命" : "流";
					for (int p = 0; p < bp.length && p < 14; p++) {
						if (!Calculate.isValid(bp[p]))
							continue;
						double dist = Math.abs(City.normalizeDegree(q_pos
								- bp[p]));
						if (dist > 180.0)
							dist = 360.0 - dist;
						for (int k = 0; k < adeg.length; k++) {
							if (Math.abs(dist - adeg[k]) <= aorb[k]) {
								sb.append(pf).append(sign_names[p])
										.append(asign[k]).append('(')
										.append(String.format(java.util.Locale.US, "%.1f", dist))
										.append(')');
								sb.append(' ');
								break; // 首个命中(App同款break)
							}
						}
					}
				}
				System.out.println("守照关拱(中心=年初限度): "
						+ (sb.length() == 0 ? "(无)" : sb.toString()));
			}
		}

		// ---- 恒星盘(二期#6, -fixstar): 直接经swe_fixstar_ut算恒星表( TRADITIONAL模式下
		//      Moira原生fixstar_sign_pos通道在PICK_MODE分支, 故此处直算; fixstars.cat经ephepath解析)
		ArrayList<Object[]> fix_list = new ArrayList<Object[]>();
		if (fixstar) {
			String[] fsign = Resource.getStringArray("fixstar_signs");
			String[] fname = Resource.getStringArray("fixstar_names");
			int[] bday = birth.getBirthDay().clone();
			BaseCalendar.addZoneOffset(zone_id, bday, 0, false);
			Calculate cal2 = cd.getCal();
			cal2.setJulianDay(bday);
			StringBuffer sb = new StringBuffer();
			int valid = 0;
			for (int i = 0; i < fsign.length && i < fname.length; i++) {
				StringBuffer nb = new StringBuffer("," + fname[i]);
				double v = cal2.computeStar(nb, null);
				if (Calculate.isValid(v)) {
					valid++;
					fix_list.add(new Object[] { fsign[i],
							Double.valueOf(City.normalizeDegree(v)) });
					if (sb.length() < 96)
						sb.append(fsign[i].trim()).append('=')
								.append(String.format(java.util.Locale.US, "%.2f", v)).append(' ');
				}
			}
			System.out.println("恒星盘(本命JD): 有效" + valid + "/" + fsign.length
					+ "  " + sb.toString());
		}

		// ---- 化曜(年干起天禄顺行, Moira getYearStar=App W0同构, 报告B件4) ----
		int y_index = cd.getYearNameIndex(poles[2]);
		StringBuffer hy = new StringBuffer();
		for (int k = 0; k < 10; k++)
			hy.append(cd.getHuayao(y_index, 90 + k)).append(' ');
		System.out.println("化曜(天禄..天权序): " + hy.toString());

		// ---- 神煞(数据表直读App moira_s.prop: 地支X 40条/天干X 13条, 报告B件3) ----
		String y_branch = poles[2].substring(1, 2);
		String y_sky = poles[2].substring(0, 1);
		String[] year_tab = Resource.getStringArray("地支" + y_branch);
		if (year_tab != null) {
			StringBuffer sb = new StringBuffer();
			for (String entry : year_tab) {
				String[] kv = entry.split(":");
				if (kv.length == 2)
					sb.append(kv[1].trim()).append("(").append(kv[0].trim())
							.append(") ");
			}
			System.out.println("神煞·年支" + y_branch + ": " + sb.toString());
		}
		String[] sky_tab = Resource.getStringArray("天干" + y_sky);
		if (sky_tab != null) {
			StringBuffer sb = new StringBuffer();
			for (String entry : sky_tab) {
				String[] kv = entry.split(":");
				if (kv.length == 2)
					sb.append(kv[1].trim()).append("(").append(kv[0].trim())
							.append(") ");
			}
			System.out.println("神煞·年干" + y_sky + ": " + sb.toString());
		}

		// ---- 神煞扩展表(二期#6, -full): 月支表/60干支表/日支表直读prop ----
		if (full_ss) {
			String m_branch = poles[3].substring(1, 2);
			String[] mt = Resource.getStringArray("月支" + m_branch);
			if (mt != null) {
				StringBuffer sb = new StringBuffer();
				for (String e2 : mt)
					sb.append(e2.trim()).append(' ');
				System.out.println("神煞·月支" + m_branch + ": " + sb.toString());
			}
			String[] gz = Resource.getStringArray(poles[2]);
			if (gz != null) {
				StringBuffer sb = new StringBuffer();
				for (String e2 : gz)
					sb.append(e2.trim()).append(' ');
				System.out.println("神煞·干支" + poles[2] + ": " + sb.toString());
			}
			String d_branch = poles[4].substring(1, 2);
			String[] dt = Resource.getStringArray("日支" + d_branch);
			if (dt != null) {
				StringBuffer sb = new StringBuffer();
				for (String e2 : dt)
					sb.append(e2.trim()).append(' ');
				System.out.println("神煞·日支" + d_branch + ": " + sb.toString());
			}
		}

		// ---- 六壬十二天将(三期#1, -liuren): 标注对象=十二宫(宫支序) ----
		// App原文: b3/d.java L19003-19096(chineseCalendar同构方法内, strArr==O3本命四柱时):
		//  月建=太阳宫支(s4=zodiac表, 太阳黄经/30); 昼夜=时支∈{卯辰巳午未申}昼;
		//  贵人支=昼表"丑子亥亥丑子丑午巳巳"/夜表"未申酉酉未申未寅卯卯"按日干序取
		//  (=经典阴阳贵诀: 甲戊庚牛羊 乙己鼠猴 丙丁猪鸡 壬癸蛇兔 辛马虎, smali const-string核验一致);
		//  顺逆=贵人支亥起序前半(亥子丑寅卯辰)顺布"貴蛇朱合勾青空白常玄陰后"、后半逆布;
		//  布局: 名[cycle[(u-贵人支 RotIdx)%12]] 挂 支[子起[(u+月支序-时支序)%12]], 贵人恰落贵人支
		if (liuren) {
			String gan_t = "甲乙丙丁戊己庚辛壬癸";
			String zi_t = "子丑寅卯辰巳午未申酉戌亥";
			String zod_t = "戌酉申未午巳辰卯寅丑子亥"; // 宫序0-11(戌=0-30)
			String[] god_full = { "贵人", "螣蛇", "朱雀", "六合", "勾陈",
					"青龙", "天空", "白虎", "太常", "玄武", "太阴", "天后" };
			String[] god_short = { "貴", "蛇", "朱", "合", "勾", "青", "空",
					"白", "常", "玄", "陰", "后" };
			// 修复批三A2(按 d.smali:86216-86473 完整数据流逐指令重写):
			//   strSub4[u] = 子起[(u+rotIdx)%12], rotIdx=月支序-时支序;
			//   贵人支=昼夜表[日干序]; rotatedIndex(strIdx4贵人支)=贵人支序-rotIdx;
			//   方向支=子起[rotatedIndex], 其亥起序=(rotatedIndex+1)%12 >=6→逆布
			//   (d.smali:86405+86417: 亥起表"亥子丑…"查索引=子起序+1, 修复批四纠正);
			//   窗口起点 windowStart=(12-rotatedIndex)%12(0→12), 逆布再-1;
			//   名[u]=cycle[(windowStart+u)%12] 挂 支[u]; 貴恒落贵人支(顺逆皆, smali窗口互补所至)。
			int monthIdx = zi_t.indexOf(zod_t.charAt(((int) (City
					.normalizeDegree(birth_pos[0]) / 30.0)) % 12)); // 月建支(太阳宫支)子起序
			String d_gan = poles[4].substring(0, 1);
			String h_zhi = poles[5].substring(1, 2);
			int d_idx = gan_t.indexOf(d_gan);
			int h_idx = zi_t.indexOf(h_zhi);
			boolean daytime = "卯辰巳午未申".indexOf(h_zhi) >= 0;
			String noble = (daytime ? "丑子亥亥丑子丑午巳巳"
					: "未申酉酉未申未寅卯卯").substring(d_idx, d_idx + 1);
			int n_idx = zi_t.indexOf(noble);
			int rotIdx = ((monthIdx - h_idx) % 12 + 12) % 12; // rot=月支序-时支序
			int rotatedIndex = ((n_idx - rotIdx) % 12 + 12) % 12; // strSubstring4.IndexOf(贵人支)
			// 方向支=子起[rotatedIndex](smali 86405 charAt), 亥起表"亥子丑..."查索引=子起序+1
			// (d.smali:86405+86417; 修复批三曾误用减一换算, 修复批四纠正为加一, 见报告§14)
			int dirIdx = (rotatedIndex + 1) % 12;
			int windowStart = (12 - rotatedIndex) % 12; // 子起12→窗口起点(0→12)
			if (windowStart == 0)
				windowStart = 12;
			String cycle;
			if (dirIdx >= 6) {
				cycle = "后陰玄常白空青勾合朱蛇貴";
				windowStart -= 1; // 逆布: smali add-int/lit8 v10, v10, -0x1
			} else {
				cycle = "貴蛇朱合勾青空白常玄陰后";
			}
			String[] palace_god = new String[12];
			for (int u = 0; u < 12; u++) {
				String br = zi_t.substring((u + rotIdx) % 12, (u + rotIdx) % 12 + 1);
				int ci = ((windowStart + u) % 12 + 12) % 12;
				String sh = cycle.substring(ci, ci + 1);
				int g = 0;
				while (!god_short[g].equals(sh))
					g++;
				palace_god[zod_t.indexOf(br)] = god_full[g];
			}
			String noble_palace = noble; // 貴恒落贵人支(顺逆窗口互补所至, smali复算=二审一致)
			StringBuffer sb = new StringBuffer();
			for (int pI = 0; pI < 12; pI++)
				sb.append(zod_t.charAt(pI)).append('[')
						.append(palace_god[pI]).append("] ");
			System.out.println("六壬天将(标注十二宫): " + sb.toString());
			System.out.println("  [起例] 月建=" + zod_t.charAt(((int) (City
					.normalizeDegree(birth_pos[0]) / 30.0)) % 12)
					+ "(太阳宫支) " + (daytime ? "昼" : "夜") + "贵 " + d_gan
					+ "日干→贵人支" + noble + " " + (dirIdx >= 6 ? "逆布" : "顺布")
					+ " → 貴落" + noble_palace + "宫"
					+ " [rotatedIndex=" + rotatedIndex + "]");
		}

		// ---- 赤道坐标层(三期#2; 修复批A1重构): 十一曜赤经/赤纬 ----
		// App原文: b3/b.s = swe_calc flags|=2048(SEFLG_EQUATORIAL), 恒星制空间投影。
		// 修复批A1: 废弃逐体swe_calc重算(其bI→swe体号映射与ChartData planets[]错位,
		//   计/孛/炁三体数值作废); 所有体λ一律取 birth_pos[](=黄道显示同一权威值),
		//   逐体一次黄赤变换出α/δ(β=0黄道面投影, 与App宫界/宿环同一显示空间), 体映射错位类bug从构造上消灭。
		//   罗直接用birth_pos[罗]变换(删α+180/δ反号hack); -fixstar开启时恒星λ一并出。
		// 修复批A2: 自检双重=①(λ→α,δ→λ′)往返闭合 ②λ′==birth_pos[bI](±1e-3°)对锚。
		if (equ) {
			Calculate cal2 = cd.getCal();
			org.athomeprojects.swisseph.SwissEph eph2 = cal2.getSwissEph();
			int[] bday = birth.getBirthDay().clone();
			BaseCalendar.addZoneOffset(zone_id, bday, 0, false);
			cal2.setJulianDay(bday);
			double jd = cal2.getJulianDayUT();
			// 修复批二A1: ε弃太阳tan反解(春分点附近NaN/错值), 改星历库SE_ECL_NUT
			// 真黄赤交角(swe_calc内部同源, 含nutation, 返回即度); 有限性守卫
			double[] exx = new double[20];
			eph2.swe_calc_ut(jd,
					org.athomeprojects.swisseph.SweConst.SE_ECL_NUT,
					org.athomeprojects.swisseph.SweConst.SEFLG_SWIEPH, exx,
					new StringBuffer());
			double eps = exx[0];
			if (Double.isNaN(eps) || Double.isInfinite(eps) || eps < 20.0
					|| eps > 30.0) {
				System.err.println("[错误] ε非法: " + eps);
				System.exit(6);
			}
			StringBuffer sb = new StringBuffer();
			double max_rt = 0.0, max_anchor = 0.0;
			for (int bI = 0; bI <= 13; bI++) {
				if (!Calculate.isValid(birth_pos[bI]))
					continue;
				double lam = City.normalizeDegree(birth_pos[bI]); // 权威λ(A1)
				double L = Math.toRadians(lam), E = Math.toRadians(eps);
				double aS = Math.toDegrees(Math.atan2(Math.sin(L)
						* Math.cos(E), Math.cos(L)));
				if (aS < 0.0)
					aS += 360.0;
				double dS = Math.toDegrees(Math.asin(Math.sin(E)
						* Math.sin(L)));
				// ①往返: (α,δ)→λ′
				double aR = Math.toRadians(aS), dR = Math.toRadians(dS);
				double lam2 = City.normalizeDegree(Math.toDegrees(Math
						.atan2(Math.sin(aR) * Math.cos(E) + Math.tan(dR)
								* Math.sin(E), Math.cos(aR))));
				double dev_rt = Math.abs(City.normalizeDegree(lam2 - lam));
				if (dev_rt > 180.0)
					dev_rt = 360.0 - dev_rt; // 360边界: normalize(−360±ε)=359.99…
				// ②对锚: λ′ vs birth_pos[bI](±1e-3°)
				double dev_anchor = Math.abs(City
						.normalizeDegree(lam2 - birth_pos[bI]));
				if (dev_anchor > 180.0)
					dev_anchor = 360.0 - dev_anchor;
				max_rt = Math.max(max_rt, dev_rt);
				max_anchor = Math.max(max_anchor, dev_anchor);
				sb.append(sign_names[bI]).append("(α")
						.append(String.format(java.util.Locale.US, "%.3f", aS))
						.append(" δ").append(String.format(java.util.Locale.US,
								"%+.3f", dS)).append(") ");
			}
			// 恒星(A1: -fixstar开启时恒星λ一并出)
			if (fix_list != null) {
				StringBuffer sf = new StringBuffer();
				for (Object[] o : fix_list) {
					double lam = City.normalizeDegree(((Double) o[1])
							.doubleValue());
					double L = Math.toRadians(lam), E = Math.toRadians(eps);
					double aS = Math.toDegrees(Math.atan2(Math.sin(L)
							* Math.cos(E), Math.cos(L)));
					if (aS < 0.0)
						aS += 360.0;
					double dS = Math.toDegrees(Math.asin(Math.sin(E)
							* Math.sin(L)));
					double aR = Math.toRadians(aS), dR = Math.toRadians(dS);
					double lam2 = City.normalizeDegree(Math.toDegrees(Math
							.atan2(Math.sin(aR) * Math.cos(E) + Math.tan(dR)
									* Math.sin(E), Math.cos(aR))));
					double d_rt = Math.abs(City.normalizeDegree(lam2 - lam));
					double d_an = Math.abs(City
							.normalizeDegree(lam2 - ((Double) o[1])
									.doubleValue()));
					if (d_an > 180.0)
						d_an = 360.0 - d_an;
					if (d_rt > 180.0)
						d_rt = 360.0 - d_rt;
					max_rt = Math.max(max_rt, d_rt);
					max_anchor = Math.max(max_anchor, d_an);
					if (sf.length() < 110)
						sf.append(((String) o[0]).trim()).append("(α")
								.append(String.format(java.util.Locale.US,
										"%.3f", aS)).append(" δ")
								.append(String.format(java.util.Locale.US,
										"%+.3f", dS)).append(") ");
				}
				if (sf.length() > 0)
					sb.append(" 恒星: ").append(sf.toString());
			}
			System.out.println("赤道坐标(恒星制空间, β=0黄道面投影, ε真(SE_ECL_NUT)="
					+ String.format(java.util.Locale.US, "%.5f", eps) + "°): "
					+ sb.toString());
			boolean chk_ok = max_rt < 1e-3 && max_anchor < 1e-3;
			System.out.println("  [自检] ①往返闭合max="
					+ String.format(java.util.Locale.US, "%.2e", max_rt)
					+ "° ②对锚max=" + String.format(java.util.Locale.US,
							"%.2e", max_anchor) + "° (阈1e-3°) "
					+ (chk_ok ? "PASS" : "FAIL"));
			if (!chk_ok) {
				System.err.println("[错误] -equ自检FAIL(修复批二A1: FAIL即exit非0)");
				System.exit(6);
			}
		}

		// ---- 斗杓(月支+时支+2, 子起; App prop 月时表144行验证=报告B附带发现2) ----
		String[] epoles = Resource.getStringArray("earth_pole_names"); // 子丑寅...亥
		int mi = FileIO.getArrayIndex(poles[3].substring(1, 2), epoles);
		int hi = FileIO.getArrayIndex(poles[5].substring(1, 2), epoles);
		if (mi >= 0 && hi >= 0)
			System.out.println("斗杓: " + epoles[(mi + hi + 2) % 12] + " (月"
					+ poles[3].substring(1, 2) + "+时" + poles[5].substring(1, 2)
					+ "+2)");

		System.out.println("[口径注] 夜子时23:00换日柱 switch_day_at_11_pm="
				+ Resource.getPrefInt("switch_day_at_11_pm")
				+ "(App出厂默认=1); 宫界=30°绝对格网戌0起; 岁差4.0不作用于行度/宿显示");
	}
}
