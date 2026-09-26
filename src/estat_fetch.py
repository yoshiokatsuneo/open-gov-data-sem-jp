# -*- coding: utf-8 -*-
"""e-Stat「社会生活統計指標－都道府県の指標－2024」の Excel を取得する。

e-Stat API（要 appId）ではなく、キー不要のファイルダウンロード URL を使う。
statInfId は e-Stat の当該データセットページの各 EXCEL リンクから取得したもの。
  https://www.e-stat.go.jp/stat-search/files?page=2&toukei=00200502
  → 社会生活統計指標－都道府県の指標－2024 → ■社会生活統計指標
"""
import paths

import os
import time
import urllib.request

BASE = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
OUT = str(paths.ESTAT_PREF_XLS)

# 表番号 → statInfId。分析に使う分野だけ落とす。
FILES = {
    "01_A_人口・世帯":     "000040133601",
    "03_C_経済基盤":       "000040133603",
    "04_D_行政基盤":       "000040133604",
    "05_E_教育":           "000040133605",
    "06_F_労働":           "000040133606",
    "09_I_健康・医療":     "000040133609",
    "10_J_福祉・社会保障": "000040133610",
    "12_L_家計":           "000040133612",
}


def main():
    os.makedirs(OUT, exist_ok=True)
    for label, sid in FILES.items():
        no = label.split("_")[0]
        dest = os.path.join(OUT, f"ssds_{no}.xls")
        if os.path.exists(dest) and os.path.getsize(dest) > 10000:
            print(f"  skip {label}")
            continue
        req = urllib.request.Request(BASE.format(sid),
                                     headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
            f.write(r.read())
        print(f"  {label:22s} {os.path.getsize(dest):>8,} bytes")
        time.sleep(1)          # 相手サーバに負荷をかけない
    print(f"\n-> {OUT}")


if __name__ == "__main__":
    main()
