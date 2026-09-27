# -*- coding: utf-8 -*-
"""都道府県SEMのパス図を SVG で生成する。出力: pref_path_diagram.svg"""
import paths

import math

import numpy as np
import pandas as pd
import semopy

from estat_sem import LABELS, MODEL, USED, wide
from make_path_diagram import (BOX_LINE, C_NEG, C_NS, C_POS, FONT, INK, INK2, INK3,
                               SURFACE, Node, arrow, esc, path_style, stars, loading_label, text)

W, H = 1280, 932
P = 104                      # パネル上端
PH = 654                     # パネル高さ


def covariance(a, b, label, bulge=105):
    """両端矢印の曲線（相関を表す）。a, b の右側にふくらませる。"""
    x1, y1 = a.cx + a.w / 2, a.cy
    x2, y2 = b.cx + b.w / 2, b.cy
    cx, cy = max(x1, x2) + bulge, (y1 + y2) / 2
    d = f"M{x1},{y1} Q{cx},{cy} {x2},{y2}"
    lx, ly = .25 * x1 + .5 * cx + .25 * x2, (y1 + y2) / 2
    s = (f'<path d="{d}" fill="none" stroke="{INK3}" stroke-width="1.5" '
         f'marker-end="url(#ah-{INK3[1:]})" marker-start="url(#ah-{INK3[1:]})"/>')
    bw = len(label) * 7.4 + 10
    s += (f'<rect x="{lx-bw/2:.1f}" y="{ly-10}" width="{bw:.1f}" height="20" rx="4" '
          f'fill="{SURFACE}" opacity="0.95"/>' + text(lx, ly + 4, label, 12, INK3, "600", "middle"))
    return s


def build():
    w = wide()
    z = (w[USED] - w[USED].mean()) / w[USED].std()
    m = semopy.Model(MODEL)
    m.fit(z)
    e = m.inspect(std_est=True)
    s = semopy.calc_stats(m).T["Value"]
    est = {(r.lval, r.rval, r.op): (float(r["Est. Std"]),
                                    None if r["p-value"] == "-" else float(r["p-value"]))
           for _, r in e.iterrows()}
    boot = pd.read_csv(paths.result("pref_bootstrap.csv")).set_index("key")

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">',
           f'<rect width="{W}" height="{H}" fill="{SURFACE}"/>', "<defs>"]
    for c in (C_POS, C_NEG, C_NS, INK3):
        out.append(f'<marker id="ah-{c[1:]}" viewBox="0 0 10 10" refX="9" refY="5" '
                   f'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
                   f'<path d="M0,1 L9,5 L0,9 z" fill="{c}"/></marker>')
    out.append("</defs>")

    out.append(text(48, 52, "都道府県の健康格差は、豊かさか、医療の量か — 47都道府県の構造方程式モデリング（SEM）",
                    22, INK, "700"))
    out.append(text(48, 78, "e-Stat 社会・人口統計体系「社会生活統計指標－都道府県の指標－2024」"
                            "（2015年前後の値）　semopy 2.3.11・最尤法・全変数を標準化", 13, INK3))

    out.append(f'<rect x="40" y="{P}" width="{W-80}" height="{PH}" rx="10" fill="#ffffff" '
               f'stroke="{BOX_LINE}"/>')
    out.append(text(64, P + 32, "経済的豊かさ・入院医療キャパシティ → 男女別の平均寿命", 16, INK, "700"))
    out.append(text(64, P + 56,
                    f"N = 47 都道府県　χ²/df = {s['chi2']/s['DoF']:.2f}　CFI = {s['CFI']:.3f}　"
                    f"TLI = {s['TLI']:.3f}　RMSEA = {s['RMSEA']:.3f}　残差相関の最大 |r| = 0.142",
                    12.5, INK3))

    WEALTH = Node(400, P + 180, 172, 66, "経済的豊かさ", True)
    MED = Node(400, P + 430, 210, 66, "入院医療キャパシティ", True, "人口当たり")
    LE_M = Node(985, P + 185, 224, 58, "平均寿命（男）", False, "78.7〜81.8年（青森〜滋賀）")
    LE_F = Node(985, P + 430, 224, 58, "平均寿命（女）", False, "85.9〜87.7年（青森〜長野）")

    wb = [Node(150, P + 125 + i * 55, 196, 38, LABELS[k])
          for i, k in enumerate(["income", "tax_income", "univ_rate"])]
    mb = [Node(150, P + 375 + i * 55, 196, 38, LABELS[k])
          for i, k in enumerate(["nurses", "beds", "hosp"])]

    for lat, boxes, keys in [(WEALTH, wb, ["income", "tax_income", "univ_rate"]),
                             (MED, mb, ["nurses", "beds", "hosp"])]:
        for n, k in zip(boxes, keys):
            out.append(arrow(lat, n, loading_label(*est[(k, lat_key(lat), '~')]), INK3, 1.3, lab_t=.46))

    for src, dst, key, t in [(WEALTH, MED, ("MED", "WEALTH"), .5),
                             (WEALTH, LE_M, ("le_m", "WEALTH"), .5),
                             (WEALTH, LE_F, ("le_f", "WEALTH"), .30),
                             (MED, LE_M, ("le_m", "MED"), .30),
                             (MED, LE_F, ("le_f", "MED"), .5)]:
        v, p = est[(key[0], key[1], "~")]
        c, wd, d = path_style(v, p)
        out.append(arrow(src, dst, f"{v:.2f}{stars(p)}", c, wd, d, lab_t=t))

    cov = est.get(("le_m", "le_f", "~~")) or est.get(("le_f", "le_m", "~~"))
    out.append(covariance(LE_M, LE_F, f"残差相関 {cov[0]:.2f}"))

    for n in (WEALTH, MED, LE_M, LE_F, *wb, *mb):
        out.append(n.svg())

    # ---- 国レベルとの対比 ----
    by = P + 522
    out.append(f'<rect x="60" y="{by}" width="520" height="112" rx="8" fill="#f2f7fd" '
               f'stroke="#cfe0f5"/>')
    out.append(text(78, by + 24, "国レベル（World Bank 128か国）との対比", 12.5, "#1c5cab", "700"))
    for i, line in enumerate([
            "国の比較では「人的資本」と「経済的繁栄」が標準化係数 0.97 で",
            "潰れ、別々の潜在変数として立てられなかった。47都道府県では",
            "所得と平均寿命(女)の相関が 0.06 しかなく、豊かさと健康は",
            "はっきり別の次元として分離する。"]):
        out.append(text(78, by + 46 + i * 17, line, 11.5, INK2))

    # ---- ブートストラップ 95% 区間 ----
    out.append(f'<rect x="600" y="{by}" width="630" height="112" rx="8" fill="#fdf8ef" '
               f'stroke="#e8d9b8"/>')
    out.append(text(618, by + 24, "ブートストラップ（復元抽出600回）標準化係数の 95% 区間",
                    12.5, "#8a6d1f", "700"))
    rows = [("MED<-WEALTH", "豊かさ → 医療キャパ"), ("le_m<-WEALTH", "豊かさ → 平均寿命(男)"),
            ("le_m<-MED", "医療キャパ → 平均寿命(男)"), ("le_f<-WEALTH", "豊かさ → 平均寿命(女)"),
            ("le_f<-MED", "医療キャパ → 平均寿命(女)")]
    for i, (k, lab) in enumerate(rows):
        r = boot.loc[k]
        y = by + 46 + i * 13.5
        zero = r["0をまたぐ"] == "はい"
        col = INK3 if zero else INK2
        out.append(text(618, y, lab, 11, col))
        out.append(text(830, y, f"{r['中央値']:+.2f}", 11, col, "600", "end"))
        out.append(text(960, y, f"[{r['2.5%']:+.2f}, {r['97.5%']:+.2f}]", 11, col, "400", "end"))
        out.append(text(980, y, "0をまたぐ（効果を示せない）" if zero else "0を含まない", 11, col))

    # ---- 凡例 ----
    lg = H - 108
    out.append(text(48, lg, "凡例", 12, INK, "700"))
    out.append(f'<ellipse cx="110" cy="{lg-5}" rx="21" ry="11" fill="#eef4fd" '
               f'stroke="{C_POS}" stroke-width="2"/>')
    out.append(text(140, lg, "潜在変数", 12, INK2))
    out.append(f'<rect x="206" y="{lg-16}" width="42" height="22" rx="4" fill="#ffffff" '
               f'stroke="{BOX_LINE}" stroke-width="1.5"/>')
    out.append(text(256, lg, "観測変数", 12, INK2))
    for x, col, wd, ds, lab in [(330, C_POS, 2.4, "", "正の効果（有意）"),
                                (500, C_NEG, 2.4, "", "負の効果（有意）"),
                                (670, C_NS, 1.6, ' stroke-dasharray="6 4"', "非有意")]:
        out.append(f'<path d="M{x},{lg-5} L{x+52},{lg-5}" stroke="{col}" stroke-width="{wd}"'
                   f'{ds} marker-end="url(#ah-{col[1:]})"/>')
        out.append(text(x + 60, lg, lab, 12, INK2))
    out.append(text(790, lg, "数値は標準化係数　*** p<.001　** p<.01　* p<.05", 12, INK3))
    out.append(text(48, lg + 22,
                    "※ N = 47 に対して推定パラメータが多く、RMSEA は小標本で過大に出る。"
                    "有意性の判断はブートストラップ区間を優先すること。", 11, INK3))
    out.append(text(48, lg + 40,
                    "※ 医師数は他指標との残差相関が大きい（医学部の所在に規定される）ため、"
                    "入院医療キャパシティの指標から除外した。", 11, INK3))
    inf = pd.read_csv(paths.result("pref_influence.csv"))
    inf = inf[inf["モデル"] == "健康"]
    g = lambda k: inf[inf["パス"].str.contains(k)].iloc[0]
    a, b = g("平均寿命\\(男\\)$"), g("入院医療キャパシティ$")
    out.append(text(48, lg + 58,
                    f"※ 1県抜き（47通り）での振れ: 豊かさ→平均寿命(男) {a['LOO最小']:+.2f}〜{a['LOO最大']:+.2f}、"
                    f"豊かさ→医療キャパ {b['LOO最小']:+.2f}〜{b['LOO最大']:+.2f}。"
                    "区間が0を含まない2本はどちらも符号が反転しない。", 11, INK3))
    out.append(f'<text x="{W-48}" y="{lg+22}" text-anchor="end" font-family="{FONT}" '
               f'font-size="11" fill="{INK3}">出典: 総務省統計局 e-Stat 社会・人口統計体系</text>')

    out.append(text(48, H - 25,
                    "因子負荷量：細い灰色の矢印。† 非標準化係数を1に固定（検定対象外）。n.s. は p≥.05。", 11, INK3))
    out.append(text(48, H - 9,
                    "星印は非標準化係数の漸近的な検定結果。表示する数値は標準化係数。", 11, INK3))
    out.append("</svg>")
    return "\n".join(out)


def lat_key(node):
    return "WEALTH" if node.label == "経済的豊かさ" else "MED"


if __name__ == "__main__":
    svg = build()
    with open(paths.figure("pref_path_diagram.svg"), "w") as f:
        f.write(svg)
    print(f"-> pref_path_diagram.svg  ({len(svg)/1024:.1f} KB)")
