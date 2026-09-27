# -*- coding: utf-8 -*-
"""国レベルSEMの作り込み版。出力: country2_*.csv

Model B（初版）は人的資本と初期所得が r = 0.91 で、両方を成長式に入れたため
標準化係数が −1.07 まで飛ぶ抑制が出ていた。指標をどう入れ替えても
相関は 0.83〜0.90 から下がらず、これは仕様の誤りではなくデータの構造。

そこで人的資本の各指標を初期所得に回帰した残差に置き換える。
「その所得水準の国として期待される以上に、人的資本が厚いか」を測る潜在変数になり、
初期所得と定義上直交するので抑制が消える。
"""
import paths

import numpy as np
import pandas as pd
import semopy

from sem_analysis import derive

HC = ["life_exp_12", "child_surv_12", "school_sec_12"]
HCR = [c + "_r" for c in HC]
BASE = ["rule_of_law", "gov_effect", "control_corrupt", "reg_quality",
        "g_gdp", "g_gni", "g_cons", "init_gdp"]

MODEL = f"""
GOV =~ rule_of_law + gov_effect + control_corrupt + reg_quality
GROWTH =~ g_gdp + g_gni + g_cons
HCX =~ {' + '.join(HCR)}

HCX ~ GOV
GROWTH ~ GOV + HCX + init_gdp

GOV ~~ init_gdp
HCX ~~ init_gdp
rule_of_law ~~ control_corrupt
gov_effect  ~~ reg_quality
"""

LABELS = {
    "rule_of_law": "法の支配", "gov_effect": "政府の有効性",
    "control_corrupt": "腐敗の抑制", "reg_quality": "規制の質",
    "life_exp_12_r": "平均寿命（所得調整後）", "child_surv_12_r": "乳幼児生存（所得調整後）",
    "school_sec_12_r": "中等教育就学率（所得調整後）",
    "g_gdp": "一人当たりGDP成長", "g_gni": "一人当たりGNI成長", "g_cons": "一人当たり消費成長",
    "init_gdp": "初期所得(2012)", "GOV": "制度の質", "HCX": "所得水準を超えた人的資本",
    "GROWTH": "その後10年の成長",
}


def prepare():
    df = derive()
    cols = BASE + HC
    d = df.dropna(subset=cols).copy()
    z = (d[cols] - d[cols].mean()) / d[cols].std()
    # 人的資本の各指標から、初期所得で説明できる分を抜く
    for c in HC:
        b = np.polyfit(z.init_gdp, z[c], 1)
        e = z[c] - (b[0] * z.init_gdp + b[1])
        z[c + "_r"] = (e - e.mean()) / e.std()
    z["income"] = d["income"].values
    z["country"] = d["country"].values
    return z


def fit(z):
    m = semopy.Model(MODEL)
    m.fit(z[BASE + HCR])
    return m


def path_coefs(m):
    e = m.inspect(std_est=True)
    return {(r.lval, r.rval, r.op): float(r["Est. Std"]) for _, r in e.iterrows()}


KEYS = [("HCX", "GOV", "~"), ("GROWTH", "GOV", "~"),
        ("GROWTH", "HCX", "~"), ("GROWTH", "init_gdp", "~")]


def bootstrap(z, n=600, seed=0):
    rng = np.random.default_rng(seed)
    draws, ok = {k: [] for k in KEYS}, 0
    for _ in range(n):
        s = z.iloc[rng.integers(0, len(z), len(z))]
        try:
            from sem_audit import diagnose
            m = fit(s)
            _, checks = diagnose(m)
            if not checks["usable"]:
                continue
            p = path_coefs(m)
        except Exception:
            continue
        if all(k in p for k in KEYS):
            ok += 1
            for k in KEYS:
                draws[k].append(p[k])
    return draws, ok


def main():
    z = prepare()
    print(f"N = {len(z)} か国\n")
    m = fit(z)
    s = semopy.calc_stats(m).T["Value"]
    print(f"=== 適合度 ===\nχ²/df = {s['chi2']/s['DoF']:.2f}　CFI = {s['CFI']:.3f}　"
          f"TLI = {s['TLI']:.3f}　RMSEA = {s['RMSEA']:.3f}　df = {int(s['DoF'])}\n")

    e = m.inspect(std_est=True).rename(columns={"Est. Std": "std", "Std. Err": "se",
                                                "p-value": "p"})
    lat = set(m.vars["latent"])
    load = e[(e.op == "~") & e.rval.isin(lat) & ~e.lval.isin(lat)]
    stru = e[((e.op == "~") & e.lval.isin(lat)) |
             ((e.op == "~~") & (e.lval != e.rval))]
    for t, sub in (("因子負荷（標準化）", load), ("パス・共分散（標準化）", stru)):
        d = sub.copy()
        d["から"] = d.rval.map(lambda x: LABELS.get(x, x))
        d["へ"] = d.lval.map(lambda x: LABELS.get(x, x))
        print(f"--- {t} ---")
        print(d[["から", "op", "へ", "std", "se", "p"]].to_string(index=False), "\n")

    print("=== ブートストラップ（復元抽出600回、95%区間）===")
    draws, ok = bootstrap(z)
    rows = []
    for (l, r, op), v in draws.items():
        v = np.array(v)
        lo, hi = np.percentile(v, 2.5), np.percentile(v, 97.5)
        rows.append({"key": f"{l}{op}{r}",
                     "パス": f"{LABELS.get(r,r)} → {LABELS.get(l,l)}",
                     "中央値": np.median(v), "2.5%": lo, "97.5%": hi,
                     "0をまたぐ": "はい" if lo * hi < 0 else "いいえ"})
    boot = pd.DataFrame(rows)
    print(f"収束 {ok}/600 回")
    print(boot.drop(columns="key").round(3).to_string(index=False), "\n")

    # ---- 所得グループ別：構造は共通か ----
    print("=== 所得グループ別（高所得 vs それ以外）===")
    grp = {"高所得": z.income == "High income", "中低所得": z.income != "High income"}
    rows = []
    for name, sel in grp.items():
        sub = z[sel]
        mm = fit(sub)
        ss = semopy.calc_stats(mm).T["Value"]
        p = path_coefs(mm)
        dr, _ = bootstrap(sub, n=400, seed=1)
        row = {"グループ": name, "N": len(sub), "CFI": ss["CFI"], "RMSEA": ss["RMSEA"]}
        for k in KEYS:
            v = np.array(dr[k])
            row[LABELS[k[1]] + "→" + LABELS[k[0]]] = (
                f"{p[k]:+.2f} [{np.percentile(v,2.5):+.2f},{np.percentile(v,97.5):+.2f}]")
        rows.append(row)
    g = pd.DataFrame(rows)
    print(g.to_string(index=False))

    boot.to_csv(paths.result("country2_bootstrap.csv"), index=False)
    e.to_csv(paths.result("country2_estimates.csv"), index=False)
    s.to_csv(paths.result("country2_fit.csv"))
    g.to_csv(paths.result("country2_groups.csv"), index=False)
    z.to_csv(paths.result("country2_sample.csv"))
    print("\n-> country2_*.csv")


if __name__ == "__main__":
    main()
