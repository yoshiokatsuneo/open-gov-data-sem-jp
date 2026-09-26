# -*- coding: utf-8 -*-
"""都道府県別データ（e-Stat 社会生活統計指標 2024）による構造方程式モデリング。

問い: 都道府県の健康格差は「経済的豊かさ」で説明できるのか、
      それとも「医療の供給量」なのか。そして男女で違うのか。

    経済的豊かさ ──┬─────────────→ 平均寿命(男)
                   │                ↗
                   └→ 入院医療キャパ ─→ 平均寿命(女)

国レベル（World Bank）では豊かさと健康が同一次元に潰れたが、
47都道府県では両者が分離するかどうかが見どころ。

実行: python estat_sem.py   （先に estat_fetch.py → estat_parse.py）
"""
import paths

import numpy as np
import pandas as pd
import semopy

from estat_parse import load_all

# 列名 → (指標コード, 採用年)
SPEC = {
    # 経済的豊かさ
    "income":     ("#C01321", 2015),   # １人当たり県民所得
    "tax_income": ("#D02206", 2015),   # 課税対象所得（納税義務者１人当たり）
    "univ_rate":  ("#E09402", 2015),   # 高等学校卒業者の進学率
    # 入院医療キャパシティ（人口当たり）
    "nurses":     ("#I0920301", 2016),  # 看護師・准看護師数（人口10万人当たり）
    "beds":       ("#I0910203", 2015),  # 一般病院病床数（人口10万人当たり）
    "hosp":       ("#I0910103", 2015),  # 一般病院数（人口10万人当たり）
    # 健康アウトカム
    "le_m":       ("#I0520101", 2015),  # 平均余命（０歳・男）＝男性の平均寿命
    "le_f":       ("#I0520102", 2015),  # 平均余命（０歳・女）＝女性の平均寿命
    # 参考（モデルには入れない）
    "doctors":    ("#I0920101", 2016),  # 医療施設に従事する医師数（人口10万人当たり）
}

MODEL = """
# ---- 測定モデル ----
WEALTH =~ income + tax_income + univ_rate
MED    =~ nurses + beds + hosp

# ---- 構造モデル ----
MED  ~ WEALTH
le_m ~ WEALTH + MED
le_f ~ WEALTH + MED

# 男女の平均寿命は同じ県の同じ環境を共有する
le_m ~~ le_f
"""

USED = ["income", "tax_income", "univ_rate", "nurses", "beds", "hosp", "le_m", "le_f"]

LABELS = {
    "income": "１人当たり県民所得", "tax_income": "課税対象所得", "univ_rate": "大学等進学率",
    "nurses": "看護師数", "beds": "一般病院病床数", "hosp": "一般病院数",
    "le_m": "平均寿命(男)", "le_f": "平均寿命(女)", "doctors": "医師数",
    "WEALTH": "経済的豊かさ", "MED": "入院医療キャパシティ",
}


def wide():
    """縦持ちの estat_long から、分析用の47行×指標 の表を作る。"""
    long = load_all()
    long = long[long.pref_cd != "00"]                 # 「全国」を落とす
    names = long.drop_duplicates("pref_cd").set_index("pref_cd")["pref"]
    w = pd.DataFrame(index=sorted(long.pref_cd.unique()))
    w.index.name = "pref_cd"
    w["pref"] = names
    for col, (code, year) in SPEC.items():
        s = long[(long.code == code) & (long.year == year)].set_index("pref_cd")["value"]
        w[col] = s
    return w


def fit(z, desc=MODEL):
    m = semopy.Model(desc)
    m.fit(z)
    return m


def bootstrap(z, n=600, seed=0):
    """N=47 なので漸近的な標準誤差は当てにならない。非復元でなく復元抽出で分布を見る。"""
    rng = np.random.default_rng(seed)
    keys = [("MED", "WEALTH"), ("le_m", "WEALTH"), ("le_m", "MED"),
            ("le_f", "WEALTH"), ("le_f", "MED")]
    draws = {k: [] for k in keys}
    ok = 0
    for _ in range(n):
        s = z.iloc[rng.integers(0, len(z), len(z))]
        try:
            e = fit(s).inspect(std_est=True)
        except Exception:
            continue
        e = e[e.op == "~"]
        vals = {}
        for l, r in keys:
            row = e[(e.lval == l) & (e.rval == r)]
            if row.empty:
                break
            vals[(l, r)] = float(row["Est. Std"].iloc[0])
        if len(vals) == len(keys):
            ok += 1
            for k, v in vals.items():
                draws[k].append(v)
    return draws, ok


def main():
    w = wide()
    print(f"N = {len(w)} 都道府県　欠損 = {w[USED].isna().sum().sum()}\n")

    z = (w[USED] - w[USED].mean()) / w[USED].std()
    print("=== 観測変数の相関 ===")
    c = z.corr()
    c.index = [LABELS[i] for i in c.index]
    c.columns = [LABELS[i] for i in c.columns]
    print(c.round(2).to_string(), "\n")

    m = fit(z)
    s = semopy.calc_stats(m).T["Value"]
    print(f"=== 適合度 ===\nχ²/df = {s['chi2']/s['DoF']:.2f}　CFI = {s['CFI']:.3f}　"
          f"TLI = {s['TLI']:.3f}　RMSEA = {s['RMSEA']:.3f}　"
          f"（自由度 {int(s['DoF'])}、N = {len(z)}）\n")

    e = m.inspect(std_est=True).rename(columns={"Est. Std": "std", "Std. Err": "se",
                                                "p-value": "p"})
    lat = set(m.vars["latent"])
    load = e[(e.op == "~") & e.rval.isin(lat) & ~e.lval.isin(lat) & ~e.lval.isin(["le_m", "le_f"])]
    stru = e[(e.op == "~") & ~e.index.isin(load.index) & (e.rval != "1")]

    def show(t, sub):
        d = sub.copy()
        d["→"] = d.lval.map(lambda x: LABELS.get(x, x))
        d["←"] = d.rval.map(lambda x: LABELS.get(x, x))
        print(f"--- {t} ---")
        print(d[["←", "→", "std", "se", "p"]].to_string(index=False), "\n")

    show("因子負荷（標準化）", load)
    show("パス係数（標準化）", stru)

    # 残差相関で局所的な当てはまりを確認
    sigma, _ = m.calc_sigma()
    nm = list(m.vars["observed"])
    cm = lambda M: M / np.outer(np.sqrt(np.diag(M)), np.sqrt(np.diag(M)))
    R = pd.DataFrame(cm(z[nm].cov().values) - cm(sigma), index=nm, columns=nm)
    iu = np.triu_indices(len(nm), 1)
    print(f"残差相関の最大絶対値: {abs(R.values[iu]).max():.3f}\n")

    print("=== ブートストラップ（復元抽出 600 回、標準化係数の 95% 区間）===")
    draws, ok = bootstrap(z)
    rows = []
    for (l, r), v in draws.items():
        v = np.array(v)
        rows.append({"パス": f"{LABELS.get(r, r)} → {LABELS.get(l, l)}",
                     "中央値": np.median(v),
                     "2.5%": np.percentile(v, 2.5), "97.5%": np.percentile(v, 97.5),
                     "0をまたぐ": "はい" if np.percentile(v, 2.5) * np.percentile(v, 97.5) < 0 else "いいえ"})
    print(f"収束 {ok}/600 回")
    boot = pd.DataFrame(rows)
    print(boot.round(3).to_string(index=False), "\n")
    boot.insert(0, "key", [f"{l}<-{r}" for (l, r) in draws])
    boot.to_csv(paths.result("pref_bootstrap.csv"), index=False)

    # 参考: 医師数はモデルから外したが、男女差が出る変数なので生の相関だけ見ておく
    d = w[["doctors", "le_m", "le_f", "income"]].corr().round(2)
    print("=== 参考：医師数（モデル外）の相関 ===")
    print(d.loc["doctors"].to_string())

    w.to_csv(paths.result("pref_sample.csv"))
    e.to_csv(paths.result("pref_estimates.csv"), index=False)
    s.to_csv(paths.result("pref_fit.csv"))
    print("\n-> pref_sample.csv / pref_estimates.csv / pref_fit.csv / pref_bootstrap.csv")


if __name__ == "__main__":
    main()
