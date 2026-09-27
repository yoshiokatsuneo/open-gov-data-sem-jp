# -*- coding: utf-8 -*-
"""都道府県別データ（e-Stat 社会生活統計指標）による転職の構造方程式モデリング。

問い: 転職が多い県は「労働市場が厚いから」なのか「雇用が不安定だから」なのか。

    都市労働市場の厚み ─┐
                        ├→ 転職率
    雇用の不安定さ ─────┘

この2つは無相関に近く、転職率へは別々の経路で効く、というのが結論。

前提: estat_fetch.py → estat_parse.py で estat_long.csv を作っておく。
実行: .venv/bin/python job_sem.py
"""
import paths

import numpy as np
import pandas as pd
import semopy

# 列名 → (指標コード, 採用年)
SPEC = {
    # 都市労働市場の厚み
    "dens":   ("#A01202", 2020),   # 可住地面積１k㎡当たり人口密度 → 対数化
    "inflow": ("#A05304", 2015),   # 流入人口比率
    "wage_f": ("#F0620104", 2021),  # きまって支給する現金給与月額（女）
    # 雇用の不安定さ
    "sep":    ("#F04102", 2017),   # 離職率
    "unemp":  ("#F01301", 2015),   # 完全失業率
    # 結果
    "jobchg": ("#F04101", 2017),   # 転職率
    # 参考（モデル外。頑健性チェックと解釈に使う）
    "wage_m": ("#F0620103", 2021),  # きまって支給する現金給与月額（男）
    "did":    ("#A01401", 2015),   # 人口集中地区人口比率
    "svc":    ("#F01203", 2015),   # 第３次産業就業者比率
    "offer":  ("#F03103", 2020),   # 有効求人倍率
}

MODEL = """
# ---- 測定モデル ----
URBAN  =~ ldens + inflow + wage_f
PRECAR =~ sep + unemp

# ---- 構造モデル ----
jobchg ~ URBAN + PRECAR

# 2つの説明側は独立かどうかを推定させる（固定しない）
URBAN ~~ PRECAR
"""

USED = ["ldens", "inflow", "wage_f", "sep", "unemp", "jobchg"]

LABELS = {
    "ldens": "人口密度（可住地・対数）", "inflow": "流入人口比率",
    "wage_f": "現金給与月額（女）", "wage_m": "現金給与月額（男）",
    "sep": "離職率", "unemp": "完全失業率", "jobchg": "転職率",
    "did": "人口集中地区人口比率", "svc": "第3次産業就業者比率", "offer": "有効求人倍率",
    "URBAN": "都市労働市場の厚み", "PRECAR": "雇用の不安定さ",
}


def wide():
    long = pd.read_csv(paths.processed("estat_long.csv"))
    long = long[long.pref_cd != 0]                    # 「全国」を落とす
    w = pd.DataFrame(index=sorted(long.pref_cd.unique()))
    w.index.name = "pref_cd"
    w["pref"] = long.drop_duplicates("pref_cd").set_index("pref_cd")["pref"]
    for col, (code, year) in SPEC.items():
        w[col] = long[(long.code == code) & (long.year == year)].set_index("pref_cd")["value"]
    w["ldens"] = np.log(w.dens)                       # 人口密度は右裾が極端に長い
    return w


def fit(z, desc=MODEL):
    m = semopy.Model(desc)
    m.fit(z)
    return m


def bootstrap(z, n=600, seed=0):
    """N=47 では漸近的な標準誤差が当てにならないので復元抽出で分布を見る。"""
    rng = np.random.default_rng(seed)
    keys = [("jobchg", "URBAN", "~"), ("jobchg", "PRECAR", "~"), ("URBAN", "PRECAR", "~~")]
    draws, ok = {k: [] for k in keys}, 0
    for _ in range(n):
        s = z.iloc[rng.integers(0, len(z), len(z))]
        try:
            from sem_audit import diagnose
            e, checks = diagnose(fit(s))
            if not checks["usable"]:
                continue
        except Exception:
            continue
        vals = {}
        for l, r, op in keys:
            row = e[(e.lval == l) & (e.rval == r) & (e.op == op)]
            if row.empty:
                row = e[(e.lval == r) & (e.rval == l) & (e.op == op)]
            if row.empty:
                break
            vals[(l, r, op)] = float(row["Est. Std"].iloc[0])
        if len(vals) == len(keys):
            ok += 1
            for k, v in vals.items():
                draws[k].append(v)
    return draws, ok


def main():
    w = wide()
    print(f"N = {len(w)} 都道府県　欠損 = {w[USED].isna().sum().sum()}\n")
    z = (w[USED] - w[USED].mean()) / w[USED].std()

    c = z.corr()
    c.index = [LABELS[i] for i in c.index]
    c.columns = [LABELS[i] for i in c.columns]
    print("=== 観測変数の相関 ===")
    print(c.round(2).to_string(), "\n")

    m = fit(z)
    s = semopy.calc_stats(m).T["Value"]
    print(f"=== 適合度 ===\nχ²/df = {s['chi2']/s['DoF']:.2f}　CFI = {s['CFI']:.3f}　"
          f"TLI = {s['TLI']:.3f}　RMSEA = {s['RMSEA']:.3f}　（df = {int(s['DoF'])}、N = {len(z)}）\n")

    e = m.inspect(std_est=True).rename(columns={"Est. Std": "std", "Std. Err": "se",
                                                "p-value": "p"})
    lat = set(m.vars["latent"])
    load = e[(e.op == "~") & e.rval.isin(lat) & (e.lval != "jobchg")]
    stru = e[((e.op == "~") & (e.lval == "jobchg")) |
             ((e.op == "~~") & (e.lval != e.rval))]
    for t, sub in [("因子負荷（標準化）", load), ("パス・共分散（標準化）", stru)]:
        d = sub.copy()
        d["から"] = d.rval.map(lambda x: LABELS.get(x, x))
        d["へ"] = d.lval.map(lambda x: LABELS.get(x, x))
        print(f"--- {t} ---")
        print(d[["から", "op", "へ", "std", "se", "p"]].to_string(index=False), "\n")

    sigma, _ = m.calc_sigma()
    nm = list(m.vars["observed"])
    cm = lambda M: M / np.outer(np.sqrt(np.diag(M)), np.sqrt(np.diag(M)))
    R = pd.DataFrame(cm(z[nm].cov().values) - cm(sigma), index=nm, columns=nm)
    iu = np.triu_indices(len(nm), 1)
    print(f"残差相関の最大絶対値: {abs(R.values[iu]).max():.3f}\n")

    print("=== ブートストラップ（復元抽出600回、標準化係数の95%区間）===")
    draws, ok = bootstrap(z)
    rows = []
    for (l, r, op), v in draws.items():
        v = np.array(v)
        lo, hi = np.percentile(v, 2.5), np.percentile(v, 97.5)
        rows.append({"key": f"{l}{op}{r}",
                     "パス": f"{LABELS.get(r,r)} {'→' if op=='~' else '↔'} {LABELS.get(l,l)}",
                     "中央値": np.median(v), "2.5%": lo, "97.5%": hi,
                     "0をまたぐ": "はい" if lo * hi < 0 else "いいえ"})
    boot = pd.DataFrame(rows)
    print(f"収束 {ok}/600 回")
    print(boot.drop(columns="key").round(3).to_string(index=False), "\n")

    # 頑健性: 給与を男に差し替える / 指標を足す
    print("=== 頑健性（主要パスの標準化係数）===")
    alts = {
        "採用モデル（給与=女）": (MODEL, USED),
        "給与を男に差し替え": (MODEL.replace("wage_f", "wage_m"),
                               [c if c != "wage_f" else "wage_m" for c in USED]),
        "都市度に人口集中地区を追加": (MODEL.replace("ldens + inflow", "ldens + did + inflow"),
                                       USED + ["did"]),
        "不安定さに第3次産業比率を追加": (MODEL.replace("sep + unemp", "sep + unemp + svc"),
                                           USED + ["svc"]),
    }
    for name, (desc, cols) in alts.items():
        zz = (w[cols] - w[cols].mean()) / w[cols].std()
        mm = fit(zz, desc)
        ee = mm.inspect(std_est=True)
        ss = semopy.calc_stats(mm).T["Value"]
        g = lambda r: float(ee[(ee.lval == "jobchg") & (ee.rval == r) & (ee.op == "~")]["Est. Std"].iloc[0])
        print(f"  {name:28s} CFI={ss['CFI']:.3f} RMSEA={ss['RMSEA']:.3f}  "
              f"都市→転職={g('URBAN'):+.3f}  不安定→転職={g('PRECAR'):+.3f}")

    w.to_csv(paths.result("job_sample.csv"))
    e.to_csv(paths.result("job_estimates.csv"), index=False)
    s.to_csv(paths.result("job_fit.csv"))
    boot.to_csv(paths.result("job_bootstrap.csv"), index=False)
    print("\n-> job_sample.csv / job_estimates.csv / job_fit.csv / job_bootstrap.csv")


if __name__ == "__main__":
    main()
