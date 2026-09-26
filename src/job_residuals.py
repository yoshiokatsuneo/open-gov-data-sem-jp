# -*- coding: utf-8 -*-
"""転職モデルの「説明からのずれ」を47都道府県について出す。

出力: job_residuals.csv / job_residual_chart.svg

都市労働市場の厚みと雇用の不安定さから重回帰で予測される転職率と、実測値の差（%ポイント）。
潜在変数のスコアは SEM の因子得点ではなく指標の標準化平均を使う。因子得点は
現金給与(女)の残差分散が 0 に潰れる Heywood ケースで計算できないため。
"""
import paths

import numpy as np
import pandas as pd

from job_sem import USED, wide
from make_path_diagram import BOX_LINE, C_NEG, C_POS, FONT, INK, INK2, INK3, SURFACE, text

URBAN_COLS = ["ldens", "inflow", "wage_f"]
PRECAR_COLS = ["sep", "unemp"]

# 8地方区分（都道府県コード）
REGIONS = {
    "北海": [1], "東北": [2, 3, 4, 5, 6, 7], "関東": [8, 9, 10, 11, 12, 13, 14],
    "中部": [15, 16, 17, 18, 19, 20, 21, 22, 23], "近畿": [24, 25, 26, 27, 28, 29, 30],
    "中国": [31, 32, 33, 34, 35], "四国": [36, 37, 38, 39],
    "九州": [40, 41, 42, 43, 44, 45, 46, 47],
}

W, H = 1280, 862
ROW = 23
DOM = (-1.35, 1.75)          # 横軸（%ポイント）


def compute():
    w = wide()
    z = (w[USED] - w[USED].mean()) / w[USED].std()
    w["urban"] = z[URBAN_COLS].mean(axis=1)
    w["precar"] = z[PRECAR_COLS].mean(axis=1)

    X = np.column_stack([np.ones(len(w)), w.urban, w.precar])
    beta, *_ = np.linalg.lstsq(X, w.jobchg.values, rcond=None)
    w["hat"] = X @ beta
    w["res"] = w.jobchg - w.hat
    r2 = 1 - (w.res ** 2).sum() / ((w.jobchg - w.jobchg.mean()) ** 2).sum()
    print(f"転職率 = {beta[0]:.3f} {beta[1]:+.3f}×都市度 {beta[2]:+.3f}×不安定さ")
    print(f"R² = {r2:.3f}　残差SD = {w.res.std():.3f}pt　実測SD = {w.jobchg.std():.3f}pt")

    w["region"] = None
    for name, codes in REGIONS.items():
        w.loc[w.index.isin(codes), "region"] = name
    return w, r2


def region_test(w, n=20000, seed=0):
    """地方によるまとまりが偶然で説明できるかを並べ替え検定で見る。

    残差を見てから地方に目が行った事後的な観察なので、そのまま報告しない。
    """
    obs = w.groupby("region").res.mean()
    stat = lambda v: np.var([v[w.region == r].mean() for r in obs.index])
    s0 = stat(w.res.values)
    rng = np.random.default_rng(seed)
    v = w.res.values.copy()
    hits = sum(stat(rng.permutation(v)) >= s0 for _ in range(n))
    p = (hits + 1) / (n + 1)
    print(f"\n=== 地方別の残差平均（pt）===")
    print(obs.sort_values(ascending=False).round(3).to_string())
    print(f"並べ替え検定（地方間分散、{n:,}回）: p = {p:.3f}")
    return obs, p


def column(d, x0, y0, plot_w, start_rank):
    lo, hi = DOM
    sx = lambda v: x0 + (v - lo) / (hi - lo) * plot_w
    out = []
    for t in (-1.0, -0.5, 0.0, 0.5, 1.0, 1.5):
        x = sx(t)
        major = t == 0
        out.append(f'<line x1="{x:.1f}" y1="{y0-16}" x2="{x:.1f}" y2="{y0+len(d)*ROW:.0f}" '
                   f'stroke="{"#b9b8b2" if major else "#eceae4"}" '
                   f'stroke-width="{1.4 if major else 1}"/>')
        out.append(text(x, y0 - 10, f"{t:+.1f}".replace("+0.0", "0"), 10.5, INK3, "400", "middle"))

    x0v = sx(0.0)
    for i, (_, r) in enumerate(d.iterrows()):
        y = y0 + i * ROW + ROW / 2 + 4
        if i % 2 == 0:
            out.append(f'<rect x="{x0-120}" y="{y-15:.1f}" width="{plot_w+260}" height="{ROW}" '
                       f'fill="#faf9f6"/>')
        out.append(text(x0 - 10, y, f"{start_rank+i}", 10.5, INK3, "400", "end"))
        out.append(text(x0 - 26, y, r.pref, 12, INK2, "400", "end"))
        out.append(text(x0 - 112, y, r.region, 10.5, "#a3a29b", "400", "start"))
        xv = sx(r.res)
        c = C_POS if r.res >= 0 else C_NEG
        out.append(f'<rect x="{min(x0v, xv):.1f}" y="{y-12:.1f}" width="{abs(xv-x0v):.1f}" '
                   f'height="11" rx="2.5" fill="{c}"/>')
        out.append(text(x0 + plot_w + 140, y,
                        f"{r.res:+.2f}　実測{r.jobchg:.1f} / 予測{r.hat:.1f}", 10.5, INK3, "400", "end"))
    return out


def build(d, r2, p_region):
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">',
           f'<rect width="{W}" height="{H}" fill="{SURFACE}"/>']
    out.append(text(48, 50, "モデルの説明からのずれ — 47都道府県の転職率の残差", 21, INK, "700"))
    out.append(text(48, 75, "「都市労働市場の厚み」と「雇用の不安定さ」から予測される転職率と、"
                            "実測値の差（%ポイント）。プラスは説明より転職が多い県。", 12.5, INK3))

    py = 128
    out.append(f'<rect x="40" y="{py}" width="{W-80}" height="{H-py-100}" rx="10" fill="#ffffff" '
               f'stroke="{BOX_LINE}"/>')
    hy = py + 74
    for x0 in (216, 796):
        out.append(text(x0, py + 32, "← 説明より転職が少ない", 12, INK3))
        out.append(text(x0 + 300, py + 32, "説明より多い →", 12, INK3, "400", "end"))

    half = 24
    out += column(d.iloc[:half], 216, hy, 300, 1)
    out += column(d.iloc[half:], 796, hy, 300, half + 1)

    ly = H - 62
    out.append(text(48, ly, "凡例", 12, INK, "700"))
    for x, c, lab in ((100, C_POS, "説明より転職が多い"), (280, C_NEG, "説明より少ない")):
        out.append(f'<rect x="{x}" y="{ly-11}" width="22" height="11" rx="2.5" fill="{c}"/>')
        out.append(text(x + 30, ly, lab, 12, INK2))
    out.append(text(470, ly, f"単位は%ポイント　モデルの説明力 R² = {r2:.3f}　"
                             f"残差SD = {d.res.std():.2f}pt", 12, INK3))
    out.append(text(48, ly + 20,
                    "※ 残差は「都市度と不安定さ以外の真の原因」ではない。測定誤差も他の原因も"
                    "ただのノイズも全部入る。47点しかなく、県ごとの値の再現性は確かめていない。", 11, INK3))
    out.append(text(48, ly + 38,
                    f"※ 地方でまとまって見えるが、これは残差を見たあとに気づいた事後的な観察。"
                    f"地方間分散の並べ替え検定では p = {p_region:.3f}。", 11, INK3))
    out.append(f'<text x="{W-48}" y="{ly+38}" text-anchor="end" font-family="{FONT}" '
               f'font-size="11" fill="{INK3}">出典: 総務省統計局 e-Stat 社会・人口統計体系</text>')
    out.append("</svg>")
    return "\n".join(out)


if __name__ == "__main__":
    w, r2 = compute()
    _, p = region_test(w)
    d = w.sort_values("res", ascending=False)
    d[["pref", "region", "jobchg", "hat", "res", "urban", "precar"]].to_csv(
        paths.result("job_residuals.csv"), index=False)
    svg = build(d, r2, p)
    with open(paths.figure("job_residual_chart.svg"), "w") as f:
        f.write(svg)
    print(f"\n-> job_residuals.csv / job_residual_chart.svg ({len(svg)/1024:.1f} KB)")
