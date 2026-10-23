//
// 六壬12种rotatedIndex查表对照探针(修复批四A2回归)
// 规格来源=App原文推导(d.smali 86405 charAt子起→86417 亥起indexOf=+1; 86428 rsub 12-r; 86456 逆-1)
// 衍生自 Moira v1.50 (GPL)，见 README.md
//
package org.athomeprojects.app;

public class LiurenProbe {
	static final String ZI = "子丑寅卯辰巳午未申酉戌亥";   // 子起
	static final String HAI = "亥子丑寅卯辰巳午未申酉戌"; // 亥起
	static final String SHUN = "貴蛇朱合勾青空白常玄陰后";
	static final String NI = "后陰玄常白空青勾合朱蛇貴";

	public static void main(String[] a) {
		// 每行: r | dirIdx | 顺/逆 | 十二宫名序列(支[u]=子起[u], 名=window[u], u=0..11)
		for (int r = 0; r < 12; r++) {
			int dirIdx = (r + 1) % 12;
			boolean ni = dirIdx >= 6;
			int w = (12 - r) % 12;
			if (w == 0)
				w = 12;
			if (ni)
				w -= 1;
			String cyc = ni ? NI : SHUN;
			StringBuilder seq = new StringBuilder();
			for (int u = 0; u < 12; u++)
				seq.append(cyc.charAt((w + u) % 12));
			System.out.println("r=" + r + " dirIdx=" + dirIdx + " "
					+ (ni ? "逆" : "顺") + " " + seq);
		}
	}
}
