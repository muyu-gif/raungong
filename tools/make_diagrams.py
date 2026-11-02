"""Generate simple architecture/flow/ER diagrams for the Word report."""

from __future__ import annotations

import pathlib

from PIL import Image, ImageChops, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "diagrams"
OUT.mkdir(exist_ok=True)

FONT_REG = "C:/Windows/Fonts/msyh.ttc"
FONT_BOLD = "C:/Windows/Fonts/msyhbd.ttc"

NAVY = "#1F3864"
BLUE = "#2E75B6"
LIGHT_BLUE = "#DEEBF7"
PALE_BLUE = "#F3F8FD"
TEAL = "#0F7B6C"
LIGHT_TEAL = "#D9F2EE"
ORANGE = "#C55A11"
LIGHT_ORANGE = "#FBE5D6"
GRAY = "#595959"
LIGHT_GRAY = "#F2F2F2"
BORDER = "#B4C6E7"
WHITE = "#FFFFFF"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size, index=0)


def text_size(draw: ImageDraw.ImageDraw, text: str, f: ImageFont.FreeTypeFont) -> tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=f)
    return box[2] - box[0], box[3] - box[1]


def wrap(draw: ImageDraw.ImageDraw, text: str, f: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for char in text:
        trial = current + char
        if text_size(draw, trial, f)[0] <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = char
    if current:
        lines.append(current)
    return lines


def box(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int, int, int],
    text: str,
    *,
    fill: str = WHITE,
    outline: str = BORDER,
    width: int = 3,
    f: ImageFont.FreeTypeFont | None = None,
    color: str = NAVY,
    radius: int = 16,
    pad: int = 16,
    align: str = "center",
) -> None:
    f = f or font(26)
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)
    x1, y1, x2, y2 = xy
    lines = wrap(draw, text, f, x2 - x1 - 2 * pad)
    line_h = text_size(draw, "国", f)[1] + 8
    total_h = line_h * len(lines)
    y = y1 + (y2 - y1 - total_h) / 2
    for line in lines:
        w, _ = text_size(draw, line, f)
        if align == "center":
            x = x1 + (x2 - x1 - w) / 2
        else:
            x = x1 + pad
        draw.text((x, y), line, font=f, fill=color)
        y += line_h


def arrow(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    *,
    color: str = BLUE,
    width: int = 4,
    label: str | None = None,
    label_font: ImageFont.FreeTypeFont | None = None,
) -> None:
    draw.line([start, end], fill=color, width=width)
    import math

    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    size = 14
    left = (
        end[0] - size * math.cos(angle - math.pi / 6),
        end[1] - size * math.sin(angle - math.pi / 6),
    )
    right = (
        end[0] - size * math.cos(angle + math.pi / 6),
        end[1] - size * math.sin(angle + math.pi / 6),
    )
    draw.polygon([end, left, right], fill=color)
    if label:
        f = label_font or font(20)
        mx, my = (start[0] + end[0]) / 2, (start[1] + end[1]) / 2
        w, h = text_size(draw, label, f)
        draw.rounded_rectangle(
            (mx - w / 2 - 8, my - h / 2 - 4, mx + w / 2 + 8, my + h / 2 + 4),
            radius=6,
            fill=WHITE,
        )
        draw.text((mx - w / 2, my - h / 2), label, font=f, fill=GRAY)


def title(draw: ImageDraw.ImageDraw, text: str, subtitle: str, width: int) -> None:
    f = font(44, bold=True)
    w, _ = text_size(draw, text, f)
    draw.text(((width - w) / 2, 30), text, font=f, fill=NAVY)
    f2 = font(22)
    w2, _ = text_size(draw, subtitle, f2)
    draw.text(((width - w2) / 2, 92), subtitle, font=f2, fill=GRAY)


def save_trimmed(img: Image.Image, path: pathlib.Path, pad: int = 32) -> None:
    background = Image.new("RGB", img.size, WHITE)
    diff = ImageChops.difference(img, background)
    bbox = diff.getbbox()
    if bbox:
        left = max(0, bbox[0] - pad)
        top = max(0, bbox[1] - pad)
        right = min(img.width, bbox[2] + pad)
        bottom = min(img.height, bbox[3] + pad)
        img = img.crop((left, top, right, bottom))
    img.save(path)
    print("wrote", path, img.size)


def architecture() -> None:
    W, H = 1800, 1120
    img = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    title(d, "活动智囊后端总体架构", "浏览器 → FastAPI → 智能体工作流 / PostgreSQL", W)

    # Client layer
    d.rounded_rectangle((70, 150, 1730, 280), radius=18, fill=PALE_BLUE, outline=BORDER, width=3)
    d.text((95, 165), "前端（A）", font=font(22, True), fill=BLUE)
    box(d, (620, 185, 1180, 260), "Vue / React + Element Plus\n表单、进度、卡片/表格、导出", fill=WHITE, f=font(25))

    # API layer
    d.rounded_rectangle((70, 330, 1730, 760), radius=18, fill=PALE_BLUE, outline=BORDER, width=3)
    d.text((95, 345), "FastAPI 后端（B）", font=font(22, True), fill=BLUE)
    labels = ["Auth 认证", "Plans 方案", "Tasks 任务", "Templates 模板", "Export 导出"]
    x = 105
    for label in labels:
        box(d, (x, 390, x + 300, 475), label, fill=LIGHT_BLUE, outline=BLUE, f=font(24, True))
        x += 325

    box(d, (105, 530, 520, 710), "GenerationService\n生成编排 / 幂等 / 重试", fill=WHITE, f=font(24))
    box(d, (570, 530, 980, 710), "ContentValidator\nSchema 校验 / 金额重算", fill=WHITE, f=font(24))
    box(d, (1030, 530, 1440, 710), "AgentAdapter\nDify / Coze / Mock", fill=WHITE, f=font(24))
    box(d, (1490, 530, 1690, 710), "JWT\n限流", fill=WHITE, f=font(24))

    # External + DB
    box(d, (900, 840, 1500, 1010), "扣子 / Dify 工作流（C）\n策划 → 物资 → 分工 → 宣传 → 风险", fill=LIGHT_TEAL, outline=TEAL, f=font(24))
    box(d, (180, 840, 800, 1010), "Supabase PostgreSQL\n方案 / 任务 / 版本 / 模板", fill=LIGHT_ORANGE, outline=ORANGE, f=font(24))

    arrow(d, (900, 280), (900, 330), label="HTTPS JSON", label_font=font(19))
    arrow(d, (1200, 710), (1200, 840), label="HTTPS / JSON", label_font=font(19))
    arrow(d, (450, 760), (450, 840), color=ORANGE, label="SQLAlchemy", label_font=font(19))
    save_trimmed(img, OUT / "architecture.png")


def flow() -> None:
    W, H = 1500, 1420
    img = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    title(d, "活动包生成流程", "异步任务 + 轮询；校验失败先修复，仍失败则降级", W)

    cx1, cx2 = 470, 1030
    nodes = [
        (180, 300, "填写活动信息\n主题 / 人数 / 预算 / 时间 / 地点"),
        (360, 480, "参数校验\n必填、范围、时间、预算"),
        (540, 660, "创建方案 + 生成任务\n返回 202 与 task_id"),
        (720, 840, "调用智能体工作流\n策划 → 物资 → 分工 → 宣传 → 风险"),
        (900, 1020, "解析 + Schema 校验\n失败则带错误修复重试"),
        (1080, 1260, "保存内容并置为 ready\n轮询任务、渲染、编辑、导出"),
    ]
    for index, (y1, y2, text) in enumerate(nodes):
        box(d, (cx1, y1, cx2, y2), text, fill=LIGHT_BLUE, outline=BLUE, f=font(25))
        if index > 0:
            arrow(d, ((cx1 + cx2) // 2, nodes[index - 1][1]), ((cx1 + cx2) // 2, y1))

    # Left branch: validation failed
    box(d, (90, 340, 390, 460), "校验失败\n返回修改", fill=LIGHT_ORANGE, outline=ORANGE, f=font(22))
    arrow(d, (cx1, 420), (390, 420), color=ORANGE, label="否", label_font=font(19))

    # Right branch: repair / fallback
    box(d, (1110, 850, 1400, 980), "修复重试 1 次\n仍失败 → 规则降级", fill=LIGHT_ORANGE, outline=ORANGE, f=font(22))
    arrow(d, (cx2, 960), (1110, 915), color=ORANGE, label="失败", label_font=font(19))

    # Side notes
    box(d, (90, 560, 390, 680), "幂等键\n10 分钟内不重复生成", fill=LIGHT_TEAL, outline=TEAL, f=font(21))
    box(d, (1110, 1090, 1400, 1210), "重算金额 / 补齐 ID\n写入 warnings", fill=LIGHT_TEAL, outline=TEAL, f=font(21))
    save_trimmed(img, OUT / "flow_generation.png")


def er() -> None:
    W, H = 1800, 1300
    img = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    title(d, "核心数据模型", "用户、方案、任务、版本、模板之间的主要关系", W)

    def entity(x, y, w, h, name: str, fields: list[str], color: str = BLUE) -> tuple[int, int, int, int]:
        d.rounded_rectangle((x, y, x + w, y + h), radius=14, fill=WHITE, outline=color, width=3)
        d.rounded_rectangle((x, y, x + w, y + 56), radius=14, fill=color, outline=color, width=3)
        d.text((x + 20, y + 12), name, font=font(25, True), fill=WHITE)
        fy = y + 72
        for line in fields:
            d.text((x + 20, fy), line, font=font(20), fill="#333333")
            fy += 34
        return (x, y, x + w, y + h)

    users = entity(80, 170, 380, 290, "USERS", ["id (PK)", "username (UK)", "password_hash", "display_name", "role", "created_at"], NAVY)
    plans = entity(620, 140, 440, 380, "PLANS", ["id (PK)", "user_id (FK)", "title / theme", "status / version", "input_json", "content_json", "deleted_at"], BLUE)
    tasks = entity(1240, 130, 440, 340, "GENERATION_TASKS", ["id (PK)", "plan_id (FK)", "status / stage", "progress", "idempotency_key", "error_code"], TEAL)
    versions = entity(1240, 620, 440, 280, "PLAN_VERSIONS", ["id (PK)", "plan_id (FK)", "version", "content_json", "editor_id", "created_at"], TEAL)
    templates = entity(80, 590, 380, 300, "TEMPLATES", ["id (PK)", "user_id (FK)", "name", "defaults_json", "content_json", "use_count"], NAVY)
    exports = entity(620, 650, 440, 320, "EXPORT_RECORDS", ["id (PK)", "plan_id (FK)", "format", "file_size", "created_at"], BLUE)

    # Relations
    arrow(d, (460, 300), (620, 300), label="1 : N", label_font=font(20))
    arrow(d, (1060, 280), (1240, 280), label="1 : N", label_font=font(20))
    arrow(d, (1060, 470), (1240, 650), color=TEAL, label="1 : N", label_font=font(20))
    arrow(d, (270, 460), (270, 590), label="1 : N", label_font=font(20))
    arrow(d, (850, 520), (850, 650), color=ORANGE, label="1 : N", label_font=font(20))
    save_trimmed(img, OUT / "er_model.png")


def sequence() -> None:
    W, H = 1800, 1120
    img = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    title(d, "活动包生成时序", "异步任务创建、智能体调用、校验保存与前端轮询", W)

    people = [
        (150, "前端 A", BLUE),
        (450, "FastAPI", NAVY),
        (750, "PostgreSQL", ORANGE),
        (1050, "Generation\nService", TEAL),
        (1350, "扣子 / Dify", TEAL),
        (1650, "Validator", BLUE),
    ]
    for cx, label, color in people:
        box(d, (cx - 115, 150, cx + 115, 225), label, fill=color, outline=color, f=font(21), color=WHITE)
        for y in range(230, 1070, 18):
            d.line([(cx, y), (cx, y + 8)], fill="#A6A6A6", width=2)

    messages = [
        (280, 0, 1, "POST /generate", BLUE),
        (340, 1, 2, "创建 plan + task", NAVY),
        (400, 1, 0, "202 task_id", NAVY),
        (470, 1, 3, "后台执行", TEAL),
        (540, 3, 4, "调用工作流", TEAL),
        (610, 4, 3, "结构化 JSON", TEAL),
        (680, 3, 5, "校验 / 重算", BLUE),
        (740, 5, 3, "通过 / 错误", BLUE),
        (810, 3, 2, "保存 ready", ORANGE),
        (950, 0, 1, "轮询任务", BLUE),
        (1010, 1, 0, "进度 / 结果", NAVY),
    ]
    for y, a, b, label, color in messages:
        x1, x2 = people[a][0], people[b][0]
        direction = 1 if x2 > x1 else -1
        start = (x1 + direction * 8, y)
        end = (x2 - direction * 8, y)
        arrow(d, start, end, color=color, width=3, label=label, label_font=font(18))

    d.rounded_rectangle((70, 880, 1730, 1045), radius=12, outline=BLUE, width=3)
    d.text((90, 892), "loop：每 2 秒轮询，直到 succeeded / failed", font=font(18, True), fill=BLUE)
    save_trimmed(img, OUT / "sequence.png")


def main() -> None:
    architecture()
    flow()
    er()
    sequence()


if __name__ == "__main__":
    main()
