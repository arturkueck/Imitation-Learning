"""Post-run descriptive contact audit and mechanism figure; no simulator."""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.ticker import MaxNLocator


def supplement(out):
    def read(name):
        return json.loads((out/name).read_text(encoding='utf-8'))
    if read('status.json')['state']!='COMPLETE' or read('plan.json')['technical_only']:
        raise ValueError('Require completed full diagnosis')
    analysis = read('analysis.json')
    col = {name:i for i,name in enumerate(read('trace_schema.json'))}
    arms = ['control','release_hold','release_feedback','guarded_bc','guarded_hold','guarded_feedback']
    contexts,paths = [],[]
    feedback = None
    for arm in arms:
        path = out/'traces'/f'release_g16_failure_{arm}.npz'
        paths.append(path)
        with np.load(path) as archive:
            trace = archive['trace']
        last = trace[-1]
        velocity = np.asarray([last[col[f'cube_velocity_{j}']] for j in range(18)]).reshape(3,6)
        release = trace[(trace[:,col['placement']]==2)&(trace[:,col['phase']]==6)&(trace[:,col['retreat']]==0)]
        free = np.flatnonzero(release[:,col['finger_cube_2']]==0)
        outside = np.flatnonzero(release[:,col['post_xy_m']]>.009)
        contexts.append(dict(arm=arm,final_xy_m=float(last[col['post_xy_m']]),final_height_m=float(last[col['post_height_m']]),
            final_pair_contact=bool(last[col['post_pair_contact']]),final_held=bool(last[col['post_held']]),
            final_fingers=[bool(last[col[f'finger_cube_{i}']]) for i in range(3)],valid_two=bool(last[col['valid_two']]),
            valid_three=bool(last[col['valid_three']]),source_linear_m_s=float(np.linalg.norm(velocity[2,:3])),
            source_angular_rad_s=float(np.linalg.norm(velocity[2,3:])),
            source_finger_frames_final_50=int(trace[-50:,col['finger_cube_2']].sum()),
            maximum_strict_tail=int(trace[:,col['valid_tail']].max()),
            first_finger_free_after_release=int(free[0]) if len(free) else None,
            first_xy_above_9mm_after_release=int(outside[0]) if len(outside) else None))
        if arm=='guarded_feedback':
            feedback = release
    (out/'critical_terminal_context.json').write_text(json.dumps(contexts,indent=2),encoding='utf-8')
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes = plt.subplots(1,2,figsize=(11,4),layout='constrained')
    candidates = ['control','grasp_timeout','grasp_ready']
    values = [analysis['panels']['grasp_failure'][a]['successes'] for a in candidates]
    axes[0].bar(range(3),values,color=['#333','#ad7398','#7e539e'])
    axes[0].set(xticks=range(3),xticklabels=['BC','Timeout','Späte Bereitschaft'],ylim=(0,6.4),
        ylabel='Vollständige Aufgaben / 6',
        title='Bekannte Griffstillstände: 2 Familien × 3 feste Parents')
    axes[0].yaxis.set_major_locator(MaxNLocator(integer=True))
    for i,value in enumerate(values):
        axes[0].text(i,value+.1,str(value),ha='center')
    axes[0].text(.03,.95,'Erfolgskontrollen: jeweils 4/4 erhalten',transform=axes[0].transAxes,va='top',fontsize=9)
    frames = feedback[:,col['frame']]-feedback[0,col['frame']]
    contact = feedback[:,col['finger_cube_2']].astype(bool)
    axes[1].fill_between(frames,0,12,where=contact,color='#b7b7b7',alpha=.3,step='mid')
    line, = axes[1].plot(frames,1000*feedback[:,col['post_xy_m']],color='#2c8866',lw=1.5,label='XY-Abstand')
    threshold = axes[1].axhline(9,color='#b24e4e',ls=':',label='9-mm-Erfolgsgrenze')
    axes[1].set(xlabel='Frames ab Freigabeeintritt',ylabel='XY-Abstand Quell-/Zielwürfel [mm]',ylim=(0,12),
        title='Parent 3 / 2026189042: Veto + Objektfeedback')
    axes[1].legend(handles=[line,threshold,Patch(facecolor='#b7b7b7',alpha=.3,label='Fingerkontakt mit Quellwürfel')],fontsize=8)
    axes[1].text(.03,.04,'Längste streng gültige Folge: 2/50 Frames',transform=axes[1].transAxes,fontsize=9)
    fig.suptitle('Lokale Korrektur und vollständiger Aufgabenerfolg',fontsize=13)
    fig.savefig(out/'mechanisms.png',dpi=170)
    fig.savefig(out/'mechanisms.pdf')
    plt.close(fig)
    paths.extend(out/name for name in ('plan.json','analysis.json','trace_schema.json'))
    proof = dict(script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        inputs_sha256={str(path.relative_to(out)):hashlib.sha256(path.read_bytes()).hexdigest() for path in paths},
        scope='Exploratory post-run contact description of the previously fixed critical case; no new intervention or changed endpoint')
    (out/'supplement_provenance.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    supplement(parser.parse_args().output.resolve())
