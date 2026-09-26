# -*- coding: utf-8 -*-
"""市区町村パス解析のパス図。出力: muni_path_diagram.svg"""
import paths

import pandas as pd
import semopy

from make_path_diagram import (BOX_LINE, C_NEG, C_NS, C_POS, FONT, INK, INK2, INK3,
                               SURFACE, Node, arrow, path_style, stars, text)
from muni_path import LABELS, MODEL, V, wide

W, H = 1280, 838
P, PH = 112, 596


def build():
    d = wide()
    z = (d[V] - d[V].mean()) / d[V].std()
    m = semopy.Model(MODEL)
    m.fit(z)
    e = m.inspect(std_est=True)
    s = semopy.calc_stats(m).T["Value"]
    est = {(r.lval, r.rval): (float(r["Est. Std"]),
                              None if r["p-value"] == "-" else float(r["p-value"]))
           for _, r in e[e.op == "~"].iterrows()}
    eff = pd.read_csv(paths.result("muni_path_effects.csv"), index_col=0).iloc[:, 0]
    boot = pd.read_csv(paths.result("muni_path_bootstrap.csv")).set_index("key")

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">',
           f'<rect width="{W}" height="{H}" fill="{SURFACE}"/>', "<defs>"]
    for c in (C_POS, C_NEG, C_NS, INK3):
        out.append(f'<marker id="ah-{c[1:]}" viewBox="0 0 10 10" refX="9" refY="5" '
                   f'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
                   f'<path d="M0,1 L9,5 L0,9 z" fill="{c}"/></marker>')
    out.append("</defs>")

    out.append(text(48, 50, "人口密度は、正反対の経路を同時に走らせて移動を生む — 1,859市区町村のパス解析",
                    21, INK, "700"))
    out.append(text(48, 76, "e-Stat「統計でみる市区町村のすがた2026（基礎データ）」。"
                            "パス解析（SEMの一種・観測変数のみ）｜数値は標準化係数。",
                    12.5, INK3))

    out.append(f'<rect x="40" y="{P}" width="{W-80}" height="{PH}" rx="10" fill="#ffffff" '
               f'stroke="{BOX_LINE}"/>')
    out.append(text(64, P + 32, "密度が上がると単身が増えて移動が増えるが、同時に通勤流出が増えて単身が減る",
                    15.5, INK, "700"))
    out.append(text(64, P + 56,
                    f"N = {len(d):,} 市区町村　χ²/df = {s['chi2']/s['DoF']:.2f}　"
                    f"CFI = {s['CFI']:.3f}　TLI = {s['TLI']:.3f}　RMSEA = {s['RMSEA']:.3f}　"
                    f"残差相関の最大 |r| = 0.023", 12.5, INK3))

    DENS = Node(180, P + 290, 208, 56, "人口密度", False, "可住地面積当たり・対数")
    COM = Node(490, P + 150, 196, 56, "通勤流出率", False, "他市区町村への通勤")
    OLD = Node(490, P + 434, 196, 52, "高齢化率", False)
    SOLO = Node(790, P + 290, 196, 52, "単独世帯割合", False)
    MOVE = Node(1090, P + 290, 206, 56, "総移動率", False, "転入＋転出")

    for src, dst, key, bow, t in (
            (DENS, COM, ("commute_out", "ldens"), 0, .5),
            (DENS, OLD, ("old", "ldens"), 0, .5),
            (DENS, SOLO, ("solo", "ldens"), 0, .5),
            (DENS, MOVE, ("move_rate", "ldens"), 285, .5),
            (COM, SOLO, ("solo", "commute_out"), 0, .5),
            (OLD, SOLO, ("solo", "old"), 0, .5),
            (COM, MOVE, ("move_rate", "commute_out"), 0, .58),
            (OLD, MOVE, ("move_rate", "old"), 0, .58),
            (SOLO, MOVE, ("move_rate", "solo"), 0, .5)):
        v, p = est[key]
        c, wd, dash = path_style(v, p)
        out.append(arrow(src, dst, f"{v:.2f}{stars(p)}", c, wd, dash, bow=bow, lab_t=t))

    for n in (DENS, COM, OLD, SOLO, MOVE):
        out.append(n.svg())

    # ---- 効果分解 ----
    by = P + 486
    out.append(f'<rect x="64" y="{by}" width="600" height="92" rx="8" fill="#f2f7fd" '
               f'stroke="#cfe0f5"/>')
    out.append(text(82, by + 24, "人口密度 → 総移動率 の効果分解（標準化）", 12.5, "#1c5cab", "700"))
    items = [("直接", "直接"), ("単身経由", "単身世帯を増やす経路"),
             ("高齢化経由", "高齢化を抑える経路"), ("通勤流出→単身経由", "通勤流出→単身減の経路"),
             ("総効果", "総効果")]
    for i, (k, lab) in enumerate(items):
        col = 82 + (i % 2) * 300
        y = by + 46 + (i // 2) * 17
        v = float(eff[k])
        c = C_POS if v >= 0 else C_NEG
        out.append(text(col, y, f"{lab}", 11.5, INK2))
        out.append(text(col + 280, y, f"{v:+.3f}", 11.5, c, "600", "end"))

    # ---- ブートストラップ ----
    out.append(f'<rect x="684" y="{by}" width="532" height="92" rx="8" fill="#fdf8ef" '
               f'stroke="#e8d9b8"/>')
    out.append(text(702, by + 24, "ブートストラップ（400回）95%区間", 12.5, "#8a6d1f", "700"))
    for i, (k, lab) in enumerate((("move_rate~solo", "単独世帯 → 移動"),
                                  ("move_rate~old", "高齢化 → 移動"),
                                  ("total", "密度 → 移動（総効果）"))):
        r = boot.loc[k]
        y = by + 46 + i * 17
        out.append(text(702, y, lab, 11.5, INK2))
        out.append(text(1010, y, f"{r['中央値']:+.3f}", 11.5, INK2, "600", "end"))
        out.append(text(1196, y, f"[{r['2.5%']:+.3f}, {r['97.5%']:+.3f}]", 11.5, INK3, "400", "end"))

    # ---- 凡例 ----
    lg = H - 60
    out.append(text(48, lg, "凡例", 12, INK, "700"))
    out.append(f'<rect x="96" y="{lg-16}" width="42" height="22" rx="4" fill="#ffffff" '
               f'stroke="{BOX_LINE}" stroke-width="1.5"/>')
    out.append(text(146, lg, "観測変数（潜在変数は使わない）", 12, INK2))
    for x, col, lab in ((360, C_POS, "正の効果"), (500, C_NEG, "負の効果")):
        out.append(f'<path d="M{x},{lg-5} L{x+52},{lg-5}" stroke="{col}" stroke-width="2.4" '
                   f'marker-end="url(#ah-{col[1:]})"/>')
        out.append(text(x + 60, lg, lab, 12, INK2))
    out.append(text(630, lg, "全パス p<.001　数値は標準化係数", 12, INK3))
    out.append(text(48, lg + 20,
                    "※ 人口1,000人未満の35自治体は率が不安定なため除外。政令市・特別区部の合計行は"
                    "区と二重計上になるため除外し、区単位で集計。", 11, INK3))
    out.append(text(48, lg + 38,
                    "※ 総移動率は住民基本台帳の転入＋転出で、居住移動であって職業移動ではない。"
                    "矢印の向きは理論上の順序であり、データからは決まらない。", 11, INK3))
    out.append(f'<text x="{W-48}" y="{lg+38}" text-anchor="end" font-family="{FONT}" '
               f'font-size="11" fill="{INK3}">出典: 総務省統計局 e-Stat 社会・人口統計体系</text>')
    out.append("</svg>")
    return "\n".join(out)


if __name__ == "__main__":
    svg = build()
    with open(paths.figure("muni_path_diagram.svg"), "w") as f:
        f.write(svg)
    print(f"-> muni_path_diagram.svg ({len(svg)/1024:.1f} KB)")
