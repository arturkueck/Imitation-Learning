"""CPU-only postprocessing with unique action vectors and explicit outcome ties."""
from pathlib import Path
import argparse
import json
import numpy as np


def classify(pred,true,tol=1e-6):
    if abs(true)<=tol:return 'outcome_tie'
    if abs(pred)<=tol:return 'prediction_tie'
    return 'correct' if pred*true>0 else 'wrong'


def unique_actions(variants):
    groups=[]
    for name,row in variants.items():
        same=next((g for g in groups if np.max(np.abs(np.asarray(g['row']['action'])-np.asarray(row['action'])))<=1e-6),None)
        if same is None:groups.append(dict(names=[name],row=row,near=row['category']=='near_policy'))
        else:
            same['names'].append(name);same['near']=same['near'] or row['category']=='near_policy'
    return groups


def actor_feasible(record,action):
    center=np.asarray(record['variants']['policy' if record['context']=='parent' else 'other_actor']['action'])
    limit=np.r_[np.minimum(.2,.5*np.abs(center[:3])),.02]
    return bool((np.abs(np.asarray(action)-center)<=limit+1e-6).all())


def calculate(rows,feasible_only=False):
    result={}
    for context in ('parent','final'):
        for critic in ('warm','final'):
            for output in ('q1','minimum'):
                all_pairs={k:0 for k in ('correct','wrong','prediction_tie','outcome_tie')}
                local={k:0 for k in all_pairs};q_up={k:0 for k in ('better','worse','unchanged','not_predicted_better','identical_action','outside_actor_constraint')}
                states=informative_states=local_informative_states=0;regret=[];examples=[];success_losses=success_wins=0
                for record in rows:
                    if record['context']!=context:continue
                    states+=1;groups=unique_actions(record['variants']);informative=False;local_informative=False
                    if feasible_only:groups=[g for g in groups if actor_feasible(record,g['row']['action'])]
                    assert groups
                    for i,a in enumerate(groups):
                        for b in groups[i+1:]:
                            ar,br=a['row'],b['row']
                            pred=ar['predictions'][critic][output]-br['predictions'][critic][output]
                            actual=ar['measured_return']-br['measured_return'];label=classify(pred,actual)
                            all_pairs[label]+=1
                            informative=informative or label!='outcome_tie'
                            if a['near'] and b['near']:
                                local[label]+=1;local_informative=local_informative or label!='outcome_tie'
                    informative_states+=informative;local_informative_states+=local_informative
                    chosen=max(groups,key=lambda g:g['row']['predictions'][critic][output])['row']
                    regret.append(max(g['row']['measured_return'] for g in groups)-chosen['measured_return'])
                    original=record['variants']['policy'];up=record['variants']['q_up']
                    dq=up['predictions'][critic][output]-original['predictions'][critic][output]
                    dr=up['measured_return']-original['measured_return']
                    if feasible_only and not actor_feasible(record,up['action']):label='outside_actor_constraint'
                    elif np.max(np.abs(np.asarray(up['action'])-np.asarray(original['action'])))<=1e-6:label='identical_action'
                    elif dq<=1e-6:label='not_predicted_better'
                    else:label='better' if dr>1e-6 else 'worse' if dr < -1e-6 else 'unchanged'
                    q_up[label]+=1
                    if dq>1e-6 and label!='outside_actor_constraint':
                        success_losses+=bool(original['outcome']['success'] and not up['outcome']['success'])
                        success_wins+=bool(not original['outcome']['success'] and up['outcome']['success'])
                    if label=='worse':examples.append(dict(model_seed=record['model_seed'],scene=record['scene_seed'],
                        probe=record['probe']['key'],predicted_gain=dq,actual_return_change=dr,
                        baseline_success=original['outcome']['success'],modified_success=up['outcome']['success']))
                result[f'{context}:{critic}:{output}']=dict(states=states,informative_states=informative_states,
                    near_policy_informative_states=local_informative_states,unique_pair_orderings=all_pairs,
                    near_policy_pair_orderings=local,q_up_outcomes=q_up,
                    q_up_generated_by='warm' if context=='parent' else 'final',
                    q_up_success_losses=success_losses,q_up_success_wins=success_wins,
                    mean_regret=float(np.mean(regret)) if regret else None,worse_q_up_examples=examples)
    return result


def main(folder,feasible_only=False):
    assert json.loads((folder/'status.json').read_text())['state']=='COMPLETED'
    rows=json.loads((folder/'counterfactuals.json').read_text());summary=calculate(rows,feasible_only)
    target=folder/('summary_actor_feasible.json' if feasible_only else 'summary_unique_actions.json');assert not target.exists()
    target.write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k in ('parent:warm:q1','final:final:q1')}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('--feasible-only',action='store_true')
    a=p.parse_args();main(a.folder.resolve(),a.feasible_only)
