#!/usr/bin/env python3
"""
Dramatica-Flow 一键升级脚本
========================================
使用方法：
  1. git clone https://github.com/ydsgangge-ux/dramatica-flow.git
  2. cd dramatica-flow
  3. 把这个 upgrade.py 放到项目根目录
  4. python upgrade.py

它会自动：
  - 创建 3 个新文件到 core/
  - 修改 core/agents/__init__.py（追加去AI味prompt）
  - 修改 core/pipeline.py（集成新组件）
  - 创建 knowledge-base/ 目录
  - 备份所有被修改的文件（.bak 后缀）
"""
import os
import re
import shutil
import sys
from pathlib import Path


def backup(path: Path):
    if path.exists():
        bak = path.with_suffix(path.suffix + ".bak")
        shutil.copy2(path, bak)
        print(f"  📦 备份: {path.name} → {bak.name}")


def write_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  ✅ 创建: {path}")


def patch_file(path: Path, old: str, new: str, label: str = "") -> bool:
    text = path.read_text(encoding="utf-8")
    if old in text:
        text = text.replace(old, new, 1)
        path.write_text(text, encoding="utf-8")
        print(f"  ✅ 修改: {path.name} — {label}")
        return True
    else:
        print(f"  ⚠️  跳过: {path.name} — 找不到匹配文本 ({label})")
        return False


def append_to_file(path: Path, content: str, label: str = ""):
    text = path.read_text(encoding="utf-8")
    if content.strip() in text:
        print(f"  ⏭️  跳过: {path.name} — 已包含 ({label})")
        return
    path.write_text(text + content, encoding="utf-8")
    print(f"  ✅ 追加: {path.name} — {label}")


# ═══════════════════════════════════════════════════════════════════════════════
# 文件内容定义
# ═══════════════════════════════════════════════════════════════════════════════

REDLINE_VALIDATOR_CONTENT = r'''"""
红线检查器 + AI 禁止词扫描
零 LLM 成本，纯正则，秒级完成。
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field

AI_FORBIDDEN_PATTERNS: list[tuple[str, str]] = [
    (r'首先.{0,8}其次', '机械排序词: 首先…其次'),
    (r'首先.{0,8}然后.{0,8}最后', '机械排序词: 首先…然后…最后'),
    (r'第一[，,、].{0,6}第二', '机械排序词: 第一…第二'),
    (r'总的来说', '总结性词汇: 总的来说'),
    (r'综上所述', '总结性词汇: 综上所述'),
    (r'归根结底', '总结性词汇: 归根结底'),
    (r'通过上文', '总结性词汇: 通过上文'),
    (r'更关键的是', 'AI过渡词: 更关键的是'),
    (r'更奇怪的是', 'AI过渡词: 更奇怪的是'),
    (r'更有趣的是', 'AI过渡词: 更有趣的是'),
    (r'有意思的是', 'AI过渡词: 有意思的是'),
    (r'值得注意的是', 'AI过渡词: 值得注意的是'),
    (r'值得一提的是', 'AI过渡词: 值得一提的是'),
    (r'不可否认', 'AI过渡词: 不可否认'),
    (r'诚然[，,]', 'AI过渡词: 诚然'),
    (r'核心动机', '元叙事词: 核心动机'),
    (r'叙事节奏', '元叙事词: 叙事节奏'),
    (r'人物弧线', '元叙事词: 人物弧线'),
    (r'戏剧张力', '元叙事词: 戏剧张力'),
    (r'情节推进', '元叙事词: 情节推进'),
    (r'角色塑造', '元叙事词: 角色塑造'),
    (r'故事走向', '元叙事词: 故事走向'),
    (r'悬念设置', '元叙事词: 悬念设置'),
    (r'分析了形势', '报告式: 分析了形势'),
    (r'从.{2,6}角度来看', '报告式: 从…角度来看'),
    (r'综合考虑', '报告式: 综合考虑'),
    (r'由此可见', '报告式: 由此可见'),
    (r'不难发现', '报告式: 不难发现'),
    (r'全场震惊', '集体反应: 全场震惊'),
    (r'众人哗然', '集体反应: 众人哗然'),
    (r'所有人都.{0,4}了', '集体反应: 所有人都…了'),
    (r'无一例外', '集体反应: 无一例外'),
    (r'在这个.{2,8}的时代', '陈词滥调: 在这个…的时代'),
    (r'众所周知', '陈词滥调: 众所周知'),
    (r'不言而喻', '陈词滥调: 不言而喻'),
    (r'毫无疑问', '陈词滥调: 毫无疑问'),
    (r'显而易见', '陈词滥调: 显而易见'),
    (r'显然[，,]', '作者说教: 显然'),
    (r'毋庸置疑', '作者说教: 毋庸置疑'),
    (r'不容置疑', '作者说教: 不容置疑'),
    (r'你知道吗', '机械询问: 你知道吗'),
    (r'大家想象一下', '机械询问: 大家想象一下'),
    (r'你有没有想过', '机械询问: 你有没有想过'),
]

REGLINE_PATTERNS: list[tuple[str, str, str]] = [
    (r'首先.{0,8}其次.{0,8}最后', '开篇平庸', '使用了机械排序词'),
    (r'我叫.{2,10}，今年.{1,4}岁', '开篇平庸', '开篇自我介绍，无吸引力'),
    (r'众所周知.{0,20}有着悠久的历史', '开篇平庸', '大段背景介绍'),
]


@dataclass
class RedlineViolation:
    category: str
    rule: str
    description: str
    severity: str = "critical"


@dataclass
class ValidationResult:
    forbidden_hits: list[str] = field(default_factory=list)
    redline_hits: list[RedlineViolation] = field(default_factory=list)
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
    def validate(self, text: str) -> ValidationResult:
        result = ValidationResult()
        for pattern, label in AI_FORBIDDEN_PATTERNS:
            matches = re.findall(pattern, text)
            if matches:
                unique = list(dict.fromkeys(matches))
                for m in unique[:3]:
                    result.forbidden_hits.append(f"{label}: 「{m}」")
        for pattern, rule, desc in REGLINE_PATTERNS:
            if re.search(pattern, text):
                result.redline_hits.append(RedlineViolation("文笔", rule, desc))
        result.word_count = len(text)
        sentences = [s.strip() for s in re.split(r'[。！？；\n]', text) if s.strip()]
        result.sentence_count = len(sentences)
        if sentences:
            result.short_sentence_ratio = sum(1 for s in sentences if len(s) <= 20) / len(sentences)
        return result


@dataclass
class DimensionScore:
    dimension: str
    weight: float
    score: int
    pass_line: int
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
        if self.redline_violations:
            return False
        if self.weighted_total < 95.0:
            return False
        return all(d.score >= 85 for d in self.dimensions)

    @property
    def critical_count(self) -> int:
        return len(self.redline_violations) + sum(1 for d in self.dimensions if not d.passed)

    def summary(self) -> str:
        lines = [f"加权总分: {self.weighted_total:.1f} | {'通过' if self.passed else '返工'}"]
        for d in self.dimensions:
            s = "✅" if d.passed else "❌"
            lines.append(f"  {s} {d.dimension}({d.weight*100:.0f}%): {d.score}分 (≥{d.pass_line})")
        if self.redline_violations:
            lines.append(f"  🚨 红线命中: {len(self.redline_violations)} 条")
        return "\n".join(lines)
'''

AUDIT_UPGRADE_CONTENT = r'''"""
9 维度加权审计 Agent
替代原有 AuditorAgent 的模糊审计。
"""
from __future__ import annotations
from .redline_validator import DimensionScore, EnhancedAuditReport, RedlineViolation, RedlineValidator
from ..llm import LLMProvider, LLMMessage, parse_llm_json, with_retry
from pydantic import BaseModel, Field

DIMENSION_CONFIG = [
    ("主线战力",  0.20, 90),
    ("文笔质量",  0.15, 90),
    ("场景构建",  0.15, 95),
    ("心理刻画",  0.15, 95),
    ("对话质量",  0.10, 90),
    ("风格一致",  0.10, 90),
    ("设定一致",  0.08, 90),
    ("结构合理",  0.05, 90),
    ("人物OOC",   0.02, 90),
]

RELINE_CHECKLIST = """逐条检查红线（任一条命中即一票否决）：
1.反派降智 2.时间线错乱 3.数据模糊 4.战力崩坏 5.配角工具人
6.主角双标 7.无脑后宫 8.机械降神 9.烂尾逻辑 10.开篇平庸
11.节奏拖沓 12.风格突变 13.人物OOC 14.对话出戏"""

class _DimensionResult(BaseModel):
    dimension: str
    score: int
    issues: list[str] = Field(default_factory=list)

class _AuditSchema(BaseModel):
    dimensions: list[_DimensionResult]
    redline_violations: list[str] = Field(default_factory=list)
    summary: str = ""

AUDIT_PROMPT = """你是严苛的文学编辑。审计第{ch}章《{title}》。

正文（前8000字）：
{content}

世界状态：
{truth}

蓝图：
{blueprint}

结算表：
{settlement}

跨线程：
{cross}

{redline_check}

9维度评分（0-100）：
主线战力20%≥90|文笔质量15%≥90|场景构建15%≥95|心理刻画15%≥95
对话质量10%≥90|风格一致10%≥90|设定一致8%≥90|结构合理5%≥90|人物OOC2%≥90

文笔专项：查禁止词（首先/其次/综上所述/更关键的是/核心动机/全场震惊等）
场景专项：空间感+五感+画面感
心理专项：层次+留白+共鸣

只输出JSON：
{{"dimensions":[{{"dimension":"主线战力","score":85,"issues":["问题"]}},...],"redline_violations":[],"summary":"一句话"}}"""

class EnhancedAuditorAgent:
    def __init__(self, llm: LLMProvider, validator: RedlineValidator | None = None):
        self.llm = llm
        self.validator = validator or RedlineValidator()

    def audit_chapter(self, chapter_content, chapter_number, blueprint=None,
                      truth_context="", settlement=None, cross_thread_context="",
                      chapter_title="") -> EnhancedAuditReport:
        val = self.validator.validate(chapter_content)

        bp = ""
        if blueprint:
            bp = f"冲突：{blueprint.core_conflict}\n情感：{blueprint.emotional_journey}\n节奏：{blueprint.pace_notes}"

        st = ""
        if settlement:
            st = f"伏笔：{settlement.new_hooks}\n回收：{settlement.resolved_hooks}\n关系：{settlement.relationship_changes}"

        prompt = AUDIT_PROMPT.format(
            ch=chapter_number, title=chapter_title,
            content=chapter_content[:8000], truth=truth_context[:3000],
            blueprint=bp[:1500], settlement=st[:1500],
            cross=cross_thread_context[:1000], redline_check=RELINE_CHECKLIST,
        )

        def _call():
            resp = self.llm.complete([
                LLMMessage("system", "你是严苛文学编辑，只输出JSON。"),
                LLMMessage("user", prompt),
            ])
            parsed = parse_llm_json(resp.content, _AuditSchema, "audit")
            dims = []
            dm = {c[0]: c for c in DIMENSION_CONFIG}
            for dr in parsed.dimensions:
                c = dm.get(dr.dimension)
                if c:
                    dims.append(DimensionScore(dr.dimension, c[1], dr.score, c[2], dr.issues))
            existing = {d.dimension for d in dims}
            for name, w, pl in DIMENSION_CONFIG:
                if name not in existing:
                    dims.append(DimensionScore(name, w, 80, pl, ["未返回"]))
            total = sum(d.score * d.weight for d in dims)
            rvs = list(val.redline_hits)
            for t in parsed.redline_violations:
                rvs.append(RedlineViolation("情节", "LLM检测", t))
            return EnhancedAuditReport(dims, rvs, total)
        return with_retry(_call)
'''

PATROL_AGENT_CONTENT = r'''"""
巡查 Agent — 系统健康监控
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class PatrolIssue:
    severity: str
    category: str
    description: str
    suggestion: str = ""

@dataclass
class PatrolReport:
    chapter: int
    timestamp: str
    issues: list[PatrolIssue] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    @property
    def has_critical(self): return any(i.severity == "critical" for i in self.issues)
    @property
    def has_warning(self): return any(i.severity == "warning" for i in self.issues)

    def summary(self) -> str:
        if not self.issues: return f"Ch.{self.chapter} 巡查完毕，一切如常。"
        lines = [f"Ch.{self.chapter} 巡查报告："]
        for i in self.issues:
            icon = "🚨" if i.severity == "critical" else "⚠️"
            lines.append(f"  {icon} [{i.category}] {i.description}")
            if i.suggestion: lines.append(f"     建议：{i.suggestion}")
        return "\n".join(lines)

class PatrolAgent:
    DORMANCY_THRESHOLD = 5
    HOOK_OVERDUE_THRESHOLD = 10
    PATROL_INTERVAL = 3

    def __init__(self, state_manager): self.sm = state_manager
    def should_patrol(self, chapter): return chapter % self.PATROL_INTERVAL == 0

    def patrol(self, chapter) -> PatrolReport:
        report = PatrolReport(chapter, datetime.now().isoformat())
        ws = self.sm.read_world_state()
        self._check_hooks(ws, chapter, report)
        self._check_threads(ws, chapter, report)
        self._check_causal(ws, chapter, report)
        self._check_truth(chapter, report)
        report.stats = {
            "open_hooks": len(ws.open_hooks()),
            "overdue": len(ws.overdue_hooks(chapter)),
            "causal_links": len(ws.causal_chain),
            "threads": len(ws.threads),
        }
        return report

    def _check_hooks(self, ws, ch, r):
        for h in ws.overdue_hooks(ch):
            gap = ch - h.expected_resolution_range[1]
            r.issues.append(PatrolIssue(
                "critical" if gap > self.HOOK_OVERDUE_THRESHOLD else "warning",
                "伏笔", f"「{h.description}」超期{gap}章", "下一章安排回收"))

    def _check_threads(self, ws, ch, r):
        for t in ws.dormant_threads(ch, self.DORMANCY_THRESHOLD):
            gap = ch - t.last_active_chapter
            r.issues.append(PatrolIssue(
                "critical" if gap > self.DORMANCY_THRESHOLD*2 else "warning",
                "支线", f"「{t.name}」已{gap}章未活跃", "近期安排该线程"))

    def _check_causal(self, ws, ch, r):
        if not ws.causal_chain and ch > 3:
            r.issues.append(PatrolIssue("warning", "因果链", "因果链为空", "检查提取逻辑"))
        elif ws.causal_chain:
            recent = [cl for cl in ws.causal_chain if cl.chapter >= ch-2]
            if not recent and ch > 2:
                r.issues.append(PatrolIssue("warning", "因果链", "近3章无新增因果链"))

    def _check_truth(self, ch, r):
        s = self.sm.read_truth("chapter_summaries")
        if ch > 1 and f"第 {ch-1} 章" not in s:
            r.issues.append(PatrolIssue("warning", "状态", f"缺少Ch.{ch-1}摘要", "补充摘要"))
'''

WRITER_PROMPT_ADDITION = '''

## 去AI味铁律（强制执行）

### 禁止词
绝对禁止：首先/其次/最后/综上所述/总的来说/更关键的是/有意思的是/值得注意的是/众所周知/不言而喻/毫无疑问/核心动机/叙事节奏/人物弧线/全场震惊/众人哗然/所有人都

### 45特征润色
1.错别字：每1000字1-2处（音近字）
2.口语化：20%书面语改口语
3.语气词：每300字3-4个（啊/呢/吧/嘛）
4.短句：≤20字占60%+
5.具体细节：写"锈迹斑斑的铜钥匙"非"旧钥匙"
6.主观感受：每段有"我觉得""说实话"
7.不完美逻辑：允许跳跃
8.情绪化标点：破折号——省略号…

### Show Don't Tell
他很愤怒→他捏碎了茶杯。她很害怕→手在发抖钥匙插了三遍。他很紧张→原地转圈深呼吸。

### 五感描写
每个场景≥2种感官（视/听/嗅/味/触）
'''

KNOWLEDGE_BASE_FILES = {
    "knowledge-base/rules/review-criteria-95.md": """# 95分审查标准
## 通过标准
总分≥95 且 单项≥85，红线一票否决
## 9维度
主线战力20%≥90|文笔15%≥90|场景15%≥95|心理15%≥95|对话10%≥90|风格10%≥90|设定8%≥90|结构5%≥90|OOC2%≥90
## 文笔检查
无AI词|口语化|短句60%+|具体细节|情感真实|读者沉浸
## 场景检查
空间感|视觉+听觉+其他感官|氛围|画面感
## 心理检查
符合性格|层次(表面→深层)|留白|共鸣
""",
    "knowledge-base/rules/redlines.md": """# 红线清单（一票否决）
## 情节类
1.反派降智 2.时间线错乱 3.数据模糊 4.战力崩坏 5.配角工具人 6.主角双标 7.无脑后宫 8.机械降神 9.烂尾逻辑
## 文笔类
10.开篇平庸 11.节奏拖沓 12.风格突变 13.人物OOC 14.对话出戏
""",
    "knowledge-base/rules/de-ai-guidelines.md": """# 去AI味指南
## 禁止词
首先/其次/最后/综上所述/更关键的是/众所周知/核心动机/全场震惊等
## 45特征
错别字/口语化/语气词/短句/细节/主观/跳跃/重复/标点
## Show Don't Tell
愤怒→摔门/害怕→发抖/紧张→转圈/伤心→发呆/兴奋→眼睛发亮
## 自检频率
每500字自检，每1000字加错别字，每场景≥2感官
""",
    "knowledge-base/examples/before-after/revision-01-scene.md": """# 修改前后对比
## 修改前（AI味）
首先，这是一个雨夜。他感到很孤独。众所周知，失去亲人很痛苦。
## 修改后
雨下得太久了。老张头睁着眼数天花板的裂缝。窗外乌鸦在叫，像是被掐住了脖子。
## 分析
删除机械词→展示而非讲述→具体细节→多感官→口语化
""",
    "knowledge-base/examples/good/dialogue-tension.md": """# 紧张对话示例
"谁派你来的？"女人看向窗外，像在数雨点。"我在问你话。"他声音低下去，不是生气，是那种更让人害怕的平静。"你知道我不会说的。""我知道你会。"他向前一步，"每个人都有一个价。你的价是什么？"
技巧：用动作打断对话，用破折号制造停顿
""",
    "knowledge-base/references/writing-techniques/show-dont-tell.md": """# Show Don't Tell
核心：不告诉感受，展示动作。
他很愤怒→他捏碎茶杯。她很害怕→钥匙插三遍。他很紧张→原地转圈。她很伤心→筷子搅十分钟。
转换：找"感到XX"→问"怎么表现"→写具体动作
""",
}


# ═══════════════════════════════════════════════════════════════════════════════
# 主逻辑
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("  Dramatica-Flow 一键升级工具")
    print("  基于 OpenMOSS 审查机制的 4 大核心改进")
    print("=" * 60)

    project_root = Path(__file__).parent
    core_dir = project_root / "core"

    # 检查是否在正确的目录
    if not core_dir.exists():
        print("\n❌ 错误：找不到 core/ 目录")
        print("   请把这个脚本放到 dramatica-flow 项目根目录下")
        print("   正确目录结构：dramatica-flow/core/...")
        sys.exit(1)

    if not (core_dir / "pipeline.py").exists():
        print("\n❌ 错误：core/pipeline.py 不存在")
        print("   请确认你在 dramatica-flow 项目根目录")
        sys.exit(1)

    print(f"\n📁 项目根目录: {project_root}\n")

    # ── 1. 创建新文件 ──
    print("【1/4】创建新文件...")
    write_file(core_dir / "redline_validator.py", REDLINE_VALIDATOR_CONTENT)
    write_file(core_dir / "audit_upgrade.py", AUDIT_UPGRADE_CONTENT)
    write_file(core_dir / "patrol_agent.py", PATROL_AGENT_CONTENT)

    # ── 2. 创建知识库 ──
    print("\n【2/4】创建知识库...")
    for rel_path, content in KNOWLEDGE_BASE_FILES.items():
        write_file(project_root / rel_path, content)

    # ── 3. 修改 agents/__init__.py ──
    print("\n【3/4】修改 core/agents/__init__.py...")
    agents_file = core_dir / "agents" / "__init__.py"
    if agents_file.exists():
        backup(agents_file)
        append_to_file(agents_file, WRITER_PROMPT_ADDITION, "去AI味prompt")
    else:
        print(f"  ⚠️  文件不存在: {agents_file}")

    # ── 4. 修改 pipeline.py ──
    print("\n【4/4】修改 core/pipeline.py...")
    pipeline_file = core_dir / "pipeline.py"
    if pipeline_file.exists():
        backup(pipeline_file)
        text = pipeline_file.read_text(encoding="utf-8")

        # 4.1 添加 import
        import_addition = "\nfrom .redline_validator import RedlineValidator\nfrom .audit_upgrade import EnhancedAuditorAgent\nfrom .patrol_agent import PatrolAgent\n"
        if "RedlineValidator" not in text:
            # 找到最后一个 from .xxx import 行，在其后插入
            lines = text.split("\n")
            insert_idx = -1
            for i, line in enumerate(lines):
                if line.startswith("from .") and "import" in line:
                    insert_idx = i + 1
            if insert_idx > 0:
                lines.insert(insert_idx, "from .redline_validator import RedlineValidator")
                lines.insert(insert_idx + 1, "from .audit_upgrade import EnhancedAuditorAgent")
                lines.insert(insert_idx + 2, "from .patrol_agent import PatrolAgent")
                text = "\n".join(lines)
                print("  ✅ 添加 import 语句")
            else:
                print("  ⚠️  找不到 import 插入位置，手动添加")

        # 4.2 修改 __init__ 参数
        if "redline_validator" not in text:
            text = text.replace(
                "all_characters: list[Character],\n    ):",
                "all_characters: list[Character],\n        redline_validator: RedlineValidator | None = None,\n        enhanced_auditor: EnhancedAuditorAgent | None = None,\n        patrol_agent: PatrolAgent | None = None,\n    ):",
                1
            )
            # 添加赋值
            text = text.replace(
                "self.all_characters = all_characters",
                "self.all_characters = all_characters\n        self.redline_validator = redline_validator or RedlineValidator()\n        self.enhanced_auditor = enhanced_auditor\n        self.patrol_agent = patrol_agent",
                1
            )
            print("  ✅ 修改 __init__ 参数")

        # 4.3 修改 MAX_REVISE_ROUNDS
        text = text.replace("MAX_REVISE_ROUNDS = 2", "MAX_REVISE_ROUNDS = 3")
        print("  ✅ MAX_REVISE_ROUNDS 2→3")

        # 4.4 在 run() 中写后验证后插入红线扫描
        old_validate = 'val_result = self.validator.validate(\n            writer_output.content,\n            target_words=adjusted_target_words,\n        )\n        current_content = writer_output.content'
        new_validate = '''val_result = self.validator.validate(
            writer_output.content,
            target_words=adjusted_target_words,
        )
        # AI 禁止词扫描
        redline_result = self.redline_validator.validate(writer_output.content)
        if redline_result.forbidden_count > 0:
            log(f"发现 {redline_result.forbidden_count} 个禁止词")
            if redline_result.forbidden_count >= 5:
                val_result.passed = False
        current_content = writer_output.content'''
        if old_validate in text and "redline_result" not in text:
            text = text.replace(old_validate, new_validate, 1)
            print("  ✅ 插入红线扫描")

        # 4.5 在 return PipelineResult 前插入巡查
        patrol_code = '''
        # ── 巡查（每 3 章一次） ──────────────────────────────────────────
        if self.patrol_agent and self.patrol_agent.should_patrol(ch):
            log("执行巡查...")
            patrol_report = self.patrol_agent.patrol(ch)
            log(patrol_report.summary())
            if patrol_report.has_warning or patrol_report.has_critical:
                self.sm.append_truth(
                    TruthFileKey.THREAD_STATUS,
                    f"\\n### Ch.{ch} 巡查报告\\n{patrol_report.summary()}\\n",
                )

'''
        if "patrol_agent" not in text:
            text = text.replace(
                "return PipelineResult(",
                patrol_code + "        return PipelineResult(",
                1
            )
            print("  ✅ 插入巡查调用")

        pipeline_file.write_text(text, encoding="utf-8")
    else:
        print(f"  ⚠️  文件不存在: {pipeline_file}")

    print("\n" + "=" * 60)
    print("  ✅ 升级完成！")
    print("=" * 60)
    print("""
改动清单：
  ✅ core/redline_validator.py   — 红线检查 + 禁止词扫描
  ✅ core/audit_upgrade.py       — 9维度加权审计
  ✅ core/patrol_agent.py        — 巡查Agent
  ✅ knowledge-base/             — 知识库（6个文件）
  ✅ core/agents/__init__.py     — 追加去AI味prompt
  ✅ core/pipeline.py            — 集成新组件

备份文件（.bak后缀）已创建，出问题可以恢复。

下一步：
  1. 配置 .env（API Key 或 Ollama）
  2. python -m uvicorn core.server:app --reload --port 8766
  3. 访问 http://localhost:8766 开始使用
""")


if __name__ == "__main__":
    main()
