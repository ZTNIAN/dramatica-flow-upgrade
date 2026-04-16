# Dramatica-Flow 升级包

基于 OpenMOSS 项目审查机制提取的 4 大核心改进。

## 改动清单

| 文件 | 作用 | 改动类型 |
|------|------|----------|
| `core_upgrade/redline_validator.py` | 17 条红线一票否决 + 100+ 禁止词正则扫描 | **新增** |
| `core_upgrade/audit_upgrade.py` | 9 维度加权审计体系（替代原有模糊审计） | **新增** |
| `core_upgrade/patrol_agent.py` | 巡查 Agent（系统健康监控） | **新增** |
| `knowledge-base/` | 结构化知识库（规则+示例+技巧） | **新增目录** |
| `patch_pipeline.py` | pipeline.py 的补丁代码（集成以上改动） | **补丁** |

## 集成步骤

### 1. 复制新文件
```bash
cp core_upgrade/*.py dramatica-flow/core/
cp -r knowledge-base/ dramatica-flow/knowledge-base/
```

### 2. 修改 core/agents/__init__.py
- 替换 AuditorAgent 的 audit_chapter 方法（见 patch_pipeline.py 注释）
- 替换 WRITER_SYSTEM_PROMPT（见 patch_pipeline.py 注释）

### 3. 修改 core/pipeline.py
- 在 WritingPipeline.__init__ 中注入新组件
- 在 run() 方法中插入红线检查和巡查调用（见 patch_pipeline.py）

### 4. 修改 core/validators/__init__.py
- 导入 RedlineValidator 和 AITextValidator
- 在 PostWriteValidator 之后串联调用

## 预期效果

- 审计从"有没有问题"升级为"9 维度精确评分"
- AI 味文本被正则秒杀（零 LLM 成本）
- 红线问题一票否决（不再靠模糊判断）
- 系统级健康监控（伏笔超期/支线掉线/因果链断裂）
