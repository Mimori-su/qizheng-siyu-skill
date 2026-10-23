// 诊断工具: 打印cusp[1](天文ASC)宫内度与童限两态推断值 (二期#5: 证实链消费B2命度而非ASC)
package org.athomeprojects.app;
import java.io.File;
import org.athomeprojects.base.*;

public class ProbeCusp {
	public static void main(String[] a) throws Exception {
		// args: date time lat lon
		File here = new File(ProbeCusp.class.getProtectionDomain().getCodeSource()
				.getLocation().toURI()).getAbsoluteFile();
		File eng = here.getParentFile();
		while (eng != null && !new File(eng, "rsrc").isDirectory())
			eng = eng.getParentFile();
		FileIO.setBaseIO(new HeadlessIO(new File(eng, "rsrc")));
		new Resource(null, "simplified", null, null, null);
		ChartMode.initChartMode();
		City.loadCities("cities.prop");
		Message.setMessage(new HeadlessMessage());
		ChartData cd = new ChartData(new HeadlessTab(), new HeadlessTab(), new HeadlessTab());
		cd.getCal().getSwissEph().swe_set_ephe_path(Main.relEphePath(new File(eng, "ephemeris")));
		cd.setTimeAdjust(0); cd.setShowNow(true); cd.setShowAspects(false);
		cd.setShowFixstar(false); cd.setShowHoriz(false); cd.setShowGauquelin(false);
		DataEntry b = new DataEntry();
		b.setCountry(""); b.setCity(a[3] + "," + a[2]); b.setZone("Asia/Shanghai");
		String[] ymd = a[0].split("-"); String[] hm = a[1].split(":");
		b.setBirthDay(new int[] { Integer.parseInt(ymd[0]), Integer.parseInt(ymd[1]),
				Integer.parseInt(ymd[2]), Integer.parseInt(hm[0]), Integer.parseInt(hm[1]) });
		DataEntry n = new DataEntry();
		n.setCountry(""); n.setCity(a[3] + "," + a[2]); n.setZone("Asia/Shanghai");
		n.setBirthDay(b.getBirthDay()); n.setNowDay(b.getBirthDay());
		cd.compute(b, n, b, new DiagramTip());
		double[] cusps = cd.getCuspArray();
		double asc = cusps[1];
		double d = City.normalizeDegree(asc) % 30.0;
		System.out.println("ASC(cusp1)=" + String.format(java.util.Locale.US, "%.4f", asc)
				+ "  宫内度=" + String.format(java.util.Locale.US, "%.4f", d));
		for (int base = 9; base <= 10; base++)
			System.out.println("  base=" + base + " -> Y=" + (int) ((base + d / 3.0) * 365.25));
		System.out.println("  命度=" + String.format(java.util.Locale.US, "%.4f", cd.getLifeSignPos()));
	}
}
