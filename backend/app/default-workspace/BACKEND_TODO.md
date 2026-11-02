# 后端待办与完成标准（B 角色）

> 配套文档：`docs/02-后端开发文档.md`、`docs/03-接口规范.md`  
> 目标：先做出**可联调、可演示、可部署**的 P0 后端，再补 P1。不要一开始追求全部功能。

## 1. 当前状态

- [x] 需求分析、后端开发文档、接口规范、OpenAPI、JSON Schema、数据库 DDL；
- [x] “迎新晚会/100 人/2000 元”标准示例；
- [ ] `backend/` 代码工程；
- [ ] Mock 智能体与异步生成任务；
- [ ] 真实扣子/Dify 联调；
- [ ] 测试、Render + Supabase 部署；
- [ ] GitHub 仓库与团队协作。

## 2. 今天先做的 5 件事（约 4 小时）

1. **建 GitHub 仓库**：空仓库，不要勾选 README，按 `GITHUB_UPLOAD.md` 推送现有文档。
2. **建后端目录**：在仓库根目录创建 `backend/`，不要把 `backend/` 单独作为仓库根。
3. **跑通 FastAPI 骨架**：`GET /healthz` 返回 200，`/docs` 能打开。
4. **建库**：先 SQLite，按 `contracts/db-schema.sql` 建 `users/plans/generation_tasks/plan_versions/templates`。
5. **做认证**：注册、登录、`GET /auth/me`，用 JWT 保护一个测试接口。

今天的验收：Postman/curl 能完成“注册 → 登录 → 带 token 访问 `/auth/me`”。

## 3. P0 任务清单（答辩必须完成）

| 编号 | 任务 | 产出 | 验收标准 | 预估 |
|---|---|---|---|---|
| B-01 | 工程骨架与配置 | `main.py`、`config.py`、日志、异常、CORS | `/healthz` 200；`/docs` 可访问；错误返回统一结构 | 2h |
| B-02 | 数据库模型与迁移 | 5 张核心表、Alembic | 本地一条命令建库；外键/索引生效 | 4h |
| B-03 | 注册/登录/JWT | `/auth/register`、`/auth/login`、`/auth/me` | 密码哈希；未登录 401；只能访问自己的数据 | 4h |
| B-04 | 方案 CRUD 与列表 | `POST /plans/generate` 建方案、`GET /plans`、`GET /plans/{id}`、`DELETE` | 分页、搜索、软删除；不返回大 JSON | 4h |
| B-05 | Mock 生成任务 | `generation_tasks`、202、轮询、Mock 适配器 | 不接真实智能体也能完整跑通“提交→轮询→ready” | 6h |
| B-06 | 内容校验与金额重算 | `ContentValidator`、金额工具 | 小计/合计必对；超预算写 warning；非法 JSON 可修复重试 | 5h |
| B-07 | Dify/Coze 适配器 | `AgentAdapter`、一个真实平台 | 真实生成成功；超时/失败有错误码；可切 Mock | 6h |
| B-08 | 在线编辑与乐观锁 | `PATCH /plans/{id}/sections/{key}` | 保存后重开仍在；并发保存返回 409 | 4h |
| B-09 | Markdown 导出 | `GET /plans/{id}/export?format=markdown` | 中文正常；含 6 个章节；文件名正确 | 3h |
| B-10 | 测试 | pytest + httpx + respx | 认证、生成、编辑、导出主流程通过；覆盖率 ≥70% | 6h |
| B-11 | 部署 | Render + Supabase | 公网 `/healthz` 200；重启后数据仍在；CORS 正确 | 3h |

**P0 合计约 47 小时**，按每天 5～6 小时约 8～10 天。

## 4. P1 任务（P0 完成后再做）

| 编号 | 任务 | 验收标准 | 预估 |
|---|---|---|---|
| B-12 | 版本历史与恢复 | 每次保存有版本；可查看/恢复；保留最近 20 版 | 4h |
| B-13 | 重新生成某一节 | 只替换该节，其他内容不变；旧内容可回滚 | 4h |
| B-14 | 模板复用 | 方案另存模板；模板新建；use_count 增加 | 3h |
| B-15 | 服务端 PDF（可选） | `PDF_ENABLED=true` 时中文正常；否则 501 | 3h |
| B-16 | 限流与幂等 | 同 key 不重复生成；超限 429 | 2h |
| B-17 | 管理统计（P2） | 生成成功率、平均耗时、Token | 3h |

## 5. 建议的 10 天排期

| 天 | 任务 | 当天必须交付 |
|---|---|---|
| D1 | B-01 + B-02 | 服务能启动，库能建，`/healthz` 通过 |
| D2 | B-03 | 注册/登录/me，401 正确 |
| D3 | B-04 | 建方案、列表、详情、删除 |
| D4 | B-05 | Mock 模式 202 → 轮询 → ready |
| D5 | B-06 | 金额重算、预算校验、修复重试 |
| D6 | B-07 | 一个真实平台跑通，另一个适配器可切换 |
| D7 | B-08 + B-09 | 编辑保存、409 冲突、Markdown 导出 |
| D8 | B-10 | P0 集成测试全部通过 |
| D9 | B-11 | Render + Supabase 公网可访问 |
| D10 | 联调 + 演示数据 | A 能独立走完页面；准备 3 份演示方案 |

如果时间不足，**优先保 B-01～B-06、B-08、B-09**；B-07 可以用 Mock 兜底演示，但答辩前尽量跑通真实工作流。

## 6. 完成标准（Definition of Done）

### 功能

- [ ] 注册、登录、`/auth/me` 正常，未登录访问受保护接口返回 401。
- [ ] 输入“迎新晚会 / 100 人 / 2000 元 / 一周后 / 学校礼堂”能生成。
- [ ] 生成结果含策划案、物资、分工、宣传、风险、复盘 6 个部分。
- [ ] 物资小计、预算合计由后端重算，金额误差为 0。
- [ ] 任务状态可轮询，失败有错误码和可读提示。
- [ ] 方案列表只返回当前用户数据，分页/搜索正常。
- [ ] 按节编辑保存成功，刷新后仍在；并发保存返回 409。
- [ ] Markdown 导出中文正常，包含 6 个章节。
- [ ] Mock 模式可完整演示；真实智能体至少一个平台跑通。

### 工程

- [ ] `.env`、`*.db`、`.venv`、`__pycache__` 没有被提交。
- [ ] `README.md` 有本地启动、环境变量、测试、部署说明。
- [ ] `requirements.txt` 版本固定，`pip install -r` 可复现。
- [ ] `pytest -q` 全部通过。
- [ ] `/docs` 与 `contracts/openapi.json` 一致。
- [ ] 日志带 `request_id`，不记录密码/Token/API Key。
- [ ] Render 公网地址可访问，Supabase 数据持久化。

### 协作

- [ ] A 能只依赖 `03-接口规范.md` + Mock 数据完成页面，不需要读后端代码。
- [ ] C 能只依赖 `contracts/plan-content.schema.json` 交付 JSON，不需要问字段。
- [ ] D 能按验收标准写测试用例，按部署清单上线。
- [ ] 每次接口变更先改 OpenAPI/文档，再通知全员。

## 7. 常用命令

```powershell
# 进入后端
cd backend

# 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置
copy .env.example .env
# 编辑 .env，填 DATABASE_URL / JWT_SECRET / AGENT_PROVIDER=mock

# 启动
uvicorn app.main:app --reload --port 8000

# 测试
pytest -q
pytest --cov=app --cov-report=term-missing

# 建库/迁移
alembic upgrade head
```

## 8. 常见坑（提前避开）

1. **Render 免费实例不能用 SQLite 持久化**：生产必须 Supabase PostgreSQL。
2. **同步等待智能体**：一定用 202 + 后台任务 + 轮询，否则网关超时。
3. **把 API Key 写进前端**：所有智能体调用只在后端，Key 放环境变量。
4. **直接相信模型金额**：后端必须重算，模型只负责内容。
5. **编辑接口不带 version**：两个人同时保存会互相覆盖，必须 409。
6. **列表返回 content_json**：列表只返回摘要，详情才返回大 JSON。
7. **CORS 只配 localhost**：上线后要加 Vercel 域名。
8. **先做 PDF/模板/分享**：这些是 P1，先把生成主流程跑通。
9. **提交 `.env`**：一旦提交，立刻 `git rm --cached .env`，并更换所有密钥。
10. **智能体输出不校验**：非 JSON、缺字段、金额错都很常见，必须有 Schema 校验和降级。

## 9. 下一步

- 先按 `GITHUB_UPLOAD.md` 把现有文档推上 GitHub；
- 再按本文 D1 建 `backend/` 骨架；
- 每完成一个 B-xx，就在 GitHub 上打一个 commit，答辩时能展示开发过程。
