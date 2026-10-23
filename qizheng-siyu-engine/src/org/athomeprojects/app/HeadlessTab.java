//
// App口径排盘引擎核心 — 无头文本桶
// 衍生自 Moira v1.50 (GPL)，见 README.md 的 GPL 声明
//
package org.athomeprojects.app;

import org.athomeprojects.base.BaseTab;

// ENGINE-DELTA: BaseTab 在 Moira 里是 SWT 文本控件的抽象；
// 无头模式下以 StringBuilder 吸收 showData() 的全部文本输出。
public class HeadlessTab extends BaseTab {
	private final StringBuilder buf = new StringBuilder();

	public void clear() {
		buf.setLength(0);
	}

	public void append(String str) {
		buf.append(str);
	}

	public void appendLine(String str) {
		buf.append(str).append('\n');
	}

	public void appendLine() {
		buf.append('\n');
	}

	public String getText() {
		return buf.toString();
	}
}
