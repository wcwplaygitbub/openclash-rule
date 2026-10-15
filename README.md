# openclash-rule

`clash-all-other.ini` 是给 subconverter（sub-web、OpenClash、路由器订阅转换）用的外部配置。
原来它引用的规则集全部走 `gh-proxy.com` 代理 GitHub，代理失效或网络抖动时规则集就取不到。

现在**所有规则集都已镜像到本仓库**，ini 里的链接也全部指向本仓库，不再依赖任何第三方加速代理。

## 怎么用

在 sub-web 或路由器的「远程配置 / 自定义配置文件」里填下面两个地址之一：

**A. 直连 GitHub（默认）**

```
https://raw.githubusercontent.com/wcwplaygitbub/openclash-rule/refs/heads/master/clash-all-other.ini
```

**B. 走 jsDelivr（国内更稳，整条链路都在 jsDelivr）**

```
https://cdn.jsdelivr.net/gh/wcwplaygitbub/openclash-rule@master/clash-all-other.jsdelivr.ini
```

注意三点：

- 两个 ini 内容完全一样，只有 39 条规则集链接的前缀不同（A 用 `raw.githubusercontent.com`，B 用 `cdn.jsdelivr.net`）。
- 本仓库必须保持 **public**。subconverter 是匿名 HTTP 客户端，私有仓库会返回 401，规则集会全部取不到。
- jsDelivr 有缓存（改动后最长约 12 小时才生效）；要立刻生效就用 A，或去 jsDelivr 手动刷新。

## 目录结构

| 路径 | 说明 |
| --- | --- |
| `clash-all-other.ini` | 主配置，39 条 `ruleset=` 指向本仓库的 GitHub 直链 |
| `clash-all-other.jsdelivr.ini` | 同上，链接前缀换成 jsDelivr |
| `list/` | 39 个规则集文件，内容与上游**逐字节一致**（已用 sha256 校验） |
| `list/sources.tsv` | 来源清单：`本地路径 <TAB> 上游地址` |
| `scripts/sync-lists.sh` | 从上游更新规则集 |
| `scripts/gen-ini.py` | 切换 ini 的引用前缀 |

## 更新规则集

```bash
bash scripts/sync-lists.sh          # 内容有变化才落盘
JOBS=8 bash scripts/sync-lists.sh   # 调并发（默认 6）
FORCE=1 bash scripts/sync-lists.sh  # 强制重新下载
```

脚本直连 `raw.githubusercontent.com`，失败时自动回退到 `gh-proxy.com`（可用 `GH_MIRROR` 换镜像）。
上游内容原样镜像，不做任何改写。

## 更换引用方式

ini 里所有链接共用一个前缀，记在文件头部的 `; repo-base: …` 行，用脚本替换即可：

```bash
# 直连 GitHub（写回 clash-all-other.ini）
python3 scripts/gen-ini.py --preset github --repo wcwplaygitbub/openclash-rule@master

# jsDelivr（生成 clash-all-other.jsdelivr.ini）
python3 scripts/gen-ini.py --preset jsdelivr --repo wcwplaygitbub/openclash-rule@master \
    --out clash-all-other.jsdelivr.ini

# 任意前缀，例如自建 HTTP 服务（结尾要带 /）
python3 scripts/gen-ini.py --base https://example.com/openclash-rule/
```

脚本会先校验每个被引用的 `list/` 文件在本地存在，校验不通过就不写文件。

### 如果是本机跑 subconverter

可以用 `file:///` 绝对路径，完全不联网（生成的 `clash-all-other.local.ini` 是本机专用的，默认不进仓库）：

```bash
python3 scripts/gen-ini.py --preset file                  # 指向当前仓库目录
python3 scripts/gen-ini.py --preset file --base /config/  # 例如 Docker 里的挂载点
```

> 原理：subconverter 的 `ruleset` 最终交给 libcurl 读取，libcurl 没有限制协议，所以 `file:///绝对路径` 可用；
> 但普通的相对路径（如 `list/x.list`）不行 —— curl 需要协议头。这种方式也只有同机的 subconverter 能读到。

## 规则集来源

见 [`list/sources.tsv`](list/sources.tsv)，全部来自上游公开仓库：

- [liandu2024/clash](https://github.com/liandu2024/clash)
- [blackmatrix7/ios_rule_script](https://github.com/blackmatrix7/ios_rule_script)
- [v2fly/domain-list-community](https://github.com/v2fly/domain-list-community)

本仓库只做镜像，未修改任何内容；规则版权与更新归各上游仓库所有。
