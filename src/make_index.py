# -*- coding: utf-8 -*-
"""図と結果の目次 index.html を results/ の中身から生成する。

手書きだと数値が陳腐化するので、適合度もブートストラップ区間も
すべて results/*.csv から読んで埋める。
"""
import html

import pandas as pd

import paths

# GitHub Pages は .md を整形表示しないので、ドキュメントへのリンクだけ
# Markdown がレンダリングされる GitHub 側に向ける。図とCSVとコードは相対のままでよい。
REPO = "https://github.com/yoshiokatsuneo/open-gov-data-sem-jp/blob/main"

SECTIONS = [
    dict(id="country", no="01", title="国レベル — 所得の割に人的資本が厚い国は、その後10年よく伸びる",
         lead="World Bank の WGI / WDI で、制度の質・人的資本・その後10年の成長の関係を推定した。"
              "人的資本の各指標は初期所得に回帰した残差に置き換え、所得と直交させてある。",
         fig="country2_path_diagram.svg", fit="country2_fit.csv", n=128,
         boot="country2_bootstrap.csv", doc="docs/01-countries.md",
         files=[("country2_estimates.csv", "推定係数"), ("country2_groups.csv", "所得グループ別"),
                ("country2_sample.csv", "分析サンプル"), ("sem_estimates.csv", "初版Model Bの推定係数"),
                ("country_model_check.csv", "モデル診断"), ("country_life_residuals.csv", "国別の寿命残差")],
         src=[("sem_country_v2.py", "採用モデル"), ("sem_analysis.py", "初版 Model A/B"),
              ("robustness.py", "頑健性チェック"), ("fetch_data.py", "データ取得"),
              ("make_country2_diagram.py", "図の生成")]),
    dict(id="pref-health", no="02", title="都道府県の健康 — 経済の勾配は男性にだけ出る",
         lead="経済的豊かさ・入院医療キャパシティ・男女別の平均寿命。"
              "豊かな県ほど人口当たりの病床が少なく、経済の勾配は男性にだけ検出される。",
         fig="pref_path_diagram.svg", fit="pref_fit.csv", n=47,
         boot="pref_bootstrap.csv", doc="docs/02-prefectures.md",
         files=[("pref_estimates.csv", "推定係数"), ("pref_influence.csv", "1県抜き診断"),
                ("pref_residuals.csv", "県別の寿命残差"), ("pref_sample.csv", "分析サンプル")],
         src=[("estat_sem.py", "SEM"), ("pref_influence.py", "LOO診断"),
              ("pref_residuals.py", "残差と図"), ("make_pref_diagram.py", "図の生成")],
         extra=[("pref_residual_chart.svg", "豊かさから予測される寿命とのずれ（47都道府県）")]),
    dict(id="pref-job", no="03", title="都道府県の転職 — 独立した2つの経路",
         lead="「都市労働市場の厚み」と「雇用の不安定さ」の相関は −0.07。"
              "まったく別の次元が、それぞれ転職率を押し上げる。",
         fig="job_path_diagram.svg", fit="job_fit.csv", n=47,
         boot="job_bootstrap.csv", doc="docs/02-prefectures.md",
         files=[("job_estimates.csv", "推定係数"), ("job_residuals.csv", "県別の転職率残差"),
                ("job_screen.csv", "375指標スクリーニング"), ("job_sample.csv", "分析サンプル")],
         src=[("job_sem.py", "SEM"), ("job_residuals.py", "残差と図"),
              ("job_screen.py", "スクリーニング"), ("make_job_diagram.py", "図の生成")],
         extra=[("job_residual_chart.svg", "説明からのずれ（47都道府県）"),
                ("job_screen_chart.svg", "375指標の総当たり — 沖縄を除くと何も残らない")]),
    dict(id="muni", no="04", title="市区町村 — 密度は正反対の経路を同時に走らせる",
         lead="潜在変数が成立しないため、観測変数だけのパス解析に切り替えた。"
              "このリポジトリで最も適合が良い。密度は単身化を通じて移動を増やし、"
              "同時に通勤流出を通じて減らす。",
         fig="muni_path_diagram.svg", fit="muni_path_fit.csv", n=1859,
         boot="muni_path_bootstrap.csv", doc="docs/03-municipalities.md",
         files=[("muni_path_estimates.csv", "推定係数"), ("muni_path_effects.csv", "効果分解"),
                ("muni_screen.csv", "80指標スクリーニング"), ("muni_path_sample.csv", "分析サンプル")],
         src=[("muni_path.py", "パス解析"), ("muni_screen.py", "回帰とスクリーニング"),
              ("muni_parse.py", "整形"), ("make_muni_path_diagram.py", "図の生成")],
         extra=[("muni_chart.svg", "集計レベルによる相関の組み替えと、Nによる検出力の差")]),
]

CSS = """
:root{color-scheme:light dark;--ink:#16242b;--muted:#5b6b73;--line:#dde5e8;--accent:#0b6b68;--bg:#f5f8f8;--card:#fff;--warn:#8a6d1f;--warnbg:#fff8ec;--warnline:#e8d9b8}
@media(prefers-color-scheme:dark){:root{--ink:#e8eef0;--muted:#a3b2b8;--line:#2c3a40;--accent:#5fd0c6;--bg:#12191c;--card:#182125;--warn:#e3c07a;--warnbg:#241f14;--warnline:#4a3f25}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.85 system-ui,-apple-system,"Hiragino Sans","Noto Sans JP",sans-serif}
main{max-width:1140px;margin:auto;padding:56px 24px}
.eyebrow{font-size:12px;letter-spacing:.16em;color:var(--accent);font-weight:700}
h1{font-size:clamp(28px,4vw,42px);line-height:1.35;margin:12px 0 8px}h2{font-size:24px;line-height:1.5;margin:6px 0 12px}h3{font-size:16px;margin:26px 0 8px}
p{color:var(--muted);margin:.6em 0}a{color:var(--accent);text-underline-offset:4px}a:focus-visible{outline:3px solid #dc9523;outline-offset:3px}
nav{display:flex;flex-wrap:wrap;gap:10px;margin:26px 0}nav a,.open{display:inline-block;border:1px solid var(--line);border-radius:8px;padding:9px 15px;background:var(--card);text-decoration:none;font-size:14px}
section{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:30px;margin:24px 0;scroll-margin-top:20px}
.number{color:var(--accent);font-weight:700;font-size:13px}
.fit{font-size:13px;color:var(--muted);font-variant-numeric:tabular-nums;border-left:3px solid var(--accent);padding-left:12px;margin:14px 0}
figure{margin:22px 0}img{width:100%;height:auto;display:block;border:1px solid var(--line);border-radius:8px;background:#fff}
figcaption{font-size:13px;color:var(--muted);margin-top:8px}
table{width:100%;border-collapse:collapse;font-size:14px;font-variant-numeric:tabular-nums}
th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--line)}th{color:var(--muted);font-weight:600;font-size:12px}
td.num{text-align:right}.ok{color:#0b6b68;font-weight:700}.no{color:var(--muted)}
ul.files{list-style:none;padding:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:0 22px}
ul.files li{padding:9px 0;border-bottom:1px solid var(--line);font-size:14px}ul.files li span{display:block;font-size:11px;color:var(--muted);overflow-wrap:anywhere}
.note{border-left:3px solid var(--warnline);background:var(--warnbg);color:var(--ink);padding:14px 18px;font-size:14px;border-radius:0 8px 8px 0;margin:18px 0}
footer{font-size:13px;color:var(--muted);margin-top:40px}
@media(max-width:640px){main{padding:28px 16px}section{padding:20px}}
@media print{body{background:#fff}nav{display:none}section{break-inside:avoid}}
"""


def esc(s):
    return html.escape(str(s))


def fit_line(fitfile, n):
    s = pd.read_csv(paths.result(fitfile), index_col=0).iloc[:, 0]
    return (f"N = {n:,}　χ²/df = {s['chi2']/s['DoF']:.2f}　CFI = {s['CFI']:.3f}　"
            f"TLI = {s['TLI']:.3f}　RMSEA = {s['RMSEA']:.3f}　df = {int(s['DoF'])}")


def boot_table(bootfile):
    d = pd.read_csv(paths.result(bootfile))
    rows = []
    for _, r in d.iterrows():
        crosses = r["2.5%"] * r["97.5%"] < 0
        mark = '<span class="no">0をまたぐ</span>' if crosses else '<span class="ok">0を含まない</span>'
        rows.append(f"<tr><td>{esc(r['パス'])}</td><td class='num'>{r['中央値']:+.3f}</td>"
                    f"<td class='num'>[{r['2.5%']:+.3f}, {r['97.5%']:+.3f}]</td><td>{mark}</td></tr>")
    return ("<table><thead><tr><th>パス</th><th class='num'>標準化係数</th>"
            "<th class='num'>ブートストラップ95%区間</th><th>判定</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table>")


def files_ul(items, prefix):
    return "<ul class='files'>" + "".join(
        f"<li><a href='{prefix}/{esc(f)}'>{esc(lab)}</a><span>{esc(f)}</span></li>"
        for f, lab in items) + "</ul>"


def build():
    nav = "".join(f"<a href='#{s['id']}'>{s['no']} {esc(s['title'].split(' — ')[0])}</a>"
                  for s in SECTIONS)
    body = []
    for s in SECTIONS:
        parts = [f"<section id='{s['id']}'><div class='number'>{s['no']}</div>",
                 f"<h2>{esc(s['title'])}</h2><p>{esc(s['lead'])}</p>",
                 f"<div class='fit'>{fit_line(s['fit'], s['n'])}</div>",
                 f"<figure><a href='figures/{s['fig']}'><img src='figures/{s['fig']}' "
                 f"alt='{esc(s['title'])}' loading='lazy'></a>"
                 f"<figcaption>figures/{s['fig']} — クリックで原寸</figcaption></figure>",
                 "<h3>ブートストラップによる判定</h3>", boot_table(s["boot"])]
        for f, cap in s.get("extra", []):
            parts.append(f"<figure><a href='figures/{f}'><img src='figures/{f}' "
                         f"alt='{esc(cap)}' loading='lazy'></a>"
                         f"<figcaption>{esc(cap)} — figures/{f}</figcaption></figure>")
        parts += ["<h3>結果データ</h3>", files_ul(s["files"], "results"),
                  "<h3>コード</h3>", files_ul(s["src"], "src"),
                  f"<p><a href='{REPO}/{s['doc']}'>詳細ドキュメント →</a></p></section>"]
        body.append("".join(parts))

    return f"""<!doctype html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>公的データによる構造方程式モデリング｜結果の目次</title>
<style>{CSS}</style></head><body><main>
<header><div class="eyebrow">PUBLIC DATA / STRUCTURAL EQUATION MODELING</div>
<h1>公的データによる構造方程式モデリング</h1>
<p>World Bank と e-Stat の公開データだけを使い、4つの分析単位でSEMを行った記録。
図をクリックすると原寸で開く。各結果に対応するCSVとPythonコードも辿れる。</p>
<nav aria-label="目次">{nav}<a href="{REPO}/docs/04-methodology.md">方法論の教訓</a>
<a href="{REPO}/README.md">README</a></nav>
<div class="note"><strong>読む前に。</strong>すべて観測データであり、矢印の向きはモデルの仮定にすぎない。
同じ共分散行列を再現する等価モデルは無数にあり、向きを逆にしても適合度は変わらない
（<a href="{REPO}/docs/04-methodology.md">方法論 §5</a>に検算あり）。
区間が0をまたぐパスは「効果を示せなかった」ものとして扱うこと。</div></header>
{''.join(body)}
<section id="repro"><h2>再現と、詳細ドキュメント</h2>
<p>Python 3.13 が必要（3.14 には semopy の wheel が無い）。
<code>make setup &amp;&amp; make all</code> で全分析と全図が約50秒で再生成される。
<code>data/raw/</code> に生データをコミットしてあるためネットワークは不要。</p>
<ul class="files">
<li><a href="{REPO}/README.md">README</a><span>結果の要約・方法論の教訓・リポジトリ構成</span></li>
<li><a href="{REPO}/AGENTS.md">AGENTS.md</a><span>後続の分析者（人・AI）向けの作法と落とし穴</span></li>
<li><a href="{REPO}/docs/01-countries.md">01 国レベル</a><span>docs/01-countries.md</span></li>
<li><a href="{REPO}/docs/02-prefectures.md">02 都道府県</a><span>docs/02-prefectures.md</span></li>
<li><a href="{REPO}/docs/03-municipalities.md">03 市区町村</a><span>docs/03-municipalities.md</span></li>
<li><a href="{REPO}/docs/04-methodology.md">04 方法論の教訓</a><span>docs/04-methodology.md</span></li>
<li><a href="{REPO}/docs/05-data-sources.md">05 データ出典</a><span>docs/05-data-sources.md</span></li>
<li><a href="{REPO}/Makefile">Makefile</a><span>再現用エントリポイント</span></li>
</ul></section>
<footer>出典: World Bank Open Data (CC BY 4.0) / 総務省統計局 e-Stat（政府標準利用規約）。
この目次は <code>src/make_index.py</code> が results/ の中身から生成している。</footer>
</main></body></html>"""


if __name__ == "__main__":
    out = paths.ROOT / "index.html"
    out.write_text(build(), encoding="utf-8")
    print(f"-> index.html ({len(build())/1024:.1f} KB)")
