# -*- coding: utf-8 -*-
"""市区町村データ（N≈1,660）での分析とスクリーニング。

出力: muni_screen.csv / muni_chart.svg

都道府県版の転職モデルを市区町村で再現しようとしたが、
  (1) 転職率（就業構造基本調査）は市区町村まで下りていないので、総移動率で代用した
  (2) 総移動率は労働市場ではなく世帯構成で決まる（単独世帯割合と r = 0.62）
  (3) 都道府県で成立した「都市労働市場の厚み」の因子は市区町村では成立しない
      （同じ3指標の相互相関が 0.70-0.88 → 0.37-0.62 に落ちる＝集計による水増し）
ので、同じ問いには答えられない。一方で N が 35 倍になったぶん、
残差スクリーニングの検出力は本来の水準になる。
"""
import paths

import os

import numpy as np
import pandas as pd


POP_FLOOR = 1000            # 人口1,000人未満は率が不安定なので除外
N_PERM = 2000

# 予測に使う変数（潜在変数は立てない。市区町村では因子にまとまらないため）
PRED = ["ldens", "svc", "tax_pc", "daytime", "unemp", "kokuho", "nonemp",
        "young", "old", "solo"]

# 既に比率・指数なので人口で割らない指標
NOT_PER_CAPITA = {"D2201", "D2202", "D2211", "H2130", "H5614"}
# 結果変数の材料（スクリーニング対象から外す）
DROP = {"A5103", "A5104", "A2301", "A1101"}


def load():
    r = pd.read_csv(paths.processed("muni_rates.csv"), index_col=0)
    r = r.replace([np.inf, -np.inf], np.nan)
    return r[r["pop"] >= POP_FLOOR]


def all_rates(index):
    """89の実数指標を人口当たりに直して、スクリーニング用の行列にする。"""
    raw = pd.read_csv(paths.processed("muni_raw.csv"), index_col=0)
    raw.index = raw.index.astype(int)
    pop = pd.to_numeric(raw["A1101"], errors="coerce")
    out = {}
    for c in raw.columns:
        if c in ("name",) or c in DROP:
            continue
        v = pd.to_numeric(raw[c], errors="coerce")
        out[c] = v if c in NOT_PER_CAPITA else v / pop
    X = pd.DataFrame(out).replace([np.inf, -np.inf], np.nan).loc[index]
    return X.loc[:, X.notna().sum() >= len(index) * 0.9]


def screen(X, res, seed=0):
    ok = X.notna().all(axis=1)
    A = X[ok].values
    A = (A - A.mean(0)) / A.std(0)
    v = res[ok.values]
    v = (v - v.mean()) / v.std()
    n = len(v)
    r = A.T @ v / n
    rng = np.random.default_rng(seed)
    mx = np.array([np.abs(A.T @ rng.permutation(v) / n).max() for _ in range(N_PERM)])
    return r, mx, n, ok


def main():
    d = load()
    print(f"市区町村（人口{POP_FLOOR:,}人以上）: {len(d):,}\n")

    m = d.dropna(subset=PRED + ["move_rate"])
    z = (m[PRED] - m[PRED].mean()) / m[PRED].std()
    y = (m.move_rate - m.move_rate.mean()) / m.move_rate.std()
    A = np.column_stack([np.ones(len(m))] + [z[c].values for c in PRED])
    beta, *_ = np.linalg.lstsq(A, y.values, rcond=None)
    pred = A @ beta
    res = y.values - pred
    r2 = 1 - (res ** 2).sum() / ((y - y.mean()) ** 2).sum()
    print(f"=== 総移動率の重回帰　N = {len(m):,}　R² = {r2:.3f} ===")
    for nm, b in sorted(zip(PRED, beta[1:]), key=lambda t: -abs(t[1])):
        print(f"  {nm:9s} {b:+.3f}")

    # 集計レベルによる指標間相関の違い
    p = pd.read_csv(paths.result("job_sample.csv"), index_col=0)
    p["ldens"] = np.log(p.dens)
    print("\n=== 同じ「都市度」指標の相互相関：集計レベルによる差 ===")
    print(f"  都道府県(N=47)   密度×賃金 {p.ldens.corr(p.wage_f):.2f}　"
          f"密度×流入 {p.ldens.corr(p.inflow):.2f}　賃金×流入 {p.wage_f.corr(p.inflow):.2f}")
    print(f"  市区町村(N={len(m):,}) 密度×所得 {m.ldens.corr(m.tax_pc):.2f}　"
          f"密度×3次産業 {m.ldens.corr(m.svc):.2f}　所得×3次産業 {m.tax_pc.corr(m.svc):.2f}")

    X = all_rates(m.index)
    X = X.drop(columns=[c for c in X.columns if c in DROP], errors="ignore")
    r, mx, n, ok = screen(X, res)
    thr = np.percentile(mx, 95)
    print(f"\n=== 残差スクリーニング　{X.shape[1]}指標 × N = {n:,} ===")
    print(f"  帰無分布の最大|r| 95%点 = {thr:.3f}（都道府県版は 0.529 だった）")
    meta = pd.read_csv(paths.processed("muni_meta.csv")).set_index("code")
    hit = pd.DataFrame({"code": X.columns, "r": r})
    hit["name"] = [meta.name.get(c, c) for c in hit.code]
    hit["year"] = [meta.year.get(c, "") for c in hit.code]
    hit = hit.reindex(hit.r.abs().sort_values(ascending=False).index)
    print(f"  閾値を超えた指標: {(hit.r.abs() > thr).sum()}件 / {len(hit)}件")
    for _, x in hit.head(10).iterrows():
        print(f"   {'★' if abs(x.r) > thr else ' '} r={x.r:+.3f}  {x['name'][:40]}（人口当たり）")
    hit.to_csv(paths.result("muni_screen.csv"), index=False)
    np.save(paths.result("muni_perm.npy"), mx)
    print("\n-> muni_screen.csv")
    return d, m, res, X, r, mx, thr


if __name__ == "__main__":
    main()
