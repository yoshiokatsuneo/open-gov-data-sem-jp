# -*- coding: utf-8 -*-
"""市区町村データで何が変わったかを1枚にまとめる。出力: muni_chart.svg"""
import paths

import itertools

import numpy as np
import pandas as pd

from make_path_diagram import (BOX_LINE, C_NEG, C_POS, FONT, INK, INK2, INK3,
                               SURFACE, text)
import job_screen as JS
import muni_screen as MS

W, H = 1280, 806
COMMON = {"密度": "#A01202", "3次産業": "#F01203", "課税所得": "#D02206",
          "失業率": "#F01301", "単独世帯": "#A06205", "高齢化率": "#A03503",
          "年少人口": "#A03501"}


def pairs():
    """両レベルに存在する7指標・21ペアの相関を、集計レベル別に返す。"""
    L = pd.read_csv(paths.processed("estat_long.csv"))
    L = L[L.pref_cd != 0]
    P = pd.DataFrame(index=sorted(L.pref_cd.unique()))
    for k, c in COMMON.items():
        g = L[L.code == c]
        P[k] = g[g.year == g.year.max()].set_index("pref_cd")["value"]
    P["密度"] = np.log(P["密度"])

    m = pd.read_csv(paths.processed("muni_rates.csv"), index_col=0).replace([np.inf, -np.inf], np.nan)
    m = m[m["pop"] >= 1000]
    M = pd.DataFrame({"密度": m.ldens, "3次産業": m.svc, "課税所得": m.tax_pc,
                      "失業率": m.unemp, "単独世帯": m.solo, "高齢化率": m.old,
                      "年少人口": m.young}).dropna()
    rows = [{"pair": f"{a}×{b}", "pref": P[a].corr(P[b]), "muni": M[a].corr(M[b])}
            for a, b in itertools.combinations(COMMON, 2)]
    return pd.DataFrame(rows), len(P.dropna()), len(M)


def axes(x0, y0, x1, y1, xd, yd, xt, yt, xlab, ylab, fmt="{:+.1f}"):
    sx = lambda v: x0 + (v - xd[0]) / (xd[1] - xd[0]) * (x1 - x0)
    sy = lambda v: y1 - (v - yd[0]) / (yd[1] - yd[0]) * (y1 - y0)
    o = [f'<rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" fill="#ffffff" '
         f'stroke="{BOX_LINE}"/>']
    for t in xt:
        o.append(f'<line x1="{sx(t):.1f}" y1="{y0}" x2="{sx(t):.1f}" y2="{y1}" '
                 f'stroke="{"#b9b8b2" if t == 0 else "#eceae4"}"/>')
        o.append(text(sx(t), y1 + 17, fmt.format(t), 10.5, INK3, "400", "middle"))
    for t in yt:
        o.append(f'<line x1="{x0}" y1="{sy(t):.1f}" x2="{x1}" y2="{sy(t):.1f}" '
                 f'stroke="{"#b9b8b2" if t == 0 else "#eceae4"}"/>')
        o.append(text(x0 - 8, sy(t) + 4, fmt.format(t), 10.5, INK3, "400", "end"))
    o.append(text((x0 + x1) / 2, y1 + 38, xlab, 11.5, INK2, "400", "middle"))
    o.append(f'<text x="{x0-40}" y="{(y0+y1)/2}" text-anchor="middle" font-family="{FONT}" '
             f'font-size="11.5" fill="{INK2}" transform="rotate(-90 {x0-40} {(y0+y1)/2})">'
             f'{ylab}</text>')
    return o, sx, sy


def hist(vals, x0, y0, x1, y1, xd, color, thr, lab):
    bins = np.linspace(*xd, 41)
    cnt, _ = np.histogram(vals, bins=bins)
    sx = lambda v: x0 + (v - xd[0]) / (xd[1] - xd[0]) * (x1 - x0)
    sy = lambda c: y1 - c / cnt.max() * (y1 - y0)
    o = []
    for i, c in enumerate(cnt):
        if c:
            o.append(f'<rect x="{sx(bins[i]):.1f}" y="{sy(c):.1f}" '
                     f'width="{max(sx(bins[i+1])-sx(bins[i])-1,1):.1f}" '
                     f'height="{y1-sy(c):.1f}" fill="{color}" opacity="0.5"/>')
    o.append(f'<line x1="{sx(thr):.1f}" y1="{y0-4}" x2="{sx(thr):.1f}" y2="{y1}" '
             f'stroke="{color}" stroke-width="2" stroke-dasharray="4 3"/>')
    o.append(text(sx(thr), y0 - 8, lab, 11, color, "700", "middle"))
    return o


def build():
    t, npref, nmuni = pairs()

    # 都道府県版・市区町村版それぞれの「偶然でも出る最大|r|」
    w = JS.wide()
    w["res"] = JS.residual(w)
    Xp, _ = JS.all_indicators(w.index)
    _, mx47 = JS.screen(Xp, w.res.values)
    thr47 = np.percentile(mx47, 95)

    d = MS.load()
    m = d.dropna(subset=MS.PRED + ["move_rate"])
    z = (m[MS.PRED] - m[MS.PRED].mean()) / m[MS.PRED].std()
    y = ((m.move_rate - m.move_rate.mean()) / m.move_rate.std()).values
    A = np.column_stack([np.ones(len(m))] + [z[c].values for c in MS.PRED])
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    res = y - A @ beta
    Xm = MS.all_rates(m.index)
    rm, mxm, nm, _ = MS.screen(Xm, res)
    thrm = np.percentile(mxm, 95)

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">',
           f'<rect width="{W}" height="{H}" fill="{SURFACE}"/>']
    out.append(text(48, 50, "市区町村データ（N≈1,660）に下りて分かったこと", 21, INK, "700"))
    out.append(text(48, 75, "転職率は市区町村まで下りていないため総移動率で代用。"
                            "結果として、同じ問いには答えられないかわりに、"
                            "相関が集計レベルに依存することと、N が検出力に効くことが見えた。", 12.5, INK3))

    # ---- 左: 集計レベルによる相関の組み替え ----
    P0 = 104
    out.append(f'<rect x="40" y="{P0}" width="592" height="512" rx="10" fill="#ffffff" '
               f'stroke="{BOX_LINE}"/>')
    out.append(text(64, P0 + 30, "相関は「現象」ではなく「集計単位」の性質", 14.5, INK, "700"))
    out.append(text(64, P0 + 52, f"両レベルに存在する7指標・21ペア。"
                                 f"対角線から離れるほど集計レベルに依存する。", 12, INK3))
    ax, sx, sy = axes(118, P0 + 78, 594, P0 + 408, (-.9, .9), (-.9, .9),
                      [-.5, 0, .5], [-.5, 0, .5],
                      f"市区町村の相関（N = {nmuni:,}）", f"都道府県の相関（N = {npref}）")
    out += ax
    out.append(f'<line x1="{sx(-.9):.1f}" y1="{sy(-.9):.1f}" x2="{sx(.9):.1f}" '
               f'y2="{sy(.9):.1f}" stroke="{INK3}" stroke-width="1.5" stroke-dasharray="5 4"/>')
    for _, r0 in t.iterrows():
        gap = abs(abs(r0.pref) - abs(r0.muni))
        c = C_NEG if gap > .25 else C_POS
        out.append(f'<circle cx="{sx(r0.muni):.1f}" cy="{sy(r0.pref):.1f}" r="5" '
                   f'fill="{c}" opacity="{1 if gap > .25 else .5}"/>')
        if gap > .3:
            out.append(text(sx(r0.muni) + 9, sy(r0.pref) + 4, r0.pair, 10.5, C_NEG, "600"))
    out.append(text(140, P0 + 474, "赤 = 集計レベルで |r| が 0.25 以上変わるペア　破線 = 一致線",
                    11, INK3))
    out.append(text(140, P0 + 494,
                    f"|r| の平均は都道府県 {t.pref.abs().mean():.2f} / 市区町村 "
                    f"{t.muni.abs().mean():.2f}。一方的な水増しではなく組み替えが起きる。", 11, INK3))

    # ---- 右: 検出力 ----
    out.append(f'<rect x="648" y="{P0}" width="592" height="512" rx="10" fill="#ffffff" '
               f'stroke="{BOX_LINE}"/>')
    out.append(text(672, P0 + 30, "N が増えて、検出の閾値が 0.53 → 0.09 に", 14.5, INK, "700"))
    out.append(text(672, P0 + 52, "残差を並べ替えたときの「全指標中の最大|r|」の分布（各2,000回）", 12, INK3))
    ax2, sx2, _ = axes(712, P0 + 90, 1204, P0 + 300, (0, .75), (0, 1), [0, .2, .4, .6],
                       [], "偶然でも出てしまう最大 |r|", "", "{:.1f}")
    out += ax2
    out += hist(mx47, 712, P0 + 100, 1204, P0 + 300, (0, .75), C_NEG, thr47,
                f"都道府県 N=47　{thr47:.3f}")
    out += hist(mxm, 712, P0 + 100, 1204, P0 + 300, (0, .75), C_POS, thrm,
                f"市区町村 N={nm:,}　{thrm:.3f}")

    hy = P0 + 372
    out.append(text(672, hy, "市区町村で閾値を超えた指標（総移動率の残差との相関）", 12.5, INK, "700"))
    meta = pd.read_csv(paths.processed("muni_meta.csv")).set_index("code")
    hits = pd.DataFrame({"code": Xm.columns, "r": rm})
    hits = hits.reindex(hits.r.abs().sort_values(ascending=False).index).head(5)
    for i, (_, x) in enumerate(hits.iterrows()):
        nm_ = str(meta.name.get(x.code, x.code))
        out.append(text(672, hy + 24 + i * 19, f"{nm_[:26]}（人口当たり）", 11.5, INK2))
        out.append(text(1204, hy + 24 + i * 19, f"r = {x.r:+.3f}", 11.5,
                        C_POS if x.r > 0 else C_NEG, "600", "end"))
    out.append(text(672, hy + 24 + 5 * 19 + 6,
                    f"80指標中 {(np.abs(rm) > thrm).sum()} 件が閾値超え。"
                    f"都道府県版は沖縄を除くと 0 件だった。", 11, INK3))

    # ---- 下: 所見 ----
    by = P0 + 528
    out.append(f'<rect x="40" y="{by}" width="1200" height="96" rx="8" fill="#fdf8ef" '
               f'stroke="#e8d9b8"/>')
    out.append(text(64, by + 24, "ただし、同じ問いには答えられていない", 12.5, "#8a6d1f", "700"))
    for i, line in enumerate([
            "・転職率は就業構造基本調査由来で、市区町村には無い。代用した総移動率は住民基本台帳の転入＋転出で、"
            "最も強い相関相手は単独世帯割合（r = 0.62）。労働市場ではなく世帯構成の現象。",
            "・完全失業率との相関は −0.14 で、都道府県で見えた「雇用の不安定さ → 転職」の経路は符号ごと再現しない。",
            "・都道府県で成立した「都市労働市場の厚み」の因子も市区町村では成立せず（RMSEA 0.22〜0.27）、潜在変数を立てずに重回帰した（R² = 0.594）。"]):
        out.append(text(64, by + 46 + i * 17, line, 11.5, INK2))

    ly = H - 34
    out.append(text(48, ly, "※ 人口1,000人未満の35自治体は率が不安定なため除外。政令市・特別区部の合計行も区と二重計上になるため除外し、区単位で集計。",
                    11, INK3))
    out.append(f'<text x="{W-48}" y="{ly}" text-anchor="end" font-family="{FONT}" '
               f'font-size="11" fill="{INK3}">出典: 総務省統計局 e-Stat 社会・人口統計体系</text>')
    out.append("</svg>")
    return "\n".join(out)


if __name__ == "__main__":
    svg = build()
    with open(paths.figure("muni_chart.svg"), "w") as f:
        f.write(svg)
    print(f"-> muni_chart.svg ({len(svg)/1024:.1f} KB)")
