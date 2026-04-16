# 项目交接文档

## 当前状态（2026-04-16 12:23）

### 已完成的事

**1. 阅读了两个项目**
- **dramatica-flow**：基于 Dramatica 叙事理论的 AI 小说写作系统（GitHub 开源项目）
  - 仓库：https://github.com/ydsgangge-ux/dramatica-flow
  - 5 层 Agent 管线：建筑师→写手→验证→审计→因果链提取
  - 技术栈：Python 3.11+ / FastAPI / Pydantic / 支持 DeepSeek + Ollama

- **OpenMOSS**：多 Agent 协作 + 质量管控平台（用户提供的两个压缩包）
  - 7z 包：归档文档（工作流程 v6.0、机制说明、进化档案）
  - gz 包：运行代码（Agent 提示词、知识库、审查标准、WebUI）
  - 核心优势：9 维度加权审计、17 条红线一票否决、45 特征去 AI 味、巡查 Agent

**2. 提取了 OpenMOSS 的优点，做了升级包**
- GitHub 仓库：https://github.com/ZTNIAN/dramatica-flow-upgrade
- 包含：3 个新 Python 模块 + 6 个知识库文件 + 一键升级脚本

**3. 在用户服务器上完成了升级集成**
- 服务器地址：用户自己的 Linux 服务器
- 项目位置：`~/dramatica-flow/`
- 升级脚本已运行成功
- 部分手动修补已完成（__init__ 参数、巡查调用插入）
- 备份文件：`core/pipeline.py.bak`、`core/agents/__init__.py.bak`

**4. 配置了 .env**
- LLM_PROVIDER=deepseek
- API Key 已配置（注意：Key 在 .env 中，请勿泄露）

### 升级了什么

| 新文件 | 作用 |
|--------|------|
| `core/redline_validator.py` | 50+ AI 禁止词正则扫描 + 17 条红线检测（零 LLM 成本） |
| `core/audit_upgrade.py` | 9 维度加权审计 Agent（替代原模糊审计） |
| `core/patrol_agent.py` | 巡查 Agent（伏笔超期/支线掉线/因果链断裂监控） |
| `knowledge-base/` | 结构化知识库（审查标准、红线、去AI指南、示例） |

| 改动的文件 | 改了什么 |
|-----------|---------|
| `core/pipeline.py` | 新增 3 个 import、3 个 __init__ 参数、红线扫描、巡查调用、MAX 2→3 |
| `core/agents/__init__.py` | WRITER_SYSTEM_PROMPT 末尾追加去 AI 味铁律 |

### 升级效果对比

| 维度 | 升级前 | 升级后 |
|------|--------|--------|
| 审计 | 模糊的"叙事审计"，passed/failed | 9 维度加权评分，总分≥95 且单项≥85 |
| 否决 | 无 | 17 条红线一票否决 |
| 去 AI 味 | 5 条 prompt 规则 | 50+ 禁止词正则扫描 + 45 特征系统 |
| 监控 | 无 | 巡查 Agent 每 3 章自动检查 |
| 返工 | 最多 2 轮 | 最多 3 轮 |

### 未完成的事

1. **依赖未安装完成**：`pip install --break-system-packages -e .` 还在运行或需要重新跑
2. **未实际测试写一章**：安装完成后需要创建一本书、配置角色、跑一章验证升级效果
3. **enhanced_auditor 未集成到 pipeline 的 run() 方法中**：目前 run() 方法的审计部分还是用的原 AuditorAgent。需要把第 4 步（审计→修订循环）替换为使用 EnhancedAuditorAgent 的版本。这是最大的一块改动，需要精确替换代码。
4. **知识库注入 prompt**：目前知识库文件只是放在目录里，Agent 的 prompt 还没有按类型选择性注入知识库内容

### 用户服务器信息

- 操作系统：Linux（Debian 系，Python 3.12）
- 用户名：ztnian
- 项目路径：~/dramatica-flow/
- GitHub 账号：ZTNIAN
- 升级包仓库：https://github.com/ZTNIAN/dramatica-flow-upgrade

### 安全提醒

- `.env` 文件包含 DeepSeek API Key，不要上传到 GitHub
- GitHub Token（ghp_qJW...）已用于推代码，建议用户去 GitHub 删除该 token
- `upgrade.py` 中硬编码的 token 已过期/删除

---

## 下一步要做的事

### 优先级 P0（必须做）

1. **安装依赖并启动服务**
   ```bash
   cd ~/dramatica-flow
   python3 -m pip install --break-system-packages -e .
   python3 -m uvicorn core.server:app --reload --port 8766
   ```

2. **完成 enhanced_auditor 集成**
   - 打开 `core/pipeline.py`
   - 找到 `run()` 方法中的审计部分（大概在第 230-280 行附近）
   - 替换为使用 `self.enhanced_auditor` 的版本
   - 参考 `docs/patch_pipeline.py` 中的 `PIPELINE_STEP_3_4_REPLACEMENT`

3. **测试写一章**
   - 浏览器打开 http://localhost:8766
   - 创建一本书
   - 配置角色
   - 生成大纲
   - 写一章，观察审计输出是否变为 9 维度评分

### 优先级 P1（建议做）

4. **把 enhanced_auditor 集成写完**（上面第 2 项是最重要也最难的一步）
5. **测试红线扫描**：故意写一段含"首先/其次/最后"的内容，看是否被拦截
6. **测试巡查 Agent**：写 3 章以上，看第 3 章后是否触发巡查

### 优先级 P2（锦上添花）

7. **知识库注入 prompt**：让 Agent 在工作时引用 knowledge-base 中的规则
8. **知识库查询激励**：参考 OpenMOSS 的积分系统
9. **质量统计仪表盘**：Web UI 新增质量趋势面板

---

## 关于 Windows 安装

**不建议在 Windows 上重新安装**。原因：

1. 你已经在 Linux 服务器上装好了，而且升级也做完了
2. Windows 安装需要额外配置 Python 环境、可能遇到路径问题
3. 项目本身支持通过浏览器访问（Web UI），你在任何电脑上打开浏览器访问服务器的 8766 端口就行

**如果你确实想在 Windows 上用**：
- 项目提供了 `install.bat` 和 `启动网页界面.bat`
- 但建议先在 Linux 上验证升级效果，确认没问题后再考虑 Windows 部署

**推荐做法**：
- 在 Linux 服务器上运行服务
- Windows 上用浏览器访问 `http://服务器IP:8766`
- 如果服务器有防火墙，需要开放 8766 端口

---

## 如果要找新 AI 继续帮忙

把这份文档发给新的 AI 对话，它就能知道：
1. 做了什么
2. 当前状态
3. 还差什么
4. 怎么继续

关键文件路径：
- 项目：~/dramatica-flow/
- 升级包仓库：https://github.com/ZTNIAN/dramatica-flow-upgrade
- 升级指南：~/dramatica-flow/docs/UPGRADE_GUIDE.md
- 改动参考：~/dramatica-flow/docs/patch_pipeline.py
- 备份：core/pipeline.py.bak、core/agents/__init__.py.bak
