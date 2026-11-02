import asyncio

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.mock import load_mock_content
from app.api.deps import get_current_user
from app.db.session import SessionLocal, get_db
from app.models.plan import Plan
from app.models.task import GenerationTask
from app.models.user import User, utcnow
from app.schemas.plan import GenerateAccepted, GeneratePlanRequest

router = APIRouter(tags=["Generation"])


async def run_mock_generation(task_id: str) -> None:
    async with SessionLocal() as db:
        task = await db.get(GenerationTask, task_id)
        if task is None:
            return

        try:
            task.status = "running"
            task.stage = "planning"
            task.progress = 30
            task.attempt = 1
            task.started_at = utcnow()
            await db.commit()

            await asyncio.sleep(1)

            plan = await db.get(Plan, task.plan_id)
            if plan is None:
                raise RuntimeError("plan not found")

            content = load_mock_content()
            content["meta"].update(
                {
                    "title": plan.title,
                    "theme": plan.theme,
                    "activity_type": plan.activity_type,
                    "participants": plan.participants,
                    "budget_yuan": plan.budget_fen / 100,
                    "starts_at": plan.starts_at.isoformat(),
                    "duration_minutes": plan.duration_minutes,
                    "location": plan.location,
                    "generated_at": utcnow().isoformat(),
                    "agent": {"provider": "mock", "prompt_version": "mock-v1"},
                }
            )

            plan.content_json = content
            plan.summary = content["plan"]["summary"][:300]
            plan.status = "ready"

            task.status = "succeeded"
            task.stage = "done"
            task.progress = 100
            task.finished_at = utcnow()
            await db.commit()

        except Exception as exc:
            await db.rollback()
            task = await db.get(GenerationTask, task_id)
            if task is None:
                return

            task.status = "failed"
            task.error_code = "MOCK_GENERATION_FAILED"
            task.error_message = str(exc)[:500]
            task.finished_at = utcnow()

            plan = await db.get(Plan, task.plan_id)
            if plan is not None:
                plan.status = "failed"
            await db.commit()


@router.post(
    "/plans/generate",
    response_model=GenerateAccepted,
    status_code=202,
)
async def generate_plan(
    body: GeneratePlanRequest,
    background: BackgroundTasks,
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
    ),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if idempotency_key:
        existing = await db.scalar(
            select(GenerationTask).where(
                GenerationTask.idempotency_key == idempotency_key,
                GenerationTask.user_id == user.id,
            )
        )
        if existing:
            return GenerateAccepted(
                task_id=existing.id,
                plan_id=existing.plan_id,
                status=existing.status,
                reused=True,
                poll_url=f"/api/v1/tasks/{existing.id}",
            )

    plan = Plan(
        user_id=user.id,
        title=f"{body.theme}活动方案",
        status="generating",
        theme=body.theme,
        activity_type=body.activity_type,
        participants=body.participants,
        budget_fen=int(round(body.budget_yuan * 100)),
        starts_at=body.starts_at,
        duration_minutes=body.duration_minutes,
        location=body.location,
        input_json=body.model_dump(mode="json"),
    )
    db.add(plan)
    await db.flush()

    task = GenerationTask(
        plan_id=plan.id,
        user_id=user.id,
        status="queued",
        idempotency_key=idempotency_key,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    background.add_task(run_mock_generation, task.id)

    return GenerateAccepted(
        task_id=task.id,
        plan_id=plan.id,
        poll_url=f"/api/v1/tasks/{task.id}",
    )


@router.get("/tasks/{task_id}")
async def get_task(
    task_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await db.scalar(
        select(GenerationTask).where(
            GenerationTask.id == task_id,
            GenerationTask.user_id == user.id,
        )
    )
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status == "succeeded":
        message = "生成完成"
    elif task.status == "failed":
        message = "生成失败"
    elif task.status == "running":
        message = "正在生成"
    else:
        message = "已排队"

    return {
        "task_id": task.id,
        "plan_id": task.plan_id,
        "type": task.type,
        "section_key": task.section_key,
        "status": task.status,
        "stage": task.stage,
        "progress": task.progress,
        "message": message,
        "attempt": task.attempt,
        "error": (
            {
                "code": task.error_code,
                "message": task.error_message,
                "retryable": True,
            }
            if task.error_code
            else None
        ),
        "created_at": task.created_at,
        "started_at": task.started_at,
        "finished_at": task.finished_at,
    }


@router.get("/plans/{plan_id}")
async def get_plan(
    plan_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    plan = await db.scalar(
        select(Plan).where(
            Plan.id == plan_id,
            Plan.user_id == user.id,
            Plan.deleted_at.is_(None),
        )
    )
    if plan is None:
        raise HTTPException(status_code=404, detail="方案不存在")

    return {
        "id": plan.id,
        "title": plan.title,
        "theme": plan.theme,
        "activity_type": plan.activity_type,
        "participants": plan.participants,
        "budget_yuan": plan.budget_fen / 100,
        "starts_at": plan.starts_at,
        "location": plan.location,
        "status": plan.status,
        "version": plan.version,
        "summary": plan.summary,
        "degraded": plan.degraded,
        "input": plan.input_json,
        "content": plan.content_json,
        "created_at": plan.created_at,
        "updated_at": plan.updated_at,
    }

@router.get("/plans")
async def list_plans(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: str | None = Query(default=None, max_length=50),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    filters = [
        Plan.user_id == user.id,
        Plan.deleted_at.is_(None),
    ]

    if keyword:
        like = f"%{keyword}%"
        filters.append(
            or_(
                Plan.title.ilike(like),
                Plan.theme.ilike(like),
            )
        )

    total = await db.scalar(
        select(func.count()).select_from(Plan).where(*filters)
    ) or 0

    rows = (
        await db.scalars(
            select(Plan)
            .where(*filters)
            .order_by(Plan.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()

    items = [
        {
            "id": plan.id,
            "title": plan.title,
            "theme": plan.theme,
            "activity_type": plan.activity_type,
            "participants": plan.participants,
            "budget_yuan": plan.budget_fen / 100,
            "starts_at": plan.starts_at,
            "location": plan.location,
            "status": plan.status,
            "degraded": plan.degraded,
            "version": plan.version,
            "summary": plan.summary,
            "created_at": plan.created_at,
            "updated_at": plan.updated_at,
        }
        for plan in rows
    ]

    total_pages = (total + page_size - 1) // page_size if total else 0

    return {
        "items": items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "has_more": page < total_pages,
        },
    }