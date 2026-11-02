-- 活动智囊数据库结构（SQLite 开发版）
-- 生产 PostgreSQL：将 TEXT 时间字段改为 TIMESTAMPTZ，将 JSON 改为 JSONB。
-- 所有时间存 UTC；所有金额存整数“分”；所有 ID 存 UUID 字符串。
-- 生产环境请使用 Alembic 迁移，不要直接执行本文件。

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS users (
    id              TEXT PRIMARY KEY,
    username        TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    display_name    TEXT NOT NULL,
    role            TEXT NOT NULL DEFAULT 'user'
                    CHECK (role IN ('user', 'admin')),
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS plans (
    id                  TEXT PRIMARY KEY,
    user_id             TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title               TEXT NOT NULL,
    status              TEXT NOT NULL DEFAULT 'draft'
                        CHECK (status IN ('draft', 'generating', 'ready', 'failed', 'archived')),
    version             INTEGER NOT NULL DEFAULT 1 CHECK (version >= 1),
    theme               TEXT NOT NULL,
    activity_type       TEXT NOT NULL,
    participants        INTEGER NOT NULL CHECK (participants BETWEEN 10 AND 2000),
    budget_fen          INTEGER NOT NULL CHECK (budget_fen >= 0),
    starts_at           TEXT NOT NULL,
    duration_minutes    INTEGER NOT NULL DEFAULT 120
                        CHECK (duration_minutes BETWEEN 30 AND 480),
    location            TEXT NOT NULL,
    input_json          TEXT NOT NULL,
    content_json        TEXT,
    summary             TEXT,
    degraded            INTEGER NOT NULL DEFAULT 0 CHECK (degraded IN (0, 1)),
    agent_provider      TEXT,
    prompt_version      TEXT,
    deleted_at          TEXT,
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_plans_user_created
    ON plans (user_id, deleted_at, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_plans_status
    ON plans (status);
CREATE INDEX IF NOT EXISTS ix_plans_user_theme
    ON plans (user_id, theme);

CREATE TABLE IF NOT EXISTS generation_tasks (
    id                  TEXT PRIMARY KEY,
    plan_id             TEXT NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
    user_id             TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type                TEXT NOT NULL DEFAULT 'generate'
                        CHECK (type IN ('generate', 'regenerate')),
    section_key         TEXT
                        CHECK (section_key IS NULL OR section_key IN
                               ('plan', 'materials', 'tasks', 'promotion', 'risks', 'review')),
    status              TEXT NOT NULL DEFAULT 'queued'
                        CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'canceled')),
    stage               TEXT,
    progress            INTEGER NOT NULL DEFAULT 0 CHECK (progress BETWEEN 0 AND 100),
    instruction         TEXT,
    idempotency_key     TEXT UNIQUE,
    attempt             INTEGER NOT NULL DEFAULT 0 CHECK (attempt >= 0),
    provider            TEXT,
    model               TEXT,
    error_code          TEXT,
    error_message       TEXT,
    started_at          TEXT,
    finished_at         TEXT,
    created_at          TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_tasks_plan_created
    ON generation_tasks (plan_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_tasks_user_created
    ON generation_tasks (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_tasks_status
    ON generation_tasks (status);
CREATE INDEX IF NOT EXISTS ix_tasks_idempotency
    ON generation_tasks (idempotency_key);

CREATE TABLE IF NOT EXISTS plan_versions (
    id              TEXT PRIMARY KEY,
    plan_id         TEXT NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
    version         INTEGER NOT NULL CHECK (version >= 1),
    content_json    TEXT NOT NULL,
    editor_id       TEXT REFERENCES users(id) ON DELETE SET NULL,
    comment         TEXT,
    created_at      TEXT NOT NULL,
    UNIQUE (plan_id, version)
);

CREATE INDEX IF NOT EXISTS ix_versions_plan_created
    ON plan_versions (plan_id, created_at DESC);

CREATE TABLE IF NOT EXISTS templates (
    id              TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    description     TEXT,
    source_plan_id  TEXT REFERENCES plans(id) ON DELETE SET NULL,
    input_json      TEXT NOT NULL,
    content_json    TEXT NOT NULL,
    is_public       INTEGER NOT NULL DEFAULT 0 CHECK (is_public IN (0, 1)),
    use_count       INTEGER NOT NULL DEFAULT 0 CHECK (use_count >= 0),
    deleted_at      TEXT,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_templates_user_name_active
    ON templates (user_id, name) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS ix_templates_user_created
    ON templates (user_id, deleted_at, created_at DESC);

CREATE TABLE IF NOT EXISTS export_records (
    id              TEXT PRIMARY KEY,
    plan_id         TEXT NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
    user_id         TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    format          TEXT NOT NULL CHECK (format IN ('markdown', 'pdf')),
    file_size       INTEGER NOT NULL DEFAULT 0 CHECK (file_size >= 0),
    created_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_exports_plan_created
    ON export_records (plan_id, created_at DESC);

CREATE TABLE IF NOT EXISTS agent_calls (
    id              TEXT PRIMARY KEY,
    task_id         TEXT NOT NULL REFERENCES generation_tasks(id) ON DELETE CASCADE,
    provider        TEXT NOT NULL,
    request_id      TEXT NOT NULL,
    status          TEXT NOT NULL,
    latency_ms      INTEGER NOT NULL DEFAULT 0 CHECK (latency_ms >= 0),
    tokens_in       INTEGER NOT NULL DEFAULT 0 CHECK (tokens_in >= 0),
    tokens_out      INTEGER NOT NULL DEFAULT 0 CHECK (tokens_out >= 0),
    error_code      TEXT,
    created_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_agent_calls_task
    ON agent_calls (task_id, created_at DESC);

CREATE TABLE IF NOT EXISTS audit_logs (
    id              TEXT PRIMARY KEY,
    request_id      TEXT NOT NULL,
    user_id         TEXT,
    action          TEXT NOT NULL,
    resource_type   TEXT,
    resource_id     TEXT,
    detail_json     TEXT,
    ip              TEXT,
    created_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_audit_user_created
    ON audit_logs (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_audit_request
    ON audit_logs (request_id);
