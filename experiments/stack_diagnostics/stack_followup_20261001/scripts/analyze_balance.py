"""Additional matched summaries and scientific figures from saved predictions/rollouts."""
import json,os
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR',str(Path(__file__).resolve().parents[4]/'experiments/stack_diagnostics/stack_balance_20261001/mpl_cache'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from balance_common import EXP,ROOT
from transport_data import summary
variants=['source','uniform','balanced'];extra={};profiles={}
for v in variants:
    z=np.load(EXP/v/'offline_predictions.npz');p=z['predictions'];e=z['expected'];ph=z['phase'];sp=z['split'];off=z['offsets'][:,None]+np.arange(2)
    extra[v]={};profiles[v]={}
    for split in ('train','valid'):
        extra[v][split]={};profiles[v][split]={}
        for region,mask in [('transport',ph==4),('early_transport',(ph==4)&(off>=0)&(off<=8)),('pre_transition',(off>=-6)&(off<0)),('late_transport',(ph==4)&(off>8))]:
            mask=mask&(sp[:,None]==split);a=p[:,mask,:].reshape(-1,7);ex=np.tile(e[mask],(3,1));m=np.linalg.norm(a[:,:2],axis=1);em=np.linalg.norm(ex[:,:2],axis=1);valid=em>.1;cos=(a[:,:2]*ex[:,:2]).sum(1)/np.maximum(m*em,1e-9)
            extra[v][split][region]=dict(n=int(mask.sum()),policy_xy=summary(m),expert_xy=summary(em),ratio=summary(m[valid]/em[valid]),cosine=summary(cos[valid]),opening=float(np.mean(a[:,-1]<0)),z_mean=float(a[:,2].mean()),expert_z_mean=float(ex[:,2].mean()))
        for chunk in (0,1):
            mask=(sp==split)&(ph[:,chunk]==4);aa=p[:,mask,chunk,:].reshape(-1,7);ex=np.tile(e[mask,chunk,:],(3,1));m=np.linalg.norm(aa[:,:2],axis=1);em=np.linalg.norm(ex[:,:2],axis=1);active=em>.1
            extra[v][split][f'chunk{chunk}']=dict(ratio=summary(m[active]/em[active]),xy=summary(m))
        trials=json.loads((EXP/v/'boundary_trials.json').read_text());trials=[t for t in trials if t['split']==split];on=[t['onset_offset'] for t in trials]
        extra[v][split]['onset']=dict(within_2_steps_fraction=sum(o is not None and abs(o)<=2 for o in on)/len(on),premature_fraction=sum(o is not None and o<-2 for o in on)/len(on),late_fraction=sum(o is not None and o>2 for o in on)/len(on),abs_error_steps=summary([abs(o) for o in on if o is not None]),left_censored_fraction=sum(o==-10 for o in on)/len(on))
        for i in range(-10,32):
            mask=(sp[:,None]==split)&(off==i)
            if not mask.any():continue
            aa=p[:,mask,:].reshape(-1,7);ex=e[mask];profiles[v][split][i]=dict(xy=float(np.linalg.norm(aa[:,:2],axis=1).mean()),expert=float(np.linalg.norm(ex[:,:2],axis=1).mean()),z=float(aa[:,2].mean()),expert_z=float(ex[:,2].mean()),opening=float(np.mean(aa[:,-1]<0)))
(EXP/'offline_extra.json').write_text(json.dumps(extra,indent=2))
paired=[]
u=np.load(EXP/'uniform/offline_predictions.npz');b=np.load(EXP/'balanced/offline_predictions.npz');meta=json.loads((EXP/'uniform/offline_samples.json').read_text());assert meta==json.loads((EXP/'balanced/offline_samples.json').read_text())
for name in sorted(set(t['demo'] for t in meta)):
    ids=np.array([i for i,t in enumerate(meta) if t['demo']==name]);off=u['offsets'][ids,None]+np.arange(2);mask=(u['phase'][ids]==4)&(off>=0)&(off<=8);ex=u['expected'][ids][mask];em=np.linalg.norm(ex[:,:2],axis=1);active=em>.1
    row=dict(demo=name,split=meta[int(ids[0])]['split'])
    for v,z in [('uniform',u),('balanced',b)]:
        aa=z['predictions'][:,ids][:,mask,:].reshape(3,-1,7);m=np.linalg.norm(aa[:,:,:2],axis=2);row[v]=dict(early_xy_mean=float(m.mean()),early_ratio_median=float(np.median(m[:,active]/em[active])))
    row['early_xy_difference']=row['balanced']['early_xy_mean']-row['uniform']['early_xy_mean'];paired.append(row)
paired_summary={s:dict(n=len([r for r in paired if r['split']==s]),improved_demos=sum(r['early_xy_difference']>0 for r in paired if r['split']==s),early_xy_difference=summary([r['early_xy_difference'] for r in paired if r['split']==s])) for s in ('train','valid')}
(EXP/'paired_offline.json').write_text(json.dumps(dict(summary=paired_summary,demos=paired),indent=2))
colors={'source':'#777777','uniform':'#3977b7','balanced':'#d65b26'}
fig,axes=plt.subplots(2,3,figsize=(13,7),sharex=True)
for row,split in enumerate(('train','valid')):
    for v in variants:
        prof=profiles[v][split];x=sorted(prof);time=np.array(x)*.05
        for col,key in enumerate(('xy','z','opening')):axes[row,col].plot(time,[prof[i][key] for i in x],label=v,color=colors[v])
    for col,key in enumerate(('expert','expert_z')):axes[row,col].plot(time,[prof[i][key] for i in x],label='Expert',color='black',ls='--')
    for col in range(3):axes[row,col].axvline(0,color='black',alpha=.4);axes[row,col].grid(alpha=.2);axes[row,col].set_xlabel('Sekunden relativ zum Expert-Transportbeginn')
    axes[row,0].set_ylabel(split);axes[row,0].legend()
axes[0,0].set_title('XY-Aktionsstärke');axes[0,1].set_title('Z-Aktion');axes[0,2].set_title('Anteil Öffnungsbefehle')
fig.tight_layout();fig.savefig(EXP/'boundary_profiles.png',dpi=160);plt.close(fig)
if not all((EXP/v/'rollouts/results.json').exists() for v in variants[1:]):raise SystemExit('Offline analysis saved; rollouts pending')
results={'source':json.loads((EXP/'source/rollout_results.json').read_text())}
for v in variants[1:]:results[v]=json.loads((EXP/v/'rollouts/results.json').read_text())
if any(len(r)!=20 for r in results.values()):raise SystemExit('Rollouts incomplete')
roll={}
for v,rs in results.items():
    roll[v]=dict(counts={k:sum(bool(r[k]) for r in rs) for k in ('grasp','lift','transport_started','near','position','lower','release','stack')},full_lift_count=sum(r['full_lift_end'] is not None for r in rs),transport_command_count=sum(r['transport_command_start'] is not None for r in rs),sustained_stack=sum(bool(r.get('sustained_success',False)) for r in rs),reversals=summary([r['xy_action_reversals'] for r in rs if r['lift']]),reversal_fraction=sum(r['xy_action_reversals'] for r in rs)/max(1,sum(r['replan_pairs'] for r in rs)),distance={s:summary([r['relative_xy_distance_after_lift_end_m'][s] for r in rs if r['relative_xy_distance_after_lift_end_m'][s] is not None]) for s in ('0.5','1.0','2.0')},transport_delay_seconds=summary([r['transport_delay_steps']*.05 for r in rs if r['transport_delay_steps'] is not None]))
common=[i for i in range(20) if all(results[v][i]['full_lift_end'] is not None for v in ('uniform','balanced'))]
roll['matched_full_lift_seeds']=[46000+i for i in common];roll['matched_distance']={v:{s:summary([results[v][i]['relative_xy_distance_after_lift_end_m'][s] for i in common if results[v][i]['relative_xy_distance_after_lift_end_m'][s] is not None]) for s in ('0.5','1.0','2.0')} for v in ('uniform','balanced')}
roll['paired_stack_discordance']=dict(balanced_only=[46000+i for i in range(20) if results['balanced'][i]['stack'] and not results['uniform'][i]['stack']],uniform_only=[46000+i for i in range(20) if results['uniform'][i]['stack'] and not results['balanced'][i]['stack']])
(EXP/'rollout_summary.json').write_text(json.dumps(roll,indent=2))
fig,ax=plt.subplots(figsize=(10,4));stages=['grasp','lift','transport_started','near','position','lower','release','stack'];x=np.arange(len(stages))
for i,v in enumerate(variants):ax.bar(x+(i-1)*.25,[roll[v]['counts'][s]*5 for s in stages],width=.24,label=v,color=colors[v])
ax.set_xticks(x,['Greifen','Lift','Transport','<3 cm','Position','Absenken','Release','Stack']);ax.set_ylabel('Erfolg [%], 20 feste Starts');ax.set_ylim(0,100);ax.legend();ax.grid(axis='y',alpha=.2);fig.tight_layout();fig.savefig(EXP/'rollout_stages.png',dpi=160);plt.close(fig)
chosen=[46002,46004,46019];success=[r['seed'] for r in results['balanced'] if r['stack']]
if success and success[0] not in chosen:chosen.append(success[0])
fig,axes=plt.subplots(len(chosen),3,figsize=(13,3*len(chosen)))
for row,seed in enumerate(chosen):
    for v in variants:
        path=ROOT/'experiments/stack_diagnostics/stack_placement_20261001/baseline'/f'{seed}.npz' if v=='source' else EXP/v/'rollouts'/f'{seed}.npz';t=np.load(path)['trace'];r=results[v][seed-46000];start=r['full_lift_end'] if r['full_lift_end'] is not None else r['first_steps']['lift'];start=start if start is not None else 0;stop=min(len(t),start+80);a=t[max(0,start-10):stop];time=(a[:,0]-start)*.05
        rel=(a[:,4:6]-a[:,1:3])*100;axes[row,0].plot(rel[:,0],rel[:,1],label=v,color=colors[v]);axes[row,1].plot(time,np.linalg.norm(rel,axis=1),color=colors[v]);axes[row,2].plot(time,a[:,6],color=colors[v])
    axes[row,0].scatter([0],[0],color='black',marker='x');axes[row,0].set_title(f'Seed {seed}: gehalten B relativ zu A');axes[row,0].set_xlabel('X [cm]');axes[row,0].set_ylabel('Y [cm]');axes[row,0].legend();axes[row,1].set_title('XY-Abstand [cm]');axes[row,2].set_title('B-Höhe [m]')
    for col in range(3):axes[row,col].grid(alpha=.2)
    for col in (1,2):axes[row,col].set_xlabel('Zeit ab vollem Lift; sonst erstem Lift/Start [s]')
fig.tight_layout();fig.savefig(EXP/'representative_rollouts.png',dpi=150);plt.close(fig)
print(json.dumps(roll,indent=2))
paths=[EXP/v/'expert_lift_rollouts/results.json' for v in variants]
if all(path.exists() and len(json.loads(path.read_text()))==20 for path in paths):
    er={v:json.loads(path.read_text()) for v,path in zip(variants,paths)};assert len(set(tuple(r['demo'] for r in er[v]) for v in variants))==1
    for i in range(20):
        assert all(er[v][i]['initial_grasp'] for v in variants)
        assert len(set(er[v][i]['initial_state_sha256'] for v in variants))==1
    es={}
    for v in variants:
        rs=er[v];flips=[];pairs=[];sustained=[]
        for r in rs:
            z=np.load(EXP/v/'expert_lift_rollouts'/(r['demo']+'.npz'));t=z['trace'];main=t[:r['measured_steps']];dist=np.linalg.norm(main[:,4:6]-main[:,1:3],axis=1);m=np.linalg.norm(main[:,20:22],axis=1);ids=np.flatnonzero((main[:,34]>0)&(dist>.02)&(m>.01)&(main[:,0].astype(int)%2==0));pair=np.diff(ids)==2
            flips.append(int((((main[ids[1:],20:22]*main[ids[:-1],20:22]).sum(1)<0)&pair).sum()));pairs.append(int(pair.sum()));sustained.append(bool(r['stack'] and np.all(t[r['measured_steps']:,36]>0)))
        es[v]=dict(counts={k:sum(r[k] for r in rs) for k in ('transport_started','near','position','lower','release','stack')},sustained_stack=sum(sustained),distance={s:summary([r['distance_from_expert_lift_start_m'][s] for r in rs]) for s in ('0.5','1.0','2.0')},reversals=summary(flips),reversal_fraction=sum(flips)/max(1,sum(pairs)),restored_position_error_m=summary([r['restored_position_error_m'] for r in rs]))
    es['matched_initial_states']=True;es['all_initial_grasps']=True;(EXP/'expert_lift_summary.json').write_text(json.dumps(es,indent=2))
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    for v in variants:
        axes[0].plot([.5,1,2],[es[v]['distance'][s]['mean']*100 for s in ('0.5','1.0','2.0')],marker='o',label=v,color=colors[v]);axes[1].plot(np.arange(6),[es[v]['counts'][s]*5 for s in ('transport_started','near','position','lower','release','stack')],marker='o',label=v,color=colors[v])
    axes[0].set_xlabel('Sekunden ab vorgegebenem Expert-Lift-Ende');axes[0].set_ylabel('Mittlerer XY-Abstand [cm], n=20');axes[1].set_xticks(np.arange(6),['Transport','<3 cm','Position','Absenken','Release','Stack'],rotation=15);axes[1].set_ylabel('Erfolg [%], n=20');axes[1].set_ylim(0,100)
    for ax in axes:ax.legend();ax.grid(alpha=.2)
    fig.tight_layout();fig.savefig(EXP/'expert_lift_comparison.png',dpi=160);plt.close(fig)
