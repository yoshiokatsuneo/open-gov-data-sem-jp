# -*- coding: utf-8 -*-
"""採用モデルに至るまでに試した全仕様を再推定して記録する。

出力: results/model_log.csv / docs/06-model-selection.md の表

「なぜこの図なのか」に答えるための台帳。採用したものだけでなく、
棄却したものも同じ条件で推定し、適合度と棄却理由を並べる。
数値は手で書かず、ここで実際に走らせた結果を出す。

    .venv/bin/python src/model_log.py
"""
import numpy as np
import pandas as pd
import semopy

import paths


# ---------------------------------------------------------------- データ準備
def prep_country_level():
    """国レベル・水準モデル（Model A 系）用。2015-19 の繁栄指標を使う。"""
    from sem_analysis import derive
    return derive()


def prep_country_growth():
    """国レベル・成長モデル（Model B 系）用。"""
    from sem_analysis import derive
    return derive()


def prep_country_resid():
    """国レベル・残差化モデル（採用版）用。"""
    from sem_country_v2 import prepare
    return prepare()


def _estat_col(index, code, year):
    """棄却した仕様でだけ使う指標を estat_long から引く。"""
    long = pd.read_csv(paths.processed("estat_long.csv"))
    long = long[(long.pref_cd != 0) & (long.code == code) & (long.year == year)]
    return long.set_index("pref_cd")["value"].reindex(index)


def prep_pref():
    from estat_sem import wide
    w = wide()
    # H1 で使う標準化死亡率（#I05101）。向きを揃えて「生存」にする
    w["surv"] = -_estat_col(w.index, "#I05101", 2015)
    return w


def prep_job():
    from job_sem import wide
    w = wide()
    # J1 / J2 で使う雇用保険受給率（#F07101）
    w["ui"] = _estat_col(w.index, "#F07101", 2020)
    return w


def prep_muni():
    r = pd.read_csv(paths.processed("muni_rates.csv"), index_col=0)
    r = r.replace([np.inf, -np.inf], np.nan)
    r = r[r["pop"] >= 1000]
    raw = pd.read_csv(paths.processed("muni_raw.csv"), index_col=0)
    raw.index = raw.index.astype(int)
    g = lambda c: pd.to_numeric(raw[c], errors="coerce")
    r["commute_out"] = (g("F2705") / g("F1102")).reindex(r.index)
    for a, b in (("nldens", "ldens"), ("nsvc", "svc"), ("nyoung", "young"), ("nold", "old")):
        r[a] = -r[b]
    return r


# ---------------------------------------------------------------- 候補
# (id, ラベル, prep, モデル記述, 使う列, 採否, 理由)
G = "GOV =~ rule_of_law + gov_effect + control_corrupt + reg_quality\n"
GR = "GROWTH =~ g_gdp + g_gni + g_cons\n"
WGI_RES = "rule_of_law ~~ control_corrupt\ngov_effect  ~~ reg_quality\n"

COUNTRY = [
    ("A1", "水準モデル（初期案）: 制度→人的資本→繁栄。電力アクセス・初等教育修了率を含む",
     prep_country_level,
     G + "HC =~ life_exp_17 + child_surv_17 + school_sec_17 + prm_complete\n"
         "PROS =~ log_gdp_pc_22 + internet_users + electricity\nHC ~ GOV\nPROS ~ GOV + HC",
     None, "棄却", "天井効果のある指標で残差相関 0.21〜0.23。かつ HC→PROS が 0.98 で判別不能"),
    ("A2", "水準モデル: 天井効果の2指標を除外し、繁栄にブロードバンドを採用",
     prep_country_level,
     G + "HC =~ life_exp_17 + child_surv_17 + school_sec_17\n"
         "PROS =~ log_gdp_pc_22 + internet_users + log_broadband\nHC ~ GOV\nPROS ~ GOV + HC",
     None, "棄却", "適合は改善するが HC→PROS が 0.97 のまま。人的資本と繁栄が同一次元に潰れる"),
    ("B0", "成長モデル（結果を水準から成長に変更）: 外生変数間の共分散なし",
     prep_country_growth,
     G + GR + "HC =~ life_exp_12 + child_surv_12 + school_sec_12\n"
              "HC ~ GOV\nGROWTH ~ GOV + HC + init_gdp",
     None, "棄却", "判別妥当性は解消したが適合が悪い。制度の質と初期所得の相関 0.75 を無視したため"),
    ("B1", "B0 + 制度の質 ↔ 初期所得 の共分散",
     prep_country_growth,
     G + GR + "HC =~ life_exp_12 + child_surv_12 + school_sec_12\n"
              "HC ~ GOV\nGROWTH ~ GOV + HC + init_gdp\nGOV ~~ init_gdp",
     None, "棄却", "改善するが残差相関に init_gdp 絡みが 0.24〜0.28 残る"),
    ("B2", "B1 + 人的資本を初期所得にも回帰",
     prep_country_growth,
     G + GR + "HC =~ life_exp_12 + child_surv_12 + school_sec_12\n"
              "HC ~ GOV + init_gdp\nGROWTH ~ GOV + HC + init_gdp\nGOV ~~ init_gdp",
     None, "棄却", "残差相関は解消するが、標準化係数が −1.07 に飛ぶ（抑制効果）"),
    ("B3", "B2 + WGI の残差相関2本 ＝ 初版 Model B",
     prep_country_growth,
     G + GR + WGI_RES + "HC =~ life_exp_12 + child_surv_12 + school_sec_12\n"
                        "HC ~ GOV + init_gdp\nGROWTH ~ GOV + HC + init_gdp\nGOV ~~ init_gdp",
     None, "一時採用", "適合は良好だが抑制が残る。指標を4通り替えても相関 0.83〜0.90 で解消せず"),
    ("C1", "統合案: 人的資本と初期所得を1つの「初期の発展水準」にまとめる",
     prep_country_growth,
     G + GR + WGI_RES + "DEV0 =~ life_exp_12 + child_surv_12 + school_sec_12 + init_gdp\n"
                        "DEV0 ~ GOV\nGROWTH ~ GOV + DEV0",
     None, "棄却", "抑制は消えるが効果も消える（DEV0→成長 ≈ 0）。符号の逆な2要素が打ち消し合う"),
    ("C2", "残差化案 ＝ 採用版。人的資本の各指標を初期所得への回帰残差に置き換える",
     prep_country_resid,
     G + GR + WGI_RES + "HCX =~ life_exp_12_r + child_surv_12_r + school_sec_12_r\n"
                        "HCX ~ GOV\nGROWTH ~ GOV + HCX + init_gdp\n"
                        "GOV ~~ init_gdp\nHCX ~~ init_gdp",
     None, "採用", "抑制が解消し適合も最良。初期所得と定義上直交するため係数が解釈できる"),
]

PREF_H = [
    ("H1", "3因子: 健康を潜在変数に（平均寿命 男・女 ＋ 標準化死亡率）", prep_pref,
     "WEALTH =~ income + tax_income + univ_rate\nMED =~ doctors + nurses + beds\n"
     "HEALTH =~ le_m + le_f + surv\nMED ~ WEALTH\nHEALTH ~ WEALTH + MED",
     ["income", "tax_income", "univ_rate", "doctors", "nurses", "beds", "le_m", "le_f", "surv"],
     "棄却", "標準化死亡率と平均寿命(男)が r=0.97 で実質同一。健康因子が男性側に偏る"),
    ("H2", "健康を男女別の観測変数に分ける（医師数は医療因子に含む）", prep_pref,
     "WEALTH =~ income + tax_income + univ_rate\nMED =~ doctors + nurses + beds\n"
     "le_m ~ WEALTH + MED\nle_f ~ WEALTH + MED\nle_m ~~ le_f",
     ["income", "tax_income", "univ_rate", "doctors", "nurses", "beds", "le_m", "le_f"],
     "棄却", "医師数の残差相関が最大 0.40。進学率・課税所得・寿命と因子を経由せず結びつく"),
    ("H3", "H2 + 看護師 ↔ 病床 の残差相関", prep_pref,
     "WEALTH =~ income + tax_income + univ_rate\nMED =~ doctors + nurses + beds\n"
     "le_m ~ WEALTH + MED\nle_f ~ WEALTH + MED\nle_m ~~ le_f\nnurses ~~ beds",
     ["income", "tax_income", "univ_rate", "doctors", "nurses", "beds", "le_m", "le_f"],
     "棄却", "医師数の残差相関が減らない。原因は共分散ではなく因子への所属"),
    ("H4", "医師数を外し、一般病院数を入れる ＝ 採用版", prep_pref,
     "WEALTH =~ income + tax_income + univ_rate\nMED =~ nurses + beds + hosp\n"
     "MED ~ WEALTH\nle_m ~ WEALTH + MED\nle_f ~ WEALTH + MED\nle_m ~~ le_f",
     ["income", "tax_income", "univ_rate", "nurses", "beds", "hosp", "le_m", "le_f"],
     "採用", "医療因子の負荷が 0.94〜0.95 に揃い、残差相関も 0.142 まで低下"),
]

PREF_J = [
    ("J1", "都市集積 ＋ 雇用の不安定さ（雇用保険受給率を含む）", prep_job,
     "URBAN =~ ldens + did + inflow + wage_f\nPRECAR =~ sep + unemp + ui\n"
     "URBAN ~~ PRECAR\njobchg ~ URBAN + PRECAR",
     ["ldens", "did", "inflow", "wage_f", "sep", "unemp", "ui", "jobchg"],
     "棄却", "雇用保険受給率が流入人口比率と残差相関 −0.41。都市度側に交差負荷する"),
    ("J2", "J1 + 第3次産業比率を予測変数に追加", prep_job,
     "URBAN =~ ldens + did + inflow + wage_f\nPRECAR =~ sep + unemp + ui\n"
     "URBAN ~~ PRECAR\nURBAN ~~ svc\nPRECAR ~~ svc\njobchg ~ URBAN + PRECAR + svc",
     ["ldens", "did", "inflow", "wage_f", "sep", "unemp", "ui", "svc", "jobchg"],
     "棄却", "第3次産業比率が両因子に交差。雇用保険の残差相関も残る"),
    ("J3", "雇用保険受給率を除外", prep_job,
     "URBAN =~ ldens + did + inflow + wage_f\nPRECAR =~ sep + unemp\n"
     "URBAN ~~ PRECAR\njobchg ~ URBAN + PRECAR",
     ["ldens", "did", "inflow", "wage_f", "sep", "unemp", "jobchg"],
     "棄却", "今度は人口集中地区人口比率が離職率と残差相関 0.29。都市集中は失業とも結びつく"),
    ("J4", "人口集中地区人口比率も除外 ＝ 採用版", prep_job,
     "URBAN =~ ldens + inflow + wage_f\nPRECAR =~ sep + unemp\n"
     "URBAN ~~ PRECAR\njobchg ~ URBAN + PRECAR",
     ["ldens", "inflow", "wage_f", "sep", "unemp", "jobchg"],
     "採用", "残差相関が 0.145 まで低下。2因子の相関が −0.07 で判別も明確"),
    ("J5", "J3 + 第3次産業比率を不安定さ因子の指標に", prep_job,
     "URBAN =~ ldens + did + inflow + wage_f\nPRECAR =~ sep + unemp + svc\n"
     "URBAN ~~ PRECAR\njobchg ~ URBAN + PRECAR",
     ["ldens", "did", "inflow", "wage_f", "sep", "unemp", "svc", "jobchg"],
     "棄却", "第3次産業比率が人口集中地区と残差相関 0.49。都市度側の性質が強い"),
]

MUNI = [
    ("M1", "潜在変数: 都市度 ＋ 雇用の不安定さ（都道府県モデルの移植）", prep_muni,
     "URBAN =~ ldens + svc + tax_pc\nPRECAR =~ unemp + kokuho\n"
     "URBAN ~~ PRECAR\nmove_rate ~ URBAN + PRECAR",
     ["ldens", "svc", "tax_pc", "unemp", "kokuho", "move_rate"],
     "棄却", "標準化係数が +1.66 / −1.57 に飛ぶ。指標が因子にまとまらない"),
    ("M2", "潜在変数: 都市度 ＋ 年齢構成 ＋ 単独世帯割合", prep_muni,
     "URBAN =~ ldens + svc + tax_pc\nAGE =~ young + nold\n"
     "URBAN ~~ AGE\nURBAN ~~ solo\nAGE ~~ solo\nmove_rate ~ URBAN + AGE + solo",
     ["ldens", "svc", "tax_pc", "young", "nold", "solo", "move_rate"],
     "棄却", "課税所得・第3次産業が因子を経由せず結果変数に直接効く（残差相関 0.25〜0.28）"),
    ("M3", "潜在変数: 過疎度（5指標） ＋ 単独世帯割合", prep_muni,
     "RURAL =~ old + nonemp + nldens + nsvc + nyoung\n"
     "move_rate ~ RURAL + solo\nRURAL ~~ solo",
     ["old", "nonemp", "nldens", "nsvc", "nyoung", "solo", "move_rate"],
     "棄却", "反映的測定モデルが成立しない。市区町村では指標が独自情報を持つ"),
    ("P1", "パス解析: 密度 → 通勤流出・高齢化・単身 → 移動", prep_muni,
     "commute_out ~ ldens\nold ~ ldens\nsolo ~ ldens + old\n"
     "move_rate ~ commute_out + solo + old + ldens",
     ["ldens", "commute_out", "old", "solo", "move_rate"],
     "棄却", "通勤流出 ↔ 単独世帯 の残差相関が −0.42。両者の関係を経路にしていない"),
    ("P2", "P1 + 単独世帯割合 ← 通勤流出率 ＝ 採用版", prep_muni,
     "commute_out ~ ldens\nold ~ ldens\nsolo ~ ldens + old + commute_out\n"
     "move_rate ~ commute_out + solo + old + ldens",
     ["ldens", "commute_out", "old", "solo", "move_rate"],
     "採用", "ベッドタウンは家族世帯が多いという関係を明示。CFI 1.000 / RMSEA 0.016"),
    ("P3", "P2 + 第3次産業比率・所得を経路に追加", prep_muni,
     "commute_out ~ ldens + svc\nsvc ~ ldens\nold ~ ldens\n"
     "tax_pc ~ ldens + svc + old\nsolo ~ ldens + old + svc + tax_pc + commute_out\n"
     "move_rate ~ commute_out + solo + old + svc + tax_pc + ldens",
     ["ldens", "commute_out", "svc", "tax_pc", "old", "solo", "move_rate"],
     "不採用", "適合は良好だが P2 に劣り、経路が増えるわりに解釈が増えない"),
]

FAMILIES = [("国レベル", COUNTRY), ("都道府県・健康", PREF_H),
            ("都道府県・転職", PREF_J), ("市区町村", MUNI)]


def observed_of(desc, extra=()):
    out = set(extra)
    for line in desc.splitlines():
        line = line.split("#")[0].strip()
        if "=~" in line:
            out |= set(line.split("=~")[1].replace("+", " ").split())
        elif "~" in line and "~~" not in line:
            l, r = line.split("~", 1)
            out.add(l.strip())
            out |= set(r.replace("+", " ").split())
    return sorted(out)


def evaluate(desc, df, cols):
    cols = cols or observed_of(desc)
    cols = [c for c in cols if c in df.columns]
    d = df.dropna(subset=cols)
    z = (d[cols] - d[cols].mean()) / d[cols].std()
    m = semopy.Model(desc)
    m.fit(z)
    s = semopy.calc_stats(m).T["Value"]
    sigma, _ = m.calc_sigma()
    nm = list(m.vars["observed"])
    cm = lambda M: M / np.outer(np.sqrt(np.diag(M)), np.sqrt(np.diag(M)))
    R = cm(z[nm].cov().values) - cm(sigma)
    iu = np.triu_indices(len(nm), 1)
    e = m.inspect(std_est=True)
    mx = pd.to_numeric(e[e.op == "~"]["Est. Std"], errors="coerce").abs().max()
    return dict(N=len(d), df=int(s["DoF"]), chi2_df=s["chi2"] / s["DoF"],
                CFI=s["CFI"], TLI=s["TLI"], RMSEA=s["RMSEA"],
                max_resid=float(abs(R[iu]).max()), max_abs_std=float(mx))


def main():
    rows = []
    cache = {}
    for fam, cands in FAMILIES:
        print(f"\n{'='*92}\n{fam}\n{'='*92}")
        print(f"{'ID':4s} {'N':>5s} {'df':>3s} {'χ²/df':>7s} {'CFI':>6s} {'TLI':>6s} "
              f"{'RMSEA':>6s} {'残差max':>7s} {'|std|max':>8s}  採否")
        for cid, label, prep, desc, cols, verdict, reason in cands:
            if prep not in cache:
                cache[prep] = prep()
            try:
                r = evaluate(desc, cache[prep], cols)
            except Exception as ex:
                print(f"{cid:4s} 推定に失敗: {ex}")
                continue
            print(f"{cid:4s} {r['N']:5d} {r['df']:3d} {r['chi2_df']:7.2f} {r['CFI']:6.3f} "
                  f"{r['TLI']:6.3f} {r['RMSEA']:6.3f} {r['max_resid']:7.3f} "
                  f"{r['max_abs_std']:8.2f}  {verdict}")
            rows.append(dict(family=fam, id=cid, label=label, verdict=verdict,
                             reason=reason, **r))
    out = pd.DataFrame(rows)
    out.to_csv(paths.result("model_log.csv"), index=False)
    print(f"\n-> results/model_log.csv（{len(out)} 仕様）")
    return out


if __name__ == "__main__":
    main()
