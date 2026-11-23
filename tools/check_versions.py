#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""发版前校验：版本号唯一性 / APK 文件名一致性 / 本地资源存在性 / 校验值公示。

用法:
    python tools/check_versions.py
    python tools/check_versions.py --apk ../apk_dl/huhuashizhe_v3.10.12.apk

退出码 0 = 全部断言通过；1 = 存在失败项。
"""
import argparse
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES = [ROOT / "index.html", ROOT / "quadcopter.html"]
VER = re.compile(r"v(\d+\.\d+\.\d+)")
APK = re.compile(r"huhuashizhe_v(\d+\.\d+\.\d+)\.apk")
ATTR = re.compile(r'(?:href|src|imagesrcset|srcset)\s*=\s*"([^"]+)"')
SHA = re.compile(r"\b[0-9a-f]{64}\b")
SKIP = ("#", "http://", "https://", "//", "data:", "mailto:", "tel:", "javascript:")

errors = []
warnings = []


def check(cond, msg):
    if not cond:
        errors.append(msg)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apk", help="本版 APK 路径，用于回算 sha256 与字节数")
    args = ap.parse_args()

    index_path = ROOT / "index.html"
    if not index_path.exists():
        print("[FAIL] 缺少 index.html")
        return 1
    index = index_path.read_text(encoding="utf-8")

    vers = set(VER.findall(index))
    check(len(vers) == 1, "index.html 版本号不唯一: %s" % sorted(vers))
    page_ver = next(iter(vers)) if len(vers) == 1 else None

    apks = set(APK.findall(index))
    check(len(apks) == 1, "index.html APK 文件名版本不唯一: %s" % sorted(apks))
    if page_ver and apks:
        check(apks == {page_ver}, "APK 文件名版本 %s 与页面版本 v%s 不一致" % (sorted(apks), page_ver))

    plain = re.findall(r'href="http://[^"]+\.apk"', index)
    if plain:
        warnings.append("%d 个 APK 下载链接仍为明文 http://" % len(plain))

    for page in PAGES:
        if not page.exists():
            errors.append("缺少页面 %s" % page.name)
            continue
        text = page.read_text(encoding="utf-8")
        for raw in ATTR.findall(text):
            if raw.strip().startswith(SKIP):
                # data: / http(s): / // / mailto: 等整值跳过，
                # 否则 srcset 里的逗号会把 data URI 切成半截当成本地路径
                continue
            for part in raw.split(","):
                ref = part.strip().split(" ")[0]
                if not ref or ref.startswith(SKIP):
                    continue
                target = (page.parent / ref.split("?")[0].split("#")[0]).resolve()
                check(target.exists(), "%s: 引用不存在的本地文件 %s" % (page.name, ref))

    check("sha256" in index.lower(), "index.html 未公示 sha256 校验值")
    digests = set(SHA.findall(index))
    check(len(digests) == 1, "公示的 sha256 数量异常: %d" % len(digests))

    if args.apk:
        apk = Path(args.apk).expanduser().resolve()
        check(apk.exists(), "APK 不存在: %s" % apk)
        if apk.exists():
            h = hashlib.sha256()
            with apk.open("rb") as fh:
                for chunk in iter(lambda: fh.read(1 << 20), b""):
                    h.update(chunk)
            actual = h.hexdigest()
            check(actual in index, "APK 实际 sha256 %s 未出现在页面中" % actual)
            print("[apk] %s  %d B  sha256=%s" % (apk.name, apk.stat().st_size, actual))
            m = re.search(r'fileSize"\s*:\s*"([^"]+)"', index)
            if m:
                print("[page] fileSize = %s" % m.group(1))

    for w in warnings:
        print("[warn] %s" % w)
    for e in errors:
        print("[FAIL] %s" % e)
    if errors:
        print("\n%d 项断言失败" % len(errors))
        return 1
    print("\n全部断言通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
