"""Life-expectancy residuals vs log real GDP per capita (PPP), circa 2012.
OLS across all saved countries/economies with both fields, equal country weights.
Not a latent SEM residual; not a causal effect. Nearest-year fallback inherited
from fetch_data.py (2010–2014); actual selected years were not retained.
"""
import json

import paths
import numpy as np
import pandas as pd
ROOT=paths.ROOT
raw=pd.read_csv(paths.raw("wb_raw.csv"),index_col='iso3')
d=raw.dropna(subset=['life_exp_12','gdp_pc_12']).copy()
d=d[d.gdp_pc_12>0]
x=np.log(d.gdp_pc_12).to_numpy();y=d.life_exp_12.to_numpy()
X=np.column_stack([np.ones(len(d)),x])
b=np.linalg.lstsq(X,y,rcond=None)[0]
d['predicted_years']=X@b;d['residual_years']=y-d.predicted_years
assert abs(d.residual_years.sum())<1e-8
assert abs(np.dot(x,d.residual_years))<1e-7
r2=1-np.sum(d.residual_years**2)/np.sum((y-y.mean())**2)
# Sensitivity to non-linearity and restriction to the existing SEM sample.
quad=np.column_stack([np.ones(len(d)),x,x*x]);bq=np.linalg.lstsq(quad,y,rcond=None)[0]
d['residual_quadratic_years']=y-quad@bq
sample=pd.read_csv(paths.result("sem_sample.csv"),index_col='iso3')
mask=d.index.isin(sample.index);bs=np.linalg.lstsq(X[mask],y[mask],rcond=None)[0]
d['residual_sem_sample_reference_years']=y-X@bs
h=np.sum((X@np.linalg.inv(X.T@X))*X,axis=1)
d['leave_one_out_residual_years']=d.residual_years/(1-h)
out=d[['country','region','gdp_pc_12','life_exp_12','predicted_years','residual_years','residual_quadratic_years','residual_sem_sample_reference_years','leave_one_out_residual_years']].sort_values('residual_years',ascending=False)
out.to_csv(paths.result("country_life_residuals.csv"))
meta={'n':len(d),'r2':r2,'intercept':b[0],'log_gdp_slope':b[1],'residual_sd_years':float(d.residual_years.std()),'reference_period':'2012頃（2010–2014年の近隣年補完あり）','outcome':'男女合計の出生時平均余命','wealth':'1人当たり実質GDP（購買力平価）の自然対数'}
(paths.result("country_life_residuals_meta.json")).write_text(json.dumps(meta,ensure_ascii=False,indent=2))
print(json.dumps(meta,ensure_ascii=False))
print(out.loc[['RUS','USA','JPN','CHN','DEU','FRA','GBR','ITA','ESP','POL','SWE']].round(2).to_string())
