# -*- coding: utf-8 -*-
"""国レベルSEM（作り込み版）のパス図。出力: country2_path_diagram.svg"""
import paths

import pandas as pd
import semopy

from make_path_diagram import (BOX_LINE, C_NEG, C_NS, C_POS, FONT, INK, INK2, INK3,
                               SURFACE, Node, arrow, path_style, stars, loading_label, text)
from sem_country_v2 import HCR, LABELS, MODEL, BASE, prepare

W, H = 1280, 956
P, PH = 116, 700


def corr_line(a, b, label, vertical=True):
    if vertical:
        x, y1, y2 = a.cx, a.cy + a.h / 2, b.cy - b.h / 2
        d = f"M{x},{y1} L{x},{y2}"
        lx, ly = x, (y1 + y2) / 2
    else:
        x1, y1 = a.edge(b.cx, b.cy)
        x2, y2 = b.edge(a.cx, a.cy)
        d = f"M{x1:.1f},{y1:.1f} L{x2:.1f},{y2:.1f}"
        lx, ly = (x1 + x2) / 2, (y1 + y2) / 2
    s = (f'<path d="{d}" fill="none" stroke="{INK3}" stroke-width="1.6" '
         f'stroke-dasharray="6 4" marker-end="url(#ah-{INK3[1:]})" '
         f'marker-start="url(#ah-{INK3[1:]})"/>')
    bw = len(label) * 7.3 + 12
    s += (f'<rect x="{lx-bw/2:.1f}" y="{ly-11:.1f}" width="{bw:.1f}" height="21" rx="4" '
          f'fill="{SURFACE}" opacity="0.96"/>' + text(lx, ly + 4, label, 12, INK3, "600", "middle"))
    return s


def build():
    z = prepare()
    m = semopy.Model(MODEL)
    m.fit(z[BASE + HCR])
    e = m.inspect(std_est=True)
    s = semopy.calc_stats(m).T["Value"]
    est = {(r.lval, r.rval, r.op): (float(r["Est. Std"]),
                                    None if r["p-value"] == "-" else float(r["p-value"]))
           for _, r in e.iterrows()}
    boot = pd.read_csv(paths.result("country2_bootstrap.csv")).set_index("key")
    grp = pd.read_csv(paths.result("country2_groups.csv"))

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">',
           f'<rect width="{W}" height="{H}" fill="{SURFACE}"/>', "<defs>"]
    for c in (C_POS, C_NEG, C_NS, INK3):
        out.append(f'<marker id="ah-{c[1:]}" viewBox="0 0 10 10" refX="9" refY="5" '
                   f'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
                   f'<path d="M0,1 L9,5 L0,9 z" fill="{c}"/></marker>')
    out.append("</defs>")

    out.append(text(48, 50, "所得の割に人的資本が厚い国は、その後10年よく伸びる — 128か国の構造方程式モデリング（SEM）",
                    21, INK, "700"))
    out.append(text(48, 76, "World Bank Open Data（WGI 2012 ／ WDI 2010-14, 2020-23）。"
                            "人的資本の各指標は初期所得に回帰した残差に置き換え、所得と直交させた。", 12.5, INK3))

    out.append(f'<rect x="40" y="{P}" width="{W-80}" height="{PH}" rx="10" fill="#ffffff" '
               f'stroke="{BOX_LINE}"/>')
    out.append(text(64, P + 32, "制度 → 人的資本 → 成長。ただし制度から成長への直行便は確立しない",
                    15.5, INK, "700"))
    out.append(text(64, P + 56,
                    f"N = 128 か国　χ²/df = {s['chi2']/s['DoF']:.2f}　CFI = {s['CFI']:.3f}　"
                    f"TLI = {s['TLI']:.3f}　RMSEA = {s['RMSEA']:.3f}　"
                    f"標準化係数の最大絶対値 = 1.00（初版の 1.07 から解消）", 12.5, INK3))

    GOV = Node(450, P + 160, 168, 66, "制度の質", True, "2012")
    INIT = Node(450, P + 330, 210, 46, "初期所得", False, "log 一人当たりGDP 2012")
    HCX = Node(740, P + 432, 236, 74, "所得水準を超えた", True, "人的資本")
    GR = Node(920, P + 160, 178, 66, "その後の成長", True, "2012→2022")

    gov_ind = ["rule_of_law", "gov_effect", "control_corrupt", "reg_quality"]
    gb = [Node(160, P + 92 + i * 46, 216, 38, LABELS[k]) for i, k in enumerate(gov_ind)]
    hb = [Node(500 + i * 240, P + 578, 228, 44,
               LABELS[k].split("（")[0], False, "所得調整後")
          for i, k in enumerate(HCR)]
    gr_ind = ["g_gdp", "g_gni", "g_cons"]
    rb = [Node(1156, P + 114 + i * 46, 154, 38, LABELS[k]) for i, k in enumerate(gr_ind)]

    for lat, boxes, keys, key in ((GOV, gb, gov_ind, "GOV"), (HCX, hb, HCR, "HCX"),
                                  (GR, rb, gr_ind, "GROWTH")):
        for n, k in zip(boxes, keys):
            out.append(arrow(lat, n, loading_label(*est[(k, key, '~')]), INK3, 1.3, lab_t=.46))

    for src, dst, key, bow, t in ((GOV, HCX, ("HCX", "GOV", "~"), 0, .42),
                                  (HCX, GR, ("GROWTH", "HCX", "~"), 0, .5),
                                  (INIT, GR, ("GROWTH", "init_gdp", "~"), 0, .66),
                                  (GOV, GR, ("GROWTH", "GOV", "~"), -70, .5)):
        v, p = est[key]
        c, wd, d = path_style(v, p)
        out.append(arrow(src, dst, f"{v:.2f}{stars(p)}", c, wd, d, bow=bow, lab_t=t))

    cv = est.get(("GOV", "init_gdp", "~~")) or est.get(("init_gdp", "GOV", "~~"))
    out.append(corr_line(GOV, INIT, f"相関 {cv[0]:+.2f}"))
    cv2 = est.get(("HCX", "init_gdp", "~~")) or est.get(("init_gdp", "HCX", "~~"))
    out.append(corr_line(INIT, HCX, f"相関 {cv2[0]:+.2f}", vertical=False))

    for n in (GOV, INIT, HCX, GR, *gb, *hb, *rb):
        out.append(n.svg())

    # ---- ブートストラップ ----
    by = P + 628
    out.append(f'<rect x="64" y="{by}" width="600" height="60" rx="8" fill="#fdf8ef" '
               f'stroke="#e8d9b8"/>')
    out.append(text(82, by + 22, "ブートストラップ（600回）95%区間", 12.5, "#8a6d1f", "700"))
    for i, (k, lab) in enumerate((("GROWTH~HCX", "人的資本 → 成長"),
                                  ("HCX~GOV", "制度 → 人的資本"))):
        r = boot.loc[k]
        y = by + 42 + i * 0
        x = 82 + i * 300
        out.append(text(x, y, f"{lab}　{r['中央値']:+.2f} "
                              f"[{r['2.5%']:+.2f}, {r['97.5%']:+.2f}]　0を含まない", 11.5, INK2))

    # ---- 所得グループ ----
    out.append(f'<rect x="684" y="{by}" width="532" height="60" rx="8" fill="#f2f7fd" '
               f'stroke="#cfe0f5"/>')
    out.append(text(702, by + 22, "所得グループ別：人的資本 → 成長", 12.5, "#1c5cab", "700"))
    cell = [c for c in grp.columns if "人的資本→" in c][0]
    txt = "　".join(f"{r['グループ']}(N={r['N']}) {r[cell]}" for _, r in grp.iterrows())
    out.append(text(702, by + 42, txt, 11, INK2))

    # ---- 凡例 ----
    lg = H - 102
    out.append(text(48, lg, "凡例", 12, INK, "700"))
    out.append(f'<ellipse cx="110" cy="{lg-5}" rx="21" ry="11" fill="#eef4fd" '
               f'stroke="{C_POS}" stroke-width="2"/>')
    out.append(text(140, lg, "潜在変数", 12, INK2))
    out.append(f'<rect x="206" y="{lg-16}" width="42" height="22" rx="4" fill="#ffffff" '
               f'stroke="{BOX_LINE}" stroke-width="1.5"/>')
    out.append(text(256, lg, "観測変数", 12, INK2))
    for x, col, wd, ds, lab in ((330, C_POS, 2.4, "", "正の効果（有意）"),
                                (500, C_NS, 1.6, ' stroke-dasharray="6 4"', "非有意")):
        out.append(f'<path d="M{x},{lg-5} L{x+52},{lg-5}" stroke="{col}" stroke-width="{wd}"'
                   f'{ds} marker-end="url(#ah-{col[1:]})"/>')
        out.append(text(x + 60, lg, lab, 12, INK2))
    out.append(f'<path d="M660,{lg-5} L712,{lg-5}" stroke="{INK3}" stroke-width="1.6" '
               f'stroke-dasharray="6 4" marker-end="url(#ah-{INK3[1:]})" '
               f'marker-start="url(#ah-{INK3[1:]})"/>')
    out.append(text(720, lg, "相関（因果を仮定しない）", 12, INK2))
    out.append(text(900, lg, "数値は標準化係数　*** p<.001　** p<.01　* p<.05", 12, INK3))
    out.append(text(48, lg + 20,
                    "※「所得水準を超えた人的資本」は、平均寿命・乳幼児生存・中等教育就学率それぞれを"
                    "初期所得に回帰した残差から作った潜在変数。初期所得とは定義上ほぼ直交する。", 11, INK3))
    out.append(text(48, lg + 38,
                    "※ 横断データの時点差による設計であり、矢印の向きはデータからは決まらない。"
                    "WGI の4指標には同一原データ由来の残差相関を2本許容。", 11, INK3))
    out.append(f'<text x="{W-48}" y="{lg+38}" text-anchor="end" font-family="{FONT}" '
               f'font-size="11" fill="{INK3}">出典: World Bank Open Data (WGI / WDI)</text>')
    out.append(text(48, H - 25,
                    "因子負荷量：細い灰色の矢印。† 非標準化係数を1に固定（検定対象外）。n.s. は p≥.05。", 11, INK3))
    out.append(text(48, H - 9,
                    "星印は非標準化係数の漸近的な検定結果。表示する数値は標準化係数。", 11, INK3))
    out.append("</svg>")
    return "\n".join(out)


if __name__ == "__main__":
    svg = build()
    with open(paths.figure("country2_path_diagram.svg"), "w") as f:
        f.write(svg)
    print(f"-> country2_path_diagram.svg ({len(svg)/1024:.1f} KB)")
