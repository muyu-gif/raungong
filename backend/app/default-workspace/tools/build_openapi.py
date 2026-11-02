"""Build contracts/openapi.json.

Run:
    python tools/build_openapi.py
"""

from __future__ import annotations

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "contracts" / "openapi.json"


def ref(name: str) -> dict:
    return {"$ref": f"#/components/schemas/{name}"}


def json_content(schema: dict, example: dict | None = None) -> dict:
    media = {"schema": schema}
    if example is not None:
        media["example"] = example
    return {"application/json": media}


def response(description: str, schema: dict | None = None, example: dict | None = None) -> dict:
    item: dict = {"description": description}
    if schema is not None:
        item["content"] = json_content(schema, example)
    return item


def error_response(description: str) -> dict:
    return response(description, ref("ErrorResponse"))


def path_param(name: str, schema: dict, description: str) -> dict:
    return {
        "name": name,
        "in": "path",
        "required": True,
        "description": description,
        "schema": schema,
    }


def query_param(name: str, schema: dict, description: str, required: bool = False) -> dict:
    return {
        "name": name,
        "in": "query",
        "required": required,
        "description": description,
        "schema": schema,
    }


SECURITY = [{"bearerAuth": []}]

common_errors = {
    "400": {"$ref": "#/components/responses/BadRequest"},
    "401": {"$ref": "#/components/responses/Unauthorized"},
    "404": {"$ref": "#/components/responses/NotFound"},
    "409": {"$ref": "#/components/responses/Conflict"},
    "429": {"$ref": "#/components/responses/RateLimited"},
    "500": {"$ref": "#/components/responses/InternalError"},
}


def build() -> dict:
    schemas: dict = {}

    schemas["ErrorDetail"] = {
        "type": "object",
        "required": ["code", "message", "request_id", "retryable"],
        "properties": {
            "code": {"type": "string", "example": "VALIDATION_ERROR"},
            "message": {"type": "string", "example": "请求参数不合法"},
            "details": {
                "oneOf": [
                    {"type": "array", "items": {"type": "object", "additionalProperties": True}},
                    {"type": "object", "additionalProperties": True},
                    {"type": "null"},
                ]
            },
            "request_id": {"type": "string", "example": "req_01J8Z3K9Q7"},
            "retryable": {"type": "boolean"},
        },
    }
    schemas["ErrorResponse"] = {
        "type": "object",
        "required": ["error"],
        "properties": {"error": ref("ErrorDetail")},
    }
    schemas["Pagination"] = {
        "type": "object",
        "required": ["page", "page_size", "total", "total_pages", "has_more"],
        "properties": {
            "page": {"type": "integer", "minimum": 1},
            "page_size": {"type": "integer", "minimum": 1, "maximum": 100},
            "total": {"type": "integer", "minimum": 0},
            "total_pages": {"type": "integer", "minimum": 0},
            "has_more": {"type": "boolean"},
        },
    }
    schemas["User"] = {
        "type": "object",
        "required": ["id", "username", "display_name", "role", "created_at"],
        "properties": {
            "id": {"type": "string", "format": "uuid"},
            "username": {"type": "string"},
            "display_name": {"type": "string"},
            "role": {"type": "string", "enum": ["user", "admin"]},
            "created_at": {"type": "string", "format": "date-time"},
        },
    }
    schemas["RegisterRequest"] = {
        "type": "object",
        "required": ["username", "password", "display_name"],
        "properties": {
            "username": {
                "type": "string",
                "pattern": "^[A-Za-z0-9_]{3,32}$",
                "example": "demo",
            },
            "password": {"type": "string", "minLength": 8, "maxLength": 64, "example": "demo12345"},
            "display_name": {"type": "string", "minLength": 1, "maxLength": 50, "example": "演示用户"},
        },
    }
    schemas["LoginRequest"] = {
        "type": "object",
        "required": ["username", "password"],
        "properties": {
            "username": {"type": "string", "example": "demo"},
            "password": {"type": "string", "example": "demo12345"},
        },
    }
    schemas["AuthResponse"] = {
        "type": "object",
        "required": ["access_token", "token_type", "expires_in", "user"],
        "properties": {
            "access_token": {"type": "string"},
            "token_type": {"type": "string", "enum": ["bearer"]},
            "expires_in": {"type": "integer", "example": 604800},
            "user": ref("User"),
        },
    }
    schemas["EnumItem"] = {
        "type": "object",
        "required": ["value", "label"],
        "properties": {"value": {"type": "string"}, "label": {"type": "string"}},
    }
    schemas["EnumsResponse"] = {
        "type": "object",
        "required": [
            "activity_types",
            "plan_statuses",
            "task_statuses",
            "sections",
            "risk_levels",
            "task_priorities",
            "tones",
        ],
        "properties": {
            "activity_types": {"type": "array", "items": ref("EnumItem")},
            "plan_statuses": {"type": "array", "items": ref("EnumItem")},
            "task_statuses": {"type": "array", "items": ref("EnumItem")},
            "sections": {"type": "array", "items": ref("EnumItem")},
            "risk_levels": {"type": "array", "items": ref("EnumItem")},
            "task_priorities": {"type": "array", "items": ref("EnumItem")},
            "tones": {"type": "array", "items": ref("EnumItem")},
        },
    }

    activity_types = [
        "welcome_party",
        "club_recruitment",
        "team_building",
        "lecture",
        "sports",
        "arts",
        "volunteer",
        "competition",
        "other",
    ]
    schemas["GeneratePlanRequest"] = {
        "type": "object",
        "required": ["theme", "activity_type", "participants", "budget_yuan", "starts_at", "location"],
        "properties": {
            "theme": {"type": "string", "minLength": 2, "maxLength": 60, "example": "迎新晚会"},
            "activity_type": {"type": "string", "enum": activity_types, "example": "welcome_party"},
            "participants": {"type": "integer", "minimum": 10, "maximum": 2000, "example": 100},
            "budget_yuan": {
                "type": "number",
                "minimum": 0,
                "maximum": 1000000,
                "multipleOf": 0.01,
                "example": 2000,
            },
            "starts_at": {
                "type": "string",
                "format": "date-time",
                "example": "2026-11-09T19:00:00+08:00",
            },
            "duration_minutes": {
                "type": "integer",
                "minimum": 30,
                "maximum": 480,
                "default": 120,
            },
            "location": {"type": "string", "minLength": 1, "maxLength": 120, "example": "学校礼堂"},
            "target_audience": {"type": "string", "maxLength": 120, "example": "2026级新生"},
            "goals": {
                "type": "array",
                "maxItems": 5,
                "items": {"type": "string", "maxLength": 60},
                "example": ["帮助新生融入校园", "展示社团风采"],
            },
            "constraints": {"type": "string", "maxLength": 500},
            "tone": {
                "type": "string",
                "enum": ["lively", "warm", "formal", "creative"],
                "default": "lively",
            },
            "template_id": {"type": "string", "format": "uuid"},
            "extra_notes": {"type": "string", "maxLength": 500},
        },
        "example": {
            "theme": "迎新晚会",
            "activity_type": "welcome_party",
            "participants": 100,
            "budget_yuan": 2000,
            "starts_at": "2026-11-09T19:00:00+08:00",
            "duration_minutes": 120,
            "location": "学校礼堂",
            "target_audience": "2026级新生",
            "goals": ["帮助新生融入校园", "展示社团风采"],
            "constraints": "场地为室内礼堂，禁止明火；音响由学校提供",
            "tone": "lively",
            "extra_notes": "希望有抽奖互动",
        },
    }
    schemas["PlanSummary"] = {
        "type": "object",
        "required": [
            "id",
            "title",
            "theme",
            "activity_type",
            "activity_type_label",
            "participants",
            "budget_yuan",
            "starts_at",
            "location",
            "status",
            "degraded",
            "version",
            "summary",
            "created_at",
            "updated_at",
        ],
        "properties": {
            "id": {"type": "string", "format": "uuid"},
            "title": {"type": "string"},
            "theme": {"type": "string"},
            "activity_type": {"type": "string", "enum": activity_types},
            "activity_type_label": {"type": "string"},
            "participants": {"type": "integer"},
            "budget_yuan": {"type": "number"},
            "starts_at": {"type": "string", "format": "date-time"},
            "location": {"type": "string"},
            "status": {
                "type": "string",
                "enum": ["draft", "generating", "ready", "failed", "archived"],
            },
            "degraded": {"type": "boolean"},
            "version": {"type": "integer"},
            "summary": {"type": ["string", "null"]},
            "created_at": {"type": "string", "format": "date-time"},
            "updated_at": {"type": "string", "format": "date-time"},
        },
    }
    schemas["PlanContent"] = {
        "type": "object",
        "description": "结构化活动包。完整约束见 contracts/plan-content.schema.json。",
        "required": [
            "schema_version",
            "meta",
            "plan",
            "materials",
            "tasks",
            "promotion",
            "risks",
            "review",
            "assumptions",
            "warnings",
        ],
        "properties": {
            "schema_version": {"const": "1.0"},
            "meta": {"type": "object", "additionalProperties": True},
            "plan": {"type": "object", "additionalProperties": True},
            "materials": {"type": "object", "additionalProperties": True},
            "tasks": {"type": "object", "additionalProperties": True},
            "promotion": {"type": "object", "additionalProperties": True},
            "risks": {"type": "object", "additionalProperties": True},
            "review": {"type": "object", "additionalProperties": True},
            "assumptions": {"type": "array", "items": {"type": "string"}},
            "warnings": {"type": "array", "items": {"type": "string"}},
        },
        "additionalProperties": False,
    }
    schemas["LatestTask"] = {
        "type": "object",
        "required": ["task_id", "status", "stage", "progress"],
        "properties": {
            "task_id": {"type": "string", "format": "uuid"},
            "status": {"type": "string", "enum": ["queued", "running", "succeeded", "failed", "canceled"]},
            "stage": {"type": "string"},
            "progress": {"type": "integer", "minimum": 0, "maximum": 100},
        },
    }
    schemas["PlanDetail"] = {
        "allOf": [
            ref("PlanSummary"),
            {
                "type": "object",
                "required": ["input", "content", "agent", "latest_task"],
                "properties": {
                    "input": ref("GeneratePlanRequest"),
                    "content": {
                        "oneOf": [ref("PlanContent"), {"type": "null"}],
                    },
                    "agent": {
                        "oneOf": [
                            {
                                "type": "object",
                                "required": ["provider", "prompt_version", "generated_at"],
                                "properties": {
                                    "provider": {"type": "string"},
                                    "prompt_version": {"type": "string"},
                                    "generated_at": {"type": "string", "format": "date-time"},
                                },
                            },
                            {"type": "null"},
                        ]
                    },
                    "latest_task": {
                        "oneOf": [ref("LatestTask"), {"type": "null"}],
                    },
                },
            },
        ]
    }
    schemas["PlanList"] = {
        "type": "object",
        "required": ["items", "pagination"],
        "properties": {
            "items": {"type": "array", "items": ref("PlanSummary")},
            "pagination": ref("Pagination"),
        },
    }
    schemas["GenerateAccepted"] = {
        "type": "object",
        "required": [
            "task_id",
            "plan_id",
            "status",
            "reused",
            "estimated_seconds",
            "poll_after_ms",
            "poll_url",
        ],
        "properties": {
            "task_id": {"type": "string", "format": "uuid"},
            "plan_id": {"type": "string", "format": "uuid"},
            "status": {"type": "string", "enum": ["queued"]},
            "reused": {"type": "boolean"},
            "estimated_seconds": {"type": "integer"},
            "poll_after_ms": {"type": "integer"},
            "poll_url": {"type": "string"},
        },
    }
    schemas["TaskError"] = {
        "type": "object",
        "required": ["code", "message", "retryable"],
        "properties": {
            "code": {"type": "string"},
            "message": {"type": "string"},
            "retryable": {"type": "boolean"},
        },
    }
    schemas["Task"] = {
        "type": "object",
        "required": [
            "task_id",
            "plan_id",
            "type",
            "section_key",
            "status",
            "stage",
            "progress",
            "message",
            "attempt",
            "error",
            "created_at",
            "started_at",
            "finished_at",
        ],
        "properties": {
            "task_id": {"type": "string", "format": "uuid"},
            "plan_id": {"type": "string", "format": "uuid"},
            "type": {"type": "string", "enum": ["generate", "regenerate"]},
            "section_key": {
                "type": ["string", "null"],
                "enum": ["plan", "materials", "tasks", "promotion", "risks", "review", None],
            },
            "status": {"type": "string", "enum": ["queued", "running", "succeeded", "failed", "canceled"]},
            "stage": {"type": "string"},
            "progress": {"type": "integer", "minimum": 0, "maximum": 100},
            "message": {"type": "string"},
            "attempt": {"type": "integer"},
            "error": {"oneOf": [ref("TaskError"), {"type": "null"}]},
            "created_at": {"type": "string", "format": "date-time"},
            "started_at": {"type": ["string", "null"], "format": "date-time"},
            "finished_at": {"type": ["string", "null"], "format": "date-time"},
        },
    }
    schemas["CancelTaskResponse"] = {
        "type": "object",
        "required": ["task_id", "status"],
        "properties": {
            "task_id": {"type": "string", "format": "uuid"},
            "status": {"type": "string", "enum": ["canceled"]},
        },
    }
    schemas["UpdatePlanRequest"] = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "minLength": 1, "maxLength": 120},
            "status": {"type": "string", "enum": ["ready", "archived"]},
            "version": {"type": "integer", "minimum": 1},
        },
        "description": "修改标题时必须带 version；只修改状态时 version 可省略。",
    }
    schemas["UpdatePlanResponse"] = {
        "type": "object",
        "required": ["id", "title", "status", "version", "updated_at"],
        "properties": {
            "id": {"type": "string", "format": "uuid"},
            "title": {"type": "string"},
            "status": {"type": "string"},
            "version": {"type": "integer"},
            "updated_at": {"type": "string", "format": "date-time"},
        },
    }
    schemas["SectionUpdateRequest"] = {
        "type": "object",
        "required": ["version", "data"],
        "properties": {
            "version": {"type": "integer", "minimum": 1},
            "data": {"type": "object", "additionalProperties": True},
            "comment": {"type": "string", "maxLength": 200},
        },
    }
    schemas["SectionUpdateResponse"] = {
        "type": "object",
        "required": ["plan_id", "section_key", "version", "data", "updated_at"],
        "properties": {
            "plan_id": {"type": "string", "format": "uuid"},
            "section_key": {"type": "string"},
            "version": {"type": "integer"},
            "data": {"type": "object", "additionalProperties": True},
            "updated_at": {"type": "string", "format": "date-time"},
        },
    }
    schemas["ContentReplaceRequest"] = {
        "type": "object",
        "required": ["version", "content"],
        "properties": {
            "version": {"type": "integer", "minimum": 1},
            "comment": {"type": "string", "maxLength": 200},
            "content": ref("PlanContent"),
        },
    }
    schemas["ContentReplaceResponse"] = {
        "type": "object",
        "required": ["plan_id", "version", "updated_at"],
        "properties": {
            "plan_id": {"type": "string", "format": "uuid"},
            "version": {"type": "integer"},
            "updated_at": {"type": "string", "format": "date-time"},
        },
    }
    schemas["RegenerateRequest"] = {
        "type": "object",
        "required": ["version"],
        "properties": {
            "section_key": {
                "type": ["string", "null"],
                "enum": ["plan", "materials", "tasks", "promotion", "risks", "review", None],
            },
            "instruction": {"type": "string", "maxLength": 500},
            "version": {"type": "integer", "minimum": 1},
        },
    }
    schemas["DuplicatePlanRequest"] = {
        "type": "object",
        "properties": {"title": {"type": "string", "minLength": 1, "maxLength": 120}},
    }
    schemas["VersionItem"] = {
        "type": "object",
        "required": ["version", "editor_id", "comment", "size_bytes", "created_at"],
        "properties": {
            "version": {"type": "integer"},
            "editor_id": {"type": ["string", "null"], "format": "uuid"},
            "comment": {"type": ["string", "null"]},
            "size_bytes": {"type": "integer"},
            "created_at": {"type": "string", "format": "date-time"},
        },
    }
    schemas["VersionList"] = {
        "type": "object",
        "required": ["items", "pagination"],
        "properties": {
            "items": {"type": "array", "items": ref("VersionItem")},
            "pagination": ref("Pagination"),
        },
    }
    schemas["VersionDetail"] = {
        "type": "object",
        "required": ["version", "editor_id", "comment", "created_at", "content"],
        "properties": {
            "version": {"type": "integer"},
            "editor_id": {"type": ["string", "null"], "format": "uuid"},
            "comment": {"type": ["string", "null"]},
            "created_at": {"type": "string", "format": "date-time"},
            "content": ref("PlanContent"),
        },
    }
    schemas["RestoreVersionRequest"] = {
        "type": "object",
        "required": ["version"],
        "properties": {
            "version": {"type": "integer", "minimum": 1, "description": "当前最新版本，用于乐观锁"},
            "comment": {"type": "string", "maxLength": 200},
        },
    }
    schemas["RestoreVersionResponse"] = {
        "type": "object",
        "required": ["plan_id", "version", "restored_from", "updated_at"],
        "properties": {
            "plan_id": {"type": "string", "format": "uuid"},
            "version": {"type": "integer"},
            "restored_from": {"type": "integer"},
            "updated_at": {"type": "string", "format": "date-time"},
        },
    }
    schemas["Template"] = {
        "type": "object",
        "required": [
            "id",
            "name",
            "description",
            "source_plan_id",
            "defaults",
            "preview",
            "use_count",
            "created_at",
            "updated_at",
        ],
        "properties": {
            "id": {"type": "string", "format": "uuid"},
            "name": {"type": "string"},
            "description": {"type": ["string", "null"]},
            "source_plan_id": {"type": ["string", "null"], "format": "uuid"},
            "defaults": {"type": "object", "additionalProperties": True},
            "preview": {"type": "object", "additionalProperties": True},
            "use_count": {"type": "integer"},
            "created_at": {"type": "string", "format": "date-time"},
            "updated_at": {"type": "string", "format": "date-time"},
        },
    }
    schemas["TemplateDetail"] = {
        "allOf": [
            ref("Template"),
            {
                "type": "object",
                "required": ["content"],
                "properties": {"content": ref("PlanContent")},
            },
        ]
    }
    schemas["TemplateList"] = {
        "type": "object",
        "required": ["items", "pagination"],
        "properties": {
            "items": {"type": "array", "items": ref("Template")},
            "pagination": ref("Pagination"),
        },
    }
    schemas["CreateTemplateRequest"] = {
        "type": "object",
        "required": ["plan_id", "name"],
        "properties": {
            "plan_id": {"type": "string", "format": "uuid"},
            "name": {"type": "string", "minLength": 1, "maxLength": 80},
            "description": {"type": "string", "maxLength": 200},
        },
    }
    schemas["UpdateTemplateRequest"] = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "minLength": 1, "maxLength": 80},
            "description": {"type": "string", "maxLength": 200},
        },
    }
    schemas["HealthResponse"] = {
        "type": "object",
        "required": ["status", "version", "database", "agent", "time"],
        "properties": {
            "status": {"type": "string", "enum": ["ok", "degraded"]},
            "version": {"type": "string"},
            "database": {"type": "string", "enum": ["ok", "error"]},
            "agent": {
                "type": "object",
                "required": ["provider", "configured"],
                "properties": {
                    "provider": {"type": "string"},
                    "configured": {"type": "boolean"},
                },
            },
            "time": {"type": "string", "format": "date-time"},
        },
    }

    paths: dict = {}

    paths["/healthz"] = {
        "get": {
            "tags": ["System"],
            "summary": "健康检查",
            "operationId": "getHealth",
            "responses": {
                "200": response("服务状态", ref("HealthResponse")),
                "503": response("数据库不可用", ref("HealthResponse")),
            },
        }
    }

    paths["/api/v1/auth/register"] = {
        "post": {
            "tags": ["Auth"],
            "summary": "注册并登录",
            "operationId": "register",
            "requestBody": {
                "required": True,
                "content": json_content(ref("RegisterRequest")),
            },
            "responses": {
                "201": response("注册成功", ref("AuthResponse")),
                "400": error_response("参数不合法"),
                "409": error_response("用户名已存在"),
                "429": error_response("注册过于频繁"),
            },
        }
    }
    paths["/api/v1/auth/login"] = {
        "post": {
            "tags": ["Auth"],
            "summary": "登录",
            "operationId": "login",
            "requestBody": {
                "required": True,
                "content": json_content(ref("LoginRequest")),
            },
            "responses": {
                "200": response("登录成功", ref("AuthResponse")),
                "401": error_response("用户名或密码错误"),
                "429": error_response("登录过于频繁"),
            },
        }
    }
    paths["/api/v1/auth/me"] = {
        "get": {
            "tags": ["Auth"],
            "summary": "获取当前用户",
            "operationId": "getMe",
            "security": SECURITY,
            "responses": {
                "200": response("当前用户", ref("User")),
                "401": error_response("未登录或令牌无效"),
            },
        }
    }

    paths["/api/v1/meta/enums"] = {
        "get": {
            "tags": ["Meta"],
            "summary": "获取枚举字典",
            "operationId": "getEnums",
            "responses": {"200": response("枚举字典", ref("EnumsResponse"))},
        }
    }

    idempotency_header = {
        "name": "Idempotency-Key",
        "in": "header",
        "required": True,
        "description": "UUID；10 分钟内相同 key 只执行一次。",
        "schema": {"type": "string", "format": "uuid"},
    }

    paths["/api/v1/plans/generate"] = {
        "post": {
            "tags": ["Generation"],
            "summary": "创建生成任务",
            "description": "创建方案与异步生成任务，立即返回 202；通过轮询任务获取结果。",
            "operationId": "generatePlan",
            "security": SECURITY,
            "parameters": [idempotency_header],
            "requestBody": {
                "required": True,
                "content": json_content(ref("GeneratePlanRequest")),
            },
            "responses": {
                "202": response("已接受", ref("GenerateAccepted")),
                "400": error_response("参数不合法"),
                "401": error_response("未登录"),
                "404": error_response("模板不存在"),
                "409": error_response("幂等键冲突或方案数量超限"),
                "429": error_response("生成次数超限"),
                "503": error_response("智能体未配置"),
            },
        }
    }

    paths["/api/v1/tasks/{task_id}"] = {
        "get": {
            "tags": ["Generation"],
            "summary": "查询任务状态",
            "operationId": "getTask",
            "security": SECURITY,
            "parameters": [path_param("task_id", {"type": "string", "format": "uuid"}, "任务 ID")],
            "responses": {
                "200": response("任务状态", ref("Task")),
                "401": error_response("未登录"),
                "404": error_response("任务不存在"),
            },
        }
    }
    paths["/api/v1/tasks/{task_id}/cancel"] = {
        "post": {
            "tags": ["Generation"],
            "summary": "取消排队中的任务",
            "operationId": "cancelTask",
            "security": SECURITY,
            "parameters": [path_param("task_id", {"type": "string", "format": "uuid"}, "任务 ID")],
            "responses": {
                "200": response("已取消", ref("CancelTaskResponse")),
                "401": error_response("未登录"),
                "404": error_response("任务不存在"),
                "409": error_response("任务已开始或已结束"),
            },
        }
    }

    plan_id_param = path_param("plan_id", {"type": "string", "format": "uuid"}, "方案 ID")
    list_params = [
        query_param("page", {"type": "integer", "minimum": 1, "default": 1}, "页码"),
        query_param(
            "page_size",
            {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
            "每页数量",
        ),
        query_param("keyword", {"type": "string", "maxLength": 50}, "标题/主题关键词"),
        query_param("status", {"type": "string"}, "状态，多个用逗号分隔"),
        query_param("activity_type", {"type": "string", "enum": activity_types}, "活动类型"),
        query_param(
            "sort",
            {"type": "string", "default": "created_at:desc"},
            "created_at:asc/desc、updated_at:asc/desc",
        ),
    ]

    paths["/api/v1/plans"] = {
        "get": {
            "tags": ["Plans"],
            "summary": "历史方案列表",
            "operationId": "listPlans",
            "security": SECURITY,
            "parameters": list_params,
            "responses": {
                "200": response("方案列表", ref("PlanList")),
                "401": error_response("未登录"),
            },
        }
    }
    paths["/api/v1/plans/{plan_id}"] = {
        "get": {
            "tags": ["Plans"],
            "summary": "方案详情",
            "operationId": "getPlan",
            "security": SECURITY,
            "parameters": [plan_id_param],
            "responses": {
                "200": response("方案详情", ref("PlanDetail")),
                "401": error_response("未登录"),
                "404": error_response("方案不存在"),
            },
        },
        "patch": {
            "tags": ["Plans"],
            "summary": "修改标题或归档状态",
            "operationId": "updatePlan",
            "security": SECURITY,
            "parameters": [plan_id_param],
            "requestBody": {
                "required": True,
                "content": json_content(ref("UpdatePlanRequest")),
            },
            "responses": {
                "200": response("修改成功", ref("UpdatePlanResponse")),
                "400": error_response("参数不合法"),
                "401": error_response("未登录"),
                "404": error_response("方案不存在"),
                "409": error_response("版本冲突"),
            },
        },
        "delete": {
            "tags": ["Plans"],
            "summary": "软删除方案",
            "operationId": "deletePlan",
            "security": SECURITY,
            "parameters": [plan_id_param],
            "responses": {
                "204": {"description": "已删除"},
                "401": error_response("未登录"),
                "404": error_response("方案不存在"),
            },
        },
    }

    paths["/api/v1/plans/{plan_id}/sections/{section_key}"] = {
        "patch": {
            "tags": ["Editing"],
            "summary": "按节保存编辑",
            "operationId": "updateSection",
            "security": SECURITY,
            "parameters": [
                plan_id_param,
                path_param(
                    "section_key",
                    {
                        "type": "string",
                        "enum": ["plan", "materials", "tasks", "promotion", "risks", "review"],
                    },
                    "内容节",
                ),
            ],
            "requestBody": {
                "required": True,
                "content": json_content(ref("SectionUpdateRequest")),
            },
            "responses": {
                "200": response("保存成功", ref("SectionUpdateResponse")),
                "400": error_response("结构不合法或预算超限"),
                "401": error_response("未登录"),
                "404": error_response("方案不存在"),
                "409": error_response("版本冲突或方案未就绪"),
            },
        }
    }
    paths["/api/v1/plans/{plan_id}/content"] = {
        "put": {
            "tags": ["Editing"],
            "summary": "整体替换内容（P1）",
            "operationId": "replaceContent",
            "security": SECURITY,
            "parameters": [plan_id_param],
            "requestBody": {
                "required": True,
                "content": json_content(ref("ContentReplaceRequest")),
            },
            "responses": {
                "200": response("替换成功", ref("ContentReplaceResponse")),
                "400": error_response("内容不合法"),
                "401": error_response("未登录"),
                "404": error_response("方案不存在"),
                "409": error_response("版本冲突或方案未就绪"),
            },
        }
    }
    paths["/api/v1/plans/{plan_id}/regenerate"] = {
        "post": {
            "tags": ["Editing"],
            "summary": "重新生成整包或某一节",
            "operationId": "regenerate",
            "security": SECURITY,
            "parameters": [plan_id_param, idempotency_header],
            "requestBody": {
                "required": True,
                "content": json_content(ref("RegenerateRequest")),
            },
            "responses": {
                "202": response("已接受", ref("GenerateAccepted")),
                "400": error_response("参数不合法"),
                "401": error_response("未登录"),
                "404": error_response("方案不存在"),
                "409": error_response("已有任务、版本冲突或方案未就绪"),
            },
        }
    }
    paths["/api/v1/plans/{plan_id}/duplicate"] = {
        "post": {
            "tags": ["Plans"],
            "summary": "复制方案",
            "operationId": "duplicatePlan",
            "security": SECURITY,
            "parameters": [plan_id_param],
            "requestBody": {
                "required": False,
                "content": json_content(ref("DuplicatePlanRequest")),
            },
            "responses": {
                "201": response("复制成功", ref("PlanSummary")),
                "401": error_response("未登录"),
                "404": error_response("方案不存在"),
            },
        }
    }

    paths["/api/v1/plans/{plan_id}/export"] = {
        "get": {
            "tags": ["Export"],
            "summary": "导出 Markdown 或 PDF",
            "operationId": "exportPlan",
            "security": SECURITY,
            "parameters": [
                plan_id_param,
                query_param(
                    "format",
                    {"type": "string", "enum": ["markdown", "pdf"], "default": "markdown"},
                    "导出格式",
                ),
                query_param(
                    "inline",
                    {"type": "boolean", "default": False},
                    "true 时浏览器内预览，false 时下载",
                ),
            ],
            "responses": {
                "200": {
                    "description": "文件内容",
                    "headers": {
                        "Content-Disposition": {
                            "description": "文件名",
                            "schema": {"type": "string"},
                        }
                    },
                    "content": {
                        "text/markdown": {"schema": {"type": "string"}},
                        "application/pdf": {"schema": {"type": "string", "format": "binary"}},
                    },
                },
                "401": error_response("未登录"),
                "404": error_response("方案不存在"),
                "409": error_response("方案未就绪"),
                "501": error_response("服务端 PDF 未启用"),
            },
        }
    }

    paths["/api/v1/plans/{plan_id}/versions"] = {
        "get": {
            "tags": ["Versions"],
            "summary": "版本列表",
            "operationId": "listVersions",
            "security": SECURITY,
            "parameters": [
                plan_id_param,
                query_param("page", {"type": "integer", "minimum": 1, "default": 1}, "页码"),
                query_param(
                    "page_size",
                    {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
                    "每页数量",
                ),
            ],
            "responses": {
                "200": response("版本列表", ref("VersionList")),
                "401": error_response("未登录"),
                "404": error_response("方案不存在"),
            },
        }
    }
    paths["/api/v1/plans/{plan_id}/versions/{version}"] = {
        "get": {
            "tags": ["Versions"],
            "summary": "版本详情",
            "operationId": "getVersion",
            "security": SECURITY,
            "parameters": [
                plan_id_param,
                path_param("version", {"type": "integer", "minimum": 1}, "版本号"),
            ],
            "responses": {
                "200": response("版本详情", ref("VersionDetail")),
                "401": error_response("未登录"),
                "404": error_response("方案或版本不存在"),
            },
        }
    }
    paths["/api/v1/plans/{plan_id}/versions/{version}/restore"] = {
        "post": {
            "tags": ["Versions"],
            "summary": "恢复到指定版本",
            "operationId": "restoreVersion",
            "security": SECURITY,
            "parameters": [
                plan_id_param,
                path_param("version", {"type": "integer", "minimum": 1}, "要恢复的版本号"),
            ],
            "requestBody": {
                "required": True,
                "content": json_content(ref("RestoreVersionRequest")),
            },
            "responses": {
                "200": response("恢复成功", ref("RestoreVersionResponse")),
                "401": error_response("未登录"),
                "404": error_response("方案或版本不存在"),
                "409": error_response("版本冲突"),
            },
        }
    }

    paths["/api/v1/templates"] = {
        "get": {
            "tags": ["Templates"],
            "summary": "模板列表",
            "operationId": "listTemplates",
            "security": SECURITY,
            "parameters": [
                query_param("page", {"type": "integer", "minimum": 1, "default": 1}, "页码"),
                query_param(
                    "page_size",
                    {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
                    "每页数量",
                ),
                query_param("keyword", {"type": "string", "maxLength": 50}, "名称关键词"),
            ],
            "responses": {
                "200": response("模板列表", ref("TemplateList")),
                "401": error_response("未登录"),
            },
        },
        "post": {
            "tags": ["Templates"],
            "summary": "从方案创建模板",
            "operationId": "createTemplate",
            "security": SECURITY,
            "requestBody": {
                "required": True,
                "content": json_content(ref("CreateTemplateRequest")),
            },
            "responses": {
                "201": response("创建成功", ref("Template")),
                "400": error_response("参数不合法"),
                "401": error_response("未登录"),
                "404": error_response("方案不存在"),
                "409": error_response("模板数量超限或名称重复"),
            },
        },
    }
    paths["/api/v1/templates/{template_id}"] = {
        "get": {
            "tags": ["Templates"],
            "summary": "模板详情",
            "operationId": "getTemplate",
            "security": SECURITY,
            "parameters": [
                path_param("template_id", {"type": "string", "format": "uuid"}, "模板 ID")
            ],
            "responses": {
                "200": response("模板详情", ref("TemplateDetail")),
                "401": error_response("未登录"),
                "404": error_response("模板不存在"),
            },
        },
        "patch": {
            "tags": ["Templates"],
            "summary": "修改模板",
            "operationId": "updateTemplate",
            "security": SECURITY,
            "parameters": [
                path_param("template_id", {"type": "string", "format": "uuid"}, "模板 ID")
            ],
            "requestBody": {
                "required": True,
                "content": json_content(ref("UpdateTemplateRequest")),
            },
            "responses": {
                "200": response("修改成功", ref("Template")),
                "400": error_response("参数不合法"),
                "401": error_response("未登录"),
                "404": error_response("模板不存在"),
                "409": error_response("名称重复"),
            },
        },
        "delete": {
            "tags": ["Templates"],
            "summary": "删除模板",
            "operationId": "deleteTemplate",
            "security": SECURITY,
            "parameters": [
                path_param("template_id", {"type": "string", "format": "uuid"}, "模板 ID")
            ],
            "responses": {
                "204": {"description": "已删除"},
                "401": error_response("未登录"),
                "404": error_response("模板不存在"),
            },
        },
    }

    return {
        "openapi": "3.1.0",
        "info": {
            "title": "活动智囊 API",
            "version": "1.0.0",
            "description": (
                "校园社团活动一键策划与执行包生成系统的后端接口。"
                "生成采用异步任务，客户端通过轮询任务状态获取结果。"
                "完整内容结构见 contracts/plan-content.schema.json。"
            ),
            "contact": {"name": "B（后端）"},
        },
        "servers": [
            {"url": "http://127.0.0.1:8000", "description": "本地开发"},
            {"url": "https://activity-mind-api.onrender.com", "description": "生产（示例）"},
        ],
        "tags": [
            {"name": "System", "description": "健康检查"},
            {"name": "Auth", "description": "注册、登录与当前用户"},
            {"name": "Meta", "description": "枚举字典"},
            {"name": "Generation", "description": "异步生成与任务轮询"},
            {"name": "Plans", "description": "方案列表、详情、复制与删除"},
            {"name": "Editing", "description": "在线编辑与重新生成"},
            {"name": "Export", "description": "Markdown/PDF 导出"},
            {"name": "Versions", "description": "版本历史与恢复"},
            {"name": "Templates", "description": "模板复用"},
        ],
        "security": SECURITY,
        "paths": paths,
        "components": {
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                }
            },
            "schemas": schemas,
            "responses": {
                "BadRequest": error_response("请求参数不合法"),
                "Unauthorized": error_response("未登录或令牌无效"),
                "NotFound": error_response("资源不存在或无权访问"),
                "Conflict": error_response("状态或版本冲突"),
                "RateLimited": error_response("请求过于频繁"),
                "InternalError": error_response("服务器内部错误"),
            },
        },
    }


def main() -> None:
    spec = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes, {len(spec['paths'])} paths)")


if __name__ == "__main__":
    main()
