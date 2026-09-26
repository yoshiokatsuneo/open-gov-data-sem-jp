# -*- coding: utf-8 -*-
"""転職モデルの残差を、e-Statの全指標に対して総当たりでスクリーニングする。

出力: job_screen.csv / job_screen_chart.svg

これは事後的な探索なので、(1) 目についた指標ではなく47都道府県そろう全指標を機械的に
試し、(2) 残差を並べ替えて「最大|r|」の帰無分布を作って多重比較を補正し、
(3) 1県抜きで結果が持つかを確認する、という手順を踏む。

結論を先に書くと、上位の相関はすべて沖縄県1県で成立しており、沖縄を除くと
375指標のどれも閾値を超えない。つまり探索では何も見つからなかった。
"""
import paths

import numpy as np
import pandas as pd

from job_sem import USED, wide
from make_path_diagram import (BOX_LINE, C_NEG, C_POS, FONT, INK, INK2, INK3,
                               SURFACE, text)

# モデルの指標そのものと、転職率・完全失業率と定義上重複するもの
DROP = {"#A01202", "#A05304", "#F0620104", "#F04102", "#F01301", "#F04101",
        "#F04103", "#F04104", "#F0130101", "#F0130102"}
FOCUS = "#A03501"      # 15歳未満人口割合（全47県での上位ヒットの代表として図示）
OKINAWA = 47
N_PERM = 2000

W, H = 1280, 742


def residual(w):
    z = (w[USED] - w[USED].mean()) / w[USED].std()
    w["urban"] = z[["ldens", "inflow", "wage_f"]].mean(axis=1)
    w["precar"] = z[["sep", "unemp"]].mean(axis=1)
    X = np.column_stack([np.ones(len(w)), w.urban, w.precar])
    beta, *_ = np.linalg.lstsq(X, w.jobchg.values, rcond=None)
    return w.jobchg.values - X @ beta


def all_indicators(index):
    """47都道府県そろう指標だけを最新年で横持ちにする。"""
    long = pd.read_csv(paths.processed("estat_long.csv"))
    long = long[long.pref_cd != 0]
    cols, names = {}, {}
    for code, g in long.groupby("code"):
        s = g[g.year == g.year.max()].set_index("pref_cd")["value"]
        s = s[~s.index.duplicated()]
        if s.notna().sum() == 47:
            cols[code], names[code] = s, g.name.iloc[0]
    X = pd.DataFrame(cols).loc[index]
    X = X.drop(columns=[c for c in DROP if c in X.columns])
    return X, names


def screen(X, res, seed=0):
    """相関と、並べ替えによる最大|r|の帰無分布を返す。"""
    A = (X.values - X.values.mean(0)) / X.values.std(0)
    v = (res - res.mean()) / res.std()
    n = len(v)
    r = A.T @ v / n
    rng = np.random.default_rng(seed)
    mx = np.empty(N_PERM)
    for i in range(N_PERM):
        q = rng.permutation(v)
        mx[i] = np.abs(A.T @ q / n).max()
    return r, mx


# ---------------------------------------------------------------- 描画
def axes(x0, y0, x1, y1, xd, yd, xt, yt, xlab, ylab, xfmt="{:.1f}", yfmt="{:+.1f}"):
    sx = lambda v: x0 + (v - xd[0]) / (xd[1] - xd[0]) * (x1 - x0)
    sy = lambda v: y1 - (v - yd[0]) / (yd[1] - yd[0]) * (y1 - y0)
    o = [f'<rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" fill="#ffffff" '
         f'stroke="{BOX_LINE}"/>']
    for t in xt:
        o.append(f'<line x1="{sx(t):.1f}" y1="{y0}" x2="{sx(t):.1f}" y2="{y1}" '
                 f'stroke="#eceae4"/>')
        o.append(text(sx(t), y1 + 18, xfmt.format(t), 10.5, INK3, "400", "middle"))
    for t in yt:
        o.append(f'<line x1="{x0}" y1="{sy(t):.1f}" x2="{x1}" y2="{sy(t):.1f}" '
                 f'stroke="{"#b9b8b2" if t == 0 else "#eceae4"}"/>')
        o.append(text(x0 - 8, sy(t) + 4, yfmt.format(t), 10.5, INK3, "400", "end"))
    o.append(text((x0 + x1) / 2, y1 + 40, xlab, 11.5, INK2, "400", "middle"))
    o.append(f'<text x="{x0-44}" y="{(y0+y1)/2}" text-anchor="middle" font-family="{FONT}" '
             f'font-size="11.5" fill="{INK2}" transform="rotate(-90 {x0-44} {(y0+y1)/2})">'
             f'{ylab}</text>')
    return o, sx, sy


def build(w, X, names, r47, mx47, r46, mx46):
    res = w.res.values
    x = X[FOCUS].values
    thr47, thr46 = np.percentile(mx47, 95), np.percentile(mx46, 95)
    m = w.index != OKINAWA
    top47 = np.abs(r47).max()
    top46 = np.abs(r46).max()

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">',
           f'<rect width="{W}" height="{H}" fill="{SURFACE}"/>']
    out.append(text(48, 50, "残差を説明するものを探した結果 — 375指標の総当たりで、何も残らなかった",
                    21, INK, "700"))
    out.append(text(48, 75, "転職モデルの残差に対し、47都道府県そろう e-Stat の全指標を機械的に相関させた。"
                            "多重比較は残差の並べ替え2,000回による最大|r|の帰無分布で補正。", 12.5, INK3))

    # ---- 左: 上位ヒットの散布図 ----
    P = 106
    out.append(f'<rect x="40" y="{P}" width="580" height="530" rx="10" fill="#ffffff" '
               f'stroke="{BOX_LINE}"/>')
    out.append(text(64, P + 30, "上位ヒットは沖縄1県で成立している", 14.5, INK, "700"))
    out.append(text(64, P + 52, f"全47県 r = {np.corrcoef(x, res)[0,1]:+.3f}　"
                                f"沖縄を除く46県 r = {np.corrcoef(x[m], res[m])[0,1]:+.3f}",
                    12, INK3))
    xd = (x.min() - .4, x.max() + .4)
    yd = (-1.35, 1.75)
    ax, sx, sy = axes(120, P + 78, 588, P + 448, xd, yd,
                      [11, 12, 13, 14, 15, 16, 17], [-1, -.5, 0, .5, 1, 1.5],
                      "15歳未満人口割合（%）", "転職率の残差（%ポイント）")
    out += ax
    for a, b, c, dash in ((np.polyfit(x, res, 1), None, C_POS, ""),
                          (np.polyfit(x[m], res[m], 1), None, INK3, ' stroke-dasharray="6 4"')):
        x1, x2 = xd
        out.append(f'<line x1="{sx(x1):.1f}" y1="{sy(a[0]*x1+a[1]):.1f}" '
                   f'x2="{sx(x2):.1f}" y2="{sy(a[0]*x2+a[1]):.1f}" stroke="{c}" '
                   f'stroke-width="2"{dash}/>')
    for i, pref in enumerate(w.pref.values):
        ok = w.index[i] == OKINAWA
        out.append(f'<circle cx="{sx(x[i]):.1f}" cy="{sy(res[i]):.1f}" r="{6 if ok else 4}" '
                   f'fill="{C_NEG if ok else C_POS}" opacity="{1 if ok else .55}"/>')
    io = list(w.index).index(OKINAWA)
    out.append(text(sx(x[io]) - 12, sy(res[io]) + 4, "沖縄県", 12, C_NEG, "700", "end"))
    out.append(text(140, P + 500, "実線 = 全47県の回帰直線　破線 = 沖縄を除いた46県", 11, INK3))

    # ---- 右: 帰無分布 ----
    out.append(f'<rect x="640" y="{P}" width="600" height="530" rx="10" fill="#ffffff" '
               f'stroke="{BOX_LINE}"/>')
    out.append(text(664, P + 30, "375指標も試せば、無関係でも |r| = 0.5 は普通に出る", 14.5, INK, "700"))
    out.append(text(664, P + 52, "残差を並べ替えたときの「375指標中の最大|r|」の分布（2,000回）", 12, INK3))

    lo, hi = 0.20, 0.78
    bins = np.linspace(lo, hi, 33)
    cnt, _ = np.histogram(mx47, bins=bins)
    ax2, sx2, sy2 = axes(716, P + 78, 1196, P + 398, (lo, hi), (0, cnt.max() * 1.12),
                         [0.2, 0.3, 0.4, 0.5, 0.6, 0.7], [0, 100, 200, 300],
                         "並べ替え時の最大 |r|", "回数", "{:.1f}", "{:.0f}")
    out += ax2
    for i, c in enumerate(cnt):
        if not c:
            continue
        x1, x2 = sx2(bins[i]), sx2(bins[i + 1])
        out.append(f'<rect x="{x1:.1f}" y="{sy2(c):.1f}" width="{x2-x1-1.5:.1f}" '
                   f'height="{sy2(0)-sy2(c):.1f}" fill="#c9d9ef"/>')
    for v, c, lab, dy in ((top46, C_POS, f"沖縄を除く最大 {top46:.3f}", 10),
                          (thr47, INK3, f"95%点 {thr47:.3f}", 28),
                          (top47, C_NEG, f"全47県の最大 {top47:.3f}", 46)):
        out.append(f'<line x1="{sx2(v):.1f}" y1="{P+78}" x2="{sx2(v):.1f}" y2="{P+398}" '
                   f'stroke="{c}" stroke-width="2" stroke-dasharray="5 3"/>')
        out.append(text(sx2(v), P + 78 + dy + 8, lab, 11.5, c, "700", "middle"))

    ry = P + 452
    out.append(f'<rect x="664" y="{ry}" width="552" height="88" rx="8" fill="#fdf3f3" '
               f'stroke="#f0c8c8"/>')
    out.append(text(682, ry + 24, "判定", 12.5, "#b03636", "700"))
    for i, line in enumerate([
            f"・全47県では2指標が閾値を超えた（工業地地価変動率 {top47:.3f}、15歳未満人口割合 0.536）。",
            f"・沖縄を除くと閾値 {thr46:.3f} に対し最大 {top46:.3f} で、375指標のうち 0 件。",
            "・上位の顔ぶれも入れ替わる。1点で動く相関は知見ではない。"]):
        out.append(text(682, ry + 46 + i * 17, line, 11.5, INK2))

    ly = H - 48
    out.append(text(48, ly,
                    "※ 沖縄県は残差 +1.54pt（3.4σ、2位の千葉 +0.85pt を大きく離す）であると同時に、"
                    "人口増減率・自然増減率・住宅地地価変動率すべてで全国1位。説明側と結果側の両方で"
                    "極端なため、1点だけで相関が立つ。", 11, INK3))
    out.append(text(48, ly + 18,
                    "※ 沖縄は誤りではなく実在する県なので、除くのが正しいわけではない。"
                    "言えるのは「この関係の根拠は観測1つ分しかない」ということ。", 11, INK3))
    out.append(f'<text x="{W-48}" y="{ly+18}" text-anchor="end" font-family="{FONT}" '
               f'font-size="11" fill="{INK3}">出典: 総務省統計局 e-Stat 社会・人口統計体系</text>')
    out.append("</svg>")
    return "\n".join(out)


if __name__ == "__main__":
    w = wide()
    w["res"] = residual(w)
    X, names = all_indicators(w.index)
    print(f"スクリーニング対象: {X.shape[1]} 指標 × N = {len(w)}\n")

    r47, mx47 = screen(X, w.res.values)
    m = w.index != OKINAWA
    r46, mx46 = screen(X[m], w.res.values[m])

    res = pd.DataFrame({"code": X.columns, "name": [names[c] for c in X.columns],
                        "r_47": r47, "r_46_excl_okinawa": r46})
    res = res.reindex(res.r_47.abs().sort_values(ascending=False).index)
    res.to_csv(paths.result("job_screen.csv"), index=False)

    for lab, r, mx, n in (("全47県", r47, mx47, 47), ("沖縄を除く46県", r46, mx46, 46)):
        thr = np.percentile(mx, 95)
        print(f"=== {lab}（N={n}）閾値|r|={thr:.3f}　超えた指標 {(np.abs(r)>thr).sum()}件 ===")
        col = "r_47" if n == 47 else "r_46_excl_okinawa"
        d = res.reindex(res[col].abs().sort_values(ascending=False).index).head(5)
        for _, x in d.iterrows():
            print(f"  {'★' if abs(x[col])>thr else ' '} r={x[col]:+.3f}  {x['name'][:46]}")
        print()

    svg = build(w, X, names, r47, mx47, r46, mx46)
    with open(paths.figure("job_screen_chart.svg"), "w") as f:
        f.write(svg)
    print(f"-> job_screen.csv / job_screen_chart.svg ({len(svg)/1024:.1f} KB)")
