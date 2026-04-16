"""
pipeline.py 改动补丁
========================================
说明：以下标注了需要修改的文件和具体位置。
      不是直接替换文件，而是标注了需要增删改的代码块。

改动的文件：
  1. core/pipeline.py
  2. core/agents/__init__.py (WRITER_SYSTEM_PROMPT)
  3. core/validators/__init__.py
"""


# ═══════════════════════════════════════════════════════════════════════════════
# 改动 1：core/agents/__init__.py — WRITER_SYSTEM_PROMPT
# ═══════════════════════════════════════════════════════════════════════════════
#
# 在原来的 WRITER_SYSTEM_PROMPT 末尾，追加以下内容：
#

WRITER_PROMPT_ADDITION = """

## 去AI味铁律（强制执行）

### 禁止词（发现即返工）
绝对禁止使用以下词汇，用其他方式表达：
- ❌ 首先、其次、最后、第一、第二、第三
- ❌ 总的来说、综上所述、归根结底
- ❌ 更关键的是、更奇怪的是、有意思的是、值得注意的是
- ❌ 众所周知、不言而喻、毫无疑问、显而易见
- ❌ 核心动机、叙事节奏、人物弧线、戏剧张力
- ❌ 全场震惊、众人哗然、所有人都
- ❌ 不禁、宛如、猛地、顿时（每3000字最多1次）

### 45特征润色（必须执行）
1. **错别字**：每1000字故意加1-2处不影响理解的小错（音近字优先）
2. **口语化**：像和朋友聊天，不用书面语。20%的表达改为口语
3. **语气词**：每300字3-4个（啊/呢/吧/嘛/哈/呀）
4. **短句为主**：短句（≤20字）占60%以上，长短交错
5. **具体细节**：写"锈迹斑斑的铜钥匙"而非"旧钥匙"
6. **主观感受**：每段都要有"我觉得""说实话""真的"等主观表达
7. **不完美逻辑**：允许思维跳跃，不用完美过渡
8. **重复强调**：关键信息可以说两遍
9. **情绪化标点**：多用破折号——和省略号…表达停顿

### Show Don't Tell（必须执行）
- ❌ "他感到很愤怒" → ✅ "他捏碎了手中的茶杯"
- ❌ "她很害怕" → ✅ "她的手在发抖，钥匙插了三遍才进去"
- ❌ "他很紧张" → ✅ "他在原地转圈，深呼吸了三次"
- ❌ "她很伤心" → ✅ "她盯着那碗面，筷子搅了十分钟，一口没吃"
- ❌ "他很富有" → ✅ "他随手把法拉利停在路边，连钥匙都没拔"

### 五感描写（必须执行）
每个场景至少包含 2 种感官：
- 视觉（看到了什么颜色/光影/细节）
- 听觉（听到了什么声音/寂静）
- 嗅觉/味觉/触觉（至少1种）

### 自检频率
每写500字，停下来自检：
- 有没有用禁止词？
- 有没有"感到XX"？
- 短句比例够不够？
- 有没有感官描写？
"""


# ═══════════════════════════════════════════════════════════════════════════════
# 改动 2：core/pipeline.py — WritingPipeline 类
# ═══════════════════════════════════════════════════════════════════════════════
#
# 2.1 在 imports 区域新增：
#
#    from .redline_validator import RedlineValidator
#    from .audit_upgrade import EnhancedAuditorAgent
#    from .patrol_agent import PatrolAgent
#
# 2.2 在 __init__ 方法中新增参数：
#
#    def __init__(
#        self,
#        state_manager: StateManager,
#        architect: ArchitectAgent,
#        writer: WriterAgent,
#        auditor: AuditorAgent,               # 保留原审计员（可删除）
#        reviser: ReviserAgent,
#        narrative_engine: NarrativeEngine,
#        summary_agent: SummaryAgent,
#        validator: PostWriteValidator,
#        protagonist: Character,
#        all_characters: list[Character],
#        # ── 新增 ──
#        redline_validator: RedlineValidator | None = None,
#        enhanced_auditor: EnhancedAuditorAgent | None = None,
#        patrol_agent: PatrolAgent | None = None,
#    ):
#        # ... 原有赋值 ...
#        self.redline_validator = redline_validator or RedlineValidator()
#        self.enhanced_auditor = enhanced_auditor
#        self.patrol_agent = patrol_agent
#
# 2.3 在 run() 方法中，修改第 3 步（写后验证）和第 4 步（审计）：
#     替换为以下代码块：


PIPELINE_STEP_3_4_REPLACEMENT = '''
        # ── 3. 写后验证（零 LLM） + 红线扫描 ────────────────────────────────
        log("写后验证 + 红线扫描...")
        val_result = self.validator.validate(
            writer_output.content,
            target_words=adjusted_target_words,
        )
        # 新增：AI 禁止词扫描
        redline_result = self.redline_validator.validate(writer_output.content)
        if redline_result.forbidden_count > 0:
            log(f"发现 {redline_result.forbidden_count} 个禁止词")
            if redline_result.forbidden_count >= 5:
                # 禁止词太多，标记为 error
                val_result.passed = False

        current_content = writer_output.content

        if not val_result.passed:
            error_issues = [
                AuditIssue(
                    dimension="写后验证",
                    severity="critical",
                    description=i.description,
                    location=i.excerpt,
                )
                for i in val_result.issues
                if i.severity == "error"
            ]
            # 追加禁止词问题
            for hit in redline_result.forbidden_hits:
                error_issues.append(AuditIssue(
                    dimension="AI禁止词",
                    severity="critical",
                    description=hit,
                    location="",
                ))
            log(f"验证未通过（{len(error_issues)} 个 error），spot-fix...")
            fix_result = self.reviser.revise(current_content, error_issues, mode="spot-fix")
            current_content = fix_result.content

        # ── 4. 9 维度审计 → 修订闭环 ────────────────────────────────────────
        log("9 维度审计...")
        audit_truth_ctx = self.sm.read_truth_bundle([
            TruthFileKey.CURRENT_STATE,
            TruthFileKey.CHARACTER_MATRIX,
            TruthFileKey.PENDING_HOOKS,
            TruthFileKey.EMOTIONAL_ARCS,
            TruthFileKey.CAUSAL_CHAIN,
        ])
        cross_thread_audit_ctx = self._build_cross_thread_audit_context(ws, thread_id, ch)

        # 使用增强审计器（9 维度 + 红线否决）
        if self.enhanced_auditor:
            enhanced_report = self.enhanced_auditor.audit_chapter(
                chapter_content=current_content,
                chapter_number=ch,
                blueprint=blueprint,
                truth_context=audit_truth_ctx,
                settlement=writer_output.settlement,
                cross_thread_context=cross_thread_audit_ctx,
                chapter_title=title,
            )
            log(enhanced_report.summary())

            revision_rounds = 0
            while not enhanced_report.passed and revision_rounds < self.MAX_REVISE_ROUNDS:
                log(f"修订第 {revision_rounds + 1} 轮（{enhanced_report.critical_count} 个问题）...")
                # 构建修订指令
                revise_issues = []
                for d in enhanced_report.dimensions:
                    if not d.passed:
                        for issue in d.issues:
                            revise_issues.append(AuditIssue(
                                dimension=d.dimension,
                                severity="critical" if d.score < 85 else "warning",
                                description=issue,
                                location="",
                            ))
                for rv in enhanced_report.redline_violations:
                    revise_issues.append(AuditIssue(
                        dimension=rv.rule,
                        severity="critical",
                        description=rv.description,
                        location="",
                    ))

                revise_result = self.reviser.revise(current_content, revise_issues, mode="spot-fix")
                current_content = revise_result.content
                revision_rounds += 1

                # 再审
                enhanced_report = self.enhanced_auditor.audit_chapter(
                    chapter_content=current_content,
                    chapter_number=ch,
                    blueprint=blueprint,
                    truth_context=audit_truth_ctx,
                    settlement=writer_output.settlement,
                    cross_thread_context=cross_thread_audit_ctx,
                    chapter_title=title,
                )
                enhanced_report.revision_round = revision_rounds
                log(enhanced_report.summary())

            # 转换为原有 AuditReport 格式（兼容 pipeline 其他代码）
            audit_report = AuditReport(
                passed=enhanced_report.passed,
                issues=[
                    AuditIssue(
                        dimension=d.dimension,
                        severity="critical" if d.score < d.pass_line else "info",
                        description="; ".join(d.issues) if d.issues else f"{d.score}分",
                        location="",
                    )
                    for d in enhanced_report.dimensions
                ],
                critical_count=enhanced_report.critical_count,
            )
        else:
            # 回退到原审计器
            audit_report = self.auditor.audit_chapter(
                chapter_content=current_content,
                chapter_number=ch,
                blueprint=blueprint,
                truth_context=audit_truth_ctx,
                settlement=writer_output.settlement,
                cross_thread_context=cross_thread_audit_ctx,
            )
            revision_rounds = 0
            while not audit_report.passed and revision_rounds < self.MAX_REVISE_ROUNDS:
                log(f"修订第 {revision_rounds + 1} 轮（{audit_report.critical_count} critical）...")
                revise_result = self.reviser.revise(current_content, audit_report.issues, mode="spot-fix")
                current_content = revise_result.content
                revision_rounds += 1
                audit_report = self.auditor.audit_chapter(
                    chapter_content=current_content,
                    chapter_number=ch,
                    blueprint=blueprint,
                    truth_context=audit_truth_ctx,
                    settlement=writer_output.settlement,
                    cross_thread_context=cross_thread_audit_ctx,
                )
'''

# 2.4 在 run() 方法的最后（return PipelineResult 之前），插入巡查：
#
PATROL_INSERTION = '''
        # ── 巡查（每 3 章一次） ───────────────────────────────────────────────
        if self.patrol_agent and self.patrol_agent.should_patrol(ch):
            log("执行巡查...")
            patrol_report = self.patrol_agent.patrol(ch)
            log(patrol_report.summary())
            # 巡查结果写入 thread_status.md
            if patrol_report.has_warning or patrol_report.has_critical:
                self.sm.append_truth(
                    TruthFileKey.THREAD_STATUS,
                    f"\\n### Ch.{ch} 巡查报告\\n{patrol_report.summary()}\\n",
                )
'''

# 2.5 MAX_REVISE_ROUNDS 改为 3（原为 2）：
#
#    MAX_REVISE_ROUNDS = 3


# ═══════════════════════════════════════════════════════════════════════════════
# 改动 3：server.py 或入口文件 — 初始化新组件
# ═══════════════════════════════════════════════════════════════════════════════
#
# 在创建 WritingPipeline 的地方，新增：
#
#    from .redline_validator import RedlineValidator
#    from .audit_upgrade import EnhancedAuditorAgent
#    from .patrol_agent import PatrolAgent
#
#    redline_validator = RedlineValidator()
#    enhanced_auditor = EnhancedAuditorAgent(llm_provider, validator=redline_validator)
#    patrol_agent = PatrolAgent(state_manager)
#
#    pipeline = WritingPipeline(
#        state_manager=state_manager,
#        architect=architect,
#        writer=writer,
#        auditor=auditor,
#        reviser=reviser,
#        narrative_engine=narrative_engine,
#        summary_agent=summary_agent,
#        validator=validator,
#        protagonist=protagonist,
#        all_characters=all_characters,
#        # ── 新增 ──
#        redline_validator=redline_validator,
#        enhanced_auditor=enhanced_auditor,
#        patrol_agent=patrol_agent,
#    )


# ═══════════════════════════════════════════════════════════════════════════════
# 改动 4：AuditReport 兼容性（如果 enhanced_auditor 存在时需要）
# ═══════════════════════════════════════════════════════════════════════════════
#
# 原 AuditReport 的 critical_count 是 property，改为普通字段：
#
# @dataclass
# class AuditReport:
#     passed: bool
#     issues: list[AuditIssue]
#     critical_count: int = 0          # ← 新增：从 property 改为字段
#     revision_round: int = 0
#
# 这样 EnhancedAuditReport 转换过来时可以直接赋值。
