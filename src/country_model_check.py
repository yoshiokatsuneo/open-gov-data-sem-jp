"""Country diagnostics for the saved Model B; no refit and no growth inputs.
Reconstruct model-implied covariance from unstandardized saved estimates.
Predict log growth conditional on eight 2012 baseline indicators, as in
https://semopy.com/predict.html . Back-transform conditional log means;
these are median predictions under a Gaussian log-growth model, not mean %.
These are in-sample diagnostics except CHN; not cross-validation or causality.
"""
from pathlib import Path

import paths
import numpy as np
import pandas as pd
ROOT = paths.ROOT
sample=pd.read_csv(paths.result("sem_sample.csv"),index_col='iso3')
raw=pd.read_csv(paths.raw("wb_raw.csv"),index_col='iso3')
e=pd.read_csv(paths.result("sem_estimates.csv"))
lat=['GOV','HC','GROWTH','init_gdp']
x=['rule_of_law','gov_effect','control_corrupt','reg_quality','life_exp_12','child_surv_12','school_sec_12','init_gdp']
y=['g_gdp','g_gni','g_cons']; obs=x+y
B=np.zeros((4,4)); P=np.zeros((4,4)); L=np.zeros((11,4)); T=np.zeros((11,11))
L[obs.index('init_gdp'),lat.index('init_gdp')]=1
P[3,3]=(len(sample)-1)/len(sample) # standardization ddof=1; ML covariance ddof=0
for r in e.itertuples():
 if r.op=='~':
  if r.lval in lat:B[lat.index(r.lval),lat.index(r.rval)]=r.Estimate
  else:L[obs.index(r.lval),lat.index(r.rval)]=r.Estimate
 elif r.op=='~~':
  if r.lval in lat and r.rval in lat:
   a,b=lat.index(r.lval),lat.index(r.rval);P[a,b]=P[b,a]=r.Estimate
  else:
   a,b=obs.index(r.lval),obs.index(r.rval);T[a,b]=T[b,a]=r.Estimate
C=np.linalg.inv(np.eye(4)-B)
S=L@C@P@C.T@L.T+T
assert np.linalg.eigvalsh(S).min()>0
# Check saved standardized loadings against reconstructed total variances.
LV=C@P@C.T
for r in e[e.op=='~'].itertuples():
 dv=LV[lat.index(r.lval),lat.index(r.lval)] if r.lval in lat else S[obs.index(r.lval),obs.index(r.lval)]
 val=r.Estimate*np.sqrt(LV[lat.index(r.rval),lat.index(r.rval)]/dv)
 assert abs(val-r.std)<1e-7,(r.lval,r.rval,val,r.std)
raw['init_gdp']=np.log(raw.gdp_pc_12)
raw['child_surv_12']=-np.log(raw.under5_mort_12)
for v,base in zip(y,['gdp','gni','cons']):raw[v]=np.log(raw[f'{base}_pc_22']/raw[f'{base}_pc_12'])
mu=sample[obs].mean();sd=sample[obs].std(ddof=1)
coef=np.linalg.solve(S[:8,:8],S[:8,8:])
cond=S[8:,8:]-S[8:,:8]@coef
assert np.linalg.eigvalsh(cond).min()>0
rows=raw.dropna(subset=x).copy()
z=(rows[x]-mu[x])/sd[x]
pred=z.to_numpy()@coef
out=rows[['country','region']].copy();out['in_estimation_sample']=out.index.isin(sample.index)
for j,v in enumerate(y):
 plog=pred[:,j]*sd[v]+mu[v]
 out[v+'_actual_pct']=100*np.expm1(rows[v])
 out[v+'_predicted_pct']=100*np.expm1(plog)
 out[v+'_gap_pp']=out[v+'_actual_pct']-out[v+'_predicted_pct']
 out[v+'_residual_sd']=(rows[v]-plog)/(sd[v]*np.sqrt(cond[j,j]))
out.to_csv(paths.result("country_model_check.csv"))
print('N=',len(sample),'Covariance min eigenvalue=',np.linalg.eigvalsh(S).min())
print('All saved standardized regression coefficients reproduced within 1e-7')
print(out.loc[['RUS','USA','JPN','CHN','DEU','FRA','GBR','ITA','ESP','POL','SWE'],['in_estimation_sample','g_gdp_actual_pct','g_gdp_predicted_pct','g_gdp_gap_pp','g_gdp_residual_sd']].round(3).to_string())
print('Sample GDP residual SD (log)',(sample.g_gdp-((sample[x]-mu[x])/sd[x]).to_numpy()@coef[:,0]*sd.g_gdp-mu.g_gdp).std())
print('Europe & Central Asia sample countries:',', '.join(sample[sample.region=='Europe & Central Asia'].index))
