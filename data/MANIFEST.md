# 生データ マニフェスト

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

**データセットページ:** https://www.e-stat.go.jp/stat-search/files?page=1&layout=datalist&toukei=00200502&tstat=000001213101&cycle=0&tclass1=000001213102&tclass2val=0

このページの各 EXCEL リンクの `statInfId` が下表の値。取得コードは
[src/estat_fetch.py](../src/estat_fetch.py)。分析に使う8分野だけ落としている
（全14分野あり、自然環境・文化・スポーツ・居住・安全・生活時間は未取得）。

| 分野 | statInfId | ローカル | サイズ | 直接ダウンロードURL | SHA256（先頭16桁） |
|---|---|---|---|---|---|
| A_人口・世帯 | `000040133601` | `data/raw/estat_pref/ssds_01.xls` | 182,272 B | [ダウンロード](https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040133601&fileKind=0) | `ea634889ce052cfa` |
| C_経済基盤 | `000040133603` | `data/raw/estat_pref/ssds_03.xls` | 123,392 B | [ダウンロード](https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040133603&fileKind=0) | `acf1b50ef387e2c7` |
| D_行政基盤 | `000040133604` | `data/raw/estat_pref/ssds_04.xls` | 143,872 B | [ダウンロード](https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040133604&fileKind=0) | `3534860c64128857` |
| E_教育 | `000040133605` | `data/raw/estat_pref/ssds_05.xls` | 162,816 B | [ダウンロード](https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040133605&fileKind=0) | `54b5eb403f183287` |
| F_労働 | `000040133606` | `data/raw/estat_pref/ssds_06.xls` | 125,440 B | [ダウンロード](https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040133606&fileKind=0) | `9f4f9a6a42b2a808` |
| I_健康・医療 | `000040133609` | `data/raw/estat_pref/ssds_09.xls` | 203,264 B | [ダウンロード](https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040133609&fileKind=0) | `39a706250f0f4919` |
| J_福祉・社会保障 | `000040133610` | `data/raw/estat_pref/ssds_10.xls` | 155,648 B | [ダウンロード](https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040133610&fileKind=0) | `b41b74f0ea890752` |
| L_家計 | `000040133612` | `data/raw/estat_pref/ssds_12.xls` | 104,448 B | [ダウンロード](https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040133612&fileKind=0) | `b06adf64353610d7` |

## 2. e-Stat 統計でみる市区町村のすがた2026（基礎データ）

**データセットページ:** https://www.e-stat.go.jp/stat-search/files?page=1&layout=datalist&toukei=00200502&tstat=000001244297&cycle=0&tclass1=000001244298&tclass2val=0

取得コードは [src/muni_fetch.py](../src/muni_fetch.py)。全10分野を取得している。

| 分野 | statInfId | ローカル | サイズ | 直接ダウンロードURL | SHA256（先頭16桁） |
|---|---|---|---|---|---|
| A_人口・世帯 | `000040463584` | `data/raw/estat_muni/muni_01.xls` | 1,056,768 B | [ダウンロード](https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040463584&fileKind=0) | `bff101b575a03ddc` |
| B_自然環境 | `000040463585` | `data/raw/estat_muni/muni_02.xls` | 729,600 B | [ダウンロード](https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040463585&fileKind=0) | `59c3460f3c04ea25` |
| C_経済基盤 | `000040463586` | `data/raw/estat_muni/muni_03.xls` | 858,624 B | [ダウンロード](https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040463586&fileKind=0) | `4b4f4144e71b25c9` |
| D_行政基盤 | `000040463587` | `data/raw/estat_muni/muni_04.xls` | 2,814,976 B | [ダウンロード](https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040463587&fileKind=0) | `d51dcd8e7a31518a` |
| E_教育 | `000040463588` | `data/raw/estat_muni/muni_05.xls` | 758,272 B | [ダウンロード](https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040463588&fileKind=0) | `97a6220cd2b22d34` |
| F_労働 | `000040463589` | `data/raw/estat_muni/muni_06.xls` | 892,928 B | [ダウンロード](https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040463589&fileKind=0) | `446d5b0d60bdf408` |
| G_文化・スポーツ | `000040463590` | `data/raw/estat_muni/muni_07.xls` | 724,992 B | [ダウンロード](https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040463590&fileKind=0) | `09460d08c2b4deb2` |
| H_居住 | `000040463591` | `data/raw/estat_muni/muni_08.xls` | 921,088 B | [ダウンロード](https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040463591&fileKind=0) | `22eae2589e51b2d5` |
| I_健康・医療 | `000040463592` | `data/raw/estat_muni/muni_09.xls` | 795,136 B | [ダウンロード](https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040463592&fileKind=0) | `b76cc27fed59f80f` |
| J_福祉・社会保障 | `000040463593` | `data/raw/estat_muni/muni_10.xls` | 765,440 B | [ダウンロード](https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040463593&fileKind=0) | `94801015ca12b75f` |

## 3. World Bank Open Data

1指標ずつ公開REST APIを叩き、[src/fetch_data.py](../src/fetch_data.py) が1枚のCSVに結合する。

- 結合後のファイル: `data/raw/wb_raw.csv` / 70,288 B / SHA256 `b5fa307ebda20426`
- WGI（source=3）の一覧: `https://api.worldbank.org/v2/source/3/indicator?format=json&per_page=100`
- WGI は指標コードに `GOV_WGI_` の接頭辞が必要。素の `RL.EST` では取れない。

| 列名 | 指標コード | source | 取得条件 | 指標ページ | API URL |
|---|---|---|---|---|---|
| `rule_of_law` | `GOV_WGI_RL.EST` | 3 | 目標年 2012 / 窓 2012-2012 | [ページ](https://databank.worldbank.org/source/worldwide-governance-indicators) | [API](https://api.worldbank.org/v2/country/all/indicator/GOV_WGI_RL.EST?format=json&date=2012:2012&per_page=2000&source=3) |
| `gov_effect` | `GOV_WGI_GE.EST` | 3 | 目標年 2012 / 窓 2012-2012 | [ページ](https://databank.worldbank.org/source/worldwide-governance-indicators) | [API](https://api.worldbank.org/v2/country/all/indicator/GOV_WGI_GE.EST?format=json&date=2012:2012&per_page=2000&source=3) |
| `control_corrupt` | `GOV_WGI_CC.EST` | 3 | 目標年 2012 / 窓 2012-2012 | [ページ](https://databank.worldbank.org/source/worldwide-governance-indicators) | [API](https://api.worldbank.org/v2/country/all/indicator/GOV_WGI_CC.EST?format=json&date=2012:2012&per_page=2000&source=3) |
| `reg_quality` | `GOV_WGI_RQ.EST` | 3 | 目標年 2012 / 窓 2012-2012 | [ページ](https://databank.worldbank.org/source/worldwide-governance-indicators) | [API](https://api.worldbank.org/v2/country/all/indicator/GOV_WGI_RQ.EST?format=json&date=2012:2012&per_page=2000&source=3) |
| `life_exp_12` | `SP.DYN.LE00.IN` | 2 | 目標年 2012 / 窓 2010-2014 | [ページ](https://data.worldbank.org/indicator/SP.DYN.LE00.IN) | [API](https://api.worldbank.org/v2/country/all/indicator/SP.DYN.LE00.IN?format=json&date=2010:2014&per_page=2000&source=2) |
| `under5_mort_12` | `SH.DYN.MORT` | 2 | 目標年 2012 / 窓 2010-2014 | [ページ](https://data.worldbank.org/indicator/SH.DYN.MORT) | [API](https://api.worldbank.org/v2/country/all/indicator/SH.DYN.MORT?format=json&date=2010:2014&per_page=2000&source=2) |
| `school_sec_12` | `SE.SEC.ENRR` | 2 | 目標年 2012 / 窓 2010-2014 | [ページ](https://data.worldbank.org/indicator/SE.SEC.ENRR) | [API](https://api.worldbank.org/v2/country/all/indicator/SE.SEC.ENRR?format=json&date=2010:2014&per_page=2000&source=2) |
| `gdp_pc_12` | `NY.GDP.PCAP.PP.KD` | 2 | 目標年 2012 / 窓 2010-2014 | [ページ](https://data.worldbank.org/indicator/NY.GDP.PCAP.PP.KD) | [API](https://api.worldbank.org/v2/country/all/indicator/NY.GDP.PCAP.PP.KD?format=json&date=2010:2014&per_page=2000&source=2) |
| `gni_pc_12` | `NY.GNP.PCAP.PP.KD` | 2 | 目標年 2012 / 窓 2010-2014 | [ページ](https://data.worldbank.org/indicator/NY.GNP.PCAP.PP.KD) | [API](https://api.worldbank.org/v2/country/all/indicator/NY.GNP.PCAP.PP.KD?format=json&date=2010:2014&per_page=2000&source=2) |
| `cons_pc_12` | `NE.CON.PRVT.PC.KD` | 2 | 目標年 2012 / 窓 2010-2014 | [ページ](https://data.worldbank.org/indicator/NE.CON.PRVT.PC.KD) | [API](https://api.worldbank.org/v2/country/all/indicator/NE.CON.PRVT.PC.KD?format=json&date=2010:2014&per_page=2000&source=2) |
| `gdp_pc_22` | `NY.GDP.PCAP.PP.KD` | 2 | 目標年 2022 / 窓 2020-2023 | [ページ](https://data.worldbank.org/indicator/NY.GDP.PCAP.PP.KD) | [API](https://api.worldbank.org/v2/country/all/indicator/NY.GDP.PCAP.PP.KD?format=json&date=2020:2023&per_page=2000&source=2) |
| `gni_pc_22` | `NY.GNP.PCAP.PP.KD` | 2 | 目標年 2022 / 窓 2020-2023 | [ページ](https://data.worldbank.org/indicator/NY.GNP.PCAP.PP.KD) | [API](https://api.worldbank.org/v2/country/all/indicator/NY.GNP.PCAP.PP.KD?format=json&date=2020:2023&per_page=2000&source=2) |
| `cons_pc_22` | `NE.CON.PRVT.PC.KD` | 2 | 目標年 2022 / 窓 2020-2023 | [ページ](https://data.worldbank.org/indicator/NE.CON.PRVT.PC.KD) | [API](https://api.worldbank.org/v2/country/all/indicator/NE.CON.PRVT.PC.KD?format=json&date=2020:2023&per_page=2000&source=2) |
| `internet_users` | `IT.NET.USER.ZS` | 2 | 目標年 2022 / 窓 2020-2023 | [ページ](https://data.worldbank.org/indicator/IT.NET.USER.ZS) | [API](https://api.worldbank.org/v2/country/all/indicator/IT.NET.USER.ZS?format=json&date=2020:2023&per_page=2000&source=2) |
| `broadband` | `IT.NET.BBND.P2` | 2 | 目標年 2022 / 窓 2020-2023 | [ページ](https://data.worldbank.org/indicator/IT.NET.BBND.P2) | [API](https://api.worldbank.org/v2/country/all/indicator/IT.NET.BBND.P2?format=json&date=2020:2023&per_page=2000&source=2) |
| `life_exp_17` | `SP.DYN.LE00.IN` | 2 | 目標年 2017 / 窓 2015-2019 | [ページ](https://data.worldbank.org/indicator/SP.DYN.LE00.IN) | [API](https://api.worldbank.org/v2/country/all/indicator/SP.DYN.LE00.IN?format=json&date=2015:2019&per_page=2000&source=2) |
| `under5_mort_17` | `SH.DYN.MORT` | 2 | 目標年 2017 / 窓 2015-2019 | [ページ](https://data.worldbank.org/indicator/SH.DYN.MORT) | [API](https://api.worldbank.org/v2/country/all/indicator/SH.DYN.MORT?format=json&date=2015:2019&per_page=2000&source=2) |
| `school_sec_17` | `SE.SEC.ENRR` | 2 | 目標年 2017 / 窓 2015-2019 | [ページ](https://data.worldbank.org/indicator/SE.SEC.ENRR) | [API](https://api.worldbank.org/v2/country/all/indicator/SE.SEC.ENRR?format=json&date=2015:2019&per_page=2000&source=2) |
| `school_ter_12` | `SE.TER.ENRR` | 2 | 目標年 2012 / 窓 2010-2014 | [ページ](https://data.worldbank.org/indicator/SE.TER.ENRR) | [API](https://api.worldbank.org/v2/country/all/indicator/SE.TER.ENRR?format=json&date=2010:2014&per_page=2000&source=2) |
| `prm_compl_12` | `SE.PRM.CMPT.ZS` | 2 | 目標年 2012 / 窓 2010-2014 | [ページ](https://data.worldbank.org/indicator/SE.PRM.CMPT.ZS) | [API](https://api.worldbank.org/v2/country/all/indicator/SE.PRM.CMPT.ZS?format=json&date=2010:2014&per_page=2000&source=2) |
| `school_sec_f_12` | `SE.SEC.ENRR.FE` | 2 | 目標年 2012 / 窓 2010-2014 | [ページ](https://data.worldbank.org/indicator/SE.SEC.ENRR.FE) | [API](https://api.worldbank.org/v2/country/all/indicator/SE.SEC.ENRR.FE?format=json&date=2010:2014&per_page=2000&source=2) |
| `edu_exp_12` | `SE.XPD.TOTL.GD.ZS` | 2 | 目標年 2012 / 窓 2010-2014 | [ページ](https://data.worldbank.org/indicator/SE.XPD.TOTL.GD.ZS) | [API](https://api.worldbank.org/v2/country/all/indicator/SE.XPD.TOTL.GD.ZS?format=json&date=2010:2014&per_page=2000&source=2) |

---

## ダウンロードの実際の手順

### e-Stat（キー不要）

```bash
curl -L -A "Mozilla/5.0" -o out.xls \
  "https://www.e-stat.go.jp/stat-search/file-download?statInfId=<12桁ID>&fileKind=0"
```

`fileKind` は 0 が Excel、2 が PDF。**検索ページは JavaScript で描画されるので curl では
中身が取れない。**新しい `statInfId` を探すときはブラウザでデータセットページを開き、
開発者コンソールで次を実行する。

```js
[...document.querySelectorAll('a')]
  .filter(a => /file-download/.test(a.href || ''))
  .map(a => ({ id: (a.href.match(/statInfId=(\d+)/) || [])[1],
              label: (a.closest('li') || a).innerText.replace(/\s+/g, ' ').slice(0, 40) }))
```

一覧の起点は `https://www.e-stat.go.jp/stat-search/files?page=2&toukei=00200502`。

### World Bank（キー不要）

```bash
curl "https://api.worldbank.org/v2/country/all/indicator/NY.GDP.PCAP.PP.KD\
?format=json&date=2010:2014&per_page=2000&page=1&source=2"
```

JSONの1要素目がページ情報、2要素目がデータ本体。`pages` を見て全ページを回す。
`country?format=json` の `region.id == "NA"` は集計値（World, Euro area 等）なので落とす。

### まとめて取り直す

```bash
make fetch     # 上の全部を実行して data/raw/ を上書きする
```

既存ファイルがある e-Stat はスキップされる。強制的に取り直すなら先に消すこと。
