"""
9 维度加权审计 Agent
替代原有 AuditorAgent 的模糊审计，改为精确的 9 维度评分体系。
基于 OpenMOSS review-criteria-95.md。
"""
from __future__ import annotations

from dataclasses import dataclass

from .redline_validator import (
    DimensionScore, EnhancedAuditReport, RedlineViolation,
    RedlineValidator,
)
from ..llm import LLMProvider, LLMMessage, parse_llm_json, with_retry

from pydantic import BaseModel, Field


# ── 9 维度配置 ──────────────────────────────────────────────────────────────

DIMENSION_CONFIG = [
    ("主线战力",  0.20, 90, "逻辑自洽、战力不崩、反派不降智、无机械降神"),
    ("文笔质量",  0.15, 90, "去AI化、口语化、短句为主、读者沉浸"),
    ("场景构建",  0.15, 95, "空间感、五感细节、氛围营造、画面感"),
    ("心理刻画",  0.15, 95, "心理真实、层次分明、有留白、情感共鸣"),
    ("对话质量",  0.10, 90, "符合身份、推动剧情、有潜台词、不OOC"),
    ("风格一致",  0.10, 90, "文笔前后统一、人物语气一致、节奏连贯"),
    ("设定一致",  0.08, 90, "世界观无矛盾、设定前后一致"),
    ("结构合理",  0.05, 90, "起承转合自然、高潮分布合理"),
    ("人物OOC",   0.02, 90, "性格连贯、行为符合人设"),
]

# 红线清单（LLM 判断项）
RELINE_CHECKLIST = """
逐条检查以下红线（任一条命中即一票否决）：
1. 反派降智 — 反派做出不符合设定的愚蠢行为
2. 时间线错乱 — 时间顺序前后矛盾
3. 数据模糊 — 关键数据前后不一致
4. 战力崩坏 — 强者突然变弱或弱者突然变强
5. 配角工具人 — 配角无独立动机，纯为服务主角
6. 主角双标 — 主角对自己和他人标准不一致
7. 无脑后宫 — 角色无理由爱上主角
8. 机械降神 — 无铺垫地出现无敌力量解决危机
9. 烂尾逻辑 — 结局仓促、悬念不回收
10. 开篇平庸 — 开头无吸引力、大段背景介绍
11. 节奏拖沓 — 多段无实质进展
12. 风格突变 — 文笔前后差异巨大
13. 人物OOC — 角色做出不符合性格的行为
14. 对话出戏 — 对话不符合时代/身份背景
"""


# ── Pydantic Schema ──────────────────────────────────────────────────────────

class _DimensionResult(BaseModel):
    dimension: str
    score: int
    issues: list[str] = Field(default_factory=list)


class _AuditSchema(BaseModel):
    dimensions: list[_DimensionResult]
    redline_violations: list[str] = Field(default_factory=list)
    summary: str = ""


# ── 审计 prompt 模板 ──────────────────────────────────────────────────────────

AUDIT_PROMPT_TEMPLATE = """\
你是严苛的文学编辑，对小说章节进行专业审计。

## 审计章节
第 {chapter_number} 章《{chapter_title}》

## 章节正文
{chapter_content}

## 世界状态上下文
{truth_context}

## 蓝图（建筑师规划）
{blueprint_summary}

## 结算表（写手声明的改变）
{settlement_summary}

## 跨线程上下文
{cross_thread_context}

---

## 审计要求

### 第一步：红线检查（一票否决）
{redline_checklist}

### 第二步：9 维度评分（0-100分）

| 维度 | 权重 | 通过线 | 检查重点 |
|------|------|--------|---------|
| 主线战力 | 20% | ≥90 | 逻辑自洽、战力不崩、反派不降智、无机械降神 |
| 文笔质量 | 15% | ≥90 | 无"首先/其次/综上所述"、口语化、短句为主(60%+)、读者沉浸 |
| 场景构建 | 15% | ≥95 | 空间感清晰、视觉+听觉+至少1种其他感官、氛围到位、画面感强 |
| 心理刻画 | 15% | ≥95 | 心理符合性格、层次分明(表面→深层)、有留白、情感共鸣 |
| 对话质量 | 10% | ≥90 | 符合人物身份、推动剧情、有潜台词、不OOC |
| 风格一致 | 10% | ≥90 | 文笔前后统一、人物语气一致、节奏连贯 |
| 设定一致 | 8% | ≥90 | 世界观无矛盾、设定前后一致 |
| 结构合理 | 5% | ≥90 | 起承转合自然、高潮分布合理 |
| 人物OOC | 2% | ≥90 | 性格连贯、行为符合人设 |

### 第三步：文笔质量专项检查
- 是否有"首先/其次/最后/综上所述/众所周知"？
- 是否有"更关键的是/有意思的是/值得注意的是"？
- 是否有"核心动机/叙事节奏/人物弧线"等元叙事词？
- 是否有"全场震惊/众人哗然/所有人都"等集体反应套话？
- 短句是否占 60% 以上？
- 是否有五感描写（视/听/嗅/味/触至少 2 种）？

### 第四步：场景构建专项检查
- 闭上眼睛能否想象出这个场景？
- 空间感是否清晰（读者知道在哪）？
- 氛围是否到位（紧张/温馨/压抑）？

### 第五步：心理刻画专项检查
- 心理活动是否符合人物性格？
- 是否有层次（表面想法 → 深层动机）？
- 是否有留白（不过度解释）？

---

## 输出格式

只输出 JSON，不要任何说明：

{
  "dimensions": [
    {"dimension": "主线战力", "score": 85, "issues": ["反派决策过于简单"]},
    {"dimension": "文笔质量", "score": 92, "issues": []},
    ...
  ],
  "redline_violations": [],
  "summary": "整体评价一句话"
}
"""


class EnhancedAuditorAgent:
    """
    9 维度加权审计 Agent

    用法：
        auditor = EnhancedAuditorAgent(llm, validator=RedlineValidator())
        report = auditor.audit_chapter(
            chapter_content=content,
            chapter_number=1,
            blueprint=blueprint,
            truth_context=ctx,
            settlement=settlement,
        )
        if not report.passed:
            print(report.summary())
    """

    def __init__(self, llm: LLMProvider, validator: RedlineValidator | None = None):
        self.llm = llm
        self.validator = validator or RedlineValidator()

    def audit_chapter(
        self,
        chapter_content: str,
        chapter_number: int,
        blueprint=None,
        truth_context: str = "",
        settlement=None,
        cross_thread_context: str = "",
        chapter_title: str = "",
    ) -> EnhancedAuditReport:

        # ── 1. 零 LLM 红线 + 禁止词扫描 ──
        val_result = self.validator.validate(chapter_content)

        # ── 2. LLM 9 维度审计 ──
        blueprint_summary = ""
        if blueprint:
            blueprint_summary = (
                f"核心冲突：{blueprint.core_conflict}\n"
                f"情感旅程：{blueprint.emotional_journey}\n"
                f"节奏建议：{blueprint.pace_notes}"
            )

        settlement_summary = ""
        if settlement:
            settlement_summary = (
                f"新开伏笔：{settlement.new_hooks}\n"
                f"回收伏笔：{settlement.resolved_hooks}\n"
                f"关系变化：{settlement.relationship_changes}\n"
                f"情感变化：{settlement.emotional_changes}"
            )

        prompt = AUDIT_PROMPT_TEMPLATE.format(
            chapter_number=chapter_number,
            chapter_title=chapter_title,
            chapter_content=chapter_content[:8000],  # 截断防止 context 过长
            truth_context=truth_context[:3000],
            blueprint_summary=blueprint_summary[:1500],
            settlement_summary=settlement_summary[:1500],
            cross_thread_context=cross_thread_context[:1000],
            redline_checklist=RELINE_CHECKLIST,
        )

        def _call() -> EnhancedAuditReport:
            resp = self.llm.complete([
                LLMMessage("system", "你是严苛的文学编辑，只输出合法 JSON，不输出任何说明文字。"),
                LLMMessage("user", prompt),
            ])
            parsed = parse_llm_json(resp.content, _AuditSchema, "audit_chapter")

            # 构建维度评分
            dimensions = []
            dim_map = {cfg[0]: cfg for cfg in DIMENSION_CONFIG}
            for dr in parsed.dimensions:
                cfg = dim_map.get(dr.dimension)
                if cfg:
                    dimensions.append(DimensionScore(
                        dimension=dr.dimension,
                        weight=cfg[1],
                        score=dr.score,
                        pass_line=cfg[2],
                        issues=dr.issues,
                    ))

            # 补全缺失维度（LLM 可能漏输出）
            existing = {d.dimension for d in dimensions}
            for name, weight, pass_line, desc in DIMENSION_CONFIG:
                if name not in existing:
                    dimensions.append(DimensionScore(
                        dimension=name, weight=weight,
                        score=80, pass_line=pass_line,
                        issues=["LLM 未返回该维度评分"],
                    ))

            # 计算加权总分
            weighted_total = sum(d.score * d.weight for d in dimensions)

            # 合并红线
            redline_violations = list(val_result.redline_hits)
            for rv_text in parsed.redline_violations:
                redline_violations.append(RedlineViolation(
                    category="情节", rule="LLM检测", description=rv_text,
                ))

            return EnhancedAuditReport(
                dimensions=dimensions,
                redline_violations=redline_violations,
                weighted_total=weighted_total,
            )

        return with_retry(_call)
