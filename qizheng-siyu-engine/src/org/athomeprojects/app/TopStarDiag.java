//
// 顶星对拍诊断工具（二期#1辅助件）
// 衍生自 Moira v1.50 (GPL)，见 README.md
//
// 用法: TopStarDiag <yyyy-mm-dd> <HH:MM> <纬度> <经度> <年1,月1,日1> [年2,月2,日2 ...]
//   对每个"流年盘日期"打印: 该日行度中心%30、本命/流年各星%30、斗罡%30、W, 并列出命中块
//
package org.athomeprojects.app;

import java.io.File;
import java.util.Calendar;
import java.util.TimeZone;

import org.athomeprojects.base.Calculate;
import org.athomeprojects.base.ChartData;
import org.athomeprojects.base.ChartMode;
import org.athomeprojects.base.City;
import org.athomeprojects.base.DataEntry;
import org.athomeprojects.base.DiagramTip;
import org.athomeprojects.base.FileIO;
import org.athomeprojects.base.Message;
import org.athomeprojects.base.Resource;

public class TopStarDiag {
	public static void main(String[] args) throws Exception {
		String[] ymd = args[0].split("-");
		String[] hm = args[1].split(":");
		double lat = Double.parseDouble(args[2]);
		double lon = Double.parseDouble(args[3]);
		String zone_id = "Asia/Shanghai";

		File here = new File(TopStarDiag.class.getProtectionDomain()
				.getCodeSource().getLocation().toURI()).getAbsoluteFile();
		File engine_dir = here.getParentFile();
		while (engine_dir != null
				&& !new File(engine_dir, "rsrc").isDirectory())
			engine_dir = engine_dir.getParentFile();
		FileIO.setBaseIO(new HeadlessIO(new File(engine_dir, "rsrc")));
		new Resource(null, "simplified", null, null, null);
		ChartMode.initChartMode();
		City.loadCities("cities.prop");
		Message.setMessage(new HeadlessMessage());

		ChartData cd = new ChartData(new HeadlessTab(), new HeadlessTab(),
				new HeadlessTab());
		cd.getCal().getSwissEph().swe_set_ephe_path(Main.relEphePath(new File(
				engine_dir, "ephemeris")));
		cd.setTimeAdjust(0);
		cd.setShowNow(true);
		cd.setShowAspects(false);
		cd.setShowFixstar(false);
		cd.setShowHoriz(false);
		cd.setShowGauquelin(false);

		DataEntry birth = new DataEntry();
		birth.setName("chart");
		birth.setCountry("");
		birth.setCity(lon + "," + lat);
		birth.setZone(zone_id);
		birth.setBirthDay(new int[] { Integer.parseInt(ymd[0]),
				Integer.parseInt(ymd[1]), Integer.parseInt(ymd[2]),
				Integer.parseInt(hm[0]), Integer.parseInt(hm[1]) });
		DataEntry now = new DataEntry();
		now.setName("t");
		now.setCountry("");
		now.setCity(lon + "," + lat);
		now.setZone(zone_id);
		int[] nd = { Integer.parseInt(ymd[0]), 10, 10, 12, 0 };
		now.setBirthDay(nd);
		now.setNowDay(nd);
		cd.compute(birth, now, birth, new DiagramTip());

		double[] birth_pos = cd.getBirthSignPos();
		double[] now_pos = cd.getNowSignPos();
		String[] names = cd.getSignNames();
		cd.computeLimitChain();
		double[] loc = new double[2];
		cd.getLocation(loc);
		int[] badj = cd.getBirthAdjDate();
		double[] dg = cd.computeDouGang(birth_pos[0], badj, loc[0]);

		System.out.println("本命恒星太阳=" + String.format(java.util.Locale.US, "%.3f", birth_pos[0])
				+ "  斗=" + String.format(java.util.Locale.US, "%.3f", dg[0]) + " 罡="
				+ String.format(java.util.Locale.US, "%.3f", dg[1]));
		System.out.print("本命各星%30: ");
		for (int p = 0; p <= 13 && p < birth_pos.length; p++)
			if (Calculate.isValid(birth_pos[p]))
				System.out.print(names[p] + "="
						+ String.format(java.util.Locale.US, "%.2f", City.normalizeDegree(birth_pos[p]) % 30)
						+ " ");
		System.out.println();
		System.out.print("流年盘(基准)各星%30: ");
		for (int p = 0; p <= 13 && p < now_pos.length; p++)
			if (Calculate.isValid(now_pos[p]))
				System.out.print(names[p] + "="
						+ String.format(java.util.Locale.US, "%.2f", City.normalizeDegree(now_pos[p]) % 30)
						+ " ");
		System.out.println();

		Calendar c = Calendar.getInstance(TimeZone.getTimeZone(zone_id));
		for (int a = 4; a < args.length; a++) {
			String[] p2 = args[a].split(",");
			int y = Integer.parseInt(p2[0]);
			int m = Integer.parseInt(p2[1]);
			int d = Integer.parseInt(p2[2]);
			c.clear();
			c.set(y, m - 1, d, 12, 0, 0);
			double center = cd.getLimitPosition(c.getTime());
			if (Double.isInfinite(center)) {
				System.out.println(y + "-" + m + "-" + d + ": 链外");
				continue;
			}
			int age = y - Integer.parseInt(ymd[0]) + 1;
			double w = cd.getLimitHalfWidth(age);
			// 流年盘该日期的星位需另算: 用链位置+中心只列命中判定
			System.out.println("流年盘 " + y + "-" + m + "-" + d + " 行度="
					+ String.format(java.util.Locale.US, "%.3f", center) + " %30="
					+ String.format(java.util.Locale.US, "%.3f", center % 30) + " 虚岁" + age
					+ " W=" + String.format(java.util.Locale.US, "%.2f", w));
		}
	}
}
