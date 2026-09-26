# -*- coding: utf-8 -*-
"""e-Stat「統計でみる市区町村のすがた2026（基礎データ）」の Excel を取得する。

都道府県版と同じく、キー不要の file-download URL を使う。
statInfId は下記ページの各 EXCEL リンクから取得したもの。
  https://www.e-stat.go.jp/stat-search/files?toukei=00200502&tstat=000001244297
基礎データなので実数。人口等で割って率に直すのは muni_parse.py 側でやる。
"""
import paths

import os
import time
import urllib.request

BASE = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
OUT = str(paths.ESTAT_MUNI_XLS)

FILES = {
    "01_A_人口・世帯":     "000040463584",
    "02_B_自然環境":       "000040463585",
    "03_C_経済基盤":       "000040463586",
    "04_D_行政基盤":       "000040463587",
    "05_E_教育":           "000040463588",
    "06_F_労働":           "000040463589",
    "07_G_文化・スポーツ": "000040463590",
    "08_H_居住":           "000040463591",
    "09_I_健康・医療":     "000040463592",
    "10_J_福祉・社会保障": "000040463593",
}


def main():
    os.makedirs(OUT, exist_ok=True)
    for label, sid in FILES.items():
        no = label.split("_")[0]
        dest = os.path.join(OUT, f"muni_{no}.xls")
        if os.path.exists(dest) and os.path.getsize(dest) > 10000:
            print(f"  skip {label}")
            continue
        req = urllib.request.Request(BASE.format(sid), headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=180) as r, open(dest, "wb") as f:
            f.write(r.read())
        print(f"  {label:22s} {os.path.getsize(dest):>9,} bytes")
        time.sleep(1)
    print(f"\n-> {OUT}")


if __name__ == "__main__":
    main()
