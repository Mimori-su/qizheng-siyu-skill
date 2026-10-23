//
// 挂起定位探针(修复批五): 子线程跑 Main.main, 40s未完则 dump 全线程栈后 exit 9
//
package org.athomeprojects.app;

import java.util.Map;

public class HangProbe {
	public static void main(String[] a) throws Exception {
		final String[] args = a;
		Thread t = new Thread(() -> {
			try {
				org.athomeprojects.app.Main.main(args);
				System.err.println("[HangProbe] DONE");
			} catch (Throwable e) {
				System.err.println("[HangProbe] THROWN: " + e);
			}
		}, "main-work");
		t.setDaemon(false);
		t.start();
		for (int i = 0; i < 4; i++) {
			Thread.sleep(10000);
			if (!t.isAlive())
				return;
			System.err.println("=== [HangProbe] alive after " + ((i + 1) * 10)
					+ "s, thread dump ===");
			for (Map.Entry<Thread, StackTraceElement[]> e : Thread
					.getAllStackTraces().entrySet()) {
				if (e.getValue().length == 0)
					continue;
				System.err.println("THREAD " + e.getKey().getName());
				for (int k = 0; k < Math.min(10, e.getValue().length); k++)
					System.err.println("    " + e.getValue()[k]);
			}
		}
		System.err.println("=== [HangProbe] HANG CONFIRMED, exit 9 ===");
		System.exit(9);
	}
}
