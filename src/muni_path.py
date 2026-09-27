# -*- coding: utf-8 -*-
"""市区町村（N=1,690）の観測変数パス解析。出力: muni_path_*.csv

潜在変数モデルは市区町村では成立しなかった（指標が因子にまとまらず RMSEA 0.22〜0.32）。
そこで測定モデルを持たない、観測変数だけのパス解析（SEMの原型）に切り替える。

    人口密度 → 通勤流出率 → 単独世帯割合 → 総移動率
       （高齢化率を経由する経路も併走）

ベッドタウン（通勤流出が多い）は家族世帯が多く単身が少ない、という関係を
経路として明示したところ適合が一気に改善した（CFI 1.000 / RMSEA 0.022）。
"""
import paths

import numpy as np
import pandas as pd
import semopy

MODEL = """
commute_out ~ ldens
old         ~ ldens
solo        ~ ldens + old + commute_out
move_rate   ~ commute_out + solo + old + ldens
"""

V = ["ldens", "commute_out", "old", "solo", "move_rate"]
LABELS = {
    "ldens": "人口密度（可住地・対数）", "commute_out": "通勤流出率",
    "old": "高齢化率", "solo": "単独世帯割合", "move_rate": "総移動率",
}
POP_FLOOR = 1000


def wide():
    raw = pd.read_csv(paths.processed("muni_raw.csv"), index_col=0)
    raw.index = raw.index.astype(int)
    r = pd.read_csv(paths.processed("muni_rates.csv"), index_col=0).replace([np.inf, -np.inf], np.nan)
    g = lambda c: pd.to_numeric(raw[c], errors="coerce")
    # 他市区町村への通勤者 ÷ 就業者。スクリーニングで残差との相関が最大だった指標
    r["commute_out"] = (g("F2705") / g("F1102")).reindex(r.index)
    return r[r["pop"] >= POP_FLOOR].dropna(subset=V)


def fit(z):
    m = semopy.Model(MODEL)
    m.fit(z)
    return m


def coefs(m):
    e = m.inspect(std_est=True)
    e = e[e.op == "~"]
    return {(r.lval, r.rval): float(r["Est. Std"]) for _, r in e.iterrows()}


def effects(c):
    """総移動率への直接・間接効果を分解する。"""
    dens_direct = c[("move_rate", "ldens")]
    via_commute = c[("commute_out", "ldens")] * c[("move_rate", "commute_out")]
    via_commute_solo = (c[("commute_out", "ldens")] * c[("solo", "commute_out")]
                        * c[("move_rate", "solo")])
    via_solo = c[("solo", "ldens")] * c[("move_rate", "solo")]
    via_old = c[("old", "ldens")] * c[("move_rate", "old")]
    via_old_solo = c[("old", "ldens")] * c[("solo", "old")] * c[("move_rate", "solo")]
    ind = via_commute + via_commute_solo + via_solo + via_old + via_old_solo
    return {"直接": dens_direct, "通勤流出経由": via_commute,
            "通勤流出→単身経由": via_commute_solo, "単身経由": via_solo,
            "高齢化経由": via_old, "高齢化→単身経由": via_old_solo,
            "間接合計": ind, "総効果": dens_direct + ind}


def bootstrap(z, n=400, seed=0):
    rng = np.random.default_rng(seed)
    keys = [("move_rate", "solo"), ("move_rate", "old"), ("move_rate", "commute_out"),
            ("move_rate", "ldens"), ("solo", "commute_out")]
    draws, tot, ok = {k: [] for k in keys}, [], 0
    for _ in range(n):
        s = z.iloc[rng.integers(0, len(z), len(z))]
        try:
            from sem_audit import diagnose
            m = fit(s)
            _, checks = diagnose(m)
            if not checks["usable"]:
                continue
            c = coefs(m)
        except Exception:
            continue
        if all(k in c for k in keys):
            ok += 1
            for k in keys:
                draws[k].append(c[k])
            tot.append(effects(c)["総効果"])
    return draws, np.array(tot), ok


def main():
    d = wide()
    z = (d[V] - d[V].mean()) / d[V].std()
    print(f"N = {len(d):,} 市区町村（人口{POP_FLOOR:,}人以上、"
          f"政令市・特別区部の合計行を除き区単位）\n")

    m = fit(z)
    s = semopy.calc_stats(m).T["Value"]
    print(f"=== 適合度 ===\nχ²/df = {s['chi2']/s['DoF']:.2f}　CFI = {s['CFI']:.3f}　"
          f"TLI = {s['TLI']:.3f}　RMSEA = {s['RMSEA']:.3f}　df = {int(s['DoF'])}\n")

    e = m.inspect(std_est=True).rename(columns={"Est. Std": "std", "Std. Err": "se",
                                                "p-value": "p"})
    st = e[e.op == "~"].copy()
    st["から"] = st.rval.map(lambda x: LABELS.get(x, x))
    st["へ"] = st.lval.map(lambda x: LABELS.get(x, x))
    print("--- パス係数（標準化）---")
    print(st[["から", "へ", "std", "se", "p"]].to_string(index=False), "\n")

    sigma, _ = m.calc_sigma()
    nm = list(m.vars["observed"])
    cm = lambda M: M / np.outer(np.sqrt(np.diag(M)), np.sqrt(np.diag(M)))
    R = pd.DataFrame(cm(z[nm].cov().values) - cm(sigma), index=nm, columns=nm)
    iu = np.triu_indices(len(nm), 1)
    print(f"残差相関の最大絶対値: {abs(R.values[iu]).max():.3f}\n")

    c = coefs(m)
    eff = effects(c)
    print("=== 人口密度から総移動率への効果分解（標準化）===")
    for k, v in eff.items():
        print(f"  {k:20s} {v:+.3f}")

    print("\n=== ブートストラップ（400回、95%区間）===")
    draws, tot, ok = bootstrap(z)
    rows = []
    for (l, r), v in draws.items():
        v = np.array(v)
        rows.append({"key": f"{l}~{r}",
                     "パス": f"{LABELS[r]} → {LABELS[l]}", "中央値": np.median(v),
                     "2.5%": np.percentile(v, 2.5), "97.5%": np.percentile(v, 97.5)})
    rows.append({"key": "total", "パス": "人口密度 → 総移動率（総効果）",
                 "中央値": np.median(tot), "2.5%": np.percentile(tot, 2.5),
                 "97.5%": np.percentile(tot, 97.5)})
    boot = pd.DataFrame(rows)
    print(f"収束 {ok}/400 回")
    print(boot.drop(columns="key").round(3).to_string(index=False))

    boot.to_csv(paths.result("muni_path_bootstrap.csv"), index=False)
    e.to_csv(paths.result("muni_path_estimates.csv"), index=False)
    s.to_csv(paths.result("muni_path_fit.csv"))
    pd.Series(eff).to_csv(paths.result("muni_path_effects.csv"))
    d.to_csv(paths.result("muni_path_sample.csv"))
    print("\n-> muni_path_*.csv")


if __name__ == "__main__":
    main()
