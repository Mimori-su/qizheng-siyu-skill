//
// App口径排盘引擎核心 — 无头消息应答
// 衍生自 Moira v1.50 (GPL)，见 README.md 的 GPL 声明
//
package org.athomeprojects.app;

import org.athomeprojects.base.BaseMessage;

// ENGINE-DELTA: Moira 桌面壳的 Message 会弹 SWT 对话框(如"星历文件缺失, 是否下载/换Moshier")。
// 无头模式禁弹窗(工作纪律): question=true 走"尝试下载"分支——离线即下载失败→该星体置INVALID并保持
// SWIEPH 精确级不变; 绝不走 question=false → setEphMode(true) 的全局 Moshier 降级(口径不可控)。
public class HeadlessMessage extends BaseMessage {
	public boolean question(String message) {
		System.err.println("[HeadlessMessage] question(答true): " + message);
		return true;
	}

	public void warn(String message) {
		System.err.println("[HeadlessMessage] warn: " + message);
	}
}
