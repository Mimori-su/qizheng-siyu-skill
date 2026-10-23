//
// 修复批二A8+修复批三(新增A)回归: 同一ChartData两连排 + 链起点确定性/出生当刻
// 衍生自 Moira v1.50 (GPL)，见 README.md
//
// 输出4行(供回归断言):
//   chart0 换限日=YYYY-MM-DD   (须2017-11-15)
//   chart1 换限日=YYYY-MM-DD   (须2015-03-10, A8: 不得复读chart0的链)
//   millis-remainder: N        (链起点毫秒余数, 须=0 —— 修复批三新增A秒毫秒清零)
//   birth-instant-in-chain: true/false (出生当刻须在链内=true)
//
package org.athomeprojects.app;

import java.io.File;
import org.athomeprojects.base.*;

public class ReuseTest {
	public static void main(String[] a) throws Exception {
		File here = new File(ReuseTest.class.getProtectionDomain()
				.getCodeSource().getLocation().toURI()).getAbsoluteFile();
		File eng = here.getParentFile();
		while (eng != null && !new File(eng, "rsrc").isDirectory())
			eng = eng.getParentFile();
		FileIO.setBaseIO(new HeadlessIO(new File(eng, "rsrc")));
		new Resource(null, "simplified", null, null, null);
		ChartMode.initChartMode();
		City.loadCities("cities.prop");
		Message.setMessage(new HeadlessMessage());
		ChartData cd = new ChartData(new HeadlessTab(), new HeadlessTab(),
				new HeadlessTab());
		cd.getCal().getSwissEph().swe_set_ephe_path(Main.relEphePath(new File(eng, "ephemeris")));
		cd.setTimeAdjust(0);
		cd.setShowNow(true);
		cd.setShowAspects(false);
		cd.setShowFixstar(false);
		cd.setShowHoriz(false);
		cd.setShowGauquelin(false);

		int[][] charts = { { 1999, 5, 3, 13, 49 }, { 2003, 1, 14, 4, 56 } };
		String[][] places = { { "29.5", "112.5" }, { "36.6667", "117.0167" } };
		for (int c = 0; c < 2; c++) {
			DataEntry b = new DataEntry();
			b.setCountry("");
			b.setCity(places[c][1] + "," + places[c][0]);
			b.setZone("Asia/Shanghai");
			b.setBirthDay(charts[c]);
			DataEntry n = new DataEntry();
			n.setCountry("");
			n.setCity(places[c][1] + "," + places[c][0]);
			n.setZone("Asia/Shanghai");
			n.setBirthDay(charts[c]);
			n.setNowDay(charts[c]);
			cd.reset();
			cd.compute(b, n, b, new DiagramTip());
			// 修复批三: 不再显式调 computeLimitChain()——直接走getter的懒重建路径,
			// 这样才能测到 A8 的缓存失效逻辑(旧回归显式重建绕过了被测路径)
			java.text.SimpleDateFormat df = new java.text.SimpleDateFormat(
					"yyyy-MM-dd HH:mm:ss.SSS");
			df.setTimeZone(java.util.TimeZone.getTimeZone("Asia/Shanghai"));
			java.util.Date s1 = cd.getLimitSegmentStart(1);
			System.out.println("chart" + c + " 换限日=" + df.format(s1)
					+ " 命度=" + String.format(java.util.Locale.US, "%.3f",
							cd.getLifeSignPos()));
			if (c == 0) {
				// 修复批三(新增A): 链起点秒毫秒清零断言 + 出生当刻在链内断言
				System.out.println("millis-remainder: " + (s1.getTime() % 60000));
				int[] bd = b.getBirthDay();
				java.util.Calendar bc = java.util.Calendar.getInstance(
						java.util.TimeZone.getTimeZone("Asia/Shanghai"));
				bc.clear();
				bc.set(bd[0], bd[1] - 1, bd[2], bd[3], bd[4], 0);
				double p = cd.getLimitPosition(bc.getTime());
				System.out.println("birth-instant-in-chain: "
						+ org.athomeprojects.base.Calculate.isValid(p));
			}
		}
	}
}
