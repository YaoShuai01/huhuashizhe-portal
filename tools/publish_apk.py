#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 APK 发布到对象存储，并把站点下载源切到 HTTPS。

用法（阿里云 OSS，纯标准库 V1 签名）:
    python tools/publish_apk.py --provider oss \\
      --endpoint https://oss-cn-hangzhou.aliyuncs.com --bucket my-bucket \\
      --ak LTAI... --sk ... --key-prefix app \\
      --public-base https://my-bucket.oss-cn-hangzhou.aliyuncs.com/app \\
      --apk ../apk_dl/huhuashizhe_v3.10.14.apk

只出预签名直链，不落任何文件:
    python tools/publish_apk.py --provider oss --presign --expires 3600 ...

Cloudflare R2 / S3 兼容（只打印等价命令，不代传）:
    python tools/publish_apk.py --provider r2 --bucket b \\
      --endpoint https://<acct>.r2.cloudflarestorage.com --apk <path>

默认上传后自动调用 tools/switch_apk_host.py --apply 切换站内链接；
加 --no-switch 可只看上传结果。
"""

import argparse
import base64
import hashlib
import hmac
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
DEFAULT_APK = ROOT.parent / "apk_dl" / "huhuashizhe_v3.10.13.apk"


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(str(path), "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def md5_b64(path: Path) -> str:
    h = hashlib.md5()
    with open(str(path), "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return base64.b64encode(h.digest()).decode("ascii")


def http_date() -> str:
    return time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())


def oss_sign(sk: str, string_to_sign: str) -> str:
    raw = hmac.new(sk.encode("utf-8"), string_to_sign.encode("utf-8"), hashlib.sha1).digest()
    return base64.b64encode(raw).decode("ascii")


def oss_put(endpoint: str, bucket: str, ak: str, sk: str, key: str, path: Path,
            content_type: str, public_read: bool) -> int:
    url = "%s/%s" % (endpoint.rstrip("/"), urllib.parse.quote(key))
    date = http_date()
    cmd5 = md5_b64(path)
    size = path.stat().st_size

    oss_headers = {}
    if public_read:
        oss_headers["x-oss-object-acl"] = "public-read"
    canon = "".join("%s:%s\n" % (k.lower(), v) for k, v in sorted(oss_headers.items()))
    resource = "/%s/%s" % (bucket, key)
    sts = "PUT\n%s\n%s\n%s\n%s%s" % (cmd5, content_type, date, canon, resource)

    headers = {
        "Date": date,
        "Content-Type": content_type,
        "Content-MD5": cmd5,
        "Content-Length": str(size),
        "Authorization": "OSS %s:%s" % (ak, oss_sign(sk, sts)),
    }
    headers.update(oss_headers)

    print("[oss] PUT %s  (%d B)" % (url, size))
    with open(str(path), "rb") as fh:
        req = urllib.request.Request(url, data=fh, method="PUT", headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=1800) as r:
                print("[oss] HTTP %s" % r.status)
                return r.status
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:600]
            print("[FAIL] HTTP %s\n%s" % (e.code, body))
            return e.code


def oss_presign_put(endpoint: str, bucket: str, ak: str, sk: str, key: str,
                    expires: int, content_type: str) -> str:
    expire_ts = int(time.time()) + expires
    resource = "/%s/%s" % (bucket, key)
    sts = "PUT\n\n%s\n%d\n%s" % (content_type, expire_ts, resource)
    sig = oss_sign(sk, sts)
    query = urllib.parse.urlencode({
        "OSSAccessKeyId": ak,
        "Expires": str(expire_ts),
        "Signature": sig,
    })
    return "%s/%s?%s" % (endpoint.rstrip("/"), urllib.parse.quote(key), query)


def head_status(url: str) -> tuple:
    req = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, int(r.headers.get("Content-Length") or 0)
    except urllib.error.HTTPError as e:
        return e.code, 0
    except Exception as e:
        print("[warn] HEAD 失败: %s" % e)
        return -1, 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", choices=["oss", "r2", "s3"], default="oss")
    ap.add_argument("--endpoint", help="对象存储访问端点")
    ap.add_argument("--bucket", help="桶名")
    ap.add_argument("--ak", help="AccessKey（OSS/用 --ak）或 AWS_ACCESS_KEY_ID")
    ap.add_argument("--sk", help="SecretKey")
    ap.add_argument("--apk", default=str(DEFAULT_APK), help="本地 APK 路径")
    ap.add_argument("--key-prefix", default="app", help="对象键前缀，默认 app")
    ap.add_argument("--public-base", help="切站前缀，例如 https://桶.oss-cn-hangzhou.aliyuncs.com/app")
    ap.add_argument("--content-type", default="application/vnd.android.package-archive")
    ap.add_argument("--presign", action="store_true", help="只输出预签名 PUT 直链")
    ap.add_argument("--expires", type=int, default=3600)
    ap.add_argument("--no-public", action="store_true", help="不设置 public-read ACL")
    ap.add_argument("--no-switch", action="store_true", help="上传后不自动切站内链接")
    args = ap.parse_args()

    apk = Path(args.apk).expanduser().resolve()
    if not apk.is_file():
        print("[FAIL] APK 不存在: %s" % apk)
        return 1
    key = "%s/%s" % (args.key_prefix.strip("/"), apk.name)
    size = apk.stat().st_size
    digest = sha256_of(apk)
    print("[apk] %s\n       %d B (%.2f MB / %.2f MiB)\n       sha256=%s"
          % (apk.name, size, size / 1e6, size / 1048576, digest))

    if args.provider in ("r2", "s3"):
        end = args.endpoint or "https://<ACCOUNT_ID>.r2.cloudflarestorage.com"
        bucket = args.bucket or "<BUCKET>"
        print("\n[S3 兼容] 请用官方工具上传，等效命令：")
        if args.provider == "r2":
            print("  npx wrangler r2 object put %s/%s --file \"%s\" --content-type %s"
                  % (bucket, key, apk, args.content_type))
        print("  aws s3 cp \"%s\" s3://%s/%s --endpoint-url %s --content-type %s"
              % (apk, bucket, key, end, args.content_type))
        print("\n上传完成后用 --public-base 指向你的公网域名再跑一次本脚本的 --no-switch 校验，")
        print("或直接:  python tools/switch_apk_host.py --base <公网前缀> --apply --apk \"%s\" --qr" % apk)
        return 0

    for name in ("endpoint", "bucket", "ak", "sk"):
        if not getattr(args, name):
            print("[FAIL] --provider oss 需要 --%s" % name)
            return 1

    if args.presign:
        url = oss_presign_put(args.endpoint, args.bucket, args.ak, args.sk,
                              key, args.expires, args.content_type)
        print("\n[presign] %d 秒内有效，PUT 上传：" % args.expires)
        print("  curl -X PUT -T \"%s\" -H 'Content-Type: %s' '%s'"
              % (apk, args.content_type, url))
        return 0

    code = oss_put(args.endpoint, args.bucket, args.ak, args.sk, key, apk,
                   args.content_type, not args.no_public)
    if code not in (200, 201):
        return 1

    base = (args.public_base or "%s/%s" % (args.endpoint.rstrip("/"), args.key_prefix)).rstrip("/")
    public_url = "%s/%s" % (base, apk.name)
    hcode, hlen = head_status(public_url)
    print("[verify] %s -> HTTP %s, Content-Length %s" % (public_url, hcode, hlen))
    if hcode != 200:
        print("[warn] 公网读不到，检查桶 ACL / CDN 绑定 / public-base 是否正确")
    elif hlen and hlen != size:
        print("[warn] 公网 Content-Length %s 与本地 %s 不一致" % (hlen, size))

    if args.no_switch:
        print("\n[skip switch] 未改站内链接；手动执行：")
        print("  python tools/switch_apk_host.py --base %s --apply --apk \"%s\" --qr" % (base, apk))
        return 0

    cmd = [sys.executable, str(ROOT / "tools" / "switch_apk_host.py"),
           "--base", base, "--apply", "--apk", str(apk), "--qr"]
    print("\n=== 切站内下载源 ===")
    print("  " + " ".join(cmd))
    return subprocess.run(cmd).returncode


if __name__ == "__main__":
    sys.exit(main())
