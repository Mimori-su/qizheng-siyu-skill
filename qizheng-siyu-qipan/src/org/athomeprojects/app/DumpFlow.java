package org.athomeprojects.app;

import java.io.File;

import org.athomeprojects.base.Calculate;
import org.athomeprojects.base.ChartData;
import org.athomeprojects.base.ChartMode;
import org.athomeprojects.base.City;
import org.athomeprojects.base.DataEntry;
import org.athomeprojects.base.DiagramTip;
import org.athomeprojects.base.FileIO;
import org.athomeprojects.base.Message;
import org.athomeprojects.base.Resource;

/** 打印流年盘十一曜黄经、宫、宿。参数与 Main 相同。 */
public class DumpFlow {
	public static void main(String[] args) throws Exception {
		if (args.length < 7) {
			System.err.println("用法: DumpFlow yyyy-mm-dd HH:MM 纬 经 年 时区 MM-DD");
			System.exit(2);
		}
		String[] ymd = args[0].split("-");
		String[] hm = args[1].split(":");
		int year = Integer.parseInt(ymd[0]);
		int month = Integer.parseInt(ymd[1]);
		int day = Integer.parseInt(ymd[2]);
		int hour = Integer.parseInt(hm[0]);
		int minute = hm.length > 1 ? Integer.parseInt(hm[1]) : 0;
		double lat = Double.parseDouble(args[2]);
		double lon = Double.parseDouble(args[3]);
		int queryYear = Integer.parseInt(args[4]);
		String zoneId = args[5];
		String[] md = args[6].split("-");
		int flowMonth = Integer.parseInt(md[0]);
		int flowDay = Integer.parseInt(md[1]);

		File engineDir = System.getProperty("engine.root") != null ? new File(
				System.getProperty("engine.root")) : new File(".");
		if (!new File(engineDir, "rsrc").isDirectory()) {
			System.err.println("找不到引擎资源: " + engineDir);
			System.exit(1);
		}
		File rsrc = new File(engineDir, "rsrc");
		File ephe = new File(engineDir, "ephemeris");
		FileIO.setBaseIO(new HeadlessIO(rsrc, engineDir));
		Message.setMessage(new HeadlessMessage());
		new Resource(null, "simplified", null, null, null);
		ChartMode.initChartMode();
		City.loadCities("cities.prop");

		ChartData cd = new ChartData(new HeadlessTab(), new HeadlessTab(),
				new HeadlessTab());
		String rel = ephe.getPath().replace('\\', '/');
		cd.getCal().getSwissEph().swe_set_ephe_path(rel);
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
		birth.setZone(zoneId);
		birth.setBirthDay(new int[] { year, month, day, hour, minute });
		DataEntry now = new DataEntry();
		now.setName("transit");
		now.setCountry("");
		now.setCity(lon + "," + lat);
		now.setZone(zoneId);
		now.setBirthDay(new int[] { queryYear, flowMonth, flowDay, 12, 0 });
		now.setNowDay(new int[] { queryYear, flowMonth, flowDay, 12, 0 });
		String err = cd.compute(birth, now, birth, new DiagramTip());
		if (err != null) {
			System.err.println("compute失败: " + err);
			System.exit(1);
		}
		String[] zodiac = Resource.getStringArray("zodiac");
		String[] names = cd.getSignNames();
		double[] pos = cd.getNowSignPos();
		double[] zzt = cd.getStellarSignPos();
		String[] stars = cd.getFullStellarSigns();
		System.out.println("流星(流年盘 " + queryYear + "-" + args[6] + " 12:00):");
		for (int i = 0; i < pos.length && i < names.length; i++) {
			if (!Calculate.isValid(pos[i]))
				continue;
			System.out.println("  " + names[i] + "  "
					+ Main.palaceName(zodiac, pos[i]) + "  "
					+ Main.findStellar(zzt, stars, pos[i]) + "  黄经 "
					+ String.format(java.util.Locale.US, "%.3f", pos[i]));
		}
	}
}
