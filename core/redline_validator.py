"""
红线检查器 + AI 禁止词扫描
零 LLM 成本，纯正则，秒级完成。
基于 OpenMOSS 17 条红线 + 100+ 禁止词清单。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


# ═══════════════════════════════════════════════════════════════════════════════
# 1. AI 禁止词清单（发现即标记）
# ═══════════════════════════════════════════════════════════════════════════════

AI_FORBIDDEN_PATTERNS: list[tuple[str, str]] = [
    # ── 机械排序词 ──
    (r'首先.{0,8}其次', '机械排序词: 首先…其次'),
    (r'首先.{0,8}然后.{0,8}最后', '机械排序词: 首先…然后…最后'),
    (r'第一[，,、].{0,6}第二', '机械排序词: 第一…第二'),
    (r'总的来说', '总结性词汇: 总的来说'),
    (r'综上所述', '总结性词汇: 综上所述'),
    (r'归根结底', '总结性词汇: 归根结底'),
    (r'通过上文', '总结性词汇: 通过上文'),

    # ── AI 过渡词 ──
    (r'更关键的是', 'AI过渡词: 更关键的是'),
    (r'更奇怪的是', 'AI过渡词: 更奇怪的是'),
    (r'更有趣的是', 'AI过渡词: 更有趣的是'),
    (r'有意思的是', 'AI过渡词: 有意思的是'),
    (r'值得注意的是', 'AI过渡词: 值得注意的是'),
    (r'值得一提的是', 'AI过渡词: 值得一提的是'),
    (r'不可否认', 'AI过渡词: 不可否认'),
    (r'诚然[，,]', 'AI过渡词: 诚然'),

    # ── 元叙事词（绝对禁止）──
    (r'核心动机', '元叙事词: 核心动机'),
    (r'叙事节奏', '元叙事词: 叙事节奏'),
    (r'人物弧线', '元叙事词: 人物弧线'),
    (r'戏剧张力', '元叙事词: 戏剧张力'),
    (r'情节推进', '元叙事词: 情节推进'),
    (r'角色塑造', '元叙事词: 角色塑造'),
    (r'故事走向', '元叙事词: 故事走向'),
    (r'悬念设置', '元叙事词: 悬念设置'),

    # ── 报告式语言 ──
    (r'分析了形势', '报告式: 分析了形势'),
    (r'从.{2,6}角度来看', '报告式: 从…角度来看'),
    (r'综合考虑', '报告式: 综合考虑'),
    (r'由此可见', '报告式: 由此可见'),
    (r'不难发现', '报告式: 不难发现'),

    # ── 集体反应套话 ──
    (r'全场震惊', '集体反应: 全场震惊'),
    (r'众人哗然', '集体反应: 众人哗然'),
    (r'所有人都.{0,4}了', '集体反应: 所有人都…了'),
    (r'无一例外', '集体反应: 无一例外'),

    # ── 陈词滥调 ──
    (r'在这个.{2,8}的时代', '陈词滥调: 在这个…的时代'),
    (r'众所周知', '陈词滥调: 众所周知'),
    (r'不言而喻', '陈词滥调: 不言而喻'),
    (r'毫无疑问', '陈词滥调: 毫无疑问'),
    (r'显而易见', '陈词滥调: 显而易见'),

    # ── 作者说教 ──
    (r'显然[，,]', '作者说教: 显然'),
    (r'毋庸置疑', '作者说教: 毋庸置疑'),
    (r'不容置疑', '作者说教: 不容置疑'),

    # ── 机械询问 ──
    (r'你知道吗', '机械询问: 你知道吗'),
    (r'大家想象一下', '机械询问: 大家想象一下'),
    (r'你有没有想过', '机械询问: 你有没有想过'),
]


# ═══════════════════════════════════════════════════════════════════════════════
# 2. 红线清单（一票否决）
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class RedlineViolation:
    category: str       # "情节" | "文笔"
    rule: str           # 规则名称
    description: str    # 具体描述
    severity: str = "critical"


# 正则可检测的红线（零 LLM）
REGLINE_PATTERNS: list[tuple[str, str, str]] = [
    # (pattern, rule_name, description)
    (r'首先.{0,8}其次.{0,8}最后', '开篇平庸', '使用了机械排序词，像写论文不像小说'),
    (r'我叫.{2,10}，今年.{1,4}岁', '开篇平庸', '开篇自我介绍，无吸引力'),
    (r'众所周知.{0,20}有着悠久的历史', '开篇平庸', '大段背景介绍，读者没耐心'),
]


@dataclass
class ValidationResult:
    forbidden_hits: list[str] = field(default_factory=list)   # 禁止词命中
    redline_hits: list[RedlineViolation] = field(default_factory=list)  # 红线命中
    word_count: int = 0
    sentence_count: int = 0
    short_sentence_ratio: float = 0.0

    @property
    def has_redline(self) -> bool:
        return len(self.redline_hits) > 0

    @property
    def forbidden_count(self) -> int:
        return len(self.forbidden_hits)


class RedlineValidator:
    """
    红线检查器 + AI 禁止词扫描
    用法：
        validator = RedlineValidator()
        result = validator.validate(content)
        if result.has_redline:
            # 一票否决，强制返工
    """

    def validate(self, text: str) -> ValidationResult:
        result = ValidationResult()

        # ── 禁止词扫描 ──
        for pattern, label in AI_FORBIDDEN_PATTERNS:
            matches = re.findall(pattern, text)
            if matches:
                # 去重
                unique = list(dict.fromkeys(matches))
                for m in unique[:3]:  # 最多报 3 个
                    result.forbidden_hits.append(f"{label}: 「{m}」")

        # ── 红线扫描（正则可检测的）──
        for pattern, rule, desc in REGLINE_PATTERNS:
            if re.search(pattern, text):
                result.redline_hits.append(RedlineViolation(
                    category="文笔", rule=rule, description=desc,
                ))

        # ── 统计指标 ──
        result.word_count = len(text)
        sentences = re.split(r'[。！？；\n]', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        result.sentence_count = len(sentences)
        if sentences:
            short = sum(1 for s in sentences if len(s) <= 20)
            result.short_sentence_ratio = short / len(sentences)

        return result


# ═══════════════════════════════════════════════════════════════════════════════
# 3. 9 维度审计数据结构
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class DimensionScore:
    dimension: str      # 维度名称
    weight: float       # 权重 0.0-1.0
    score: int          # 0-100
    pass_line: int      # 通过线
    issues: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.score >= self.pass_line


@dataclass
class EnhancedAuditReport:
    dimensions: list[DimensionScore] = field(default_factory=list)
    redline_violations: list[RedlineViolation] = field(default_factory=list)
    weighted_total: float = 0.0
    revision_round: int = 0

    @property
    def passed(self) -> bool:
        # 红线一票否决
        if self.redline_violations:
            return False
        # 总分 >= 95 且单项 >= 85
        if self.weighted_total < 95.0:
            return False
        for d in self.dimensions:
            if d.score < 85:
                return False
        return True

    @property
    def critical_count(self) -> int:
        return len(self.redline_violations) + sum(
            1 for d in self.dimensions if d.score < d.pass_line
        )

    def summary(self) -> str:
        lines = [f"加权总分: {self.weighted_total:.1f} | 判定: {'通过' if self.passed else '返工'}"]
        for d in self.dimensions:
            status = "✅" if d.passed else "❌"
            lines.append(f"  {status} {d.dimension}({d.weight*100:.0f}%): {d.score}分 (≥{d.pass_line})")
        if self.redline_violations:
            lines.append(f"  🚨 红线命中: {len(self.redline_violations)} 条（一票否决）")
            for v in self.redline_violations:
                lines.append(f"    - [{v.rule}] {v.description}")
        return "\n".join(lines)
