# 活动智囊 · 后端文档包

本目录是“活动智囊——基于智能体的校园社团活动一键策划与执行包生成系统”的后端交付文档，面向 B（后端）开发，同时可供 A（前端）、C（智能体）、D（测试/部署）联调使用。

## 1. 文件清单

| 文件 | 内容 | 主要读者 |
|---|---|---|
| `docs/01-需求分析.md` | 背景、用户、场景、功能需求、业务流程、数据需求、非功能指标、验收标准 | 全员、指导老师 |
| `docs/02-后端开发文档.md` | 技术选型、架构、目录、配置、数据库、生成流程、智能体接入、校验、编辑、导出、测试、部署 | B，A/C/D 参考 |
| `docs/03-接口规范.md` | 通用约定、鉴权、枚举、全部接口、完整 JSON 示例、错误码、联调指南 | A/B/C/D |
| `contracts/openapi.json` | OpenAPI 3.1 机器可读契约，可导入 Swagger Editor/Postman | A/B |
| `contracts/plan-content.schema.json` | 智能体输出/方案内容的 JSON Schema | B/C |
| `contracts/db-schema.sql` | SQLite 建表脚本，PostgreSQL 迁移参考 | B |
| `examples/plan_welcome_party.json` | “迎新晚会/100人/2000元”标准输出，可直接作为 Mock fixture | A/B/C/D |
| `tools/validate_contracts.py` | 校验示例是否符合 JSON Schema（无第三方依赖） | B/C/D |
| `tools/build_openapi.py` | 重新生成 `contracts/openapi.json` | B |
| `tools/extract_toc.py` | 从 PDF 导出中提取标题与页码，用于生成 Word 静态目录 | B |
| `diagrams/` | 架构图、生成流程图、时序图、ER 图 PNG 源文件 | B/答辩 PPT |
| `活动智囊-后端文档合集.docx` | 三份文档的合并版，适合课程报告/打印提交 | 全员、指导老师 |
| `活动智囊-后端文档合集.pdf` | 90 页排版版，目录页码与正文一致，适合直接提交/打印 | 全员、指导老师 |

> **Word/PDF 版说明：** 为避免 30 KB 的完整 JSON 示例占满 20 页，Word/PDF 版在 7.9 节用一段说明代替全文；完整 JSON 见 `examples/plan_welcome_party.json` 与 `docs/03-接口规范.md`。Word/PDF 的目录为静态页码，按 LibreOffice 排版生成，与 PDF 完全一致。

## 2. 推荐阅读顺序

**B（后端）自己：**

1. `01-需求分析.md` 第 6～9 节：知道要做什么、边界在哪；
2. `02-后端开发文档.md` 第 3～8 节：架构、数据库、智能体接入；
3. `03-接口规范.md` 第 2～7 节：把接口先定死；
4. 按开发文档第 19 节 W1～W4 推进。

**A（前端）：**

1. `03-接口规范.md` 第 2～7 节：通用约定、鉴权、生成、方案、编辑；
2. 第 7.9 节完整 JSON：直接照着写卡片和表格；
3. 第 13 节联调指南：轮询、保存、下载、错误处理；
4. `examples/plan_welcome_party.json`：Mock 数据。

**C（智能体）：**

1. `contracts/plan-content.schema.json`：必须严格输出的结构；
2. `03-接口规范.md` 第 7 节：字段含义和示例；
3. `02-后端开发文档.md` 第 8 节：输入包装、解析、修复重试；
4. 先交付 5 份不同活动类型的合法 JSON，再调提示词。

**D（测试/部署）：**

1. `01-需求分析.md` 第 11 节：验收标准；
2. `02-后端开发文档.md` 第 16～17 节：测试矩阵、部署清单；
3. `03-接口规范.md` 第 11～12 节：错误码与限流；
4. 用 `examples/plan_welcome_party.json` 做回归 fixture。

## 3. 快速校验

```bash
# 校验标准示例是否符合内容 Schema（仅需 Python 标准库）
python tools/validate_contracts.py

# 重新生成 OpenAPI（修改 tools/build_openapi.py 后执行）
python tools/build_openapi.py
```

OpenAPI 导入方式：

- Swagger Editor：打开 https://editor.swagger.io/ ，粘贴 `contracts/openapi.json`；
- 本地 FastAPI 启动后访问 `http://127.0.0.1:8000/docs`；
- Postman：Import → 选择 `contracts/openapi.json`；
- Apifox：导入 OpenAPI 3.1。

## 4. 后端落地顺序（建议）

| 周 | 目标 | 验收 |
|---|---|---|
| W1 | 工程骨架、配置、健康检查、用户表、认证 | `/healthz` 200，注册/登录可用 |
| W1 | `plans`、`tasks`、`versions`、`templates` 表与迁移 | 本地建库成功 |
| W2 | 方案列表、详情、复制、软删除 | 只能看到自己的方案 |
| W2 | Mock 智能体 + 异步生成 + 轮询 | 无真实 API 也能跑通全流程 |
| W2 | Dify/Coze 适配器、解析、Schema 校验、金额重算 | 真实生成成功 |
| W3 | 按节编辑、乐观锁、版本、重新生成 | 冲突返回 409 |
| W3 | Markdown 导出、PDF 打印、模板 | 中文正常 |
| W3 | 与 A 联调 | A 能独立完成页面 |
| W4 | 测试、Render + Supabase 部署、演示数据 | 公网可访问 |

## 5. 关键设计决策

| 决策 | 结论 | 原因 |
|---|---|---|
| 生成方式 | 异步任务 + 轮询 | 智能体耗时 30～120 秒，同步会超时 |
| 数据库 | 本地 SQLite，生产 Supabase PostgreSQL | Render 免费磁盘不持久 |
| 金额 | 整数“分”存储，API 用“元” | 避免浮点误差 |
| 智能体职责 | 只生成内容，不决定最终金额和权限 | 防止模型篡改关键数据 |
| 失败策略 | 重试 1 次 → 规则降级 | 保证演示可用 |
| 编辑 | 整节替换 + 版本号 | 实现简单，避免 diff 冲突 |
| 导出 | 后端 Markdown + 前端打印 PDF | 降低字体和部署风险 |
| 认证 | JWT + user_id 过滤 | 满足课程项目，成本低 |

## 6. 需要团队确认的事项

1. **智能体平台最终选型**：扣子还是 Dify？B 的适配器两个都写，但部署只启用一个；
2. **生产域名**：文档中的 `activity-mind-api.onrender.com` 是占位符，部署后替换；
3. **PDF 方案**：默认前端打印；若答辩要求服务端 PDF，再开 `PDF_ENABLED=true` 并改用 Docker；
4. **模板公开**：本期固定私有，不做公开模板库；
5. **分享链接**：本期不做，老师审核通过导出件完成；
6. **登录方式**：本期用户名+密码，不做校统一身份认证。

## 7. 文档维护约定

- 接口字段变更：先改 `tools/build_openapi.py` 和 `03-接口规范.md`，运行生成，再通知 A/C/D；
- 内容结构变更：先改 `contracts/plan-content.schema.json` 和 `examples/plan_welcome_party.json`，运行 `validate_contracts.py`；
- 数据库变更：写 Alembic 迁移，同步 `contracts/db-schema.sql`；
- 每次变更在 `03-接口规范.md` 第 14 节记录版本和影响；
- 不要在文档或代码中写入真实 API Key、JWT Secret、数据库密码。
