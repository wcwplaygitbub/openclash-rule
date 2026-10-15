#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按不同的引用方式重新生成 ini 里的规则集链接。

ini 里所有规则集链接共用一个前缀，记在文件头部的 `; repo-base: <前缀>` 行。
本脚本只替换这个前缀，并校验每个被引用的 list/ 文件在本地确实存在。

用法示例：
    # 1) 直连 GitHub（默认原地改写 --in 指定的文件，即 clash-all-other.ini）
    python3 scripts/gen-ini.py --preset github --repo wcwplaygitbub/openclash-rule@master

    # 2) 另存一份 jsDelivr 版（国内加速，主配置保持不动）
    python3 scripts/gen-ini.py --preset jsdelivr --repo wcwplaygitbub/openclash-rule@master \
        --out clash-all-other.jsdelivr.ini

    # 3) subconverter 与本仓库同机：file:/// 绝对路径，完全离线
    #    默认另存为 clash-all-other.local.ini（本机专用，别提交到公开仓库）
    python3 scripts/gen-ini.py --preset file
    python3 scripts/gen-ini.py --preset file --base /config/   # 例如 Docker 挂载点

    # 4) 任意地址（自建 HTTP 服务等，结尾带 /）
    python3 scripts/gen-ini.py --base https://example.com/clash-rule/

默认输出：原地改写 --in 指定的文件；只有 file 预设默认另存为 clash-all-other.local.ini
（避免把本机绝对路径写进主配置）。需要别的输出路径就加 --out。
"""

import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_IN = os.path.join(ROOT, "clash-all-other.ini")
GITEE_BASE = "https://gitee.com/wcw1993/clash-rule/raw/master/"

BASE_RE = re.compile(r"^;\s*repo-base:\s*(\S+)\s*$", re.M)
URL_LINE_RE = re.compile(r"^\s*;?\s*ruleset=[^,]+,\s*(\S+)\s*$")


def read_base(text):
    """从文件头部取出当前的 repo-base 前缀。"""
    m = BASE_RE.search(text)
    if not m:
        sys.exit("错误：%s 里找不到 `; repo-base: <前缀>` 行，无法确定要替换的前缀。" % DEFAULT_IN)
    return m.group(1)


def collect_urls(text):
    """取出所有 ruleset 行里的链接（含被注释掉的行），跳过 []FINAL 这类特殊值。"""
    urls = []
    for line in text.split("\n"):
        m = URL_LINE_RE.match(line)
        if m and not m.group(1).startswith("[]"):
            urls.append(m.group(1))
    return urls


def check_files(urls, new_base):
    """校验每个链接指向的 list/ 文件在本地存在，避免推送出去才发现漏文件。"""
    bad = []
    for url in urls:
        if not url.startswith(new_base):
            bad.append(("前缀不一致", url))
            continue
        rel = url[len(new_base):]
        if not os.path.isfile(os.path.join(ROOT, rel)):
            bad.append(("本地文件不存在", rel))
    return bad


def main():
    ap = argparse.ArgumentParser(description="重新生成 ini 的规则集引用前缀")
    ap.add_argument("--preset", choices=["gitee", "github", "jsdelivr", "file"], help="预设的引用方式")
    ap.add_argument("--repo", help="GitHub 仓库，格式 用户名/仓库名[@分支]，github 和 jsdelivr 预设需要")
    ap.add_argument("--base", help="自定义前缀（以 / 结尾）；file 预设下是本地绝对路径")
    ap.add_argument("--in", dest="infile", default=DEFAULT_IN, help="输入 ini（默认 clash-all-other.ini）")
    ap.add_argument("--out", help="输出文件（默认原地改写输入文件；file 预设默认另存为 .local.ini）")
    args = ap.parse_args()

    if not args.preset and not args.base:
        ap.error("至少要给 --preset 或 --base")

    # ---- 计算新的前缀 ----
    if args.base:
        base = args.base
        if args.preset == "file":
            path = os.path.abspath(os.path.join(ROOT, base)) if not os.path.isabs(base) else base
            base = "file://" + path.rstrip("/") + "/"
        elif not base.startswith(("http://", "https://", "file://")):
            ap.error("--base 需要是 http(s)、file:// 或配合 --preset file 的本地路径")
        if not base.endswith("/"):
            base += "/"
    elif args.preset == "gitee":
        base = GITEE_BASE
    elif args.preset == "file":
        base = "file://" + ROOT.rstrip("/") + "/"
    else:  # github / jsdelivr
        if not args.repo:
            ap.error("--preset %s 需要配合 --repo 用户名/仓库名[@分支]" % args.preset)
        repo = args.repo
        branch = "main"
        if "@" in repo:
            repo, branch = repo.split("@", 1)
        repo = repo.strip("/")
        if args.preset == "github":
            base = "https://raw.githubusercontent.com/%s/refs/heads/%s/" % (repo, branch)
        else:
            base = "https://cdn.jsdelivr.net/gh/%s@%s/" % (repo, branch)

    raw = open(args.infile, encoding="utf-8", newline="").read()
    # 原文件是 CRLF，内部统一按 LF 处理，写回时还原，避免出现混合行尾
    nl = "\r\n" if "\r\n" in raw else "\n"
    text = raw.replace("\r\n", "\n")
    old_base = read_base(text)
    urls = collect_urls(text)
    if not urls:
        sys.exit("错误：%s 里没有解析到任何 ruleset 链接。" % args.infile)

    # ---- 替换前缀 ----
    new_text = text.replace(old_base, base)
    new_text = BASE_RE.sub("; repo-base: " + base, new_text, count=1)

    # ---- 校验 ----
    bad = check_files(collect_urls(new_text), base)
    if bad:
        print("以下链接校验未通过，已中止（未写文件）：", file=sys.stderr)
        for reason, item in bad:
            print("  - %s: %s" % (reason, item), file=sys.stderr)
        sys.exit(1)

    out = args.out
    if not out:
        if args.preset == "file":
            out = os.path.join(ROOT, "clash-all-other.local.ini")
        else:
            out = args.infile

    with open(out, "w", encoding="utf-8", newline="") as f:
        f.write(new_text.replace("\n", nl))

    shown = os.path.relpath(out, ROOT)
    print("已生成: %s" % (shown if not shown.startswith("..") else out))
    print("  引用前缀: %s" % base)
    print("  规则集数量: %d 个（本地文件全部存在）" % len(urls))
    if base.startswith("file://"):
        print("  提醒: file:// 只有运行在本机的 subconverter 能读到，远程后端会全部失败。")
    elif "gitee.com" in base:
        print("  提醒: 远程后端必须能匿名访问该地址；仓库为私有时请先设为公开。")


if __name__ == "__main__":
    main()
