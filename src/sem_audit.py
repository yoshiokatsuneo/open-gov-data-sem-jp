"""推定の健全性と健康モデルの男女差の対比較。既存結果を残して監査する。"""
import numpy as np
import pandas as pd
import paths

TOL = 1e-8


def diagnose(m):
    result = m.last_result
    e = m.inspect(std_est=True)
    numeric = e[['Estimate', 'Est. Std']].to_numpy(dtype=float)
    variances = e[(e.op == '~~') & (e.lval == e.rval)]
    finite = bool(np.isfinite(numeric).all() and np.isfinite(result.fun))
    negative = bool((variances.Estimate < -TOL).any())
    boundary = variances.loc[variances.Estimate.abs() <= TOL, 'lval'].tolist()
    sigma, _ = m.calc_sigma()
    eigmin = float(np.linalg.eigvalsh(sigma).min()) if np.isfinite(sigma).all() else np.nan
    usable = bool(result.success and finite and not negative and eigmin > 0)
    return e, dict(converged=bool(result.success), finite=finite,
                   negative_variance=negative, boundary=';'.join(boundary),
                   min_sigma_eigenvalue=eigmin, usable=usable,
                   optimizer_message=str(result.message))


def contrast(e, outcome_sd):
    def coef(y,x,col):
        return float(e[(e.lval==y)&(e.rval==x)&(e.op=='~')][col].iloc[0])
    values = {}
    for x in ['WEALTH','MED']:
        # 共通の潜在変数の1単位当たり、男女とも年に戻して比較する。
        values[x+'_years'] = (coef('le_m',x,'Estimate')*outcome_sd['le_m']
                             - coef('le_f',x,'Estimate')*outcome_sd['le_f'])
        values[x+'_std'] = coef('le_m',x,'Est. Std')-coef('le_f',x,'Est. Std')
    return values


def main(n_override=None):
    import estat_sem as health
    import job_sem as job
    import sem_country_v2 as country
    import muni_path as muni
    hw = health.wide()
    hz = (hw[health.USED]-hw[health.USED].mean())/hw[health.USED].std()
    jw=job.wide(); jz=(jw[job.USED]-jw[job.USED].mean())/jw[job.USED].std()
    mw=muni.wide(); mz=(mw[muni.V]-mw[muni.V].mean())/mw[muni.V].std()
    configurations=[('country', country.prepare(), country.fit,600),
                    ('pref-health',hz,health.fit,600),('pref-job',jz,job.fit,600),
                    ('muni',mz,muni.fit,400)]
    records=[]; summaries=[]; contrast_draws=[]; original_contrast=None
    for name,z,fit,n in configurations:
        n=n_override or n
        rng=np.random.default_rng(0)
        for iteration in range(-1,n):
            sample=z if iteration==-1 else z.iloc[rng.integers(0,len(z),len(z))]
            row=dict(model=name,iteration=iteration,converged=False,finite=False,
                     negative_variance=False,boundary='',min_sigma_eigenvalue=np.nan,
                     usable=False,optimizer_message='')
            try:
                e,flags=diagnose(fit(sample)); row.update(flags)
                if name=='pref-health' and row['usable']:
                    values=contrast(e,hw[['le_m','le_f']].std())
                    if iteration==-1: original_contrast=values
                    else: contrast_draws.append(dict(iteration=iteration,boundary=row['boundary'],**values))
            except Exception as exc:
                row['optimizer_message']=type(exc).__name__+': '+str(exc)
            records.append(row)
        subset=pd.DataFrame([r for r in records if r['model']==name and r['iteration']>=0])
        base=[r for r in records if r['model']==name and r['iteration']==-1][0]
        summaries.append(dict(model=name,n=len(z),attempts=n,usable=int(subset.usable.sum()),
                              failed=int((~subset.usable).sum()),
                              nonconverged=int((~subset.converged).sum()),
                              boundary=int(subset.boundary.ne('').sum()),
                              usable_boundary=int((subset.usable & subset.boundary.ne('')).sum()),
                              original_usable=base['usable'],original_boundary=base['boundary']))
        print(summaries[-1],flush=True)
    pd.DataFrame(records).to_csv(paths.result('sem_audit_trials.csv'),index=False)
    pd.DataFrame(summaries).to_csv(paths.result('sem_audit_summary.csv'),index=False)
    d=pd.DataFrame(contrast_draws)
    if original_contrast is None or len(d)<100:
        raise RuntimeError('Insufficient valid health estimates for contrast intervals')
    d.to_csv(paths.result('pref_gender_contrast_draws.csv'),index=False)
    rows=[]
    for key,point in original_contrast.items():
        for scope,subset in [('usable_including_boundary',d),('interior_only',d[d.boundary==''])]:
            low,high=np.quantile(subset[key],[.025,.975]) if len(subset)>=100 else (np.nan,np.nan)
            # 主比較は同じ単位（年）の2本。Bonferroni対応の各97.5%区間。
            family_low,family_high=np.quantile(subset[key],[.0125,.9875]) if len(subset)>=100 else (np.nan,np.nan)
            rows.append(dict(parameter=key,scope=scope,estimate=point,valid=len(subset),
                             low=low,high=high,family_low=family_low,family_high=family_high,
                             zero_included=bool(low<=0<=high) if np.isfinite(low) else None))
    pd.DataFrame(rows).to_csv(paths.result('pref_gender_contrasts.csv'),index=False)
    loo=[]
    for index in hz.index:
        e,flags=diagnose(health.fit(hz.drop(index)))
        loo.append(dict(excluded=hw.loc[index,'pref'],usable=flags['usable'],
                        boundary=flags['boundary'],**contrast(e,hw[['le_m','le_f']].std())))
    pd.DataFrame(loo).to_csv(paths.result('pref_gender_contrast_loo.csv'),index=False)
    print(pd.DataFrame(rows).to_string(index=False))

if __name__=='__main__':
    main()
