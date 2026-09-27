# -*- coding: utf-8 -*-
"""図と結果の目次 index.html を results/ の中身から生成する。

手書きだと数値が陳腐化するので、適合度もブートストラップ区間も
すべて results/*.csv から読んで埋める。
"""
import csv
import html
import io
import keyword
import tokenize
from urllib.parse import urlencode

import pandas as pd

import paths

# GitHub Pages は .md を整形表示しないので、ドキュメントへのリンクだけ
# Markdown がレンダリングされる GitHub 側に向ける。CSVとコードはページ内に埋め込む。
REPO_URL = "https://github.com/yoshiokatsuneo/open-gov-data-sem-jp"
REPO = f"{REPO_URL}/blob/main"
SITE_URL = "https://yoshiokatsuneo.github.io/open-gov-data-sem-jp/"


def share_buttons(selected=None):
    titles = {
        None: '国と地域の「なぜ？」を公的データで探る',
        'country': '所得が同程度でも、人的資本が充実した国ほど成長する？',
        'pref-health': '豊かな県ほど長寿？ 男女を分けて調べてみました。',
        'pref-job': '都市部ほど転職が多い？ 公的データで調べてみました。',
        'muni': '人口密度と人の移動は、どう関係する？',
    }
    url = SITE_URL + (selected + '.html' if selected else '')
    intent = 'https://twitter.com/intent/tweet?' + urlencode({'text': titles[selected], 'url': url})
    image = ("<a href='figures/pref-health_post.png' download>投稿用の画像を保存</a>"
             if selected == 'pref-health' else '')
    return (f"<div class='share-tools' aria-label='共有'><span>{'この分析' if selected else 'このサイト'}を共有</span>"
            f"<a href='{esc(intent)}' target='_blank' rel='noopener noreferrer'>"
            "<svg width='16' height='16' viewBox='0 0 24 24' aria-hidden='true' focusable='false' style='vertical-align:-2px;margin-right:6px;fill:currentColor'>"
            "<path d='M18.901 1.153h3.68l-8.04 9.19L24 22.846h-7.406l-5.8-7.584-6.64 7.584H.47l8.6-9.835L0 1.154h7.594l5.243 6.932 6.064-6.933ZM17.61 20.644h2.039L6.486 3.24H4.298L17.61 20.644Z'/></svg>"
            "Xで共有</a>"
            f"<button type='button' data-share-url='{esc(url)}'>リンクをコピー</button>{image}"
            "<span class='share-status' role='status' aria-live='polite'></span></div>")


SHARE_JS = """
document.addEventListener('click', async (event) => {
  const button = event.target.closest('button[data-share-url]');
  if (!button) return;
  const status = button.parentElement.querySelector('.share-status');
  try {
    await navigator.clipboard.writeText(button.dataset.shareUrl);
    status.textContent = 'リンクをコピーしました';
  } catch (_) {
    status.textContent = 'このリンクを選択してコピーしてください：';
    const input = document.createElement('input');
    input.value = button.dataset.shareUrl;
    input.readOnly = true;
    input.setAttribute('aria-label', '共有するページのURL');
    status.appendChild(input);
    input.focus();
    input.select();
  }
});
"""


def social_meta(page, title, description):
    card = page if page in {'country', 'pref-health', 'pref-job', 'muni'} else 'site'
    url = SITE_URL + ('' if page == 'index' else page + '.html')
    image = SITE_URL + 'figures/' + card + '_social.png'
    if page in {'pref-health', 'country'}:
        image = SITE_URL + 'figures/' + page + '_card_v2.png'
    values = {'og:type': 'website', 'og:locale': 'ja_JP', 'og:title': title,
              'og:description': description, 'og:url': url, 'og:image': image,
              'og:image:width': '1600', 'og:image:height': '800' if page in {'pref-health', 'country'} else '1200',
              'og:image:alt': title + '。観測データによる探索的分析。因果関係を示すものではありません。'}
    tags = [f'<meta property="{key}" content="{esc(value)}">' for key, value in values.items()]
    tags += [f'<meta name="{key}" content="{esc(value)}">' for key, value in
             {'description': description, 'twitter:card': 'summary_large_image',
              'twitter:title': title, 'twitter:description': description, 'twitter:image': image,
              'twitter:image:alt': values['og:image:alt']}.items()]
    return '\n'.join(tags) + f'\n<link rel="canonical" href="{url}">'

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
    dict(id="pref-health", no="02", title="都道府県の健康 — 豊かさと寿命の関連を男女別に比較",
         lead="経済的豊かさ・入院医療キャパシティ・男女別の平均寿命。"
              "豊かな県ほど人口当たりの病床が少なく、男性では豊かさとの関連が検出される。",
         fig="pref_path_diagram.svg", fit="pref_fit.csv", n=47,
         boot="pref_bootstrap.csv", doc="docs/02-prefectures.md",
         files=[("pref_estimates.csv", "推定係数"), ("pref_influence.csv", "1県抜き診断"),
                ("pref_residuals.csv", "県別の寿命残差"), ("pref_sample.csv", "分析サンプル")],
         src=[("estat_sem.py", "SEM"), ("pref_influence.py", "LOO診断"),
              ("pref_residuals.py", "残差と図"), ("make_pref_diagram.py", "図の生成")],
         extra=[("pref_residual_chart.svg", "豊かさから予測される寿命とのずれ（47都道府県）")]),
    dict(id="pref-job", no="03", title="都道府県の転職 — 都市度と雇用の不安定さという2つの側面",
         lead="「都市労働市場の厚み」と「雇用の不安定さ」の相関は −0.07。"
              "都市度と不安定さを分けて転職率との関連を検討する。",
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

SUMMARIES = {
    "country": "所得水準から期待される以上に人的資本が充実した国ほど、その後の成長率が高いという関連が見られました。",
    "pref-health": "地域の豊かさ・医療供給量・平均寿命の関係を、男女別に分析しました。",
    "pref-job": "都市労働市場の厚みと雇用の不安定さという、2つの側面から転職率を分析しました。",
    "muni": "人口密度と居住移動の関係を、単身世帯・高齢化・通勤を通じた経路に分解しました。",
}

RESULT_OVERVIEWS = {
    "country": "所得水準から期待される以上に人的資本が充実した国ほど、その後の成長率が高いという関連が見られました。制度の質は、この人的資本の充実とも正の関連があります。制度と成長の直接の関係については、今回の分析では明確に示せませんでした。",
    "pref-health": "経済的に豊かな県ほど、男性の平均寿命が長く、人口当たりの病床・看護師・病院が少ないという関連が見られました。女性の平均寿命との関連と、医療供給量から寿命への効果は明確に示せませんでした。男女の係数差は、下記の追加検証で直接比較しています。",
    "pref-job": "都市労働市場が厚い県ほど、転職率が高いという関連が見られました。都市度と雇用の不安定さは、ほぼ相関しない別の側面として捉えられます。雇用の不安定さと転職率との関係には不確実性が残ります。",
    "muni": "人口が密集した地域ほど、居住移動が活発になる経路と、抑えられる経路の両方が見られました。単身世帯の多さは移動の多さと関連し、通勤流出を経由する経路は逆向きに働きます。人口密度と移動の関係は、これらを合わせて読む必要があります。",
}

DISCUSSIONS = {
    "country": [
        "今回の結果で中心となったのは、所得水準から期待される以上に人的資本が充実した国ほど、その後の成長率が高いという関係です。出発点は制度の質と成長の関係でしたが、制度から成長への直接の経路は明確にならず、制度と人的資本、人的資本と成長というつながりが見えてきました。ただし、各経路の関連が支持されても、制度が人的資本を通じて成長を引き起こすという因果的な媒介まで証明したわけではありません。",
        "この関係を読む鍵は、人的資本と初期所得の強い重なりでした。初版では両方を成長の説明に入れたことで標準化係数の絶対値が1を超え、指標を入れ替えても問題は解消しませんでした。そこで所得で説明できる部分を取り除くと、「豊かな国かどうか」から「同程度の所得の国と比べて人的資本が充実しているか」へと問いが明確になりました。採用モデルの結果も、この条件付きの比較として読む必要があります。",
        "一方、所得グループ別に分けると推定区間が広くなり、関係がグループ間で異なるかは判断できませんでした。人的資本の尺度も保健面の負荷が強いため、教育や技能全般についての結論には広げられません。次は教育と保健を分けた仕様を事前に定め、別期間でも関係が再現するか、国ごとに変わらない特徴を調整しても残るかを確かめることが重要です。",
    ],
    "pref-health": [
        "豊かな県ほど男性の平均寿命が長い一方、人口当たりの病床・看護師・病院は少ないという関係が見られました。この2つの関係は、県を1つずつ除いても符号が変わりませんでした。豊かさと医療供給量が同じ方向に並ばないことから、地域の健康を考える際には、経済条件と医療の量を分けて捉える必要があります。医療供給量から寿命への効果は示せませんでしたが、供給量だけでは医療の質や必要性を表し切れないため、医療が役立たないという意味ではありません。",
        "豊かさだけを使った補助回帰では、予測からのずれが男女で似ていました。これは、その回帰では捉えていない共通の地域要因を考える手掛かりですが、原因を特定した結果ではありません。また、女性で豊かさとの関連を検出できなかったことも、女性への効果がないことや、男女の効果が異なることの証明にはなりません。そこで、下記の追加検証では同じ標本内の係数差を直接比較しました。",
        "分析の過程では、国と都道府県で相関が違う理由を集計単位の違いと解釈しかけました。しかし、所得の範囲をそろえると国でも相関が弱まり、その説明は撤回しました。比較する地域のばらつきが結論を左右するという教訓です。今後は過去の地域条件と後年の寿命を組み合わせ、生活習慣や医療へのアクセスなども事前に定義して検証することで、今回残った問いを絞り込めます。",
    ],
    "pref-job": [
        "転職率の高さを説明する候補として、都市の労働市場の厚みと雇用の不安定さを検討したところ、より明確な根拠が得られたのは都市側の関係でした。両者の相関は点推定ではほぼなく、東京と沖縄のように転職率が高い県でも、その背景となる指標の組み合わせは異なります。ただし、不安定さから転職率への経路は推定区間が0をまたぎ、不安定さだけで沖縄を説明できるわけでもありません。補助回帰でも沖縄には大きな残差が残ります。",
        "この違いを確かめるうえで、結果の頑健性の検証が重要でした。不安定さからの経路は沖縄を除くと弱まり、残差と関連する指標を総当たりした探索でも、多重比較補正後の候補が沖縄の除外で残りませんでした。地方別に残差がまとまって見えた点も検定では支持されず、結論にすることを見送りました。目立つ地域や見た目のまとまりに説明を与えたくなっても、それが他の地域でも成り立つかは別に確かめる必要があります。",
        "今回の地域集計からは、誰が何を理由に転職し、その後どうなったかまでは分かりません。都市で転職が多いことを、良いマッチングや賃金上昇と同一視することもできません。次の課題は個票を使い、自発的な転職と失職後の転職、転職前後の賃金や職務の変化を分けて調べることです。それによって、移動の多さと個人にとっての便益を結びつけて検証できます。",
    ],
    "muni": [
        "市区町村の分析では、単独世帯割合が高い地域ほど総移動率が高く、高齢化率が高い地域ほど低いという関連が見られました。人口密度には逆向きの経路が併存し、モデル上の総効果は正でした。密度から単独世帯割合を経由する経路と、通勤流出から単独世帯割合を経由する経路を分けることで、単純な相関では見えない、関連が打ち消し合う構造を捉えられました。",
        "この分析は、都道府県より観測数を増やして労働移動を調べる試みから始まりました。しかし、市区町村では転職率が得られず、問いを居住移動へ変更しています。さらに、都道府県で用いたような潜在変数モデルは試した仕様で適合せず、観測変数のパス解析へ切り替えました。集計単位を細かくすることは、単に同じ分析の精度を上げる操作ではなく、測れる現象や指標間の関係そのものを変えることになりました。",
        "採用モデルの当てはまりは良好ですが、残差を見ながら経路を選んだ探索的なモデルであり、因果関係や別データでの再現性は確認できていません。指標の年次も混在し、居住移動の結果を転職の説明へ置き換えることはできません。次は別年次で同じ経路が再現するかを確かめ、都市圏・地方圏や人口規模別、年齢別の転入・転出に分けて比較することで、どの地域や層に当てはまる説明なのかを明らかにしていく必要があります。",
    ],
}

DISCUSSION_HIGHLIGHTS = {
    "country": [
        "今回の結果で中心となったのは、所得水準から期待される以上に人的資本が充実した国ほど、その後の成長率が高いという関係です。",
        "出発点は制度の質と成長の関係でしたが、制度から成長への直接の経路は明確にならず、制度と人的資本、人的資本と成長というつながりが見えてきました。",
    ],
    "pref-health": [
        "豊かな県ほど男性の平均寿命が長い一方、人口当たりの病床・看護師・病院は少ないという関係が見られました。",
        "医療供給量から寿命への効果は示せませんでしたが、供給量だけでは医療の質や必要性を表し切れないため、医療が役立たないという意味ではありません。",
    ],
    "pref-job": [
        "転職率の高さを説明する候補として、都市の労働市場の厚みと雇用の不安定さを検討したところ、より明確な根拠が得られたのは都市側の関係でした。",
        "ただし、不安定さから転職率への経路は推定区間が0をまたぎ、不安定さだけで沖縄を説明できるわけでもありません。",
    ],
    "muni": [
        "市区町村の分析では、単独世帯割合が高い地域ほど総移動率が高く、高齢化率が高い地域ほど低いという関連が見られました。",
        "人口密度には逆向きの経路が併存し、モデル上の総効果は正でした。",
    ],
}


def discussion_html(section_id):
    paragraphs = [esc(p) for p in DISCUSSIONS[section_id]]
    for sentence in DISCUSSION_HIGHLIGHTS[section_id]:
        target = esc(sentence)
        assert sum(p.count(target) for p in paragraphs) == 1, sentence
        paragraphs = [p.replace(target, f"<strong>{target}</strong>") for p in paragraphs]
    return ''.join(f"<p>{p}</p>" for p in paragraphs)


ARROW_NOTES = {
    "country": [
        "制度・人的資本からその後の成長への矢印は、初期時点の条件と後年の変化を区別しており、時間順序に根拠があります。ただし、欠損を補うため近接年の観測を採用していることにも注意が必要です。初期の制度や人的資本には過去の成長が影響しており、共通の要因も残るため、因果効果とは断定できません。",
        "制度から人的資本への矢印は、制度が教育・保健を支えるという仮説です。指標はほぼ同時期であり、人的資本が制度を改善する逆方向も考えられます。成長への時間差のある矢印と同じ強さの根拠はありません。人的資本を所得で残差化しても、因果の向きや未測定の交絡が解決するわけではありません。",
        "このモデルは、時間順序を考慮した関連の分析として読みます。制度→人的資本→成長という経路を示しても、制度の因果的な媒介効果を確定したものではありません。潜在変数から各指標への矢印は、概念が指標に表れるとする測定上の仮定です。",
    ],
    "pref-health": [
        "豊かさから医療供給量や寿命への矢印は、経済条件が医療資源や健康に関係するという仮説に基づきます。しかし、健康が経済活動を支える逆方向や、医療需要に応じて供給量が増える関係も考えられます。近接年の地域集計だけでは、これらを区別できません。",
        "実際に、豊かさ→医療供給量を逆向きの矢印や双方向の共分散に置き換えた検算では、適合度がほぼ同じでした。この関連について、適合度は矢印の向きを選ぶ根拠になっていません。",
        "したがって、仮説として方向を置いた地域間の関連として読みます。医療供給量の係数から病床を増減させた場合の寿命への効果を推定することはできません。豊かさや医療供給量から各指標への細い矢印も、指標が同じ概念を反映するという測定上の仮定です。",
    ],
    "pref-job": [
        "都市度や雇用の不安定さから転職率への矢印は、仕事の選択肢や失職が転職に関係するという仮説です。一方、転職や人の移動が都市への集積・賃金・失業率に影響する逆方向も考えられます。",
        "指標の年次は混在しており、一部の説明変数は転職率より後の時点です。そのため、この図を「先に生じた地域条件が、その後の転職を引き起こした」という時間順序の証拠にはできません。",
        "このモデルは、方向を仮定した地域間の関連の整理です。都市度を高める政策で転職率がどれだけ変わるかは、この係数だけでは分かりません。潜在変数から各指標への矢印も測定上の仮定であり、逆方向の構造モデルとの適合比較や因果方向の確定は行っていません。",
    ],
    "muni": [
        "人口密度から世帯構成・通勤を経て総移動率へ至る矢印は、都市構造と居住移動を整理するために置いたものです。国勢調査の条件を後年の住民基本台帳の移動と結びつける時間順序はありますが、密度・世帯構成・通勤の相互の向きまでは決まりません。",
        "人の移動はその後の密度や世帯構成も変えます。また、中間の経路には残差を見て採用したものがあり、探索的なモデルです。「単身世帯が移動を生む」などの個人の行動の因果説明を、自治体間の関連から直接導くことはできません。",
        "直接・間接の経路が打ち消し合うという結果は、採用した矢印の向きのモデル内での分解です。別方向のモデルでも同じ結論になるかは未確認です。適合度が良いこととは分けて解釈し、別年次・代替方向での比較を今後の検証課題とします。",
    ],
}

METHODS = {
    "country": "World BankのWGI・WDIによる国別データを用い、制度の質・人的資本・その後の成長の関係をSEMで推定しました。人的資本の各指標は初期所得に回帰した残差に置き換え、所得水準から期待される部分を取り除いています。",
    "pref-health": "e-Statの都道府県データを用い、経済的豊かさと入院医療キャパシティを潜在変数とするSEMで、男女別の平均寿命との関係を推定しました。小標本のため、係数の解釈ではブートストラップ区間と1県抜き診断を併せて確認します。",
    "pref-job": "e-Statの都道府県データを用い、都市労働市場の厚みと雇用の不安定さを潜在変数とするSEMで、転職率との関係を推定しました。小標本のため、ブートストラップ区間と1県抜き診断で結果の不確実性を確認します。",
    "muni": "2020年国勢調査と2024年住民基本台帳などの市区町村データを用いました。潜在変数による測定モデルの適合が悪かったため、観測変数のパス解析で直接・間接の関係を分解しました。総移動率は転入と転出による居住移動を測り、転職を測る指標ではありません。",
}

RELATED = {
    "country": dict(
        papers=[
            ("Glaeserほか（2004）Do Institutions Cause Growth?",
             "https://www.nber.org/papers/w10568",
             "人的資本と成長が制度改善に先行する可能性を論じ、制度指標や因果推定の方法を検討した研究。"),
            ("Acemoglu・Johnson・Robinson（2004）Institutions as the Fundamental Cause of Long-Run Growth",
             "https://www.nber.org/papers/w10481",
             "歴史的な事例などを基に、制度が長期的な経済発展の基礎になるという議論を展開した研究。"),
        ],
        common="制度・人的資本・経済発展の関係という問いを共有する。今回の人的資本とその後の成長との正の関連は、人的資本を重視する議論と方向性が整合的である。",
        difference="今回は初期所得で残差化した人的資本と、約10年間の成長を扱うSEM。先行研究とは指標・期間・推定方法が異なり、直接の追試ではない。",
        unknown="人的資本と制度のどちらが因果的に先行するかは決められない。制度の直接パスの区間が0をまたぐことも、制度の長期的重要性を否定しない。"),
    "pref-health": dict(
        papers=[
            ("Kataokaほか（2021）Geographical socioeconomic inequalities in healthy life expectancy in Japan, 2010–2014: An ecological study",
             "https://doi.org/10.1016/j.lanwpc.2021.100204",
             "日本の1,707市区町村で、地域の社会経済的不利と平均寿命・健康寿命などの関係を分析した研究。"),
        ],
        common="地域の経済・社会条件と健康の関係を、地域単位のデータから調べる点が共通する。",
        difference="先行研究は市区町村の地域剥奪指標を用いる。今回は都道府県の豊かさと医療供給量を潜在変数として扱い、平均寿命を説明する。集計単位と指標が違うため係数は直接比較できない。",
        unknown="男性で関連を検出し女性で検出できなかったことだけでは、男女の効果が異なるとは言えない。本ページの追加検証で係数差を直接比較しているが、モデル上の条件付きの比較である。また、医療供給量の効果を示せなかったことは、医療が無効であることを意味しない。"),
    "pref-job": dict(
        papers=[
            ("森川正之（2011）都市密度・人的資本と生産性―賃金データによる分析―",
             "https://www.rieti.go.jp/jp/publications/dp/11j046.pdf",
             "賃金構造基本調査の個票を使い、都市密度・人的資本と賃金の関係を分析。都市集積による学習や労働者と企業のマッチング改善を示唆している。"),
        ],
        common="都市の労働市場の厚みが働き方に関係するという問題意識が近い。マッチング改善は、今回の都市度と転職率との関連を考える際の説明候補になる。",
        difference="先行研究は個人の賃金を扱い、今回は都道府県の転職率を扱う。転職の頻度と、転職によって得られる便益は異なる。",
        unknown="転職率が高いだけでは、賃金上昇や生産性向上、良いマッチングが実現したとは判断できない。個票で転職前後の賃金や職務との適合を調べる必要がある。"),
    "muni": dict(
        papers=[
            ("中澤克佳（2007）高齢者の地域間移動要因の実証分析",
             "https://www.jstage.jst.go.jp/article/pfsjipf/3/0/3_142/_article/-char/ja/",
             "東京圏の市区町村で高齢者の移動を分析。前期・後期高齢者の移動性向の違いと、介護施設が相対的に充実した自治体への後期高齢者の流入を報告している。"),
        ],
        common="地域の人口構成や地域条件と居住移動の関係を扱う点が共通する。",
        difference="先行研究は東京圏の高齢者の社会増加を扱う。今回は全国の全年齢の転入＋転出による総移動率を扱う。高齢化率と総移動率の負の関連は、一部の自治体への高齢者の流入と矛盾しない。",
        unknown="全年齢をまとめた結果から、若者・高齢者それぞれの移動理由は特定できない。年齢別、転入・転出別に分け、施設立地や住宅条件との関係を検証する余地がある。"),
}

CSS = """
:root{color-scheme:light dark;--ink:#16242b;--muted:#5b6b73;--line:#dde5e8;--accent:#0b6b68;--bg:#f5f8f8;--card:#fff;--warn:#8a6d1f;--warnbg:#fff8ec;--warnline:#e8d9b8}
@media(prefers-color-scheme:dark){:root{--ink:#e8eef0;--muted:#a3b2b8;--line:#2c3a40;--accent:#5fd0c6;--bg:#12191c;--card:#182125;--warn:#e3c07a;--warnbg:#241f14;--warnline:#4a3f25}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.85 system-ui,-apple-system,"Hiragino Sans","Noto Sans JP",sans-serif}
main{max-width:1140px;margin:auto;padding:56px 24px}
.eyebrow{display:block;font-size:16px;letter-spacing:.02em;color:var(--accent);font-weight:700;text-decoration:none}
.eyebrow:hover{text-decoration:underline}.site-subtitle{display:block;font-size:12px;color:var(--muted);font-weight:400;margin-top:4px}
.share-tools{display:flex;flex-wrap:wrap;align-items:center;gap:10px;margin:16px 0 24px;font-size:14px;color:var(--muted)}.share-tools a,.share-tools button{font:inherit;color:var(--accent);background:var(--card);border:1px solid var(--line);border-radius:7px;padding:8px 12px;text-decoration:none;cursor:pointer}.share-tools button:focus-visible{outline:3px solid #dc9523;outline-offset:3px}.share-status input{width:min(100%,540px);font:inherit}.share-status:empty{display:none}
.home-main{padding-top:20px}.home-header{padding:0 0 28px}.home-header .header-top{justify-content:flex-end}.home-header h1{font-size:clamp(24px,4.6vw,52px);line-height:1.4;margin:8px 0 16px}.home-title-line{display:block;white-space:nowrap}.home-subtitle{font-size:clamp(16px,2vw,21px);color:var(--accent)}.home-question{font-size:22px;color:var(--ink);margin-top:28px}.home-actions{margin:28px 0}.home-actions .primary{background:var(--accent);color:var(--card);border-color:var(--accent)}
.header-top{display:flex;align-items:center;justify-content:space-between;gap:16px}
.header-top .eyebrow{min-width:0}
.github-link{display:inline-flex;align-items:center;gap:8px;flex-shrink:0;min-height:44px;padding:6px 10px;color:var(--ink);text-decoration:none;font-size:14px;font-weight:600;border-radius:8px}
.github-link:hover{background:var(--line)}.github-link svg{width:22px;height:22px;fill:currentColor}
h1{font-size:clamp(28px,4vw,42px);line-height:1.35;margin:12px 0 8px}h2{font-size:24px;line-height:1.5;margin:6px 0 12px}h3{font-size:16px;margin:26px 0 8px}
p{color:var(--muted);margin:.6em 0}a{color:var(--accent);text-underline-offset:4px}a:focus-visible{outline:3px solid #dc9523;outline-offset:3px}
nav{display:flex;flex-wrap:wrap;gap:10px;margin:26px 0}nav a,.open{display:inline-block;border:1px solid var(--line);border-radius:8px;padding:9px 15px;background:var(--card);text-decoration:none;font-size:14px}
section{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:30px;margin:24px 0;scroll-margin-top:20px}
.analysis-content>p,.analysis-content>details>p,.page-header>p{max-width:48em}.analysis-content>h2:not(:first-of-type){margin-top:48px;padding-top:24px;border-top:1px solid var(--line)}.analysis-content>p{line-height:1.95}.analysis-content strong{color:var(--ink)}.technical-details{margin:18px 0;padding:16px 20px;border:1px solid var(--line);border-radius:10px}.technical-details>summary{font-weight:600;color:var(--accent);cursor:pointer}.technical-details[open]>summary{margin-bottom:18px}@media(max-width:600px){.analysis-content{padding:18px 12px}.technical-details{padding:12px}.analysis-content figcaption{display:flex;flex-wrap:wrap;align-items:center;gap:12px}}
.number{color:var(--accent);font-weight:700;font-size:13px}
.fit{font-size:13px;color:var(--muted);font-variant-numeric:tabular-nums;border-left:3px solid var(--accent);padding-left:12px;margin:14px 0}
figure{margin:22px 0}img{width:100%;height:auto;display:block;border:1px solid var(--line);border-radius:8px;background:#fff}
figcaption{font-size:13px;color:var(--muted);margin-top:8px}
table{width:100%;border-collapse:collapse;font-size:14px;font-variant-numeric:tabular-nums}
th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--line)}th{color:var(--muted);font-weight:600;font-size:12px}
td.num{text-align:right}.ok{color:#0b6b68;font-weight:700}.no{color:var(--muted)}
ul.files{list-style:none;padding:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:0 22px}
ul.files li{padding:9px 0;border-bottom:1px solid var(--line);font-size:14px}ul.files li span{display:block;font-size:11px;color:var(--muted);overflow-wrap:anywhere}
ul.files li:has(details[open]){grid-column:1/-1;min-width:0}
summary{cursor:pointer;color:var(--accent);overflow-wrap:anywhere}summary:focus-visible{outline:3px solid #dc9523;outline-offset:3px}
.file-toolbar{display:flex;flex-wrap:wrap;align-items:center;gap:12px;margin:12px 0;font-size:13px}
.file-toolbar input{max-width:100%;padding:7px 10px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--ink);font:inherit}
.file-preview{max-height:560px;overflow:auto;border:1px solid var(--line);border-radius:8px;background:var(--bg)}
.file-preview:focus-visible{outline:3px solid #dc9523;outline-offset:2px}
.file-preview table{white-space:pre;font-size:12px}.file-preview th{position:sticky;top:0;background:var(--card)}
.file-preview pre{margin:0;padding:16px;font:13px/1.65 ui-monospace,SFMono-Regular,Consolas,monospace;tab-size:4}
.file-preview code{font:inherit}
ul.files li .file-preview code span{display:inline;font-size:inherit;overflow-wrap:normal}
.file-preview code .syn-keyword{color:#8250df;font-weight:600}
.file-preview code .syn-string{color:#0a3069}
.file-preview code .syn-comment{color:#57606a;font-style:italic}
.file-preview code .syn-number{color:#0550ae}
.file-preview code .syn-definition{color:#953800;font-weight:600}
@media(prefers-color-scheme:dark){.file-preview code .syn-keyword{color:#d2a8ff}.file-preview code .syn-string{color:#a5d6ff}.file-preview code .syn-comment{color:#a3b2b8}.file-preview code .syn-number{color:#79c0ff}.file-preview code .syn-definition{color:#ffa657}}
[hidden]{display:none!important}
.note{border-left:3px solid var(--warnline);background:var(--warnbg);color:var(--ink);padding:14px 18px;font-size:14px;border-radius:0 8px 8px 0;margin:18px 0}
footer{font-size:13px;color:var(--muted);margin-top:40px}
.related{margin:28px 0;padding:20px;border:1px solid var(--line);border-radius:10px;background:var(--bg);font-size:14px}
.related h3{margin:0 0 12px}.related ul{padding-left:20px}.related li{margin:12px 0}.related li p{margin:4px 0}
.related dt{font-weight:700;margin-top:12px}.related dd{margin:4px 0;color:var(--muted)}
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


def highlight_python(source):
    """標準ライブラリで字句を色分けし、空白・改行と元コードを保持する。"""
    offsets = [0]
    for line in source.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))

    def position(point):
        row, column = point
        return offsets[min(row - 1, len(offsets) - 1)] + column

    parts, cursor, definition_next = [], 0, False
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            kind = None
            if token.type == tokenize.COMMENT:
                kind = "comment"
            elif token.type == tokenize.STRING or tokenize.tok_name[token.type].startswith("FSTRING"):
                kind = "string"
            elif token.type == tokenize.NUMBER:
                kind = "number"
            elif token.type == tokenize.NAME:
                if keyword.iskeyword(token.string):
                    kind = "keyword"
                elif definition_next:
                    kind = "definition"
                definition_next = token.string in ("def", "class")
            if kind is None:
                continue
            start, end = position(token.start), position(token.end)
            parts.append(esc(source[cursor:start]))
            parts.append(f'<span class="syn-{kind}">{esc(source[start:end])}</span>')
            cursor = end
    except (tokenize.TokenError, IndentationError):
        # 編集途中のコードでも内容を欠落させず表示する。
        return esc(source)
    parts.append(esc(source[cursor:]))
    return "".join(parts)


def files_ul(items, prefix):
    entries = []
    for filename, label in items:
        source = paths.result(filename) if prefix == "results" else paths.ROOT / prefix / filename
        content = source.read_text(encoding="utf-8")
        toolbar = f"<a href='{prefix}/{esc(filename)}' download>元ファイルをダウンロード</a>"
        if source.suffix == ".csv":
            rows = list(csv.reader(io.StringIO(content)))
            header, records = (rows[0], rows[1:]) if rows else ([], [])
            preview = ("<table><thead><tr>" + "".join(f"<th scope='col'>{esc(v)}</th>" for v in header)
                       + "</tr></thead><tbody>" + "".join(
                           "<tr>" + "".join(f"<td>{esc(v)}</td>" for v in row) + "</tr>"
                           for row in records) + "</tbody></table>")
            toolbar += (f"<label class='file-search' hidden>行を検索 <input type='search' placeholder='国名・県名・変数名など'></label>"
                        f"<output aria-live='polite'>{len(records):,} 行</output>")
        else:
            preview = f"<pre><code>{highlight_python(content)}</code></pre>"
        entries.append(
            f"<li><details><summary>{esc(label)}<span>{esc(filename)} — クリックで表示</span></summary>"
            f"<div class='file-toolbar'>{toolbar}</div>"
            f"<div class='file-preview' tabindex='0' role='region' aria-label='{esc(label)}：{esc(filename)}'>"
            f"{preview}</div></details></li>")
    return "<ul class='files'>" + "".join(entries) + "</ul>"


# 内容は生成時に埋め込むため、ローカルで開いても通信なしで閲覧できる。
PREVIEW_JS = """
document.querySelectorAll('.file-search').forEach(label => {
  label.hidden = false;
  const details = label.closest('details');
  const rows = Array.from(details.querySelectorAll('tbody tr'));
  const searchable = rows.map(row => row.textContent.toLocaleLowerCase());
  const output = details.querySelector('output');
  label.querySelector('input').addEventListener('input', event => {
    const query = event.target.value.trim().toLocaleLowerCase();
    let count = 0;
    rows.forEach((row, index) => {
      row.hidden = !searchable[index].includes(query);
      if (!row.hidden) count++;
    });
    output.textContent = `${count.toLocaleString()} / ${rows.length.toLocaleString()} 行`;
  });
});
"""


def related_research(section_id):
    item = RELATED[section_id]
    papers = "".join(
        f"<li><a href='{esc(url)}'>{esc(title)}</a><p>{esc(summary)}</p></li>"
        for title, url, summary in item["papers"])
    comparison = "".join(
        f"<dt>{label}</dt><dd>{esc(item[key])}</dd>"
        for key, label in [("common", "共通する点"), ("difference", "異なる点"),
                           ("unknown", "今回まだ分からないこと")])
    return (f"<aside class='related' aria-labelledby='related-{section_id}'>"
            f"<h3 id='related-{section_id}'>関連研究と今回の位置づけ</h3>"
            "<p>関連する代表例を選んだ比較であり、網羅的な文献レビューではありません。"
            "以下の位置づけは本サイトによる整理です。対象・指標・調整要因が異なるため、"
            "標準化係数の大小だけで研究間の効果を比べることはできません。</p>"
            f"<ul>{papers}</ul><dl>{comparison}</dl></aside>")


def audit_section(section_id):
    a = pd.read_csv(paths.result('sem_audit_summary.csv')).set_index('model').loc[section_id]
    out = ["<h3>追加検証：推定の健全性</h3>",
           f"<p>復元抽出{int(a.attempts):,}回のうち、最適化の成功・係数と目的関数の有限性・負の分散なし・"
           f"モデル共分散の正定値性という基本条件を満たしたのは{int(a.usable):,}回、除外は{int(a.failed):,}回でした。"
           f"基本条件を満たしたうち、分散がほぼゼロの境界解は{int(a.usable_boundary):,}回です。</p>",
           "<p>境界の基準は分散の絶対値が10⁻⁸以下。境界解は収束失敗とは区別して記録し、一律には除外していません。"
           "これは局所最適性・情報行列・全てのモデル仮定を保証する検査ではありません。"
           "再抽出は既存と同じ前処理済みデータから行い、前処理やモデル選択の不確実性は含めていません。</p>"]
    if section_id == 'pref-health':
        d = pd.read_csv(paths.result('pref_gender_contrasts.csv'))
        loo = pd.read_csv(paths.result('pref_gender_contrast_loo.csv'))
        rows=[]
        sensitivity=[]
        for key,label in [('WEALTH_years','豊かさ'),('MED_years','医療供給量')]:
            r=d[(d.parameter==key)&(d.scope=='usable_including_boundary')].iloc[0]
            interior=d[(d.parameter==key)&(d.scope=='interior_only')].iloc[0]
            decision='0を含むため、差を示せない' if r.family_low<=0<=r.family_high else '0を含まず、男性側が大きい' if r.family_low>0 else '0を含まず、女性側が大きい'
            v=loo.loc[loo.usable,key]
            rows.append(f"<tr><th>{label}</th><td>{r.estimate:+.3f}</td><td>[{r.low:+.3f}, {r.high:+.3f}]</td>"
                        f"<td>[{r.family_low:+.3f}, {r.family_high:+.3f}]</td><td>{decision}</td></tr>")
            sensitivity.append(f"<p>{label}の男女差：1県抜きの差の範囲は{v.min():+.3f}〜{v.max():+.3f}年"
                       f"（基本条件を満たす{len(v)}県分）。境界解を除いた参考区間は"
                       f"[{interior.low:+.3f}, {interior.high:+.3f}]（{int(interior.valid)}反復）です。"
                       "境界解の除外自体が標本を選別するため、主結果の代わりにはしません。</p>")
        out.append("<h3>男女差を直接比較する</h3><p>同じ再抽出標本の中で、男性と女性の回帰係数の差を計算しました。"
                   "主比較は寿命をどちらも年に戻した係数の「男−女」です。豊かさは県民所得の、医療供給量は看護師数の"
                   "元標本の1標準偏差に尺度を合わせた潜在変数1単位当たりの差で、異なる因子間の比較には使いません。"
                   "結果を見た後の追加検証であり、事前登録された検証ではありません。</p>")
        out.append("<div style='overflow-x:auto'><table><thead><tr><th>説明側</th><th>男−女（年）</th>"
                   "<th>95％区間</th><th>2比較を考慮した各97.5％区間</th><th>読み取り</th></tr></thead><tbody>"
                   + ''.join(rows) + "</tbody></table></div><p>2本の年単位の比較にBonferroni対応の区間を併記しています。"
                   "標準化係数の差は参考値としてCSVに収録。区間はブートストラップ近似で、境界解の多さやモデル選択の影響は残ります。"
                   "女性側の効果がゼロという結論や、男女の因果効果の差を証明するものではありません。</p>")
        out.extend(sensitivity)
        out.append(files_ul([('pref_gender_contrasts.csv','男女の係数差と区間'),('pref_gender_contrast_loo.csv','男女差の1県抜き診断')],'results'))
    out.append(files_ul([('sem_audit_summary.csv','全モデルの推定監査集計')],'results'))
    out.append("<p><a href='results/sem_audit_trials.csv' download>全反復の監査記録をダウンロード</a></p>")
    out.append(files_ul([('sem_audit.py','推定監査と男女差の検証コード')],'src'))
    return ''.join(out)


def case_examples(section_id):
    groups = {
        "country": [("country", "一人当たりGDP成長（対数差×100・年率ではない）", ["United States", "Japan", "China"])],
        "pref-health": [("health_m", "平均寿命・男（年）", ["東京都", "大阪府"]),
                        ("health_f", "平均寿命・女（年）", ["東京都", "大阪府"])],
        "pref-job": [("job", "転職率（％・差はポイント）", ["東京都", "大阪府", "沖縄県"])],
        "muni": [("muni", "総移動率（％・差はポイント）", ["新宿区 [13104]"])],
    }[section_id]
    out = ["<h2>予測とのずれ</h2><h3>主要な国・地域の具体例</h3>",
           "<p>主要国・身近な地域をあらかじめ指定し、それに加えて各指標で残差の絶対値が最小の地域、"
           "正の残差が最大の地域、負の残差が最小の地域を機械的に選びました。同じ地域は1行にまとめています。"
           "残差の大小は記述的な比較であり、統計的な異常の判定ではありません。</p>"]
    translations = {"United States": "アメリカ", "Japan": "日本", "China": "中国"}
    chart_groups = []
    for key, title, named in groups:
        data = pd.read_csv(paths.result(f"{key}_prediction_diagnostics.csv")).set_index("region")
        selected = {}
        for name in named:
            selected[name] = ["指定した比較例"]
        for name, reason in [(data.residual.abs().idxmin(), "予測に最も近い"),
                             (data.residual.idxmax(), "予測を最も上回る"),
                             (data.residual.idxmin(), "予測を最も下回る")]:
            selected.setdefault(name, []).append(reason)
        chart_groups.append((key, data, selected))
        interval = "mean_ci_low" in data
        rows = []
        for name, reasons in selected.items():
            if name not in data.index:
                missing = "分析対象外。現在の国モデルでは一人当たりGNI成長が欠損しているため、中国を除外。予測は算出していません。" if key == "country" and name == "China" else "現在の分析対象に含まれていません。"
                rows.append(f"<tr><th scope='row'>{esc(translations.get(name,name))}</th><td colspan='{6 if interval else 5}'>{esc(missing)}</td></tr>")
                continue
            r = data.loc[name]
            direction = "上回る" if r.residual > 0 else "下回る" if r.residual < 0 else "一致する"
            interpretation = f"実測値は予測値を{abs(r.residual):.2f}{'年' if key.startswith('health') else '対数ポイント' if key == 'country' else 'ポイント'}{direction}。"
            ci = f"<td>[{r.mean_ci_low:.2f}, {r.mean_ci_high:.2f}]</td>" if interval else ""
            rows.append(f"<tr><th scope='row'>{esc(translations.get(name,name))}</th><td>{esc('／'.join(reasons))}</td>"
                        f"<td>{r.observed:.2f}</td><td>{r.predicted:.2f}</td><td>{r.residual:+.2f}</td>{ci}<td>{esc(interpretation)}</td></tr>")
        out.append(f"<h3>{esc(title)}</h3><div style='overflow-x:auto' tabindex='0' role='region' aria-label='{esc(title)}の事例比較'>"
                   "<table><thead><tr><th>国・地域</th><th>選定理由</th><th>実測</th><th>予測</th><th>実測−予測</th>"
                   + ("<th>平均予測の95％区間</th>" if interval else "")
                   + "<th>読み取り</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")
    from make_case_diagram import build as case_diagram
    chart = case_diagram(section_id, chart_groups)
    out.insert(2, f"<figure><a href='figures/{chart}'><img src='figures/{chart}' alt='選定した国・地域の予測との差。0を中心に左右で比較。健康は男女を併記。' loading='lazy'></a>"
               "<figcaption>地域名と予測との差を表示。クリックで原寸。正確な数値と選定理由は下表で確認できます。</figcaption></figure>")
    explanations = {
        "country": "これは制度・所得調整後の人的資本・初期所得を使った補助回帰による比較です。日本とアメリカのずれも、これらの条件だけでは成長を説明し切れないことを示します。人口構成・産業構造・期間中の出来事などは説明候補ですが、この分析では個別の原因として検証していません。中国は対象外であり、説明できた／できなかったという評価自体をしていません。",
        "pref-health": "この予測は豊かさのみを使う補助回帰です。予測に近くても健康の原因が説明されたわけではありません。東京は豊かさスコアが他県から離れており、回帰の傾きや予測がその位置に影響されます。生活習慣や医療へのアクセスなどは追加検証の候補ですが、個別の残差から原因を特定することはできません。",
        "pref-job": "東京は補助回帰の予測に近い一方、沖縄は都市度と雇用の不安定さを考慮しても予測を上回ります。したがって「沖縄は雇用の不安定さで説明できる」とは言い切れません。産業構成・年齢構成や転職理由の違いは調べる候補ですが、既存の指標探索では頑健な追加説明が得られておらず、理由は未特定です。",
        "muni": "パスモデルの総移動率の式は、人口密度・高齢化率・単独世帯割合・通勤流出率を使います。ずれは、それらを考慮しても残る差です。住宅の供給や大学・事業所の立地、期間中の出来事は追加検証の候補ですが、このモデルだけから特定の自治体の原因にはできません。区単位のデータを含むため、名称とともに自治体コードも示しています。",
    }
    out.append(f"<p>{esc(explanations[section_id])}</p>")
    out.append("<p>補助回帰の区間は合成指標を固定した600回の復元抽出による平均予測の区間です。個別の実測値の予測区間ではなく、区間の外にあるだけで異常とは判定できません。すべて標本内の当てはめです。</p>")
    return "".join(out)


def prediction_section(section_id):
    keys = {"country": [("country", "一人当たりGDP成長")],
            "pref-health": [("health_m", "平均寿命（男）"), ("health_f", "平均寿命（女）")],
            "pref-job": [("job", "転職率")], "muni": [("muni", "総移動率")]}[section_id]
    parts = ["<details><summary>全地域の当てはまり・診断図とデータを見る</summary>",
             "<p>左は実測値と予測値（破線上で一致）、右は予測値と残差です。残差が正なら予測より高く、負なら低い値です。"
             "同じ標本に当てはめた結果であり、未知の地域や将来への予測精度ではありません。</p>"]
    if section_id == "muni":
        parts.append("<p>総移動率のパス方程式に、説明変数の実測値を入れて計算しています。人口密度だけから全経路をたどった予測とは異なります。単位は％、残差はパーセントポイントです。</p>")
    else:
        parts.append("<p>上の具体例と同じ補助回帰の結果を、全地域について表示しています。"
                     "CSVのmean_ci_low／mean_ci_highは上で説明した平均予測の95％区間で、前処理の不確実性は含みません。</p>")
    for key,label in keys:
        f = f"{key}_prediction_diagnostics.svg"
        parts.append(f"<figure><a href='figures/{f}'><img src='figures/{f}' alt='{esc(label)}の実測値・予測値と残差' loading='lazy'></a>"
                     f"<figcaption>{esc(label)} — 全点表示。クリックで原寸</figcaption></figure>")
    parts.append("<p>表のregionは国・地域名、observedは実測値、predictedは予測値、residualは実測値−予測値です。地域名で検索できます。</p>")
    parts.append(files_ul([(f"{key}_prediction_diagnostics.csv", label + "：実測・予測・残差") for key,label in keys], "results"))
    parts.append(files_ul([("prediction_diagnostics.py", "予測と残差の計算・図の生成")], "src"))
    parts.append("</details>")
    return "".join(parts)


def build(selected=None):
    sections = [s for s in SECTIONS if selected is None or s["id"] == selected]
    if not sections:
        raise ValueError(f"Unknown analysis: {selected}")
    nav = "".join(f"<a href='{s['id']}.html'"
                  + (" aria-current='page'" if s['id'] == selected else "")
                  + f">{s['no']} {esc(s['title'].split(' — ')[0])}</a>"
                  for s in SECTIONS)
    if selected:
        nav = "<a href='index.html'>← 分析の一覧に戻る</a>" + nav
    nav += "<a href='guide.html'>図の読み方</a>"
    heading = sections[0]["title"] if selected else "豊かさ・健康・人の移動は、どう関係する？"
    intro = (RESULT_OVERVIEWS[selected]
             if selected else "World Bank と e-Stat の公開データを用いた、国・都道府県・市区町村の4つの分析。気になる図から詳細に進めます。")
    note = (f"すべて観測データであり、矢印の向きはモデルの仮定にすぎない。"
            "同じ共分散行列を再現する等価モデルは無数にあり、向きを逆にしても適合度は変わらない"
            f"（<a href='{REPO}/docs/04-methodology.md'>方法論 §5</a>に検算あり）。"
            "区間が0をまたぐパスは「効果を示せなかった」ものとして扱うこと。"
            "図中の因子負荷のうち1本だけ有意性が示されないのは、その指標が潜在変数のスケールを決める"
            f"参照指標として固定され推定されていないため（<a href='{REPO}/docs/06-model-selection.md'>台帳</a>に説明）。"
            if selected else "観測データから関係を調べたもので、因果関係を証明する分析ではありません。")
    about = """<section id="about"><h2>このプロジェクトについて</h2>
<p>公開データを使い、経済・健康・労働・人口移動の関係を、国・都道府県・市区町村の単位で調べるプロジェクトです。
構造方程式モデリング（SEM）を中心に、複数の関係を同時に捉えます。</p>
<p>問いを立て、データを確認し、モデルを推定したうえで、不確実性や特定の地域への依存を検証します。
分析がうまく成立しなかった試行や、見直した解釈も残し、コードと結果を公開しています。</p>
<p>AIとの対話を通じて分析を進め、コード・図・説明文の作成や改善にもAIを活用しています。
AIが生成した説明をそのまま結論とせず、データや検証結果に照らして見直す方針です。</p></section>""" if selected is None else ""
    body = []
    for s in sections:
        if selected is None:
            body.append(
                f"<section id='{s['id']}'><div class='number'>{s['no']} · N = {s['n']:,}</div>"
                f"<h2><a href='{s['id']}.html'>{esc(s['title'])}</a></h2>"
                f"<figure><a href='{s['id']}.html'><img src='figures/{s['fig']}' "
                f"alt='{esc(s['title'])}のパス図。クリックで分析の詳細へ' loading='lazy'></a></figure>"
                f"<p>{esc(SUMMARIES[s['id']])}</p>"
                f"<a class='open' href='{s['id']}.html'>詳しく見る →</a></section>")
            continue
        parts = [f"<section class='analysis-content' id='{s['id']}'><div class='number'>{s['no']}</div>",
                 "<h2>結果を図で見る</h2>",
                 f"<figure><a href='figures/{s['fig']}'><img src='figures/{s['fig']}' "
                 f"alt='{esc(s['title'])}' loading='lazy'></a>"
                 f"<figcaption><a class='open' href='figures/{s['fig']}'>図を拡大して読む ↗</a> <a href='guide.html#legend'>凡例・数字の読み方</a></figcaption></figure>",
                 share_buttons(s["id"]),
                 "<h2>考察</h2>",
                 discussion_html(s['id']),
                 f"<p><a href='{REPO}/{s['doc']}'>分析と試行の記録を読む →</a></p>",
                 case_examples(s["id"]),
                 prediction_section(s["id"]),
                 "<h2>結果の確かさを確認する</h2>",
                 "<p>区間が0を含む経路は、関連を明確に示せていません。以下の検証は、採用したモデルと前処理に条件づけられたものです。</p>",
                 "<details class='technical-details'><summary>ブートストラップによる各経路の判定</summary>", boot_table(s["boot"]), "</details>"]
        audit = pd.read_csv(paths.result('sem_audit_summary.csv')).set_index('model').loc[s['id']]
        parts.append(f"<p>再抽出{int(audit.attempts)}回中、分散がほぼゼロの境界解は{int(audit.usable_boundary)}回でした。境界解も含めた区間であり、モデルの安定性に注意が必要です。</p>" if audit.usable_boundary else
                     "<p>今回の再抽出では、基本的な推定条件を満たさない結果や分散がほぼゼロの境界解はありませんでした。因果関係や別データでの再現性を保証するものではありません。</p>")
        if s['id'] == 'pref-health':
            parts.append("<p><strong>追加検証では、豊かさの係数は男性側が大きく、医療供給量の係数の男女差は示せませんでした。</strong>比較の区間と1県抜きの検証は下に掲載しています。</p>")
        parts.append("<details class='technical-details'><summary>推定の診断と追加検証を詳しく見る</summary>" + audit_section(s["id"]) + "</details>")
        for f, cap in s.get("extra", []):
            parts.append(f"<figure><a href='figures/{f}'><img src='figures/{f}' "
                         f"alt='{esc(cap)}' loading='lazy'></a>"
                         f"<figcaption>{esc(cap)} — figures/{f}</figcaption></figure>")
        parts += ["<h3>データと分析方法</h3>", f"<p>{esc(METHODS[s['id']])}</p>",
                  f"<div class='fit'>{fit_line(s['fit'], s['n'])}</div>",
                  "<h3 id='arrow-direction'>仮定した関係と根拠：関連と因果の違い</h3>",
                  "<p>図の矢印は、モデルで仮定した関係の方向を示します。相関や関連があることと、一方を変えることで他方が変わる因果関係があることは別です。モデルがよく当てはまっても、因果関係が証明されたわけではありません。回帰パス係数は偏相関係数とは異なり、ここでは主に「関連」と表現しています。<a href='guide.html#association'>関連・相関・因果と係数の違い →</a></p>",
                  "".join(f"<p>{esc(paragraph)}</p>" for paragraph in ARROW_NOTES[s['id']]),
                  f"<p><a href='{REPO}/docs/04-methodology.md'>矢印の向きと等価モデルの検算記録</a></p>",
                  f"<h3>解釈上の注意</h3><div class='note'>{note}</div>",
                  related_research(s["id"]),
                  "</section>"]
        body.append("".join(parts))

    resources = ''
    if selected:
        current = sections[0]
        resources = ("<h3>結果データ</h3>" + files_ul(current['files'], 'results')
                     + "<h3>分析コード</h3>" + files_ul(current['src'], 'src')
                     + f"<p><a href='{REPO}/{current['doc']}'>この分析の詳細ドキュメント →</a></p>")
    repro = f"""<details id="repro" class="technical-details"><summary>データ・コード・再現方法</summary>
{resources}
<h3>分析を再現する</h3>
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
<li><a href="{REPO}/docs/06-model-selection.md">06 モデル選択の台帳</a><span>docs/06-model-selection.md</span></li>
<li><a href="{REPO}/Makefile">Makefile</a><span>再現用エントリポイント</span></li>
</ul></details>"""
    if selected:
        body[-1] = body[-1].removesuffix("</section>") + repro + "</section>"
    detail_nav = f'<nav aria-label="目次">{nav}<a href="{REPO}/docs/06-model-selection.md">モデル選択の台帳</a>\n<a href="{REPO}/docs/04-methodology.md">方法論の教訓</a>\n<a href="{REPO}/README.md">README</a></nav>'
    brand = '<div><a class="eyebrow" href="index.html" aria-label="国と地域の「なぜ？」を公的データで探る — トップページへ">国と地域の「なぜ？」を公的データで探る</a><span class="site-subtitle">構造方程式モデリング（SEM）による探索的分析</span></div>'
    return f"""<!doctype html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(heading)}｜公的データによるSEM</title>
<style>{CSS}</style></head><body><main class="{'home-main' if selected is None else 'page-main'}">
<header class="{'home-header' if selected is None else 'page-header'}"><div class="header-top">
{brand if selected else ''}
<a class="github-link" href="{REPO_URL}" aria-label="GitHubでコード・変更履歴を見る">
<svg viewBox="0 0 16 16" aria-hidden="true" focusable="false"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82a7.65 7.65 0 0 1 2-.27c.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8Z"/></svg>
<span>GitHub</span></a></div>
<h1>{esc(heading) if selected else '<span class="home-title-line">国と地域の「なぜ？」を</span><span class="home-title-line">公的データで探る</span>'}</h1>
{'<p class="home-subtitle">構造方程式モデリング（SEM）による探索的分析</p><p class="home-question">豊かさ・健康・人の移動は、どう関係する？</p>' if selected is None else ''}
<p>{esc(intro)}</p>
{('<p class="fit">分析手法：' + ('パス解析（SEMの一種・観測変数のみ）' if selected == 'muni' else '構造方程式モデリング（SEM）') + '</p>') if selected else ''}
{'<p>複数の関係を同時に推定し、直接の関係と他の変数を経由する間接の関係を分けて調べます。</p>' if selected == 'muni' else ''}
{detail_nav if selected else '<nav class="home-actions" aria-label="サイトの入口"><a class="primary" href="#country">4つの分析を見る →</a><a href="guide.html">図の読み方を知る →</a></nav>'}
{share_buttons() if selected is None else ''}
{f'<div class="note">{note}</div>' if selected is None else ''}</header>
{about}
{''.join(body)}
<nav aria-label="分析ページ">{nav}</nav>
{repro if selected is None else ''}
<footer>出典: World Bank Open Data (CC BY 4.0) / 総務省統計局 e-Stat（政府標準利用規約）。
このページは <code>src/make_index.py</code> が results/ の中身から生成している。</footer>
</main><script>{SHARE_JS}</script>{f'<script>{PREVIEW_JS}</script>' if selected else ''}</body></html>"""


if __name__ == "__main__":
    for selected in [None, *(s["id"] for s in SECTIONS)]:
        filename = f"{selected}.html" if selected else "index.html"
        out = paths.ROOT / filename
        page = build(selected)
        title = ('豊かな県ほど長寿？ 男女を分けて調べてみた' if selected == 'pref-health'
                 else next(s["title"] for s in SECTIONS if s["id"] == selected) if selected
                 else '国と地域の「なぜ？」を公的データで探る')
        description = RESULT_OVERVIEWS[selected] if selected else '豊かさ・健康・人の移動は、どう関係する？ 公的データを使った4つの探索的分析を図で紹介します。'
        page = page.replace('</head>', social_meta(selected or 'index', title, description) + '\n</head>')
        out.write_text(page, encoding="utf-8")
        print(f"-> {filename} ({len(page.encode('utf-8'))/1024:.1f} KB)")
    from reading_guide import content
    # 共通の書式・GitHubリンク・フッターを保ち、解説本文を差し込む。
    top = build("country")
    head = top.split('<h1>', 1)[0].replace(
        f'<title>{esc(SECTIONS[0]["title"])}｜公的データによるSEM</title>',
        '<title>図の読み方と分析手法｜公的データによるSEM</title>')
    guide = head + '</header>' + content() + '<footer>' + top.split('<footer>', 1)[1]
    guide = guide.replace('</head>', social_meta('guide', '図の読み方と分析手法', 'SEM・パス図・係数・不確実性の読み方を解説します。') + '\n</head>')
    (paths.ROOT / 'guide.html').write_text(guide, encoding='utf-8')
    print('-> guide.html')
