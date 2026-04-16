"""
巡查 Agent — 系统健康监控
基于 OpenMOSS Task Patrol 机制，适配 Dramatica-Flow 的小说创作场景。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class PatrolIssue:
    severity: str       # "warning" | "critical"
    category: str       # "伏笔" | "支线" | "因果链" | "状态" | "质量"
    description: str
    suggestion: str = ""


@dataclass
class PatrolReport:
    chapter: int
    timestamp: str
    issues: list[PatrolIssue] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    @property
    def has_critical(self) -> bool:
        return any(i.severity == "critical" for i in self.issues)

    @property
    def has_warning(self) -> bool:
        return any(i.severity == "warning" for i in self.issues)

    def summary(self) -> str:
        if not self.issues:
            return f"Ch.{self.chapter} 巡查完毕，一切如常。"
        lines = [f"Ch.{self.chapter} 巡查报告："]
        for i in self.issues:
            icon = "🚨" if i.severity == "critical" else "⚠️"
            lines.append(f"  {icon} [{i.category}] {i.description}")
            if i.suggestion:
                lines.append(f"     建议：{i.suggestion}")
        return "\n".join(lines)


class PatrolAgent:
    """
    巡查 Agent — 每隔 N 章自动检查系统健康状态

    检查项：
    1. 伏笔回收超期
    2. 支线掉线
    3. 因果链断裂
    4. 真相文件一致性
    5. 质量趋势下降
    """

    # 掉线阈值（章）
    DORMANCY_THRESHOLD = 5
    # 伏笔超期阈值（章）
    HOOK_OVERDUE_THRESHOLD = 10
    # 巡查间隔（每 N 章巡查一次）
    PATROL_INTERVAL = 3

    def __init__(self, state_manager):
        self.sm = state_manager

    def should_patrol(self, chapter: int) -> bool:
        """是否应该在本章巡查"""
        return chapter % self.PATROL_INTERVAL == 0

    def patrol(self, chapter: int) -> PatrolReport:
        """执行巡查"""
        report = PatrolReport(
            chapter=chapter,
            timestamp=datetime.now().isoformat(),
        )
        ws = self.sm.read_world_state()

        # ── 1. 伏笔超期检查 ──
        self._check_overdue_hooks(ws, chapter, report)

        # ── 2. 支线掉线检查 ──
        self._check_dormant_threads(ws, chapter, report)

        # ── 3. 因果链断裂检查 ──
        self._check_causal_chain_gaps(ws, chapter, report)

        # ── 4. 真相文件一致性 ──
        self._check_truth_consistency(chapter, report)

        # ── 5. 统计信息 ──
        report.stats = {
            "total_hooks": len(ws.pending_hooks),
            "open_hooks": len(ws.open_hooks()),
            "overdue_hooks": len(ws.overdue_hooks(chapter)),
            "total_causal_links": len(ws.causal_chain),
            "total_threads": len(ws.threads),
            "active_threads": len(ws.get_active_threads()),
            "total_timeline_events": len(ws.timeline),
        }

        return report

    def _check_overdue_hooks(self, ws, chapter: int, report: PatrolReport):
        """检查超期伏笔"""
        overdue = ws.overdue_hooks(chapter)
        for hook in overdue:
            gap = chapter - hook.expected_resolution_range[1]
            severity = "critical" if gap > self.HOOK_OVERDUE_THRESHOLD else "warning"
            report.issues.append(PatrolIssue(
                severity=severity,
                category="伏笔",
                description=f"伏笔「{hook.description}」超期 {gap} 章未回收（预期 Ch.{hook.expected_resolution_range[1]}）",
                suggestion="在下一章安排回收，或调整预期回收范围",
            ))

    def _check_dormant_threads(self, ws, chapter: int, report: PatrolReport):
        """检查支线掉线"""
        dormant = ws.dormant_threads(chapter, threshold=self.DORMANCY_THRESHOLD)
        for thread in dormant:
            gap = chapter - thread.last_active_chapter
            severity = "critical" if gap > self.DORMANCY_THRESHOLD * 2 else "warning"
            report.issues.append(PatrolIssue(
                severity=severity,
                category="支线",
                description=f"线程「{thread.name}」已 {gap} 章未活跃",
                suggestion="在近期安排该线程的章节，或标记为暂停",
            ))

    def _check_causal_chain_gaps(self, ws, chapter: int, report: PatrolReport):
        """检查因果链断裂"""
        if not ws.causal_chain:
            if chapter > 3:
                report.issues.append(PatrolIssue(
                    severity="warning",
                    category="因果链",
                    description=f"已写到 Ch.{chapter} 但因果链为空",
                    suggestion="检查因果链提取是否正常工作",
                ))
            return

        # 检查最近是否有因果链
        recent_links = [cl for cl in ws.causal_chain if cl.chapter >= chapter - 2]
        if not recent_links and chapter > 2:
            report.issues.append(PatrolIssue(
                severity="warning",
                category="因果链",
                description=f"最近 3 章无新增因果链",
                suggestion="检查因果链提取逻辑",
            ))

    def _check_truth_consistency(self, chapter: int, report: PatrolReport):
        """检查真相文件一致性"""
        # 检查 chapter_summaries 是否有最近章节的摘要
        summaries = self.sm.read_truth("chapter_summaries")
        if chapter > 1 and f"第 {chapter - 1} 章" not in summaries:
            report.issues.append(PatrolIssue(
                severity="warning",
                category="状态",
                description=f"chapter_summaries 缺少 Ch.{chapter - 1} 的摘要",
                suggestion="补充上一章摘要，否则写手缺少前情上下文",
            ))

        # 检查 current_state.md 是否更新
        current_state = self.sm.read_truth("current_state")
        if chapter > 1 and f"Ch.{chapter - 1}" not in current_state and f"第{chapter - 1}章" not in current_state:
            report.issues.append(PatrolIssue(
                severity="warning",
                category="状态",
                description=f"current_state.md 可能未更新到 Ch.{chapter - 1}",
                suggestion="运行 update_current_state_md()",
            ))
