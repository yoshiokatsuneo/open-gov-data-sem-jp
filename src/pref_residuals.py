# -*- coding: utf-8 -*-
"""「豊かさから予測される平均寿命」と実際のずれを47都道府県について出す。

出力: pref_residuals.csv / pref_residual_chart.svg

豊かさスコアは、SEM の因子得点ではなく３指標（県民所得・課税対象所得・大学等進学率）の
標準化平均を使う。CFA の因子得点は課税対象所得の残差分散が 0 に潰れる Heywood ケース
になり、実質その１指標と同じものになってしまうため。両者の結果はほぼ変わらない
（平均寿命(男)との相関 0.482 → 0.489）。
"""
import paths

import numpy as np
import pandas as pd

from estat_sem import wide
from make_path_diagram import BOX_LINE, FONT, INK, INK2, INK3, SURFACE, text

M_COL, F_COL = "#2a78d6", "#eb6834"          # 男 / 女
WEALTH_COLS = ["income", "tax_income", "univ_rate"]

W, H = 1280, 858
ROW = 23                                      # 1都道府県あたりの行の高さ
DOM = (-1.85, 1.35)                           # 横軸（年）の描画範囲


def compute():
    w = wide()
    z = (w[WEALTH_COLS] - w[WEALTH_COLS].mean()) / w[WEALTH_COLS].std()
    w["wealth"] = z.mean(axis=1)
    for y in ("le_m", "le_f"):
        b, a = np.polyfit(w.wealth, w[y], 1)
        w[y + "_hat"] = a + b * w.wealth
        w[y + "_res"] = w[y] - w[y + "_hat"]
        r = np.corrcoef(w.wealth, w[y])[0, 1]
        print(f"{y}: 傾き {b:+.3f} 年/SD　r = {r:+.3f}　R² = {r**2:.3f}　"
              f"残差SD = {w[y+'_res'].std():.3f} 年")
    print(f"男女の残差の相関: {np.corrcoef(w.le_m_res, w.le_f_res)[0,1]:+.3f}")
    return w.sort_values("le_m_res", ascending=False)


def column(d, x0, y0, plot_w, start_rank):
    """1列ぶん（都道府県名・ダンベル・数値）の SVG を返す。"""
    lo, hi = DOM
    sx = lambda v: x0 + (v - lo) / (hi - lo) * plot_w
    out = []

    # 目盛り
    for t in (-1.5, -1.0, -0.5, 0.0, 0.5, 1.0):
        x = sx(t)
        major = t == 0
        out.append(f'<line x1="{x:.1f}" y1="{y0-16}" x2="{x:.1f}" y2="{y0+len(d)*ROW:.0f}" '
                   f'stroke="{"#b9b8b2" if major else "#eceae4"}" stroke-width="{1.4 if major else 1}"/>')
        out.append(text(x, y0 - 10, f"{t:+.1f}".replace("+0.0", "0"), 10.5, INK3, "400", "middle"))

    for i, (_, r) in enumerate(d.iterrows()):
        y = y0 + i * ROW + ROW / 2 + 4
        if i % 2 == 0:
            out.append(f'<rect x="{x0-92}" y="{y-15:.1f}" width="{plot_w+190}" height="{ROW}" '
                       f'fill="#faf9f6"/>')
        out.append(text(x0 - 10, y, f"{start_rank+i}", 10.5, INK3, "400", "end"))
        out.append(text(x0 - 26, y, r.pref, 12, INK2, "400", "end"))
        xm, xf = sx(r.le_m_res), sx(r.le_f_res)
        out.append(f'<line x1="{xm:.1f}" y1="{y-4:.1f}" x2="{xf:.1f}" y2="{y-4:.1f}" '
                   f'stroke="#c9c8c2" stroke-width="1.6"/>')
        for x, c in ((xf, F_COL), (xm, M_COL)):
            out.append(f'<circle cx="{x:.1f}" cy="{y-4:.1f}" r="4.6" fill="{c}" '
                       f'stroke="{SURFACE}" stroke-width="1.4"/>')
        out.append(text(x0 + plot_w + 88, y,
                        f"{r.le_m_res:+.2f} / {r.le_f_res:+.2f}", 11, INK3, "400", "end"))
    return out


def build(d):
    r2 = {y: np.corrcoef(d.wealth, d[y])[0, 1] ** 2 for y in ("le_m", "le_f")}
    rmf = np.corrcoef(d.le_m_res, d.le_f_res)[0, 1]
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">',
           f'<rect width="{W}" height="{H}" fill="{SURFACE}"/>']
    out.append(text(48, 50, "豊かさで説明できる分を差し引いた平均寿命 — 47都道府県の残差", 21, INK, "700"))
    out.append(text(48, 75, "県民所得・課税対象所得・大学等進学率の標準化平均を「豊かさ」とし、"
                            "そこから回帰で予測される平均寿命と実測値の差（年）。"
                            "平均寿命(男)の残差が大きい順。", 12.5, INK3))

    py = 128
    out.append(f'<rect x="40" y="{py}" width="{W-80}" height="{H-py-92}" rx="10" fill="#ffffff" '
               f'stroke="{BOX_LINE}"/>')
    hy = py + 74
    for x0 in (200, 780):
        out.append(text(x0, py + 32, "← 予測より短命", 12, INK3))
        out.append(text(x0 + 330, py + 32, "予測より長生き →", 12, INK3, "400", "end"))

    half = 24
    out += column(d.iloc[:half], 200, hy, 330, 1)
    out += column(d.iloc[half:], 780, hy, 330, half + 1)

    ly = H - 58
    out.append(text(48, ly, "凡例", 12, INK, "700"))
    for x, c, lab in ((100, M_COL, "平均寿命（男）の残差"), (300, F_COL, "平均寿命（女）の残差")):
        out.append(f'<circle cx="{x}" cy="{ly-4}" r="4.6" fill="{c}"/>')
        out.append(text(x + 12, ly, lab, 12, INK2))
    out.append(text(500, ly, "数値は 男 / 女（年）", 12, INK3))
    out.append(text(48, ly + 20,
                    f"※ 豊かさで説明できるのは男性で {r2['le_m']*100:.0f}%（R²={r2['le_m']:.3f}）、"
                    f"女性では {r2['le_f']*100:.0f}%（R²={r2['le_f']:.3f}）。"
                    "女性の残差は実質そのまま平均寿命の順位であり、豊かさを差し引いた効果ではない。", 11, INK3))
    out.append(text(48, ly + 38,
                    "※ 東京都は豊かさスコアが突出した高レバレッジ点で、予測値が外挿になっている。"
                    f"男女の残差の相関は {rmf:.2f} で、豊かさ以外の要因は男女で共通している。", 11, INK3))
    out.append(f'<text x="{W-48}" y="{ly+38}" text-anchor="end" font-family="{FONT}" '
               f'font-size="11" fill="{INK3}">出典: 総務省統計局 e-Stat 社会・人口統計体系</text>')
    out.append("</svg>")
    return "\n".join(out)


if __name__ == "__main__":
    d = compute()
    keep = ["pref", "wealth", "income", "tax_income", "univ_rate",
            "le_m", "le_m_hat", "le_m_res", "le_f", "le_f_hat", "le_f_res"]
    d[keep].to_csv(paths.result("pref_residuals.csv"), index=False)
    svg = build(d)
    with open(paths.figure("pref_residual_chart.svg"), "w") as f:
        f.write(svg)
    print(f"\n-> pref_residuals.csv / pref_residual_chart.svg ({len(svg)/1024:.1f} KB)")
