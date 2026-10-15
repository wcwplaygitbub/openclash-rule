#!/usr/bin/env bash
# 同步上游规则集到本仓库 list/ 目录（清单见 list/sources.tsv）
#
# 用法：
#   bash scripts/sync-lists.sh          # 增量同步：内容有变化才落盘
#   JOBS=8 bash scripts/sync-lists.sh   # 调整并发数（默认 6）
#   FORCE=1 bash scripts/sync-lists.sh  # 忽略本地内容，强制重新下载
#
# 直连 raw.githubusercontent.com 失败时会自动回退到镜像（默认 gh-proxy.com，
# 可用 GH_MIRROR 覆盖）。上游内容原样镜像，不做任何改写。

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST="$ROOT/list/sources.tsv"
MIRROR="${GH_MIRROR:-https://gh-proxy.com/}"
JOBS="${JOBS:-6}"
FORCE="${FORCE:-0}"

if [ ! -f "$MANIFEST" ]; then
  echo "找不到清单文件：$MANIFEST" >&2
  exit 1
fi

fetch_one() {
  local rel="$1" url="$2" dest tmp
  dest="$ROOT/$rel"
  mkdir -p "$(dirname "$dest")"
  tmp="$(mktemp)"

  if curl -fsSL --connect-timeout 10 --max-time 120 "$url" -o "$tmp" && [ -s "$tmp" ]; then
    :
  elif curl -fsSL --connect-timeout 10 --max-time 120 "${MIRROR}${url}" -o "$tmp" && [ -s "$tmp" ]; then
    echo "  [镜像] $rel"
  else
    echo "  [失败] $rel  <- $url" >&2
    rm -f "$tmp"
    return 1
  fi

  if [ "$FORCE" != "1" ] && [ -f "$dest" ] && cmp -s "$tmp" "$dest"; then
    echo "  [不变] $rel"
  else
    mv "$tmp" "$dest"
    printf '  [更新] %-38s %9d 字节\n' "$rel" "$(wc -c < "$dest" | tr -d ' ')"
  fi
}
export -f fetch_one
export ROOT MIRROR FORCE

total="$(grep -c -v '^#' "$MANIFEST")"
echo "同步 $total 个规则集 -> $ROOT/list"

fail=0
grep -v '^#' "$MANIFEST" | grep -v '^[[:space:]]*$' \
  | xargs -P "$JOBS" -n 2 bash -c 'fetch_one "$0" "$1"' || fail=1

if [ "$fail" != "0" ]; then
  echo "有规则集同步失败，请检查网络后重试。" >&2
  exit 1
fi

echo "完成。可用 git status 查看变更。"
