"""具体例の残差図。選定済みの表と同じデータを使う。"""
import numpy as np
from make_path_diagram import text, SURFACE, INK, INK3, C_POS, BOX_LINE
import paths


def build(section_id, groups):
    # 男女のいずれかで選ばれた県は、共通の行で両方を示す。
    names = list(dict.fromkeys(name for _, data, selected in groups for name in selected if name in data.index))
    names.sort(key=lambda n: float(groups[0][1].loc[n, 'residual']), reverse=True)
    health = section_id == 'pref-health'
    extent = max(abs(float(data.loc[n, 'residual'])) for _,data,_ in groups for n in names)
    extent = extent * 1.18 or 1
    h = 190 + len(names)*52
    sx = lambda v: 720 + float(v)/extent*310
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="{h}" viewBox="0 0 1280 {h}" role="img">',
           '<title>具体例：予測とのずれ</title>',f'<rect width="1280" height="{h}" fill="{SURFACE}"/>',
           text(40,38,'具体例：予測とのずれ',23,INK,'700'),
           text(40,65,'残差＝実測値−予測値。標本内の当てはめであり、因果・異常の判定ではありません。',13,INK3),
           text(40,89,('青丸：男 ／ 橙四角：女。単位：年' if health else '単位：対数差×100（年率ではない）' if section_id=='country' else '単位：パーセントポイント') + (' ｜ パスモデルの式による当てはめ' if section_id=='muni' else ' ｜ 補助回帰（SEM自体の予測ではない）'),13,INK3),
           text(490,112,'← 予測より低い',12,INK3),text(830,112,'予測より高い →',12,INK3)]
    for tick in np.linspace(-extent,extent,5):
        x=sx(tick)
        out.append(f'<path d="M{x:.2f},124V{h-61}" stroke="{INK3 if tick==0 else BOX_LINE}" stroke-width="{1.5 if tick==0 else 1}"/>')
        out.append(text(x,h-39,f'{tick:+.2f}' if tick else '0',12,INK3,'400','middle'))
    tr={'United States':'アメリカ','Japan':'日本','China':'中国'}
    for i,n in enumerate(names):
        y=147+i*52
        out.append(text(40,y+5,tr.get(n,n),15,INK))
        values=[float(data.loc[n,'residual']) for _,data,_ in groups]
        if health:
            out.append(f'<path d="M{sx(values[0]):.2f},{y}H{sx(values[1]):.2f}" stroke="#aaa" stroke-width="2"/>')
        else:
            out.append(f'<path d="M{sx(0):.2f},{y}H{sx(values[0]):.2f}" stroke="{C_POS}" stroke-width="3"/>')
        for j,v in enumerate(values):
            if j==0:out.append(f'<circle cx="{sx(v):.2f}" cy="{y}" r="5" fill="{C_POS}"/>')
            else:out.append(f'<rect x="{sx(v)-5:.2f}" y="{y-5}" width="10" height="10" fill="#eb6834"/>')
        out.append(text(1235,y+5,' / '.join(f'{v:+.2f}' for v in values),14,INK,'600','end'))
    note = '中国は必要なGNI成長データが欠損し対象外。予測値なし。' if section_id=='country' else '指定例と残差の極値・最小絶対値の例。' + ('男女の選定例の和集合を表示し、男の残差順。' if health else '残差が大きい順。')
    out += [text(40,h-12,note,12,INK3),'</svg>']
    filename=f'{section_id}_case_residuals.svg'
    paths.figure(filename).write_text('\n'.join(out))
    return filename
