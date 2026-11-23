#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把全站 APK 下载源从明文 HTTP 迁到 HTTPS 对象存储，并同步 JSON-LD 与二维码。

用法:
    # 只演练，不落盘
    python tools/switch_apk_host.py --base https://bucket.oss-cn-hangzhou.aliyuncs.com/app --dry-run

    # 真正改，并自动重建单文件包 + 跑发布校验
    python tools/switch_apk_host.py --base https://bucket.oss-cn-hangzhou.aliyuncs.com/app --apply

参数:
    --base   新的 HTTPS 目录前缀，末尾不要带斜杠；APK 文件名保持不变
    --apply  真正写入（默认 dry-run）
    --apk    上一版 APK 路径，用于 --apply 后自动跑 check_versions
    --qr     重新生成二维码图片（需要 qrcode + pillow）
    --keep   旧版本保留数量提示（仅打印策略建议，不删远端文件）

退出码 0 = 成功；1 = 有失败项。
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES = ["index.html", "quadcopter.html", "404.html"]
OLD_HOST = re.compile(r"http://121\.199\.75\.235:8080/app")
VER = re.compile(r"v(\d+\.\d+\.\d+)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="新 HTTPS 目录前缀，例如 https://cdn.example.com/app")
    ap.add_argument("--apply", action="store_true", help="真正写入文件")
    ap.add_argument("--dry-run", action="store_true", help="只演练不落盘（默认行为，显式写出更清晰）")
    ap.add_argument("--apk", help="本版 APK 路径，用于改完自动校验")
    ap.add_argument("--qr", action="store_true", help="重新生成 assets/img/download-qr.png")
    ap.add_argument("--keep", type=int, default=3, help="建议保留的旧版本数量")
    args = ap.parse_args()
    if args.apply and args.dry_run:
        print("[FAIL] 请勿同时使用 --apply 与 --dry-run")
        return 1

    base = args.base.rstrip("/")
    if not base.startswith("https://"):
        print("[FAIL] --base 必须是 https:// 开头，否则迁移没有意义")
        return 1

    index = (ROOT / "index.html").read_text(encoding="utf-8")
    vers = set(VER.findall(index))
    if len(vers) != 1:
        print("[FAIL] 版本号不唯一，先跑 tools/check_versions.py: %s" % sorted(vers))
        return 1
    ver = "v" + next(iter(vers))
    apk_name = "huhuashizhe_%s.apk" % ver
    new_url = "%s/%s" % (base, apk_name)
    print("版本     : %s" % ver)
    print("新下载址 : %s" % new_url)

    changed = 0
    for name in PAGES:
        p = ROOT / name
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8")
        hits = len(OLD_HOST.findall(text))
        if not hits:
            print("  %-16s 无需改动" % name)
            continue
        text = OLD_HOST.sub(base, text)
        changed += hits
        print("  %-16s 替换 %d 处" % (name, hits))
        if args.apply:
            p.write_text(text, encoding="utf-8")

    if not changed:
        print("[warn] 没有找到旧主机引用，可能已经迁移过")

    if args.qr:
        try:
            import qrcode  # type: ignore
        except ImportError:
            print("[warn] 未安装 qrcode，跳过二维码重生成（pip install qrcode pillow）")
        else:
            out = ROOT / "assets" / "img" / "download-qr.png"
            qr = qrcode.QRCode(box_size=10, border=2)
            qr.add_data(new_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
            if img.size != (444, 444):
                img = img.resize((444, 444))
            img.save(out)
            print("  二维码已重生成: %s  %s" % (out.name, img.size))

    print("\n旧版本保留策略建议：远端至少保留最近 %d 个版本，避免收藏夹/缓存链接落到 404" % args.keep)
    for i in range(1, args.keep + 1):
        print("  建议保留: %s/huhuashizhe_v3.10.%d.apk" % (base, 12 - i))

    if not args.apply:
        print("\n[dry-run] 未写入任何文件。确认无误后加 --apply 重跑。")
        return 0

    print("\n=== 重建单文件包 ===")
    subprocess.run([sys.executable, str(ROOT / "tools" / "build_singlefile.py")], check=False)
    if args.apk:
        print("\n=== 发布校验 ===")
        r = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "check_versions.py"), "--apk", args.apk],
            check=False,
        )
        return r.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
