# -*- coding: utf-8 -*-
"""e-Stat「社会生活統計指標－都道府県の指標－2024」の .xls を縦持ちに変換する。

シートの構造（社会生活統計指標の共通レイアウト）:
  row 7  ... 指標の日本語名（指標グループの先頭列にだけ入る）
  row 9  ... 指標コード（#I0910103 など。同じく先頭列だけ）
  row 10 ... 各列の年次
  row 11+... 全国 + 47都道府県のデータ。col 7 = 都道府県コード, col 8 = 名称
  末尾   ... 分母・出典などの注記行（都道府県コードが無いので落ちる）
"""
import paths

import glob
import os
import re

import pandas as pd
import xlrd

RAW = str(paths.ESTAT_PREF_XLS)
ROW_NAME, ROW_CODE, ROW_YEAR, ROW_DATA0, COL_DATA0 = 7, 9, 10, 11, 11


def ffill(row, n):
    """指標名・コードは先頭列にしか入らないので右方向に埋める。"""
    out, cur = [], ""
    for i in range(n):
        v = str(row[i].value).strip() if i < len(row) else ""
        if v:
            cur = v
        out.append(cur)
    return out


def parse(path):
    sh = xlrd.open_workbook(path).sheet_by_index(0)
    names = ffill(sh.row(ROW_NAME), sh.ncols)
    codes = ffill(sh.row(ROW_CODE), sh.ncols)
    years = [str(sh.row(ROW_YEAR)[i].value).strip() for i in range(sh.ncols)]

    recs = []
    for r in range(ROW_DATA0, sh.nrows):
        row = sh.row(r)
        pref_cd = str(row[7].value).strip()
        pref = str(row[8].value).strip()
        if not re.fullmatch(r"\d{2}", pref_cd) or not pref:
            continue                                   # 注記行を飛ばす
        for c in range(COL_DATA0, sh.ncols):
            code = codes[c]
            if not code.startswith("#"):
                continue                               # 単位・脚注の列
            v = row[c].value
            if isinstance(v, str):
                v = v.replace(",", "").strip()
                if v in ("", "-", "－", "…", "***", "x", "X"):
                    continue
                try:
                    v = float(v)
                except ValueError:
                    continue
            if v == "" or v is None:
                continue
            y = years[c]
            recs.append((pref_cd, pref, code, re.sub(r"\s+", "", names[c]),
                         int(float(y)) if re.fullmatch(r"[\d.]+", y) else None, float(v)))

    return pd.DataFrame(recs, columns=["pref_cd", "pref", "code", "name", "year", "value"])


def load_all():
    frames = [parse(p) for p in sorted(glob.glob(os.path.join(RAW, "ssds_*.xls")))]
    return pd.concat(frames, ignore_index=True)


if __name__ == "__main__":
    df = load_all()
    print(f"{len(df):,} 行　指標 {df.code.nunique()} 種　都道府県 {df.pref_cd.nunique()}")
    print(f"年次: {sorted(x for x in df.year.dropna().unique())}\n")
    df.to_csv(paths.processed("estat_long.csv"), index=False)
    print("-> estat_long.csv")
