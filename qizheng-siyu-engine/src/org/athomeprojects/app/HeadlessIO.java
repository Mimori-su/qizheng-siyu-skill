//
// App口径排盘引擎核心 — 无头资源IO
// 衍生自 Moira v1.50 (GPL)，见 README.md 的 GPL 声明
//
package org.athomeprojects.app;

import java.io.File;
import java.net.MalformedURLException;
import java.net.URL;

import org.athomeprojects.base.BaseIO;

// ENGINE-DELTA: Moira 桌面版由 SWT 壳提供 prop 文件定位(BaseIO.getURL)，
// 无头 CLI 改为在指定资源目录(含 moira_s.prop/cities.prop)下解析。
// 修复批四B补充: -Dengine.rsrc 隔离副本时 base 在外层(如 C:\Temp), 相对星历路径
// (ephepath="ephemeris")必须仍可达——故增加 codeSource 引擎根作最后兜底 base。
public class HeadlessIO extends BaseIO {
	private final File base_dir;

	private final File code_dir; // 引擎根(经codeSource定位, 绝对路径, CWD无关)

	public HeadlessIO(File dir) {
		this(dir, null);
	}

	public HeadlessIO(File dir, File code_engine_root) {
		base_dir = dir;
		code_dir = code_engine_root;
	}

	public URL getURL(String file_name) {
		if (base_dir == null || file_name == null)
			return null;
		File f = new File(file_name);
		if (!f.isAbsolute()) {
			// 依次在 rsrc/、其父目录(engine/)、codeSource引擎根 解析:
			// prop 在 rsrc/, 星历在 engine/ephemeris/(经codeSource绝对定位, CWD无关)
			f = new File(base_dir, file_name);
			if (!f.exists() && base_dir.getParentFile() != null)
				f = new File(base_dir.getParentFile(), file_name);
			if (!f.exists() && code_dir != null)
				f = new File(code_dir, file_name);
		}
		if (!f.exists())
			System.err.println("[HeadlessIO] NOT FOUND(交给调用方降级): " + f);
		try {
			// 注意: 对缺失文件也返回URL(与Moira桌面壳一致)——
			// swisseph swi_fopen 依赖 getURL()!=null, 由 RandomAccessFile 的 IOException 走其内部降级链
			return f.toURI().toURL();
		} catch (MalformedURLException e) {
			return null;
		}
	}
}
