#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 index.html 打成单文件版（图片内联为 data URI），并压成 无人机官网.zip。

用法:
    python tools/build_singlefile.py
"""
import base64
import re
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MIME = {
    ".webp": "image/webp",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".svg": "image/svg+xml",
}


def data_uri(p: Path) -> str:
    mime = MIME.get(p.suffix.lower(), "application/octet-stream")
    return "data:%s;base64,%s" % (mime, base64.b64encode(p.read_bytes()).decode("ascii"))


def main() -> int:
    src_path = ROOT / "index.html"
    html = src_path.read_text(encoding="utf-8")
    original = len(html.encode("utf-8"))

    # 1. 内联后 preload 无意义，去掉
    html = re.sub(r'\n<link rel="preload"[^>]*>', "", html)

    # 2. srcset / imagesrcset：逐候选项替换
    def fix_set(m):
        attr, val = m.group(1), m.group(2)
        parts = []
        for item in val.split(","):
            item = item.strip()
            if not item:
                continue
            bits = item.split()
            ref = bits[0]
            if ref.startswith(("data:", "http://", "https://", "//")):
                parts.append(item)
                continue
            p = ROOT / ref.split("?")[0]
            if not p.is_file():
                parts.append(item)
                continue
            parts.append(" ".join([data_uri(p)] + bits[1:]))
        return '%s="%s"' % (attr, ", ".join(parts))

    html = re.sub(r'\b(srcset|imagesrcset)="([^"]*)"', fix_set, html)

    # 3. src / href 指向本地图片的换成 data URI
    def fix_one(m):
        attr, val = m.group(1), m.group(2)
        v = val.strip()
        if v.startswith(("data:", "http://", "https://", "//", "#", "mailto:", "tel:")):
            return m.group(0)
        p = ROOT / v.split("?")[0].split("#")[0]
        if p.is_file() and p.suffix.lower() in MIME:
            return '%s="%s"' % (attr, data_uri(p))
        return m.group(0)

    html = re.sub(r'\b(src|href)="([^"]*)"', fix_one, html)

    # 4. 单文件包里没有 quadcopter.html，跳转改回首页，避免包内死链
    html = html.replace('href="quadcopter.html"', 'href="./"')

    m = re.search(r"v(\d+\.\d+\.\d+)", html)
    ver = "v" + m.group(1) if m else "unknown"

    # 中间产物写到系统临时目录，仓库根目录只留 zip，避免 1.8 MB 中间文件被误提交
    out = Path(tempfile.gettempdir()) / ("无人机官网-单文件版-%s.html" % ver)
    out.write_text(html, encoding="utf-8")

    zp = ROOT / "无人机官网.zip"
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.write(out, arcname=out.name)

    print("版本      :", ver)
    print("源文件    : %d B" % original)
    print("单文件版  : %s  %d B" % (out.name, out.stat().st_size))
    print("zip       : %s  %d B" % (zp.name, zp.stat().st_size))

    left = [
        u
        for u in re.findall(r'(?:src|href)="(?!data:|https?:|//|#|mailto:|tel:)([^"]+)"', html)
        if u not in ("./", "index.html")
    ]
    print("剩余外部引用:", left[:10] if left else "无")
    return 0


if __name__ == "__main__":
    sys.exit(main())
