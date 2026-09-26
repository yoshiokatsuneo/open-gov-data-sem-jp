"""各分析の標本内当てはめと残差。SEMと補助回帰を明確に区別する。"""
import numpy as np
import pandas as pd
import paths
from make_path_diagram import text, esc, SURFACE, INK, INK3, C_POS, BOX_LINE


def auxiliary(names, y, predictors):
    """固定した合成指標を使うOLS。区間は合成指標を固定した条件付き区間。"""
    x = np.column_stack([np.ones(len(y)), predictors])
    y = np.asarray(y, dtype=float)
    fitted = x @ np.linalg.lstsq(x, y, rcond=None)[0]
    rng = np.random.default_rng(2026)
    draws = []
    for _ in range(600):
        ix = rng.integers(0, len(y), len(y))
        draws.append(x @ np.linalg.lstsq(x[ix], y[ix], rcond=None)[0])
    lo, hi = np.quantile(draws, [.025, .975], axis=0)
    return pd.DataFrame(dict(region=list(names), observed=y, predicted=fitted,
                             residual=y-fitted, mean_ci_low=lo, mean_ci_high=hi))


def compute():
    from sem_country_v2 import prepare, HCR
    from sem_analysis import derive
    from pref_residuals import compute as pref_compute
    from job_residuals import compute as job_compute
    from muni_path import wide, V, fit
    z = prepare()
    gov = z[['rule_of_law', 'gov_effect', 'control_corrupt', 'reg_quality']].mean(axis=1)
    country = auxiliary(z.country, derive().loc[z.index, 'g_gdp'] * 100,
                        np.column_stack([gov, z[HCR].mean(axis=1), z.init_gdp]))
    p = pref_compute()
    j, _ = job_compute()
    datasets = [
        ('country', '国：一人当たりGDPの成長', '対数差×100', country,
         '補助回帰：制度・所得調整後人的資本の標準化平均と初期所得。SEMの潜在成長因子の予測ではない。'),
        ('health_m', '都道府県：平均寿命（男）', '年', auxiliary(p.pref, p.le_m, p[['wealth']]),
         '補助回帰：豊かさの3指標の標準化平均のみ。医療供給量を含むSEM全体の予測ではない。'),
        ('health_f', '都道府県：平均寿命（女）', '年', auxiliary(p.pref, p.le_f, p[['wealth']]),
         '補助回帰：豊かさの3指標の標準化平均のみ。医療供給量を含むSEM全体の予測ではない。'),
        ('job', '都道府県：転職率', '%（残差はポイント）', auxiliary(j.pref, j.jobchg, j[['urban','precar']]),
         '補助回帰：都市度・雇用の不安定さの指標の標準化平均。SEMの因子得点は使わない。'),
    ]
    w = wide()
    zz = (w[V] - w[V].mean()) / w[V].std()
    estimates = fit(zz).inspect()
    pred = np.zeros(len(w))
    for _, row in estimates[(estimates.op == '~') & (estimates.lval == 'move_rate')].iterrows():
        pred += row.Estimate * zz[row.rval].to_numpy()
    pred = pred * w.move_rate.std() + w.move_rate.mean()
    names = [f'{name} [{code}]' for code, name in zip(w.index, w['name'])]
    d = pd.DataFrame(dict(region=names, observed=w.move_rate.to_numpy(), predicted=pred,
                         residual=w.move_rate.to_numpy()-pred))
    datasets.append(('muni', '市区町村：総移動率', '%（残差はポイント）', d,
                     'パスモデルの総移動率の式：通勤流出率・単独世帯割合・高齢化率・人口密度の実測値から当てはめ。'))
    return datasets


def build(title, unit, d, method):
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="690" viewBox="0 0 1280 690" role="img">',
           f'<title>{esc(title)}：実測・予測と残差</title>',
           f'<rect width="1280" height="690" fill="{SURFACE}"/>',
           text(40, 38, title + ' — 予測とのずれ', 22, INK, '700'),
           text(40, 66, f'N = {len(d):,} ｜単位：{unit}｜全点を表示・各点は国／地域', 13, INK3),
           text(40, 92, method, 12, INK3)]
    for panel, ycol in enumerate(['observed','residual']):
        left, top, size = 92 + panel * 620, 154, 440
        x = d.predicted.to_numpy(); y = d[ycol].to_numpy()
        if panel == 0:
            low = min(x.min(), y.min()); high = max(x.max(), y.max())
            pad = (high-low)*.08 or 1
            xmin,ymin = low-pad,low-pad; xmax,ymax = high+pad,high+pad
        else:
            pad = np.ptp(x)*.08 or 1
            xmin,xmax = x.min()-pad,x.max()+pad
            edge=max(abs(y.min()),abs(y.max()))*1.08 or 1
            ymin,ymax=-edge,edge
        sx=lambda v:left+(v-xmin)/(xmax-xmin)*size
        sy=lambda v:top+size-(v-ymin)/(ymax-ymin)*size
        out.append(text(left, 128, '実測値と予測値（破線は一致線）' if panel==0 else '残差＝実測値−予測値（破線は0）',15,INK,'600'))
        for v in np.linspace(xmin,xmax,5):
            out.append(f'<path d="M{sx(v):.2f},{top}v{size}" stroke="{BOX_LINE}"/>')
            out.append(text(sx(v), top+size+24, f'{v:.2f}',11,INK3,'400','middle'))
        for v in np.linspace(ymin,ymax,5):
            out.append(f'<path d="M{left},{sy(v):.2f}h{size}" stroke="{BOX_LINE}"/>')
            out.append(text(left-10,sy(v)+4,f'{v:.2f}',11,INK3,'400','end'))
        out.append(f'<path d="M{left},{top}v{size}h{size}" fill="none" stroke="{INK3}"/>')
        line = f'M{sx(xmin)},{sy(xmin)}L{sx(xmax)},{sy(xmax)}' if panel==0 else f'M{left},{sy(0)}h{size}'
        out.append(f'<path d="{line}" stroke="{INK3}" stroke-dasharray="5 4" fill="none"/>')
        for (_, r), xx, yy in zip(d.iterrows(), x, y):
            label=f'{r.region}：実測 {r.observed:.3f} / 予測 {r.predicted:.3f} / 残差 {r.residual:+.3f}'
            out.append(f'<circle cx="{sx(xx):.2f}" cy="{sy(yy):.2f}" r="3" fill="{C_POS}" opacity="0.6"><title>{esc(label)}</title></circle>')
        out.append(text(left+size/2,top+size+48,'予測値',13,INK,'400','middle'))
    out += [text(40,658,'同じデータで推定した標本内の当てはめ。未知の地域・将来に対する予測精度ではない。',12,INK3),
            text(40,679,'補助回帰の平均予測の95%区間はCSVに収録（600回・指標固定）。個々の実測値の予測区間ではない。' if 'mean_ci_low' in d else '地域名と全数値は付属CSVで検索可能。残差の大きさだけで原因や異常を断定しない。',12,INK3), '</svg>']
    return '\n'.join(out)


def main():
    for key,title,unit,d,method in compute():
        assert np.isfinite(d.select_dtypes('number')).all().all()
        assert np.allclose(d.observed-d.predicted,d.residual)
        d.to_csv(paths.result(f'{key}_prediction_diagnostics.csv'),index=False)
        paths.figure(f'{key}_prediction_diagnostics.svg').write_text(build(title,unit,d,method))
        print(key, len(d))

if __name__ == '__main__':
    main()
