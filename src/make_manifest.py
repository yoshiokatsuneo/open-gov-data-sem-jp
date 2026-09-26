# -*- coding: utf-8 -*-
"""生データ1件ごとの入手元・URL・サイズ・SHA256 を一覧にする。

出力: data/MANIFEST.md（人が読む）/ data/manifest.csv（機械が読む）

「このファイルはどこから、どうやって取ったのか」を1行ずつ辿れるようにするためのもの。
SHA256 を載せてあるので、各自がダウンロードしたものと突き合わせられる。
上流が改訂されて一致しなくなった場合は src/check_revisions.py で差分が出せる。
"""
import hashlib

import pandas as pd

import paths
from estat_fetch import BASE as ESTAT_DL, FILES as PREF_FILES
from fetch_data import API as WB_API, SPECS as WB_SPECS
from muni_fetch import FILES as MUNI_FILES

# e-Stat のデータセットページ（ここの各 EXCEL リンクから statInfId が取れる）
PREF_PAGE = ("https://www.e-stat.go.jp/stat-search/files?page=1&layout=datalist"
             "&toukei=00200502&tstat=000001213101&cycle=0&tclass1=000001213102&tclass2val=0")
MUNI_PAGE = ("https://www.e-stat.go.jp/stat-search/files?page=1&layout=datalist"
             "&toukei=00200502&tstat=000001244297&cycle=0&tclass1=000001244298&tclass2val=0")
WB_WDI_PAGE = "https://data.worldbank.org/indicator/{}"
WB_WGI_PAGE = "https://databank.worldbank.org/source/worldwide-governance-indicators"

WB_COLS = {c: (ind, t, y0, y1, src) for c, ind, t, y0, y1, src in WB_SPECS}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def estat_rows():
    rows = []
    for kind, files, prefix, folder, page in (
            ("estat_pref", PREF_FILES, "ssds", paths.ESTAT_PREF_XLS, PREF_PAGE),
            ("estat_muni", MUNI_FILES, "muni", paths.ESTAT_MUNI_XLS, MUNI_PAGE)):
        for label, sid in files.items():
            no = label.split("_")[0]
            f = folder / f"{prefix}_{no}.xls"
            rows.append(dict(
                source=kind, name=label.split("_", 1)[1], key=sid,
                local=str(f.relative_to(paths.ROOT)),
                url=ESTAT_DL.format(sid), page=page,
                bytes=f.stat().st_size if f.exists() else 0,
                sha256=sha256(f) if f.exists() else ""))
    return rows


def worldbank_rows():
    rows = []
    for col, (ind, target, y0, y1, src) in WB_COLS.items():
        page = WB_WGI_PAGE if src == 3 else WB_WDI_PAGE.format(ind)
        url = (f"{WB_API}/country/all/indicator/{ind}"
               f"?format=json&date={y0}:{y1}&per_page=2000&source={src}")
        rows.append(dict(source="worldbank", name=col, key=ind,
                         local="data/raw/wb_raw.csv", url=url, page=page,
                         bytes="", sha256="",
                         note=f"目標年 {target} / 窓 {y0}-{y1} / source={src}"))
    f = paths.raw("wb_raw.csv")
    rows.append(dict(source="worldbank", name="（結合後のファイル）", key="",
                     local="data/raw/wb_raw.csv", url="", page="",
                     bytes=f.stat().st_size, sha256=sha256(f),
                     note=f"src/fetch_data.py が上記 {len(WB_COLS)} 指標をまとめたもの"))
    return rows


def md_table(rows, cols, headers):
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join(["---"] * len(headers)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(r.get(c, "")) for c in cols) + " |")
    return "\n".join(out)


def main():
    rows = estat_rows() + worldbank_rows()
    df = pd.DataFrame(rows)
    df.to_csv(paths.ROOT / "data" / "manifest.csv", index=False)

    pref = [r for r in rows if r["source"] == "estat_pref"]
    muni = [r for r in rows if r["source"] == "estat_muni"]
    wb = [r for r in rows if r["source"] == "worldbank" and r["key"]]
    wbf = [r for r in rows if r["source"] == "worldbank" and not r["key"]][0]

    def estat_md(rs):
        out = ["| 分野 | statInfId | ローカル | サイズ | 直接ダウンロードURL | SHA256（先頭16桁） |",
               "|---|---|---|---|---|---|"]
        for r in rs:
            out.append(f"| {r['name']} | `{r['key']}` | `{r['local']}` | "
                       f"{r['bytes']:,} B | [ダウンロード]({r['url']}) | `{r['sha256'][:16]}` |")
        return "\n".join(out)

    wb_md = ["| 列名 | 指標コード | source | 取得条件 | 指標ページ | API URL |", "|---|---|---|---|---|---|"]
    for r in wb:
        wb_md.append(f"| `{r['name']}` | `{r['key']}` | {r['note'].split('source=')[1]} | "
                     f"{r['note'].split(' / source')[0]} | [ページ]({r['page']}) | [API]({r['url']}) |")

    text = f"""# 生データ マニフェスト

`data/raw/` に入っている生データ1件ごとの入手元。**すべてAPIキー・ログイン不要**で取得できる。
機械可読版は [manifest.csv](manifest.csv)。

このファイルは `src/make_manifest.py` が生成している。手で編集しない。

上流が改訂されて SHA256 が合わなくなることがある（実際に World Bank の WGI で起きた）。
差分を確認するには:

```bash
.venv/bin/python src/check_revisions.py
```

---

## 1. e-Stat 社会生活統計指標－都道府県の指標－2024

**データセットページ:** {PREF_PAGE}

このページの各 EXCEL リンクの `statInfId` が下表の値。取得コードは
[src/estat_fetch.py](../src/estat_fetch.py)。分析に使う8分野だけ落としている
（全14分野あり、自然環境・文化・スポーツ・居住・安全・生活時間は未取得）。

{estat_md(pref)}

## 2. e-Stat 統計でみる市区町村のすがた2026（基礎データ）

**データセットページ:** {MUNI_PAGE}

取得コードは [src/muni_fetch.py](../src/muni_fetch.py)。全10分野を取得している。

{estat_md(muni)}

## 3. World Bank Open Data

1指標ずつ公開REST APIを叩き、[src/fetch_data.py](../src/fetch_data.py) が1枚のCSVに結合する。

- 結合後のファイル: `{wbf['local']}` / {wbf['bytes']:,} B / SHA256 `{wbf['sha256'][:16]}`
- WGI（source=3）の一覧: `{WB_API}/source/3/indicator?format=json&per_page=100`
- WGI は指標コードに `GOV_WGI_` の接頭辞が必要。素の `RL.EST` では取れない。

{chr(10).join(wb_md)}

---

## ダウンロードの実際の手順

### e-Stat（キー不要）

```bash
curl -L -A "Mozilla/5.0" -o out.xls \\
  "https://www.e-stat.go.jp/stat-search/file-download?statInfId=<12桁ID>&fileKind=0"
```

`fileKind` は 0 が Excel、2 が PDF。**検索ページは JavaScript で描画されるので curl では
中身が取れない。**新しい `statInfId` を探すときはブラウザでデータセットページを開き、
開発者コンソールで次を実行する。

```js
[...document.querySelectorAll('a')]
  .filter(a => /file-download/.test(a.href || ''))
  .map(a => ({{ id: (a.href.match(/statInfId=(\\d+)/) || [])[1],
              label: (a.closest('li') || a).innerText.replace(/\\s+/g, ' ').slice(0, 40) }}))
```

一覧の起点は `https://www.e-stat.go.jp/stat-search/files?page=2&toukei=00200502`。

### World Bank（キー不要）

```bash
curl "https://api.worldbank.org/v2/country/all/indicator/NY.GDP.PCAP.PP.KD\\
?format=json&date=2010:2014&per_page=2000&page=1&source=2"
```

JSONの1要素目がページ情報、2要素目がデータ本体。`pages` を見て全ページを回す。
`country?format=json` の `region.id == "NA"` は集計値（World, Euro area 等）なので落とす。

### まとめて取り直す

```bash
make fetch     # 上の全部を実行して data/raw/ を上書きする
```

既存ファイルがある e-Stat はスキップされる。強制的に取り直すなら先に消すこと。
"""
    out = paths.ROOT / "data" / "MANIFEST.md"
    out.write_text(text, encoding="utf-8")
    print(f"-> data/MANIFEST.md（{len(rows)} 行）/ data/manifest.csv")


if __name__ == "__main__":
    main()
