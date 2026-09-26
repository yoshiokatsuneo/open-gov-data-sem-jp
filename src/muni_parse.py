# -*- coding: utf-8 -*-
"""「統計でみる市区町村のすがた2026（基礎データ）」の .xls を横持ちに変換する。

出力: muni_raw.csv（実数）/ muni_rates.csv（率に直したもの）

シートの構造（都道府県版とは別レイアウト）:
  row 5  ... 指標の日本語名   row 7 ... 指標コード   row 9 ... 年次
  row 10+... データ。col 1 = 団体コード, col 8 = 名称。指標は1列ずつ。

行の選別:
  末尾3桁が000 = 都道府県（47行）→ 落とす
  末尾2桁が00  = 政令市・特別区部の合計（17行）→ 区と二重計上になるので落とす
  残り 1,896行 = 市区町村（政令市は区単位）
"""
import paths

import glob
import os
import re

import numpy as np
import pandas as pd
import xlrd

RAW = str(paths.ESTAT_MUNI_XLS)
ROW_NAME, ROW_CODE, ROW_YEAR, ROW_DATA0, COL_DATA0 = 5, 7, 9, 10, 10


def parse(path):
    sh = xlrd.open_workbook(path).sheet_by_index(0)
    names = [re.sub(r"\s+", "", str(sh.row(ROW_NAME)[i].value).strip()) for i in range(sh.ncols)]
    codes = [str(sh.row(ROW_CODE)[i].value).strip() for i in range(sh.ncols)]
    years = [str(sh.row(ROW_YEAR)[i].value).strip() for i in range(sh.ncols)]
    cols = [i for i in range(COL_DATA0, sh.ncols) if codes[i] and names[i]]

    recs, meta = {}, {}
    for i in cols:
        meta[codes[i]] = (names[i], years[i])
    for r in range(ROW_DATA0, sh.nrows):
        row = sh.row(r)
        cd = str(row[1].value).strip()
        if not re.fullmatch(r"\d{5}", cd):
            continue
        rec = {"name": str(row[8].value).strip()}
        for i in cols:
            v = row[i].value
            if isinstance(v, str):
                v = v.replace(",", "").strip()
                if v in ("", "-", "－", "…", "***", "x", "X"):
                    v = np.nan
                else:
                    try:
                        v = float(v)
                    except ValueError:
                        v = np.nan
            rec[codes[i]] = v if v != "" else np.nan
        recs[cd] = rec
    return pd.DataFrame.from_dict(recs, orient="index"), meta


def load_all():
    frames, meta = [], {}
    for p in sorted(glob.glob(os.path.join(RAW, "muni_*.xls"))):
        df, m = parse(p)
        meta.update(m)
        frames.append(df.drop(columns=["name"]) if frames else df)
    out = pd.concat(frames, axis=1)
    out = out.loc[:, ~out.columns.duplicated()]
    out.index.name = "code"
    pd.DataFrame([{"code": k, "name": v[0], "year": v[1]} for k, v in meta.items()]).to_csv(
        paths.processed("muni_meta.csv"), index=False)
    return out, meta


def municipalities(df):
    """都道府県行と、政令市・特別区部の合計行を落とす。"""
    cd = df.index.astype(str)
    keep = ~(cd.str.endswith("000") | cd.str.endswith("00"))
    return df[keep]


def rates(df):
    """実数を率・密度に直す。分母が0や欠損のものは NaN になる。"""
    g = lambda c: pd.to_numeric(df[c], errors="coerce")
    r = pd.DataFrame(index=df.index)
    r["name"] = df["name"]
    r["pref_cd"] = df.index.astype(str).str[:2].astype(int)

    pop, jumin = g("A1101"), g("A2301")
    r["pop"] = pop
    # ---- 結果: 総移動率（転入＋転出）。転職率と同じ「総フロー」の考え方 ----
    r["move_rate"] = (g("A5103") + g("A5104")) / jumin * 100
    r["in_rate"] = g("A5103") / jumin * 100
    r["out_rate"] = g("A5104") / jumin * 100
    r["net_rate"] = (g("A5103") - g("A5104")) / jumin * 100
    # ---- 都市労働市場の厚み ----
    r["ldens"] = np.log(pop / g("B1103"))              # 可住地面積当たり人口密度（対数）
    r["daytime"] = g("A6107") / pop                    # 昼夜間人口比率
    r["tax_pc"] = g("C120110") / g("C120120")          # 納税義務者1人当たり課税対象所得
    r["svc"] = g("F2221") / g("F1102")                 # 第3次産業就業者比率
    r["estab"] = g("C2208") / pop                      # 人口当たり従業者数（民営）
    # ---- 雇用の不安定さ ----
    r["unemp"] = g("F1107") / g("F1101") * 100         # 完全失業率
    r["kokuho"] = g("J4101") / pop                     # 国民健康保険加入率
    r["nonemp"] = 1 - g("F2401") / g("F1102")          # 雇用者でない就業者の割合
    # ---- 参考 ----
    r["young"] = g("A1301") / pop
    r["old"] = g("A1303") / pop
    r["solo"] = g("A810105") / g("A710101")
    r["owner"] = g("H1310") / g("H1101")
    r["did"] = g("A1801") / pop
    return r


if __name__ == "__main__":
    df, meta = load_all()
    print(f"読み込み: {len(df):,}行 × {df.shape[1]-1}指標")
    m = municipalities(df)
    print(f"市区町村のみ: {len(m):,}行")
    m.to_csv(paths.processed("muni_raw.csv"))

    r = rates(m)
    cols = [c for c in r.columns if c not in ("name", "pref_cd")]
    print(f"\n導出した率: {len(cols)}件")
    print(r[cols].describe().T[["count", "mean", "std", "min", "50%", "max"]].round(3).to_string())
    r.to_csv(paths.processed("muni_rates.csv"))
    print("\n-> muni_raw.csv / muni_rates.csv")
