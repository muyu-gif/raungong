"""Extract heading outline (title/page/level) from a LibreOffice PDF export.

Usage:
    python tools/extract_toc.py preview.pdf toc.json
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def objects(pdf: bytes) -> dict[int, bytes]:
    found = {}
    for match in re.finditer(rb"(?m)^(\d+) 0 obj\b(.*?)\bendobj", pdf, re.S):
        found[int(match.group(1))] = match.group(2)
    return found


def refs(value: bytes) -> list[int]:
    return [int(x) for x in re.findall(rb"(\d+) 0 R", value)]


def decode_title(body: bytes) -> str | None:
    match = re.search(rb"/Title\s*<([0-9A-Fa-f\s]+)>", body)
    if match:
        raw = bytes.fromhex(re.sub(rb"\s+", b"", match.group(1)).decode())
        if raw.startswith(b"\xfe\xff"):
            raw = raw[2:]
        try:
            return raw.decode("utf-16-be")
        except UnicodeDecodeError:
            return raw.decode("latin-1", "replace")
    match = re.search(rb"/Title\s*\((.*?)\)", body, re.S)
    if match:
        return match.group(1).decode("latin-1", "replace")
    return None


def page_order(objs: dict[int, bytes]) -> dict[int, int]:
    catalog = None
    for num, body in objs.items():
        if b"/Type/Catalog" in body:
            catalog = body
            break
    if catalog is None:
        raise RuntimeError("catalog not found")
    pages_match = re.search(rb"/Pages\s+(\d+)\s+0\s+R", catalog)
    if not pages_match:
        raise RuntimeError("pages root not found")
    root = int(pages_match.group(1))

    ordered: list[int] = []

    def walk(num: int) -> None:
        body = objs.get(num)
        if body is None:
            return
        kids = re.search(rb"/Kids\s*\[(.*?)\]", body, re.S)
        if kids:
            for kid in refs(kids.group(1)):
                walk(kid)
        elif b"/Type/Page" in body:
            ordered.append(num)

    walk(root)
    return {page_ref: index + 1 for index, page_ref in enumerate(ordered)}


def outline(objs: dict[int, bytes], pages: dict[int, int]) -> list[dict]:
    root_num = None
    for body in objs.values():
        if b"/Type/Catalog" in body:
            match = re.search(rb"/Outlines\s+(\d+)\s+0\s+R", body)
            if match:
                root_num = int(match.group(1))
                break
    if root_num is None:
        return []
    root = objs.get(root_num, b"")
    first = re.search(rb"/First\s+(\d+)\s+0\s+R", root)
    if not first:
        return []

    result: list[dict] = []

    def walk_item(num: int, level: int) -> None:
        body = objs.get(num)
        if body is None:
            return
        title = decode_title(body)
        dest = re.search(rb"/Dest\s*\[\s*(\d+)\s+0\s+R", body)
        if title and dest:
            page_ref = int(dest.group(1))
            result.append({"title": title, "page": pages.get(page_ref, 0), "level": level})
        child = re.search(rb"/First\s+(\d+)\s+0\s+R", body)
        if child:
            walk_item(int(child.group(1)), level + 1)
        nxt = re.search(rb"/Next\s+(\d+)\s+0\s+R", body)
        if nxt:
            walk_item(int(nxt.group(1)), level)

    walk_item(int(first.group(1)), 1)
    return result


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    pdf_path, out_path = Path(sys.argv[1]), Path(sys.argv[2])
    data = pdf_path.read_bytes()
    objs = objects(data)
    pages = page_order(objs)
    entries = outline(objs, pages)
    out_path.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"pages={len(pages)} entries={len(entries)} -> {out_path}")
    for item in entries[:12]:
        print(f"  {'  ' * (item['level'] - 1)}{item['title']}  ....  {item['page']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
