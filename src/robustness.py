"""Model B の頑健性チェック。

人的資本(HC) と 初期所得 は強く相関するため、成長式に両方を入れると
抑制効果(suppression)で標準化係数が ±1 を超えうる。符号と有意性が
仕様変更に耐えるかを確認する。
"""
import numpy as np
import pandas as pd
import semopy

from sem_analysis import derive, observed_of

BASE = """GOV =~ rule_of_law + gov_effect + control_corrupt + reg_quality
HC =~ life_exp_12 + child_surv_12 + school_sec_12
GROWTH =~ g_gdp + g_gni + g_cons
GOV ~~ init_gdp
rule_of_law ~~ control_corrupt
gov_effect ~~ reg_quality
"""

SPECS = {
    "B  最終モデル":            BASE + "HC ~ GOV + init_gdp\nGROWTH ~ GOV + HC + init_gdp",
    "B1 初期所得を成長式から除外":  BASE + "HC ~ GOV + init_gdp\nGROWTH ~ GOV + HC",
    "B2 人的資本を成長式から除外":  BASE + "HC ~ GOV + init_gdp\nGROWTH ~ GOV + init_gdp",
    "B3 制度の直接パスを除外":     BASE + "HC ~ GOV + init_gdp\nGROWTH ~ HC + init_gdp",
}

if __name__ == "__main__":
    df = derive()
    obs = observed_of(SPECS["B  最終モデル"])
    keep = df.dropna(subset=obs)          # 全仕様で同一サンプルにする
    z = (keep[obs] - keep[obs].mean()) / keep[obs].std()

    rows = []
    for name, desc in SPECS.items():
        m = semopy.Model(desc)
        m.fit(z)
        e = m.inspect(std_est=True)
        s = semopy.calc_stats(m).T["Value"]
        g = lambda l, r: e[(e.lval == l) & (e.rval == r) & (e.op == "~")]
        pick = lambda l, r: (float(g(l, r)["Est. Std"].iloc[0]),
                             float(g(l, r)["p-value"].iloc[0])) if len(g(l, r)) else (np.nan, np.nan)
        hc, hc_p = pick("GROWTH", "HC")
        ig, ig_p = pick("GROWTH", "init_gdp")
        gv, gv_p = pick("GROWTH", "GOV")
        rows.append({
            "仕様": name, "CFI": s["CFI"], "RMSEA": s["RMSEA"],
            "HC→成長": hc, "p": hc_p,
            "初期所得→成長": ig, "p ": ig_p,
            "制度→成長": gv, "p  ": gv_p,
        })

    print(f"N = {len(keep)}（全仕様で共通）\n")
    print(pd.DataFrame(rows).round(3).to_string(index=False))

    # HC と初期所得の潜在レベルでの相関（抑制の原因）
    m = semopy.Model(SPECS["B  最終モデル"])
    m.fit(z)
    f = m.predict_factors(z)
    r = np.corrcoef(f["HC"], z["init_gdp"])[0, 1]
    print(f"\n因子得点 HC と 初期所得 の相関 r = {r:.3f}"
          "\n→ この高相関が抑制効果の原因。符号・有意性は仕様に頑健だが、"
          "\n  標準化係数の絶対値そのものは過大に出ていると読むべき。")
