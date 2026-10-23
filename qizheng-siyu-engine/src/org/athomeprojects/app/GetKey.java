package org.athomeprojects.app;
import java.io.File;
import org.athomeprojects.base.*;
public class GetKey {
	public static void main(String[] a) throws Exception {
		File here = new File(GetKey.class.getProtectionDomain().getCodeSource()
				.getLocation().toURI()).getAbsoluteFile();
		File eng = here.getParentFile();
		while (eng != null && !new File(eng, "rsrc").isDirectory())
			eng = eng.getParentFile();
		FileIO.setBaseIO(new HeadlessIO(new File(eng, "rsrc")));
		new Resource(null, "simplified", null, null, null);
		System.out.println("hasKey(use_six_ren_god)=" + Resource.hasKey("use_six_ren_god"));
		System.out.println("getInt=" + Resource.getInt("use_six_ren_god"));
		System.out.println("hasKey(show_dou_sign)=" + Resource.hasKey("show_dou_sign"));
		System.out.println("raw=" + Resource.getString("use_six_ren_god"));
	}
}
