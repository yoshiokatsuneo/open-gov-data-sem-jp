"""World Bank のオープンデータ（WDI / WGI）を取得して SEM 用のワイド表を作る。

出力: wb_raw.csv

設計の要は「時点をずらすこと」。横断データで因果の向きを主張できないので、
説明側は 2012 年（初期条件）、結果側は 2012→2022 の変化に取る。

  制度の質 (GOV)     ... 2012年       Worldwide Governance Indicators (source=3)
  人的資本 (HC)      ... 2010-2014    World Development Indicators
  初期所得 (init)    ... 2010-2014    World Development Indicators
  その後の成長 (GROWTH) ... 2012 → 2022 の対数差

単年だと欠損が多い指標があるため、窓の中で目標年に最も近い観測値を採用する。
"""
import paths

import json
import time
import urllib.request

import pandas as pd

API = "https://api.worldbank.org/v2"

# (列名, 指標ID, 目標年, 窓の開始, 窓の終了, source)
SPECS = [
    # --- 制度の質 (2012) ---
    ("rule_of_law",     "GOV_WGI_RL.EST", 2012, 2012, 2012, 3),
    ("gov_effect",      "GOV_WGI_GE.EST", 2012, 2012, 2012, 3),
    ("control_corrupt", "GOV_WGI_CC.EST", 2012, 2012, 2012, 3),
    ("reg_quality",     "GOV_WGI_RQ.EST", 2012, 2012, 2012, 3),
    # --- 人的資本 (2012 前後) ---
    ("life_exp_12",     "SP.DYN.LE00.IN", 2012, 2010, 2014, 2),
    ("under5_mort_12",  "SH.DYN.MORT",    2012, 2010, 2014, 2),
    ("school_sec_12",   "SE.SEC.ENRR",    2012, 2010, 2014, 2),
    # --- 初期所得と、10年後の到達水準 (成長率の材料) ---
    ("gdp_pc_12",       "NY.GDP.PCAP.PP.KD",  2012, 2010, 2014, 2),
    ("gni_pc_12",       "NY.GNP.PCAP.PP.KD",  2012, 2010, 2014, 2),
    ("cons_pc_12",      "NE.CON.PRVT.PC.KD",  2012, 2010, 2014, 2),
    ("gdp_pc_22",       "NY.GDP.PCAP.PP.KD",  2022, 2020, 2023, 2),
    ("gni_pc_22",       "NY.GNP.PCAP.PP.KD",  2022, 2020, 2023, 2),
    ("cons_pc_22",      "NE.CON.PRVT.PC.KD",  2022, 2020, 2023, 2),
    # --- 参考: 水準モデル(Model A)用の 2020年代の繁栄指標 ---
    ("internet_users",  "IT.NET.USER.ZS",     2022, 2020, 2023, 2),
    ("broadband",       "IT.NET.BBND.P2",     2022, 2020, 2023, 2),
    ("life_exp_17",     "SP.DYN.LE00.IN",     2017, 2015, 2019, 2),
    ("under5_mort_17",  "SH.DYN.MORT",        2017, 2015, 2019, 2),
    ("school_sec_17",   "SE.SEC.ENRR",        2017, 2015, 2019, 2),
    # --- 人的資本の指標入れ替え検討用（採用モデルには入っていないが、
    #     「教育のみ」「保健のみ」の試行で使ったので再現のため残す。docs/01-countries.md 参照）---
    ("school_ter_12",   "SE.TER.ENRR",        2012, 2010, 2014, 2),
    ("prm_compl_12",    "SE.PRM.CMPT.ZS",     2012, 2010, 2014, 2),
    ("school_sec_f_12", "SE.SEC.ENRR.FE",     2012, 2010, 2014, 2),
    ("edu_exp_12",      "SE.XPD.TOTL.GD.ZS",  2012, 2010, 2014, 2),
    # --- 水準モデル（Model A 系）の初期案で使い、天井効果のため外した2指標。
    #     棄却の経緯を再現できるよう残す（src/model_log.py の A1）---
    ("prm_complete",    "SE.PRM.CMPT.ZS",     2017, 2015, 2019, 2),
    ("electricity",     "EG.ELC.ACCS.ZS",     2022, 2020, 2023, 2),
]


def get_json(url):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.loads(r.read().decode())
        except Exception as e:  # ネットワークの一時的な失敗はリトライ
            if attempt == 2:
                raise
            print(f"  retry ({e})")
            time.sleep(2)


def real_countries():
    """集計値（"World", "Euro area" 等）を除いた実在国のみ返す。"""
    rows, page = [], 1
    while True:
        d = get_json(f"{API}/country?format=json&per_page=300&page={page}")
        rows += d[1]
        if page >= d[0]["pages"]:
            break
        page += 1
    return {
        c["id"]: {"country": c["name"], "region": c["region"]["value"],
                  "income": c["incomeLevel"]["value"]}
        for c in rows if c["region"]["id"] != "NA"
    }


def fetch(indicator, target, y0, y1, source):
    """窓 [y0, y1] の観測のうち、目標年 target に最も近い年の値を国ごとに返す。"""
    best = {}  # iso3 -> (目標年との距離, 値)
    page = 1
    while True:
        url = (f"{API}/country/all/indicator/{indicator}"
               f"?format=json&date={y0}:{y1}&per_page=2000&page={page}&source={source}")
        d = get_json(url)
        if not isinstance(d, list) or len(d) < 2 or d[1] is None:
            break
        for row in d[1]:
            iso, val = row["countryiso3code"], row["value"]
            if val is None or not iso:
                continue
            dist = abs(int(row["date"]) - target)
            if iso not in best or dist < best[iso][0]:
                best[iso] = (dist, val)
        if page >= d[0]["pages"]:
            break
        page += 1
    return pd.Series({k: v[1] for k, v in best.items()})


if __name__ == "__main__":
    meta = real_countries()
    print(f"実在国: {len(meta)}\n")

    df = pd.DataFrame.from_dict(meta, orient="index")
    for col, ind, target, y0, y1, src in SPECS:
        df[col] = fetch(ind, target, y0, y1, src)
        print(f"{col:16s} {ind:17s} 窓{y0}-{y1}  取得 {df[col].notna().sum():3d}/{len(df)}")

    df.index.name = "iso3"
    df.to_csv(paths.raw("wb_raw.csv"))
    print("\n-> wb_raw.csv")
