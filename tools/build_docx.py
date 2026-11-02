"""Build the combined Word report from the three Markdown documents.

Run with the bundled Python that has python-docx/Pillow:
    <bundled-python> tools/build_docx.py
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import re
from typing import Iterable

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCS = [
    ROOT / "docs" / "01-需求分析.md",
    ROOT / "docs" / "02-后端开发文档.md",
    ROOT / "docs" / "03-接口规范.md",
]
OUT = ROOT / "活动智囊-后端文档合集.docx"
DIAGRAMS = ROOT / "diagrams"

NAVY = RGBColor(0x1F, 0x38, 0x64)
BLUE = RGBColor(0x2E, 0x75, 0xB6)
DARK = RGBColor(0x26, 0x26, 0x26)
GRAY = RGBColor(0x59, 0x59, 0x59)
LIGHT_GRAY = RGBColor(0x7F, 0x7F, 0x7F)

BODY_FONT_CN = "宋体"
BODY_FONT_EN = "Times New Roman"
HEAD_FONT_CN = "黑体"
CODE_FONT = "Consolas"
CODE_FONT_CN = "微软雅黑"

INLINE_RE = re.compile(r"(\*\*.+?\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))")


def set_run_font(
    run,
    *,
    name: str = BODY_FONT_EN,
    east_asia: str = BODY_FONT_CN,
    size: float | None = None,
    bold: bool | None = None,
    color: RGBColor | None = None,
    italic: bool | None = None,
) -> None:
    run.font.name = name
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:eastAsia"), east_asia)
    rfonts.set(qn("w:ascii"), name)
    rfonts.set(qn("w:hAnsi"), name)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    if color is not None:
        run.font.color.rgb = color


def shade_run(run, fill: str = "F1F3F5") -> None:
    rpr = run._element.get_or_add_rPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    rpr.append(shd)


def set_paragraph_shading(paragraph, fill: str) -> None:
    ppr = paragraph._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    ppr.append(shd)


def set_paragraph_border(paragraph, side: str, color: str, size: int = 6) -> None:
    ppr = paragraph._p.get_or_add_pPr()
    pbdr = ppr.find(qn("w:pBdr"))
    if pbdr is None:
        pbdr = OxmlElement("w:pBdr")
        ppr.append(pbdr)
    border = OxmlElement(f"w:{side}")
    border.set(qn("w:val"), "single")
    border.set(qn("w:sz"), str(size))
    border.set(qn("w:space"), "6")
    border.set(qn("w:color"), color)
    pbdr.append(border)


def set_cell_shading(cell, fill: str) -> None:
    tcpr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tcpr.append(shd)


def set_cell_margins(cell, top: int = 60, bottom: int = 60, left: int = 90, right: int = 90) -> None:
    tcpr = cell._tc.get_or_add_tcPr()
    tcmar = OxmlElement("w:tcMar")
    for tag, value in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        node = OxmlElement(f"w:{tag}")
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")
        tcmar.append(node)
    tcpr.append(tcmar)


def repeat_table_header(table) -> None:
    trpr = table.rows[0]._tr.get_or_add_trPr()
    header = OxmlElement("w:tblHeader")
    header.set(qn("w:val"), "true")
    trpr.append(header)


def cant_split_row(row) -> None:
    trpr = row._tr.get_or_add_trPr()
    trpr.append(OxmlElement("w:cantSplit"))


def add_field(paragraph, instruction: str, placeholder: str = "") -> None:
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = f" {instruction} "
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = placeholder
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.append(begin)
    run._r.append(instr)
    run._r.append(separate)
    run._r.append(text)
    run._r.append(end)


def add_toc_page(doc: Document) -> None:
    entries = []
    toc_path = ROOT / "tools" / "toc.json"
    if toc_path.exists():
        entries = [item for item in json.loads(toc_path.read_text(encoding="utf-8")) if item["level"] <= 2]
    if not entries:
        p = doc.add_paragraph()
        p.paragraph_format.page_break_before = True
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run("目  录")
        set_run_font(run, name=HEAD_FONT_CN, east_asia=HEAD_FONT_CN, size=22, bold=True, color=NAVY)
        p = doc.add_paragraph()
        run = p.add_run("目录数据尚未生成。请先运行预览导出与 tools/extract_toc.py。")
        set_run_font(run, size=10, color=GRAY)
        return

    split = 27
    add_toc_entries(doc, entries[:split], continued=False, first_page=True)
    add_toc_entries(doc, entries[split:], continued=True, first_page=False)


def add_toc_entries(doc: Document, entries: list[dict], *, continued: bool, first_page: bool) -> None:
    p = doc.add_paragraph()
    if first_page:
        p.paragraph_format.page_break_before = True
    else:
        p.paragraph_format.page_break_before = True
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run("目  录" if not continued else "目  录（续）")
    set_run_font(run, name=HEAD_FONT_CN, east_asia=HEAD_FONT_CN, size=22, bold=True, color=NAVY)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(16)
    run = p.add_run("页码为本文档排版页码；标注“（续）”的条目承接上页")
    set_run_font(run, size=8.5, color=GRAY)

    for item in entries:
        level = item["level"]
        paragraph = doc.add_paragraph()
        paragraph.paragraph_format.left_indent = Cm(0.0 if level == 1 else 0.65)
        paragraph.paragraph_format.first_line_indent = Cm(0)
        paragraph.paragraph_format.space_before = Pt(9 if level == 1 else 1)
        paragraph.paragraph_format.space_after = Pt(2)
        paragraph.paragraph_format.line_spacing = 1.1
        paragraph.paragraph_format.tab_stops.add_tab_stop(
            Cm(15.0), alignment=WD_TAB_ALIGNMENT.RIGHT, leader=WD_TAB_LEADER.DOTS
        )
        title_run = paragraph.add_run(item["title"])
        if level == 1:
            set_run_font(title_run, name=HEAD_FONT_CN, east_asia=HEAD_FONT_CN, size=11.5, bold=True, color=NAVY)
        else:
            set_run_font(title_run, size=9.5, color=DARK)
        page_run = paragraph.add_run(f"\t{item['page']}")
        if level == 1:
            set_run_font(page_run, name=HEAD_FONT_CN, east_asia=HEAD_FONT_CN, size=10.5, bold=True, color=NAVY)
        else:
            set_run_font(page_run, size=9.5, color=GRAY)


def add_inline(paragraph, text: str, base_size: float = 10.5, color: RGBColor = DARK) -> None:
    text = text.replace("\\|", "|").replace("&nbsp;", " ").replace("<br>", "\n")
    pos = 0
    for match in INLINE_RE.finditer(text):
        if match.start() > pos:
            _add_plain(paragraph, text[pos : match.start()], base_size, color)
        token = match.group(0)
        if token.startswith("**") and token.endswith("**"):
            inner = token[2:-2]
            for part in re.split(r"(`[^`]+`)", inner):
                if not part:
                    continue
                if part.startswith("`") and part.endswith("`"):
                    run = paragraph.add_run(part[1:-1])
                    set_run_font(
                        run,
                        name=CODE_FONT,
                        east_asia=CODE_FONT_CN,
                        size=base_size - 1,
                        bold=True,
                        color=RGBColor(0xB0, 0x30, 0x60),
                    )
                    shade_run(run)
                else:
                    run = paragraph.add_run(part)
                    set_run_font(run, size=base_size, bold=True, color=color)
        elif token.startswith("`") and token.endswith("`"):
            inner = token[1:-1]
            run = paragraph.add_run(inner)
            set_run_font(run, name=CODE_FONT, east_asia=CODE_FONT_CN, size=base_size - 1, color=RGBColor(0xB0, 0x30, 0x60))
            shade_run(run)
        elif token.startswith("["):
            label, url = re.match(r"\[([^\]]+)\]\(([^)]+)\)", token).groups()
            run = paragraph.add_run(label)
            set_run_font(run, size=base_size, color=BLUE)
            run2 = paragraph.add_run(f"（{url}）")
            set_run_font(run2, size=base_size - 1.5, color=LIGHT_GRAY)
        pos = match.end()
    if pos < len(text):
        _add_plain(paragraph, text[pos:], base_size, color)


def _add_plain(paragraph, text: str, size: float, color: RGBColor) -> None:
    if not text:
        return
    parts = text.split("\n")
    for index, part in enumerate(parts):
        if index > 0:
            paragraph.add_run().add_break()
        if part:
            run = paragraph.add_run(part)
            set_run_font(run, size=size, color=color)


def new_body_paragraph(doc: Document, text: str = "") -> None:
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.line_spacing = 1.5
    paragraph.paragraph_format.space_after = Pt(4)
    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT if "\n" in text else WD_ALIGN_PARAGRAPH.JUSTIFY
    if text:
        add_inline(paragraph, text)


def add_heading(doc: Document, text: str, level: int, *, page_break: bool = False) -> None:
    text = re.sub(r"[`*]", "", text).strip()
    paragraph = doc.add_paragraph(style=f"Heading {level}")
    if page_break:
        paragraph.paragraph_format.page_break_before = True
    run = paragraph.add_run(text)
    if level == 1:
        set_run_font(run, name=HEAD_FONT_CN, east_asia=HEAD_FONT_CN, size=20, bold=True, color=NAVY)
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.space_before = Pt(0)
        paragraph.paragraph_format.space_after = Pt(20)
        set_paragraph_border(paragraph, "bottom", "1F3864", 8)
    elif level == 2:
        set_run_font(run, name=HEAD_FONT_CN, east_asia=HEAD_FONT_CN, size=15, bold=True, color=NAVY)
        paragraph.paragraph_format.space_before = Pt(16)
        paragraph.paragraph_format.space_after = Pt(7)
        paragraph.paragraph_format.keep_with_next = True
    elif level == 3:
        set_run_font(run, name=HEAD_FONT_CN, east_asia=HEAD_FONT_CN, size=12.5, bold=True, color=BLUE)
        paragraph.paragraph_format.space_before = Pt(11)
        paragraph.paragraph_format.space_after = Pt(4)
        paragraph.paragraph_format.keep_with_next = True
    else:
        set_run_font(run, name=HEAD_FONT_CN, east_asia=HEAD_FONT_CN, size=11, bold=True, color=DARK)
        paragraph.paragraph_format.space_before = Pt(8)
        paragraph.paragraph_format.space_after = Pt(3)
        paragraph.paragraph_format.keep_with_next = True


def add_code_block(doc: Document, code: str, language: str) -> None:
    language = language.lower().strip()
    if language == "mermaid":
        image_map = [
            ("sequenceDiagram", DIAGRAMS / "sequence.png", "活动包生成时序"),
            ("erDiagram", DIAGRAMS / "er_model.png", "核心数据模型"),
            ("flowchart LR", DIAGRAMS / "architecture.png", "后端总体架构"),
            ("flowchart TD", DIAGRAMS / "flow_generation.png", "活动包生成流程"),
        ]
        for marker, path, caption in image_map:
            if marker in code and path.exists():
                add_figure(doc, path, caption)
                return
        return

    lines = code.rstrip("\n").split("\n")
    if language == "json" and len(lines) > 150:
        add_note(
            doc,
            "完整 JSON 示例约 30 KB（含 9 项物资、12 条任务、7 条风险），"
            "受版面限制不在 Word 中全文展开。请打开配套文件 "
            "examples/plan_welcome_party.json 查看完整内容；"
            "字段定义见 7.1～7.8 节，Markdown 版接口规范保留了全文。",
        )
        return

    chunk_size = 24
    for start in range(0, len(lines), chunk_size):
        chunk = lines[start : start + chunk_size]
        paragraph = doc.add_paragraph()
        paragraph.paragraph_format.space_before = Pt(2)
        paragraph.paragraph_format.space_after = Pt(2)
        paragraph.paragraph_format.line_spacing = 1.0
        paragraph.paragraph_format.left_indent = Cm(0.25)
        paragraph.paragraph_format.right_indent = Cm(0.1)
        set_paragraph_shading(paragraph, "F6F8FA")
        set_paragraph_border(paragraph, "left", "2E75B6", 12)
        if len(chunk) <= 14:
            paragraph.paragraph_format.keep_together = True
        run = paragraph.add_run("\n".join(chunk))
        set_run_font(run, name=CODE_FONT, east_asia=CODE_FONT_CN, size=8.5, color=RGBColor(0x33, 0x33, 0x33))


def add_figure(doc: Document, path: pathlib.Path, caption: str) -> None:
    global FIGURE_COUNTER
    FIGURE_COUNTER += 1
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_before = Pt(8)
    paragraph.paragraph_format.space_after = Pt(2)
    paragraph.paragraph_format.keep_with_next = True
    run = paragraph.add_run()
    width = Cm(15.0)
    if path.name == "flow_generation.png":
        width = Cm(12.6)
    run.add_picture(str(path), width=width)
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_before = Pt(2)
    cap.paragraph_format.space_after = Pt(10)
    r = cap.add_run(f"图 {FIGURE_COUNTER}  {caption}")
    set_run_font(r, size=9, color=GRAY)


def add_note(doc: Document, text: str) -> None:
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.left_indent = Cm(0.35)
    paragraph.paragraph_format.right_indent = Cm(0.2)
    paragraph.paragraph_format.space_before = Pt(6)
    paragraph.paragraph_format.space_after = Pt(8)
    set_paragraph_shading(paragraph, "F2F6FC")
    set_paragraph_border(paragraph, "left", "2E75B6", 12)
    add_inline(paragraph, text, base_size=9.5, color=GRAY)


def add_blockquote(doc: Document, lines: list[str]) -> None:
    text = " ".join(line.lstrip("> ").strip() for line in lines)
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.left_indent = Cm(0.6)
    paragraph.paragraph_format.right_indent = Cm(0.4)
    paragraph.paragraph_format.space_before = Pt(4)
    paragraph.paragraph_format.space_after = Pt(6)
    set_paragraph_shading(paragraph, "F2F6FC")
    set_paragraph_border(paragraph, "left", "2E75B6", 12)
    add_inline(paragraph, text, base_size=9.5, color=GRAY)


def add_horizontal_rule(doc: Document) -> None:
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(6)
    paragraph.paragraph_format.space_after = Pt(6)
    set_paragraph_border(paragraph, "bottom", "D9D9D9", 6)


def add_list_item(doc: Document, text: str, ordered: bool = False, level: int = 0) -> None:
    if text.startswith("[ ] "):
        text = "☐ " + text[4:]
    elif text.startswith("[x] ") or text.startswith("[X] "):
        text = "☑ " + text[4:]
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.left_indent = Cm(0.75 + 0.55 * level)
    paragraph.paragraph_format.first_line_indent = Cm(-0.4)
    paragraph.paragraph_format.space_after = Pt(2)
    paragraph.paragraph_format.line_spacing = 1.35
    prefix = "• " if not ordered else ""
    if ordered:
        match = re.match(r"^(\d+)\.\s+(.*)$", text)
        if match:
            prefix = f"{match.group(1)}. "
            text = match.group(2)
    run = paragraph.add_run(prefix)
    set_run_font(run, size=10.5, color=BLUE, bold=not ordered)
    add_inline(paragraph, text)


def split_table_row(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    line = line.replace("\\|", "\u0000")
    cells = [cell.strip().replace("\u0000", "|") for cell in line.split("|")]
    return cells


def is_table_separator(line: str) -> bool:
    stripped = line.strip()
    if "-" not in stripped:
        return False
    return bool(re.fullmatch(r"\|?[\s:|-]+\|?", stripped))


def display_width(text: str) -> int:
    total = 0
    for char in text:
        total += 2 if ord(char) > 127 else 1
    return total


def add_table(doc: Document, rows: list[list[str]]) -> None:
    if not rows:
        return
    columns = max(len(row) for row in rows)
    for row in rows:
        while len(row) < columns:
            row.append("")
        if len(row) > columns:
            row[columns - 1] = " | ".join(row[columns - 1 :])
            del row[columns:]

    table = doc.add_table(rows=len(rows), cols=columns)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    table.allow_autofit = False
    tblpr = table._tbl.tblPr
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tblpr.append(layout)

    weights = []
    for col in range(columns):
        longest = max(display_width(row[col]) for row in rows)
        weights.append(max(8, min(longest, 52)))
    total_weight = sum(weights) or 1
    usable = 15.2
    widths = [max(1.8, usable * weight / total_weight) for weight in weights]
    for c_index, width in enumerate(widths):
        table.columns[c_index].width = Cm(width)

    keep_table = len(rows) <= 8
    for r_index, row in enumerate(rows):
        table_row = table.rows[r_index]
        for c_index, value in enumerate(row):
            cell = table_row.cells[c_index]
            cell.width = Cm(widths[c_index])
            set_cell_margins(cell)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            paragraph = cell.paragraphs[0]
            paragraph.paragraph_format.space_after = Pt(0)
            paragraph.paragraph_format.line_spacing = 1.15
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER if r_index == 0 else WD_ALIGN_PARAGRAPH.LEFT
            if keep_table and r_index < len(rows) - 1:
                paragraph.paragraph_format.keep_with_next = True
            add_inline(paragraph, value, base_size=8.8, color=RGBColor(0x33, 0x33, 0x33))
            if r_index == 0:
                set_cell_shading(cell, "1F3864")
                for run in paragraph.runs:
                    run.font.bold = True
                    run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
            elif r_index % 2 == 0:
                set_cell_shading(cell, "F3F8FD")

    spacer = doc.add_paragraph()
    spacer.paragraph_format.space_after = Pt(2)
    spacer.paragraph_format.line_spacing = 1.0


def parse_table(lines: list[str], start: int) -> tuple[list[list[str]], int]:
    rows: list[list[str]] = []
    index = start
    while index < len(lines) and lines[index].strip().startswith("|"):
        if not is_table_separator(lines[index]):
            rows.append(split_table_row(lines[index]))
        index += 1
    return rows, index


def is_special_start(lines: list[str], index: int) -> bool:
    line = lines[index]
    stripped = line.strip()
    if not stripped:
        return True
    if stripped.startswith("```") or stripped.startswith("#"):
        return True
    if stripped.startswith("|") or stripped.startswith(">"):
        return True
    if stripped in ("---", "***", "___"):
        return True
    if re.match(r"^\s*[-*]\s+", line) or re.match(r"^\s*\d+\.\s+", line):
        return True
    return False


def smart_join(parts: Iterable[str]) -> str:
    raw_parts = list(parts)
    result = ""
    for index, raw in enumerate(raw_parts):
        part = raw.strip()
        if not part:
            continue
        if result:
            previous = raw_parts[index - 1] if index > 0 else ""
            if previous.endswith("  "):
                result += "\n"
            elif result[-1].isascii() and part[0].isascii():
                result += " "
        result += part
    return result


def render_markdown(doc: Document, path: pathlib.Path, first_document: bool) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    index = 0
    seen_h1 = False
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()

        if not stripped:
            index += 1
            continue

        if stripped.startswith("```"):
            language = stripped[3:].strip()
            index += 1
            code_lines = []
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code_lines.append(lines[index])
                index += 1
            index += 1
            add_code_block(doc, "\n".join(code_lines), language)
            continue

        heading_match = re.match(r"^(#{1,4})\s+(.*)$", line)
        if heading_match:
            level = len(heading_match.group(1))
            text = heading_match.group(2).strip()
            page_break = level == 1
            if level == 1:
                seen_h1 = True
            add_heading(doc, text, level, page_break=page_break)
            index += 1
            continue

        if stripped.startswith("|") and index + 1 < len(lines) and is_table_separator(lines[index + 1]):
            rows, index = parse_table(lines, index)
            add_table(doc, rows)
            continue

        if stripped.startswith(">"):
            quote_lines = []
            while index < len(lines) and lines[index].strip().startswith(">"):
                quote_lines.append(lines[index])
                index += 1
            add_blockquote(doc, quote_lines)
            continue

        if stripped in ("---", "***", "___"):
            add_horizontal_rule(doc)
            index += 1
            continue

        list_match = re.match(r"^(\s*)[-*]\s+(.*)$", line)
        if list_match:
            level = len(list_match.group(1)) // 2
            add_list_item(doc, list_match.group(2).strip(), ordered=False, level=level)
            index += 1
            continue

        ordered_match = re.match(r"^(\s*)(\d+)\.\s+(.*)$", line)
        if ordered_match:
            level = len(ordered_match.group(1)) // 2
            add_list_item(doc, f"{ordered_match.group(2)}. {ordered_match.group(3).strip()}", ordered=True, level=level)
            index += 1
            continue

        paragraph_lines = [line]
        index += 1
        while index < len(lines) and not is_special_start(lines, index):
            paragraph_lines.append(lines[index])
            index += 1
        text = smart_join(paragraph_lines)
        if text:
            new_body_paragraph(doc, text)


def set_style_font(style, english: str, east_asia: str, size: float | None = None, bold: bool | None = None) -> None:
    style.font.name = english
    if size is not None:
        style.font.size = Pt(size)
    if bold is not None:
        style.font.bold = bold
    rpr = style._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:ascii"), english)
    rfonts.set(qn("w:hAnsi"), english)
    rfonts.set(qn("w:eastAsia"), east_asia)


def setup_document() -> Document:
    doc = Document()
    section = doc.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.54)
    section.bottom_margin = Cm(2.54)
    section.left_margin = Cm(3.0)
    section.right_margin = Cm(2.5)
    section.header_distance = Cm(1.5)
    section.footer_distance = Cm(1.4)
    section.different_first_page_header_footer = True

    styles = doc.styles
    normal = styles["Normal"]
    set_style_font(normal, BODY_FONT_EN, BODY_FONT_CN, size=10.5)
    normal.font.color.rgb = DARK
    normal.paragraph_format.line_spacing = 1.5
    normal.paragraph_format.space_after = Pt(4)

    for style_name in ("Heading 1", "Heading 2", "Heading 3", "Heading 4"):
        style = styles[style_name]
        set_style_font(style, HEAD_FONT_CN, HEAD_FONT_CN)
        style.font.bold = True
        style.font.color.rgb = NAVY

    # Header
    header = section.header
    header_para = header.paragraphs[0]
    header_para.paragraph_format.tab_stops.clear_all()
    header_para.paragraph_format.tab_stops.add_tab_stop(Cm(15.2), alignment=WD_TAB_ALIGNMENT.RIGHT)
    run = header_para.add_run("活动智囊 · 后端文档包")
    set_run_font(run, size=9, color=GRAY)
    run = header_para.add_run("\t\tv1.0")
    set_run_font(run, size=9, color=GRAY)
    set_paragraph_border(header_para, "bottom", "BFBFBF", 4)

    # Footer
    footer = section.footer
    footer_para = footer.paragraphs[0]
    footer_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = footer_para.add_run("第 ")
    set_run_font(run, size=9, color=GRAY)
    add_field(footer_para, "PAGE", "1")
    run = footer_para.add_run(" 页 / 共 ")
    set_run_font(run, size=9, color=GRAY)
    add_field(footer_para, "NUMPAGES", "1")
    run = footer_para.add_run(" 页")
    set_run_font(run, size=9, color=GRAY)

    doc.core_properties.title = "活动智囊——基于智能体的校园社团活动一键策划与执行包生成系统"
    doc.core_properties.subject = "需求分析、后端开发文档、接口规范"
    doc.core_properties.author = "B（后端）"
    doc.core_properties.keywords = "活动智囊, FastAPI, 智能体, 校园社团, 活动策划"
    doc.core_properties.comments = "课程项目后端文档包 v1.0"
    return doc


def add_cover(doc: Document) -> None:
    for _ in range(4):
        doc.add_paragraph()

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("校园社团活动数字化工具")
    set_run_font(run, name=HEAD_FONT_CN, east_asia=HEAD_FONT_CN, size=12, color=BLUE)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(12)
    run = p.add_run("活动智囊")
    set_run_font(run, name=HEAD_FONT_CN, east_asia=HEAD_FONT_CN, size=40, bold=True, color=NAVY)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.line_spacing = 1.4
    run = p.add_run("基于智能体的校园社团活动\n一键策划与执行包生成系统")
    set_run_font(run, name=HEAD_FONT_CN, east_asia=HEAD_FONT_CN, size=19, color=DARK)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(30)
    run = p.add_run("后端文档包")
    set_run_font(run, name=HEAD_FONT_CN, east_asia=HEAD_FONT_CN, size=18, bold=True, color=BLUE)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(10)
    run = p.add_run("需求分析  ·  后端开发  ·  接口规范")
    set_run_font(run, size=12, color=GRAY)

    # decorative line
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(18)
    p.paragraph_format.space_after = Pt(26)
    set_paragraph_border(p, "bottom", "2E75B6", 12)

    table = doc.add_table(rows=6, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    rows = [
        ("项目名称", "活动智囊"),
        ("文档组成", "需求分析 / 后端开发文档 / 接口规范"),
        ("文档版本", "v1.0"),
        ("编写", "B（后端）"),
        ("技术栈", "FastAPI · SQLite/PostgreSQL · 扣子/Dify · Render"),
        ("日期", "2026 年 11 月"),
    ]
    for row_index, (label, value) in enumerate(rows):
        for col, text in enumerate((label, value)):
            cell = table.cell(row_index, col)
            cell.width = Cm(4.0 if col == 0 else 11.0)
            set_cell_margins(cell, top=60, bottom=60)
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            run = p.add_run(text)
            if col == 0:
                set_run_font(run, size=10.5, bold=True, color=GRAY)
            else:
                set_run_font(run, size=10.5, color=DARK)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(16)
    run = p.add_run("内部资料 · 用于课程项目设计与答辩")
    set_run_font(run, size=9, color=LIGHT_GRAY)


def add_toc_page(doc: Document) -> None:
    entries = []
    toc_path = ROOT / "tools" / "toc.json"
    if toc_path.exists():
        entries = [item for item in json.loads(toc_path.read_text(encoding="utf-8")) if item["level"] <= 2]
    if not entries:
        p = doc.add_paragraph()
        p.paragraph_format.page_break_before = True
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run("目  录")
        set_run_font(run, name=HEAD_FONT_CN, east_asia=HEAD_FONT_CN, size=22, bold=True, color=NAVY)
        p = doc.add_paragraph()
        run = p.add_run("目录数据尚未生成。请先运行预览导出与 tools/extract_toc.py。")
        set_run_font(run, size=10, color=GRAY)
        return

    split = 27
    add_toc_entries(doc, entries[:split], continued=False, first_page=True)
    add_toc_entries(doc, entries[split:], continued=True, first_page=False)


FIGURE_COUNTER = 0


def main() -> None:
    doc = setup_document()
    add_cover(doc)
    add_toc_page(doc)
    for index, path in enumerate(DOCS):
        render_markdown(doc, path, first_document=(index == 0))
    doc.save(OUT)
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
