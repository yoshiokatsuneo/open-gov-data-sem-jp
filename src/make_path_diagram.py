# -*- coding: utf-8 -*-
"""SEM のパス図を SVG で生成する。

sem_analysis.py の Model A / Model B を再推定し、標準化係数を図に埋め込む。
出力: sem_path_diagram.svg
"""
import paths

import math
from xml.sax.saxutils import escape as esc

import semopy

from sem_analysis import MODEL_A, MODEL_B, derive, observed_of

# --- 配色（data-viz 既定パレット。正=青 / 負=赤 / 非有意=グレー）---
C_POS, C_NEG, C_NS = "#2a78d6", "#e34948", "#8a8985"
INK, INK2, INK3 = "#0b0b0b", "#52514e", "#77766f"
SURFACE, BOX_BG, BOX_LINE = "#fcfcfb", "#ffffff", "#d5d4cf"
LAT_BG, LAT_LINE = "#eef4fd", "#2a78d6"
FONT = "'Hiragino Sans','Noto Sans JP','Yu Gothic',sans-serif"

W, H = 1280, 1100


# ---------------------------------------------------------------- 推定
def estimates(desc, df):
    obs = observed_of(desc)
    keep = df.dropna(subset=obs)
    z = (keep[obs] - keep[obs].mean()) / keep[obs].std()
    m = semopy.Model(desc)
    m.fit(z)
    e = m.inspect(std_est=True)
    s = semopy.calc_stats(m).T["Value"]
    out = {}
    for _, r in e[e.op == "~"].iterrows():
        out[(r.rval, r.lval)] = (float(r["Est. Std"]),
                                 None if r["p-value"] == "-" else float(r["p-value"]))
    return out, s, len(keep)


def stars(p):
    if p is None:
        return ""          # 尺度固定のため検定しない
    return "***" if p < .001 else "**" if p < .01 else "*" if p < .05 else " n.s."


def fmt(v, p):
    return f"{v:.2f}{stars(p)}"


# ---------------------------------------------------------------- 図形
class Node:
    def __init__(self, cx, cy, w, h, label, latent=False, sub=None):
        self.cx, self.cy, self.w, self.h = cx, cy, w, h
        self.label, self.latent, self.sub = label, latent, sub

    def edge(self, tx, ty):
        """中心から (tx,ty) 方向に伸ばしたときの外周上の点。"""
        dx, dy = tx - self.cx, ty - self.cy
        if dx == 0 and dy == 0:
            return self.cx, self.cy
        if self.latent:
            t = 1 / math.sqrt((dx / (self.w / 2)) ** 2 + (dy / (self.h / 2)) ** 2)
        else:
            t = 1 / max(abs(dx) / (self.w / 2), abs(dy) / (self.h / 2))
        return self.cx + dx * t, self.cy + dy * t

    def svg(self):
        if self.latent:
            shape = (f'<ellipse cx="{self.cx}" cy="{self.cy}" rx="{self.w/2}" ry="{self.h/2}" '
                     f'fill="{LAT_BG}" stroke="{LAT_LINE}" stroke-width="2"/>')
            size, weight, fill = 16, "600", INK
        else:
            shape = (f'<rect x="{self.cx-self.w/2}" y="{self.cy-self.h/2}" width="{self.w}" '
                     f'height="{self.h}" rx="5" fill="{BOX_BG}" stroke="{BOX_LINE}" '
                     f'stroke-width="1.5"/>')
            size, weight, fill = 12.5, "400", INK2
        dy = -4 if self.sub else 5
        t = text(self.cx, self.cy + dy, self.label, size, fill, weight, "middle")
        if self.sub:
            t += text(self.cx, self.cy + 13, self.sub, 11, INK3, "400", "middle")
        return shape + t


def text(x, y, s, size=13, fill=INK2, weight="400", anchor="start"):
    return (f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="{FONT}" '
            f'font-size="{size}" font-weight="{weight}" fill="{fill}">{esc(s)}</text>')


def arrow(a, b, label=None, color=INK3, width=1.6, dash=None, bow=0, lab_t=.5):
    """a → b の矢印。bow>0 で進行方向の右側へ膨らむ。"""
    if bow:
        x1, y1 = a.edge(b.cx, b.cy)
        x2, y2 = b.edge(a.cx, a.cy)
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        dx, dy = x2 - x1, y2 - y1
        L = math.hypot(dx, dy) or 1
        cx, cy = mx - dy / L * bow, my + dx / L * bow
        x1, y1 = a.edge(cx, cy)          # 制御点を踏まえて端点を取り直す
        x2, y2 = b.edge(cx, cy)
        d = f"M{x1:.1f},{y1:.1f} Q{cx:.1f},{cy:.1f} {x2:.1f},{y2:.1f}"
        t = lab_t
        lx = (1 - t) ** 2 * x1 + 2 * t * (1 - t) * cx + t ** 2 * x2
        ly = (1 - t) ** 2 * y1 + 2 * t * (1 - t) * cy + t ** 2 * y2
    else:
        x1, y1 = a.edge(b.cx, b.cy)
        x2, y2 = b.edge(a.cx, a.cy)
        d = f"M{x1:.1f},{y1:.1f} L{x2:.1f},{y2:.1f}"
        lx, ly = x1 + (x2 - x1) * lab_t, y1 + (y2 - y1) * lab_t

    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    s = (f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}"{dash_attr} '
         f'marker-end="url(#ah-{color[1:]})"/>')
    if label:
        bw = len(label) * 7.6 + 12
        s += (f'<rect x="{lx-bw/2:.1f}" y="{ly-11:.1f}" width="{bw:.1f}" height="21" rx="4" '
              f'fill="{SURFACE}" opacity="0.94"/>'
              + text(lx, ly + 4, label, 13, color, "600", "middle"))
    return s


def path_style(v, p):
    if p is not None and p >= .05:
        return C_NS, 1.6, "6 4"
    return (C_POS if v >= 0 else C_NEG), 2.4, None


# ---------------------------------------------------------------- 本体
def build():
    df = derive()
    A, sA, nA = estimates(MODEL_A, df)
    B, sB, nB = estimates(MODEL_B, df)

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
           f'width="{W}" height="{H}">',
           f'<rect width="{W}" height="{H}" fill="{SURFACE}"/>', "<defs>"]
    for c in (C_POS, C_NEG, C_NS, INK3):
        out.append(f'<marker id="ah-{c[1:]}" viewBox="0 0 10 10" refX="9" refY="5" '
                   f'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
                   f'<path d="M0,1 L9,5 L0,9 z" fill="{c}"/></marker>')
    out.append("</defs>")

    out.append(text(48, 52, "制度の質は経済成長を生むか — World Bank 公開データによる構造方程式モデリング",
                    22, INK, "700"))
    out.append(text(48, 78, "Worldwide Governance Indicators (2012) ／ World Development Indicators "
                            "(2010-14, 2020-23)　semopy 2.3.11・最尤法・全変数を標準化", 13, INK3))

    # ===== Panel A: 棄却されたモデル =====
    y0 = 106
    out.append(f'<rect x="40" y="{y0}" width="{W-80}" height="215" rx="10" fill="#ffffff" '
               f'stroke="{BOX_LINE}"/>')
    out.append(text(64, y0 + 30, "Model A　水準 → 水準（棄却）", 15, INK, "700"))
    out.append(text(64, y0 + 52, f"N = {nA}　CFI = {sA['CFI']:.3f}　RMSEA = {sA['RMSEA']:.3f}",
                    12, INK3))

    ay = y0 + 118
    a1 = Node(280, ay, 152, 62, "制度の質", True, "WGI 4指標")
    a2 = Node(590, ay, 152, 62, "人的資本", True, "寿命・生存・就学")
    a3 = Node(900, ay, 152, 62, "経済的繁栄", True, "GDP・ネット・BB")
    for src, dst, key, bow, t in [(a1, a2, ("GOV", "HC"), 0, .5),
                                  (a2, a3, ("HC", "PROS"), 0, .5),
                                  (a1, a3, ("GOV", "PROS"), 110, .5)]:
        v, p = A[key]
        c, w_, d = path_style(v, p)
        out.append(arrow(src, dst, fmt(v, p), c, w_, d, bow=bow, lab_t=t))
    for n in (a1, a2, a3):
        out.append(n.svg())

    out.append(f'<rect x="1000" y="{y0+26}" width="232" height="162" rx="8" fill="#fdf3f3" '
               f'stroke="#f0c8c8"/>')
    out.append(text(1016, y0 + 50, "判別妥当性の失敗", 13, "#b03636", "700"))
    for i, line in enumerate([
            "「人的資本 → 繁栄」の標準化係数が",
            "ほぼ 1.0。2つの潜在変数が事実上",
            "同じものを測っている。国レベルの",
            "横断データでは「発展」はひとつの",
            "次元に潰れてしまう。",
            "→ 結果変数を “水準” ではなく",
            "　 “その後の成長” に取り直す。"]):
        out.append(text(1016, y0 + 74 + i * 17, line, 11.5, INK2))

    # ===== Panel B: 採用モデル =====
    y1 = 344
    PB = 664
    out.append(f'<rect x="40" y="{y1}" width="{W-80}" height="{PB}" rx="10" fill="#ffffff" '
               f'stroke="{BOX_LINE}"/>')
    out.append(text(64, y1 + 32, "Model B　初期条件（2012）→ その後10年の成長（2012→2022）　【採用】",
                    16, INK, "700"))
    out.append(text(64, y1 + 56,
                    f"N = {nB} か国　χ²/df = {sB['chi2']/sB['DoF']:.2f}　CFI = {sB['CFI']:.3f}　"
                    f"TLI = {sB['TLI']:.3f}　RMSEA = {sB['RMSEA']:.3f}　残差相関の最大 |r| = 0.067",
                    12.5, INK3))

    GOV = Node(390, y1 + 180, 160, 66, "制度の質", True, "2012")
    HC = Node(660, y1 + 400, 160, 66, "人的資本", True, "2012")
    GR = Node(925, y1 + 180, 172, 66, "その後の成長", True, "2012→2022")
    INIT = Node(180, y1 + 400, 200, 46, "初期所得", False, "log 一人当たりGDP 2012")

    gov_ind = [("法の支配", "rule_of_law"), ("政府の有効性", "gov_effect"),
               ("腐敗の抑制", "control_corrupt"), ("規制の質", "reg_quality")]
    hc_ind = [("平均寿命", "life_exp_12"), ("乳幼児生存率", "child_surv_12"),
              ("中等教育就学率", "school_sec_12")]
    gr_ind = [("一人当たりGDP", "g_gdp"), ("一人当たりGNI", "g_gni"),
              ("一人当たり消費", "g_cons")]

    gb = [Node(140, y1 + 113 + i * 45, 160, 36, lab) for i, (lab, _) in enumerate(gov_ind)]
    hb = [Node(460 + i * 200, y1 + 545, 186, 36, lab) for i, (lab, _) in enumerate(hc_ind)]
    rb = [Node(1162, y1 + 135 + i * 45, 146, 36, lab) for i, (lab, _) in enumerate(gr_ind)]

    # 因子負荷は細い灰色の矢印で
    for lat, boxes, keys, t in [(GOV, gb, gov_ind, .46), (HC, hb, hc_ind, .55),
                                (GR, rb, gr_ind, .46)]:
        for n, (_, key) in zip(boxes, keys):
            v, _p = B[(lat_name(lat), key)]
            out.append(arrow(lat, n, f"{v:.2f}", INK3, 1.3, lab_t=t))

    # 構造パス
    for src, dst, key, bow, t in [(GOV, HC, ("GOV", "HC"), 0, .34),
                                  (INIT, HC, ("init_gdp", "HC"), 0, .5),
                                  (HC, GR, ("HC", "GROWTH"), 0, .5),
                                  (INIT, GR, ("init_gdp", "GROWTH"), 0, .74),
                                  (GOV, GR, ("GOV", "GROWTH"), -90, .5)]:
        v, p = B[key]
        c, w_, d = path_style(v, p)
        out.append(arrow(src, dst, fmt(v, p), c, w_, d, bow=bow, lab_t=t))

    for n in (GOV, HC, GR, INIT, *gb, *hb, *rb):
        out.append(n.svg())
    out.append(text(1162, y1 + 108, "2012→2022 の対数差", 11, INK3, "400", "middle"))

    # 注記
    ny = y1 + 592
    out.append(f'<rect x="64" y="{ny-26}" width="560" height="92" rx="8" fill="#fdf8ef" '
               f'stroke="#e8d9b8"/>')
    out.append(text(80, ny - 5, "読むときの注意", 12.5, "#8a6d1f", "700"))
    for i, line in enumerate([
            "・人的資本と初期所得は因子得点で r = 0.91。両方を成長式に入れたため抑制効果が生じ、",
            "　標準化係数の絶対値は過大に出ている。符号と有意性は仕様変更に頑健（robustness.py）。",
            "・観測データの時点差による設計であり、実験による因果同定ではない。"]):
        out.append(text(80, ny + 16 + i * 17, line, 11.5, INK2))

    a_, b_ = B[("GOV", "HC")][0], B[("HC", "GROWTH")][0]
    c_ = B[("GOV", "GROWTH")][0]
    out.append(f'<rect x="660" y="{ny-26}" width="572" height="92" rx="8" fill="#f2f7fd" '
               f'stroke="#cfe0f5"/>')
    out.append(text(676, ny - 5, "制度の質 → 成長 の効果分解（標準化）", 12.5, "#1c5cab", "700"))
    for i, line in enumerate([
            f"・直接効果 {c_:+.2f}（非有意）　・人的資本を経由する間接効果 {a_*b_:+.2f}　"
            f"・総効果 {c_ + a_*b_:+.2f}",
            "・制度の質が成長に効くとしても、それは人的資本という経路を通ってのこと。",
            "　制度から成長への直線的な近道は、このデータでは確認できない。"]):
        out.append(text(676, ny + 16 + i * 17, line, 11.5, INK2))

    # ===== 凡例 =====
    lg = H - 52
    out.append(text(48, lg, "凡例", 12, INK, "700"))
    out.append(f'<ellipse cx="110" cy="{lg-5}" rx="21" ry="11" fill="{LAT_BG}" '
               f'stroke="{LAT_LINE}" stroke-width="2"/>')
    out.append(text(140, lg, "潜在変数", 12, INK2))
    out.append(f'<rect x="206" y="{lg-16}" width="42" height="22" rx="4" fill="{BOX_BG}" '
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
                    "※ WGI の4指標は同一の原データを共有するため、法の支配↔腐敗の抑制 と "
                    "政府の有効性↔規制の質 に残差相関を許容。制度の質と初期所得の共分散も推定。",
                    11, INK3))
    out.append(f'<text x="{W-48}" y="{lg+22}" text-anchor="end" font-family="{FONT}" '
               f'font-size="11" fill="{INK3}">出典: World Bank Open Data (WGI / WDI)</text>')

    out.append("</svg>")
    return "\n".join(out)


def lat_name(node):
    return {"制度の質": "GOV", "人的資本": "HC", "その後の成長": "GROWTH"}[node.label]


if __name__ == "__main__":
    svg = build()
    with open(paths.figure("sem_path_diagram.svg"), "w") as f:
        f.write(svg)
    print(f"-> sem_path_diagram.svg  ({len(svg)/1024:.1f} KB)")
