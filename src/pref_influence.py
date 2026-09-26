# -*- coding: utf-8 -*-
"""都道府県2モデルの影響度診断（leave-one-out）。出力: pref_influence.csv

沖縄1県で残差スクリーニングの結果が全部飛んだ経験を踏まえ、
既存2モデルの主要パスについても「1県抜いたら係数がどれだけ動くか」を確認する。
"""
import paths

import numpy as np
import pandas as pd
import semopy

import estat_sem as HEALTH
import job_sem as JOB

MODELS = {
    "健康": (HEALTH.MODEL, HEALTH.USED, HEALTH.wide, HEALTH.LABELS,
             [("le_m", "WEALTH"), ("le_f", "WEALTH"), ("MED", "WEALTH"),
              ("le_m", "MED"), ("le_f", "MED")]),
    "転職": (JOB.MODEL, JOB.USED, JOB.wide, JOB.LABELS,
             [("jobchg", "URBAN"), ("jobchg", "PRECAR")]),
}


def loo(desc, used, wide, keys):
    w = wide()
    z = (w[used] - w[used].mean()) / w[used].std()
    full = fitpaths(desc, z, keys)
    rows = []
    for i, idx in enumerate(z.index):
        try:
            p = fitpaths(desc, z.drop(index=idx), keys)
        except Exception:
            continue
        for k in keys:
            rows.append({"抜いた県": w.pref.loc[idx], "path": f"{k[1]}→{k[0]}",
                         "係数": p[k], "全県": full[k], "変化": p[k] - full[k]})
    return full, pd.DataFrame(rows)


def fitpaths(desc, z, keys):
    m = semopy.Model(desc)
    m.fit(z)
    e = m.inspect(std_est=True)
    e = e[e.op == "~"]
    out = {}
    for l, r in keys:
        row = e[(e.lval == l) & (e.rval == r)]
        out[(l, r)] = float(row["Est. Std"].iloc[0]) if len(row) else np.nan
    return out


def main():
    allrows = []
    for name, (desc, used, wide, labels, keys) in MODELS.items():
        full, d = loo(desc, used, wide, keys)
        print(f"\n{'='*76}\n{name}モデル　1県抜きでの主要パスの振れ\n{'='*76}")
        for k in keys:
            lab = f"{labels.get(k[1], k[1])} → {labels.get(k[0], k[0])}"
            s = d[d.path == f"{k[1]}→{k[0]}"]
            worst = s.loc[s["変化"].abs().idxmax()]
            lo, hi = s["係数"].min(), s["係数"].max()
            flip = "★符号反転あり" if lo * hi < 0 else ""
            print(f"  {lab:32s} 全県 {full[k]:+.3f}　1県抜き {lo:+.3f}〜{hi:+.3f}"
                  f"　最大変化 {worst['変化']:+.3f}（除 {worst['抜いた県']}）{flip}")
            allrows.append({"モデル": name, "パス": lab, "全県": full[k],
                            "LOO最小": lo, "LOO最大": hi,
                            "最大変化": worst["変化"], "その県": worst["抜いた県"]})
    pd.DataFrame(allrows).to_csv(paths.result("pref_influence.csv"), index=False)
    print("\n-> pref_influence.csv")


if __name__ == "__main__":
    main()
