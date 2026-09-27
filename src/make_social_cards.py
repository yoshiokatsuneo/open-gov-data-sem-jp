"""既存の健康SEMパス図を主役にしたSNS画像。
Pillow、Node.jsのsharp、日本語フォントが必要。
python src/make_social_cards.py --font FONT --node NODE --sharp SHARP_MODULE
"""
import argparse
import csv
import math
import io
import subprocess
from PIL import Image, ImageDraw, ImageFont
import paths


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--font', required=True)
    p.add_argument('--node', default='node')
    p.add_argument('--sharp', default='sharp')
    args = p.parse_args()
    # 既存SVGをそのまま描画するので、モデルの係数・区間・凡例が追随する。
    js = "const sharp=require(process.argv[1]);sharp(process.argv[2],{density:144}).resize({width:1400}).png().toBuffer().then(b=>process.stdout.write(b));"
    png = subprocess.check_output([args.node, '-e', js, args.sharp,
                                   str(paths.figure('pref_path_diagram.svg'))])
    graph = Image.open(io.BytesIO(png)).convert('RGB')
    for name,title,footer in [
        ('pref-health','豊かな県ほど長寿？ 男女を分けて調べてみた','豊かさと寿命の関連は、今回のモデルでは男性側が大きい。'),
        ('site','国と地域の「なぜ？」を公的データで探る','4つの分析を公開中 ｜ 図は47都道府県の健康分析'),
    ]:
        im=Image.new('RGB',(1600,1200),'#fcfcfb')
        im.paste(graph,((1600-graph.width)//2,85))
        d=ImageDraw.Draw(im)
        def text(y,value,size,color):
            font=ImageFont.truetype(args.font,size)
            width=d.textlength(value,font=font)
            assert width<1520
            d.text(((1600-width)/2,y),value,font=font,fill=color)
        text(20,title,44,'#0b6b68')
        text(1113,footer,30,'#16242b')
        text(1160,'観測データによる探索的分析・因果関係を示すものではありません',23,'#5b6b73')
        im.save(paths.figure(name+'_social.png'))

    # 投稿用の抜粋図。係数と区間は保存された分析結果から取得する。
    with paths.result('pref_estimates.csv').open() as f:
        estimates = {r['lval']: float(r['std']) for r in csv.DictReader(f)
                     if r['op']=='~' and r['rval']=='WEALTH'}
    with paths.result('pref_bootstrap.csv').open() as f:
        intervals = {r['key']: (float(r['2.5%']), float(r['97.5%'])) for r in csv.DictReader(f)}
    im=Image.new('RGB',(1600,1000),'#fcfcfb'); d=ImageDraw.Draw(im)
    def label(x,y,value,size=30,color='#16242b'):
        font=ImageFont.truetype(args.font,size)
        d.text((x,y),value,font=font,fill=color)
    label(70,40,'豊かな県ほど長寿？',64,'#0b6b68')
    label(70,135,'47都道府県のSEM ｜ 豊かさから寿命への経路を抜粋',31)
    d.ellipse((60,350,490,540),fill='#e0efeb',outline='#0b6b68',width=4)
    label(135,415,'経済的豊かさ',39)
    for y,key,sex,color in [(270,'le_m','男','#2378cd'),(590,'le_f','女','#737c80')]:
        a=(490,425 if sex=='男' else 465); b=(1130,y+55)
        if sex=='男': d.line([a,b],fill=color,width=7)
        else:
            for i in range(0,100,5):
                d.line([(a[0]+(b[0]-a[0])*t/100,a[1]+(b[1]-a[1])*t/100) for t in (i,i+2.5)],fill=color,width=5)
        theta=math.atan2(b[1]-a[1],b[0]-a[0])
        d.polygon([b]+[(b[0]-25*math.cos(theta+t),b[1]-25*math.sin(theta+t)) for t in (-.5,.5)],fill=color)
        d.rounded_rectangle((1130,y,1540,y+110),radius=18,fill='#f0f3f4',outline=color,width=3)
        label(1180,y+30,'平均寿命（'+sex+'）',36)
        low,high=intervals[key+'<-WEALTH']
        label(580,y-35,f"係数 {estimates[key]:+.2f}",40,color)
        label(580,y+18,f'95％区間 [{low:+.2f}, {high:+.2f}]',29,color)
    label(70,750,'豊かさと寿命の関連は、今回のモデルでは男性側が大きい。',36,'#0b6b68')
    label(70,817,'標準化係数と600回のブートストラップ区間。破線は区間が0を含む経路。',26)
    label(70,864,'医療供給量を考慮したモデルの抜粋。男女差は別途、係数差を直接検証。',26)
    label(70,911,'出典：e-Stat ｜ 境界解を含む探索的分析。個人の因果関係は示しません。',26)
    im.save(paths.figure('pref-health_post.png'))

if __name__=='__main__':
    main()
