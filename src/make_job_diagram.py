# -*- coding: utf-8 -*-
"""転職SEMのパス図を SVG で生成する。出力: job_path_diagram.svg"""
import paths

import pandas as pd
import semopy

from job_sem import LABELS, MODEL, USED, wide
from make_path_diagram import (BOX_LINE, C_NS, C_POS, FONT, INK, INK2, INK3,
                               SURFACE, Node, arrow, path_style, stars, loading_label, text)

W, H = 1280, 862
P, PH = 118, 572


def covariance(a, b, label):
    """2つの潜在変数を結ぶ両端矢印（縦）。"""
    x, y1, y2 = a.cx, a.cy + a.h / 2, b.cy - b.h / 2
    s = (f'<path d="M{x},{y1} L{x},{y2}" fill="none" stroke="{INK3}" stroke-width="1.6" '
         f'stroke-dasharray="6 4" marker-end="url(#ah-{INK3[1:]})" '
         f'marker-start="url(#ah-{INK3[1:]})"/>')
    ly = (y1 + y2) / 2
    bw = len(label) * 7.4 + 12
    s += (f'<rect x="{x-bw/2:.1f}" y="{ly-11}" width="{bw:.1f}" height="21" rx="4" '
          f'fill="{SURFACE}" opacity="0.96"/>' + text(x, ly + 4, label, 12.5, INK3, "600", "middle"))
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
    boot = pd.read_csv(paths.result("job_bootstrap.csv")).set_index("key")

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">',
           f'<rect width="{W}" height="{H}" fill="{SURFACE}"/>', "<defs>"]
    for c in (C_POS, C_NS, INK3):
        out.append(f'<marker id="ah-{c[1:]}" viewBox="0 0 10 10" refX="9" refY="5" '
                   f'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
                   f'<path d="M0,1 L9,5 L0,9 z" fill="{c}"/></marker>')
    out.append("</defs>")

    out.append(text(48, 52, "転職が多い県は、労働市場が厚いのか、雇用が不安定なのか — 47都道府県の構造方程式モデリング（SEM）",
                    21, INK, "700"))
    out.append(text(48, 78, "e-Stat 社会・人口統計体系「社会生活統計指標－都道府県の指標－2024」"
                            "（転職率・離職率は2017年、他は2015〜2021年）　semopy 2.3.11・最尤法・全変数を標準化",
                    12.5, INK3))

    out.append(f'<rect x="40" y="{P}" width="{W-80}" height="{PH}" rx="10" fill="#ffffff" '
               f'stroke="{BOX_LINE}"/>')
    out.append(text(64, P + 32, "都市度と雇用の不安定さを分けて、転職率との関連を調べる", 16, INK, "700"))
    out.append(text(64, P + 56,
                    f"N = 47 都道府県　χ²/df = {s['chi2']/s['DoF']:.2f}　CFI = {s['CFI']:.3f}　"
                    f"TLI = {s['TLI']:.3f}　RMSEA = {s['RMSEA']:.3f}　残差相関の最大 |r| = 0.145",
                    12.5, INK3))

    URBAN = Node(480, P + 170, 216, 70, "都市労働市場の厚み", True)
    PRECAR = Node(480, P + 398, 206, 70, "雇用の不安定さ", True)
    rate = w.jobchg
    JOB = Node(980, P + 284, 252, 72, "転職率", False,
               f"平均 {rate.mean():.1f}%　{rate.min():.1f}〜{rate.max():.1f}%")

    ub = [Node(190, P + 98 + i * 56, 236, 40, LABELS[k])
          for i, k in enumerate(["ldens", "inflow", "wage_f"])]
    pb = [Node(190, P + 370 + i * 56, 236, 40, LABELS[k])
          for i, k in enumerate(["sep", "unemp"])]

    for lat, boxes, keys in [(URBAN, ub, ["ldens", "inflow", "wage_f"]),
                             (PRECAR, pb, ["sep", "unemp"])]:
        name = "URBAN" if lat is URBAN else "PRECAR"
        for n, k in zip(boxes, keys):
            out.append(arrow(lat, n, loading_label(*est[(k, name, '~')]), INK3, 1.3, lab_t=.46))

    for src, key in ((URBAN, "URBAN"), (PRECAR, "PRECAR")):
        v, p = est[("jobchg", key, "~")]
        c, wd, d = path_style(v, p)
        out.append(arrow(src, JOB, f"{v:.2f}{stars(p)}", c, wd, d, lab_t=.46))

    cv = est.get(("URBAN", "PRECAR", "~~")) or est.get(("PRECAR", "URBAN", "~~"))
    out.append(covariance(URBAN, PRECAR, f"相関 {cv[0]:+.2f}（n.s.）"))

    for n in (URBAN, PRECAR, JOB, *ub, *pb):
        out.append(n.svg())

    # ---- 所見 ----
    by = P + 470
    out.append(f'<rect x="64" y="{by}" width="560" height="86" rx="8" fill="#f2f7fd" '
               f'stroke="#cfe0f5"/>')
    out.append(text(82, by + 24, "読みどころ", 12.5, "#1c5cab", "700"))
    for i, line in enumerate([
            "・説明側の相関の点推定は小さい。独立性を示したわけではない。",
            "・離職率は「雇用の不安定さ」の指標であって、転職率とは r = 0.29 しかない。",
            "・有効求人倍率は転職率と −0.36。逼迫と労働移動は別物（モデル外）。"]):
        out.append(text(82, by + 46 + i * 17, line, 11.5, INK2))

    # ---- ブートストラップ ----
    out.append(f'<rect x="648" y="{by}" width="568" height="86" rx="8" fill="#fdf8ef" '
               f'stroke="#e8d9b8"/>')
    out.append(text(666, by + 24, "ブートストラップ（復元抽出600回）標準化係数の 95% 区間",
                    12.5, "#8a6d1f", "700"))
    for i, (k, lab) in enumerate([("jobchg~URBAN", "都市労働市場の厚み → 転職率"),
                                  ("jobchg~PRECAR", "雇用の不安定さ → 転職率")]):
        r = boot.loc[k]
        y = by + 47 + i * 18
        zero = r["0をまたぐ"] == "はい"
        col = INK3 if zero else INK2
        out.append(text(666, y, lab, 11.5, col))
        out.append(text(900, y, f"{r['中央値']:+.2f}", 11.5, col, "600", "end"))
        out.append(text(1010, y, f"[{r['2.5%']:+.2f}, {r['97.5%']:+.2f}]", 11.5, col, "400", "end"))
        out.append(text(1024, y, "0をまたぐ" if zero else "0を含まない", 11.5, col))

    # ---- 凡例 ----
    lg = H - 102
    out.append(text(48, lg, "凡例", 12, INK, "700"))
    out.append(f'<ellipse cx="110" cy="{lg-5}" rx="21" ry="11" fill="#eef4fd" '
               f'stroke="{C_POS}" stroke-width="2"/>')
    out.append(text(140, lg, "潜在変数", 12, INK2))
    out.append(f'<rect x="206" y="{lg-16}" width="42" height="22" rx="4" fill="#ffffff" '
               f'stroke="{BOX_LINE}" stroke-width="1.5"/>')
    out.append(text(256, lg, "観測変数", 12, INK2))
    out.append(f'<path d="M330,{lg-5} L382,{lg-5}" stroke="{C_POS}" stroke-width="2.4" '
               f'marker-end="url(#ah-{C_POS[1:]})"/>')
    out.append(text(390, lg, "正の効果（有意）", 12, INK2))
    out.append(f'<path d="M510,{lg-5} L562,{lg-5}" stroke="{INK3}" stroke-width="1.6" '
               f'stroke-dasharray="6 4" marker-end="url(#ah-{INK3[1:]})" '
               f'marker-start="url(#ah-{INK3[1:]})"/>')
    out.append(text(570, lg, "相関（因果を仮定しない）", 12, INK2))
    out.append(text(760, lg, "数値は標準化係数　*** p<.001　** p<.01　* p<.05", 12, INK3))
    out.append(text(48, lg + 20,
                    "※ 横断データであり矢印の向きはデータからは決まらない。N = 47 に対して"
                    "推定パラメータが多く、RMSEA は小標本で過大に出る。判断はブートストラップ区間を優先。", 11, INK3))
    out.append(text(48, lg + 38,
                    "※「就業異動率」は転職率＋新規就業率との相関が 0.97 で定義上重複するため除外。"
                    "「人口集中地区人口比率」は離職率と残差相関 0.29 を残すため都市度の指標から外した。", 11, INK3))
    inf = pd.read_csv(paths.result("pref_influence.csv"))
    inf = inf[inf["モデル"] == "転職"]
    u = inf[inf["パス"].str.startswith("都市")].iloc[0]
    q = inf[inf["パス"].str.startswith("雇用")].iloc[0]
    out.append(text(48, lg + 56,
                    f"※ 1県抜き（47通り）での振れ: 都市→転職 {u['LOO最小']:+.2f}〜{u['LOO最大']:+.2f}（安定）、"
                    f"雇用の不安定さ→転職 {q['LOO最小']:+.2f}〜{q['LOO最大']:+.2f}"
                    f"（沖縄を抜くと {q['全県']+q['最大変化']:+.2f} まで落ちる）。", 11, INK3))
    out.append(f'<text x="{W-48}" y="{lg+38}" text-anchor="end" font-family="{FONT}" '
               f'font-size="11" fill="{INK3}">出典: 総務省統計局 e-Stat 社会・人口統計体系</text>')

    out.append(text(48, H - 25,
                    "因子負荷量：細い灰色の矢印。† 非標準化係数を1に固定（検定対象外）。n.s. は p≥.05。", 11, INK3))
    out.append(text(48, H - 9,
                    "星印は非標準化係数の漸近的な検定結果。表示する数値は標準化係数。", 11, INK3))
    out.append("</svg>")
    return "\n".join(out)


if __name__ == "__main__":
    svg = build()
    with open(paths.figure("job_path_diagram.svg"), "w") as f:
        f.write(svg)
    print(f"-> job_path_diagram.svg ({len(svg)/1024:.1f} KB)")
