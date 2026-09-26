# 05 データ出典・取得方法・指標定義

全データが **APIキー・アカウント登録なし**で取得できる。`data/raw/` にコミット済み。

---

## 1. World Bank Open Data

### 取得

[src/fetch_data.py](../src/fetch_data.py) — 公開REST APIをキーなしで叩く。

```
https://api.worldbank.org/v2/country/all/indicator/<CODE>?format=json&date=<Y0>:<Y1>&per_page=2000&page=<N>&source=<S>
```

- `source=2` … World Development Indicators（既定）
- `source=3` … Worldwide Governance Indicators

**WGI の指標コードは `RL.EST` ではなく `GOV_WGI_RL.EST`。**`source=3` を付けないと 404、付けても素の `RL.EST` では 400 になる。一覧は `https://api.worldbank.org/v2/source/3/indicator?format=json&per_page=100`。

`country?format=json` で取れる国リストのうち `region.id == "NA"` は集計値（World, Euro area など）なので落とす。217の実在国・地域が残る。

**窓内で目標年に最も近い観測値を採る**実装にしてある。単年指定だと欠損が多い（例: 中等教育就学率は2017年単年で 140件、2015-19窓で 178件）。

### 使用指標

| 列名 | コード | source | 目標年 | 窓 |
|---|---|---|---|---|
| `rule_of_law` | `GOV_WGI_RL.EST` | 3 | 2012 | 2012 |
| `gov_effect` | `GOV_WGI_GE.EST` | 3 | 2012 | 2012 |
| `control_corrupt` | `GOV_WGI_CC.EST` | 3 | 2012 | 2012 |
| `reg_quality` | `GOV_WGI_RQ.EST` | 3 | 2012 | 2012 |
| `life_exp_12` | `SP.DYN.LE00.IN` | 2 | 2012 | 2010-14 |
| `under5_mort_12` | `SH.DYN.MORT` | 2 | 2012 | 2010-14 |
| `school_sec_12` | `SE.SEC.ENRR` | 2 | 2012 | 2010-14 |
| `gdp_pc_12` / `gdp_pc_22` | `NY.GDP.PCAP.PP.KD` | 2 | 2012 / 2022 | 2010-14 / 2020-23 |
| `gni_pc_12` / `gni_pc_22` | `NY.GNP.PCAP.PP.KD` | 2 | 同上 | 同上 |
| `cons_pc_12` / `cons_pc_22` | `NE.CON.PRVT.PC.KD` | 2 | 同上 | 同上 |
| `internet_users` | `IT.NET.USER.ZS` | 2 | 2022 | 2020-23 |
| `broadband` | `IT.NET.BBND.P2` | 2 | 2022 | 2020-23 |
| `life_exp_17` / `under5_mort_17` / `school_sec_17` | 上と同じ | 2 | 2017 | 2015-19 |
| `school_ter_12` | `SE.TER.ENRR` | 2 | 2012 | 2010-14 |
| `prm_compl_12` | `SE.PRM.CMPT.ZS` | 2 | 2012 | 2010-14 |
| `school_sec_f_12` | `SE.SEC.ENRR.FE` | 2 | 2012 | 2010-14 |
| `edu_exp_12` | `SE.XPD.TOTL.GD.ZS` | 2 | 2012 | 2010-14 |

### 派生変数（[src/sem_analysis.py](../src/sem_analysis.py) の `derive()`）

- `init_gdp = log(gdp_pc_12)`
- `child_surv_12 = -log(under5_mort_12)` … 死亡率を「生存」に向きを揃える
- `g_gdp = log(gdp_pc_22) - log(gdp_pc_12)` … 累積成長率（GNI・消費も同様）

### ライセンス

[CC BY 4.0](https://datacatalog.worldbank.org/public-licenses)。出典表示すれば商用利用可。

---

## 2. e-Stat（政府統計の総合窓口）

### API キー無しで統計表を落とす

e-Stat の**API**（`api.e-stat.go.jp`）は appId 登録が必須。しかし**ファイル提供されている統計表は認証なしで直接ダウンロードできる**。

```
https://www.e-stat.go.jp/stat-search/file-download?statInfId=<12桁ID>&fileKind=0
```

- `fileKind=0` … Excel
- `fileKind=2` … PDF

`statInfId` はデータセット一覧ページの各ダウンロードリンクから取る。**検索ページは JavaScript レンダリングなので curl では中身が取れない。**ブラウザで開いて次を実行するのが早い。

```js
Array.from(document.querySelectorAll('a'))
  .filter(a => /file-download/.test(a.href || ''))
  .map(a => ({ href: a.href, t: (a.closest('li') || a).innerText.replace(/\s+/g, ' ').slice(0, 60) }))
```

一覧の起点: `https://www.e-stat.go.jp/stat-search/files?page=2&toukei=00200502`

### 2-1. 社会生活統計指標－都道府県の指標－2024

[src/estat_fetch.py](../src/estat_fetch.py)（取得）/ [src/estat_parse.py](../src/estat_parse.py)（整形）

人口当たりに正規化済みの指標が約390種、47都道府県分。`data/raw/estat_pref/ssds_*.xls`。

| 表番号 | 分野 | statInfId |
|---|---|---|
| A | 人口・世帯 | 000040133601 |
| C | 経済基盤 | 000040133603 |
| D | 行政基盤 | 000040133604 |
| E | 教育 | 000040133605 |
| F | 労働 | 000040133606 |
| I | 健康・医療 | 000040133609 |
| J | 福祉・社会保障 | 000040133610 |
| L | 家計 | 000040133612 |

**シート構造:** 行7 = 指標の日本語名、行9 = 指標コード（`#I0910103` 形式）、行10 = 年次、行11以降 = 全国＋47都道府県（col 7 = 都道府県コード、col 8 = 名称）。
**指標名とコードはグループ先頭列にしか入らないので右方向に ffill する。**1指標につき3年分の列が並ぶ。

出力 `data/processed/estat_long.csv` は縦持ち（pref_cd, pref, code, name, year, value）で 39,022行・387指標。

### 2-2. 統計でみる市区町村のすがた2026（基礎データ）

[src/muni_fetch.py](../src/muni_fetch.py) / [src/muni_parse.py](../src/muni_parse.py)

**実数**の指標が89種、1,896市区町村分。`data/raw/estat_muni/muni_*.xls`。

| 表番号 | 分野 | statInfId |
|---|---|---|
| 01 | A 人口・世帯 | 000040463584 |
| 02 | B 自然環境 | 000040463585 |
| 03 | C 経済基盤 | 000040463586 |
| 04 | D 行政基盤 | 000040463587 |
| 05 | E 教育 | 000040463588 |
| 06 | F 労働 | 000040463589 |
| 07 | G 文化・スポーツ | 000040463590 |
| 08 | H 居住 | 000040463591 |
| 09 | I 健康・医療 | 000040463592 |
| 10 | J 福祉・社会保障 | 000040463593 |

**都道府県版とシート構造が違う。**行5 = 指標名、行7 = コード（`A1101` 形式、`#` なし）、行9 = 年次、行10以降 = データ（col 1 = 団体コード、col 8 = 名称）。**1指標1列**（都道府県版は3列）。

**行の選別:** 末尾3桁が `000` は都道府県（47行）、末尾2桁が `00` は政令市・特別区部の合計（17行）。後者は区と二重計上になるので落とし、**区単位**で 1,896行。

**注意: 就業構造基本調査由来の指標（転職率・離職率）は市区町村版に存在しない。**労働ファイルは国勢調査由来の15指標のみ。

出力は `data/processed/muni_raw.csv`（実数）、`muni_rates.csv`（率に変換）、`muni_meta.csv`（コード→名称・年次）。

### ライセンス

[政府標準利用規約（第2.0版）](https://www.e-stat.go.jp/terms-of-use)。出典表示すれば商用利用可。

### 項目定義

- 都道府県: [社会生活統計指標－都道府県の指標－](https://www.stat.go.jp/data/ssds/shihyou.html)
- 基礎データ項目定義: [https://www.stat.go.jp/data/ssds/9.html](https://www.stat.go.jp/data/ssds/9.html)

---

## 3. 再取得するときの注意

```bash
make fetch    # data/raw/ を上書きする
```

**公的機関側の更新で数値が変わる。**e-Stat の「すがた」シリーズは毎年更新され、World Bank も遡及改訂する。`data/raw/` を固定してコミットしてあるのはそのため。再取得したら `make all` を回し、`results/` の差分を確認してからコミットすること。

`estat_fetch.py` / `muni_fetch.py` は既存ファイルがあればスキップする。強制的に取り直すなら先に該当ファイルを消す。

## 4. 相手サーバへの配慮

`muni_fetch.py` / `estat_fetch.py` はファイル間に 1 秒のスリープを入れてある。World Bank API はページングで数十リクエストになるので、大量の指標を追加するときはリトライ間隔（現行 2 秒、3回まで）を守ること。
