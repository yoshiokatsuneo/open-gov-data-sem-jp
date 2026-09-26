# -*- coding: utf-8 -*-
"""data/raw/ に固定した生データと、いま公的機関が配っているものを突き合わせる。

`make all` は data/raw/ を使うので結果は常に再現する。一方、公的機関側は
データを遡って改訂する。このスクリプトは「固定版と最新版がどれだけ違うか」を
機械的に出す。数値が動いていれば、README の結論がどれだけ上流に依存しているかが分かる。

    .venv/bin/python src/check_revisions.py

ダウンロードは一時ディレクトリに行い、data/raw/ は書き換えない。
"""
import hashlib
import shutil
import tempfile
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

import paths
from estat_fetch import BASE as ESTAT_BASE, FILES as PREF_FILES
from muni_fetch import FILES as MUNI_FILES


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def download(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=180) as r, open(dest, "wb") as f:
        f.write(r.read())


def check_estat(tmp):
    rows = []
    for label, sid in PREF_FILES.items():
        no = label.split("_")[0]
        local = paths.ESTAT_PREF_XLS / f"ssds_{no}.xls"
        rows.append(("都道府県", label, sid, local, tmp / f"p_{no}.xls"))
    for label, sid in MUNI_FILES.items():
        no = label.split("_")[0]
        local = paths.ESTAT_MUNI_XLS / f"muni_{no}.xls"
        rows.append(("市区町村", label, sid, local, tmp / f"m_{no}.xls"))

    print(f"\n=== e-Stat の {len(rows)} ファイル ===")
    diff = 0
    for kind, label, sid, local, dest in rows:
        download(ESTAT_BASE.format(sid), dest)
        same = sha(local) == sha(dest)
        diff += not same
        print(f"  {kind} {label:22s} {'一致' if same else '★変更あり'}"
              f"  {dest.stat().st_size:>9,} B")
    print(f"  → 変更 {diff} / {len(rows)} ファイル")
    return diff


def check_worldbank(tmp):
    """fetch_data.py を一時ディレクトリ向けに走らせ、固定版と数値を比べる。"""
    import fetch_data

    meta = fetch_data.real_countries()
    new = pd.DataFrame.from_dict(meta, orient="index")
    for col, ind, target, y0, y1, src in fetch_data.SPECS:
        new[col] = fetch_data.fetch(ind, target, y0, y1, src)
    old = pd.read_csv(paths.raw("wb_raw.csv"), index_col="iso3")
    new = new.reindex(old.index)

    print("\n=== World Bank の指標ごとの差 ===")
    num = [c for c in old.columns if old[c].dtype.kind in "fi"]
    changed = []
    for c in num:
        if c not in new:
            continue
        d = (old[c] - new[c]).abs()
        n = int((d > 1e-9).sum())
        if n:
            i = d.idxmax()
            changed.append((c, n, d.max(), i, old.loc[i, c], new.loc[i, c]))
    if not changed:
        print("  変更なし")
    for c, n, mx, i, a, b in changed:
        print(f"  {c:16s} 値が変わった国 {n:3d}  最大差 {mx:.4g}"
              f"（{i}: {a:.4g} → {b:.4g}）")
    return new, changed


if __name__ == "__main__":
    tmp = Path(tempfile.mkdtemp(prefix="revcheck-"))
    try:
        check_estat(tmp)
        check_worldbank(tmp)
        print(f"\n差があった場合は docs/05-data-sources.md の「上流の改訂」に追記すること。"
              f"\ndata/raw/ は書き換えていない。")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
