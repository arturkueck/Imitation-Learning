"""Disjoint temperature, policy selection and family audit; test stays blind."""
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scipy.special import logsumexp
from q_protocol import verify,save,read,sha
from q_data import load
from q_policy import ensemble,probabilities,choose,evaluate_selection
from q_train import weights

def wilson(k,n):
    if not n:return [0.,1.]
    z=1.96;p=k/n;den=1+z*z/n;center=(p+z*z/(2*n))/den;half=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [max(0.,center-half),min(1.,center+half)]

def calibrate(run):
    run=Path(run);cfg=verify(run)
    if (run/'policy_freeze.json').exists():raise RuntimeError('Policy already frozen; no threshold refitting')
    data=load(run,'calibration/temperature');logits,gains=ensemble(run,data);m=data['eligible']&data['labelled']
    if m.sum()<60:raise RuntimeError('Insufficient eligible calibration labels')
    x=logits[m];y=data['classes'][m];w=weights(data['family'][m]);w/=w.sum()
    def objective(a):
        z=x/np.exp(a[0])+np.array([a[1],a[2],-a[1]-a[2]])
        return float(np.sum(w*(logsumexp(z,axis=1)-z[np.arange(len(y)),y]))+.001*np.square(a).sum())
    fit=minimize(objective,np.zeros(3),method='L-BFGS-B',bounds=[(-2,2),(-4,4),(-4,4)],options=dict(maxiter=200))
    if not fit.success:raise RuntimeError('Temperature/bias calibration failed')
    a=fit.x;cal=dict(temperature=float(np.exp(a[0])),bias=[float(a[1]),float(a[2]),float(-a[1]-a[2])],source='calibration/temperature_only',head_freeze_sha256=sha(run/'head_freeze.json'))
    save(run/'calibrator.json',cal)
    data=load(run,'calibration/policy');logits,gains=ensemble(run,data);p=probabilities(logits,cal);options=[]
    for threshold in cfg['calibration']['risk_grid']:
        selected=choose(data,p,gains,threshold);metrics=evaluate_selection(run,'calibration/policy',data,selected)
        eligible=metrics['harm_count']/metrics['families']<=.05 and metrics['coverage']>=.2 and metrics['mean_selected']<metrics['mean_initial'] and metrics['updated_families']>=30
        options.append(dict(threshold=threshold,eligible=eligible,metrics=metrics))
    save(run/'threshold_search.json',options);valid=[o for o in options if o['eligible']]
    if not valid:
        save(run/'calibration_failure.json',dict(reason='No empirical risk/coverage/benefit tradeoff passed; do not relax thresholds automatically'));return False
    winner=max(valid,key=lambda o:(o['metrics']['mean_initial']-o['metrics']['mean_selected'],-o['metrics']['harm_count'],-o['threshold']))
    save(run/'policy_freeze.json',dict(threshold=winner['threshold'],minimum_gain=1.,minimum_helpful_probability=.5,
        head_freeze_sha256=sha(run/'head_freeze.json'),calibrator_sha256=sha(run/'calibrator.json'),source='calibration/policy_only'))
    audit=load(run,'calibration/audit');logits,gains=ensemble(run,audit);selected=choose(audit,probabilities(logits,cal),gains,winner['threshold'])
    metrics=evaluate_selection(run,'calibration/audit',audit,selected)
    passed=metrics['harm_count']/metrics['families']<=.05 and metrics['coverage']>=.2 and metrics['updated_families']>=30 and metrics['mean_selected']<metrics['mean_initial']
    save(run/'audit.json',dict(passed=passed,metrics=metrics,family_harm_wilson95=wilson(metrics['harm_count'],metrics['families']),
        threshold_adjusted_after_audit=False,meaning='empirical simulation gate, not real-world safety guarantee'))
    return passed
