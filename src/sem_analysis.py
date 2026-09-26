"""World Bank オープンデータによる構造方程式モデリング（SEM）。

Model A（水準 → 水準）:
    制度(2012) → 人的資本(2015-19) → 繁栄(2020-23)
    ... 判別妥当性の検証用。結論としては採用しない。

Model B（初期条件 → その後の成長）= 最終モデル:
    制度(2012) ┐
               ├→ 人的資本(2012) ─→ 成長(2012→2022)
    初期所得 ──┘         └────────────────↗

実行: python sem_analysis.py   （事前に fetch_data.py で wb_raw.csv を作る）
"""
import paths

import numpy as np
import pandas as pd
import semopy

RAW = paths.raw("wb_raw.csv")

MODEL_A = """
GOV  =~ rule_of_law + gov_effect + control_corrupt + reg_quality
HC   =~ life_exp_17 + child_surv_17 + school_sec_17
PROS =~ log_gdp_pc_22 + internet_users + log_broadband
HC   ~ GOV
PROS ~ GOV + HC
"""

MODEL_B = """
# ---- 測定モデル ----
GOV    =~ rule_of_law + gov_effect + control_corrupt + reg_quality
HC     =~ life_exp_12 + child_surv_12 + school_sec_12
GROWTH =~ g_gdp + g_gni + g_cons

# ---- 構造モデル ----
HC     ~ GOV + init_gdp
GROWTH ~ GOV + HC + init_gdp

# ---- 外生変数間の共分散 ----
GOV ~~ init_gdp

# ---- 残差相関（WGI は同一の原データを共有するため方法要因が残る）----
rule_of_law ~~ control_corrupt
gov_effect  ~~ reg_quality
"""

LABELS = {
    "rule_of_law": "法の支配", "gov_effect": "政府の有効性",
    "control_corrupt": "腐敗の抑制", "reg_quality": "規制の質",
    "life_exp_12": "平均寿命(2012)", "child_surv_12": "乳幼児生存(2012)",
    "school_sec_12": "中等教育就学率(2012)",
    "g_gdp": "一人当たりGDP成長", "g_gni": "一人当たりGNI成長",
    "g_cons": "一人当たり消費成長",
    "init_gdp": "初期所得(2012)",
    "GOV": "制度の質", "HC": "人的資本", "GROWTH": "その後の成長",
    "PROS": "経済的繁栄",
}


def derive(path=RAW):
    df = pd.read_csv(path, index_col="iso3")
    # 右裾の長い金額系は対数化。死亡率は符号を反転して「生存」に揃える
    df["init_gdp"] = np.log(df.gdp_pc_12)
    df["child_surv_12"] = -np.log(df.under5_mort_12)
    df["child_surv_17"] = -np.log(df.under5_mort_17)
    df["log_gdp_pc_22"] = np.log(df.gdp_pc_22)
    df["log_broadband"] = np.log1p(df.broadband)
    # 2012 → 2022 の対数差 ＝ 累積成長率
    df["g_gdp"] = np.log(df.gdp_pc_22) - np.log(df.gdp_pc_12)
    df["g_gni"] = np.log(df.gni_pc_22) - np.log(df.gni_pc_12)
    df["g_cons"] = np.log(df.cons_pc_22) - np.log(df.cons_pc_12)
    return df


def observed_of(desc):
    """モデル記述から観測変数名を拾う。"""
    out = []
    for line in desc.splitlines():
        line = line.split("#")[0].strip()
        if "=~" in line:
            out += [t for t in line.split("=~")[1].replace("+", " ").split()]
        elif "~" in line and "~~" not in line:
            rhs = line.split("~")[1].replace("+", " ").split()
            out += [t for t in rhs if t in ("init_gdp",)]
    return sorted(set(out))


def run(desc, df, title):
    obs = observed_of(desc)
    keep = df.dropna(subset=obs)
    z = (keep[obs] - keep[obs].mean()) / keep[obs].std()  # 標準化解を読むため

    model = semopy.Model(desc)
    model.fit(z)
    est = model.inspect(std_est=True).rename(
        columns={"Est. Std": "std", "Std. Err": "se", "p-value": "p"})
    stats = semopy.calc_stats(model).T["Value"]

    print(f"\n{'=' * 64}\n{title}   N = {len(keep)}  観測変数 {len(obs)}\n{'=' * 64}")
    print(f"χ²/df = {stats['chi2'] / stats['DoF']:.2f}   CFI = {stats['CFI']:.3f}   "
          f"TLI = {stats['TLI']:.3f}   RMSEA = {stats['RMSEA']:.3f}")

    lat = set(model.vars["latent"])
    load = est[(est.op == "~") & est.rval.isin(lat) & ~est.lval.isin(lat)]
    path_ = est[(est.op == "~") & ~(est.rval.isin(lat) & ~est.lval.isin(lat)) & (est.rval != "1")]

    def show(t, sub, cols):
        print(f"\n--- {t} ---")
        d = sub.copy()
        d["from"] = d.rval.map(lambda x: LABELS.get(x, x))
        d["to"] = d.lval.map(lambda x: LABELS.get(x, x))
        print(d[cols].to_string(index=False))

    show("因子負荷（標準化）", load, ["to", "from", "std", "se", "p"])
    show("パス係数（標準化）", path_, ["from", "to", "std", "se", "p"])

    # 残差相関で局所的な当てはまりを確認する（MI の代用）
    sigma, _ = model.calc_sigma()
    names = list(model.vars["observed"])
    cm = lambda M: M / np.outer(np.sqrt(np.diag(M)), np.sqrt(np.diag(M)))
    R = pd.DataFrame(cm(z[names].cov().values) - cm(sigma), index=names, columns=names)
    worst = max(abs(R.values[np.triu_indices(len(names), 1)]))
    print(f"\n残差相関の最大絶対値: {worst:.3f}")
    return model, est, stats, keep


def main():
    df = derive()

    run(MODEL_A, df, "Model A: 制度 → 人的資本 → 繁栄（すべて水準）")
    print("\n※ Model A の HC → PROS は標準化係数がほぼ 1。"
          "\n   国レベルの横断データでは人的資本と繁栄が同一次元に潰れ、判別妥当性を満たさない。"
          "\n   → 結果変数を「水準」から「その後の成長」に変更したものが Model B。")

    model, est, stats, keep = run(
        MODEL_B, df, "Model B（最終）: 初期条件 → その後10年の成長")

    p = {(r.lval, r.rval): r["std"] for _, r in est[est.op == "~"].iterrows()}
    a, b, c = p[("HC", "GOV")], p[("GROWTH", "HC")], p[("GROWTH", "GOV")]
    print("\n--- 制度の効果の分解（標準化）---")
    print(f"  直接効果 GOV → GROWTH        : {c:+.3f}")
    print(f"  間接効果 GOV → HC → GROWTH   : {a * b:+.3f}")
    print(f"  総効果                        : {c + a * b:+.3f}")

    est.to_csv(paths.result("sem_estimates.csv"), index=False)
    stats.to_csv(paths.result("sem_fit.csv"))
    keep.to_csv(paths.result("sem_sample.csv"))
    print("\n-> sem_estimates.csv / sem_fit.csv / sem_sample.csv")


if __name__ == "__main__":
    main()
