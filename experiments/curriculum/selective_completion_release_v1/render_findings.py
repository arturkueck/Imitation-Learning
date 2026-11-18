"""Derived scientific figures from completed frozen-policy traces."""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator


def render(out):
    def read(name):
        return json.loads((out/name).read_text(encoding='utf-8'))
    plan = read('plan.json')
    if read('status.json')['state']!='COMPLETE' or plan['technical_only']:
        raise ValueError('Require completed full diagnosis')
    analysis = read('analysis.json')
    columns = {name:i for i,name in enumerate(read('trace_schema.json'))}
    labels = dict(control='Kontrolle',grasp_timeout='Griff: Timeout',grasp_ready='Griff: späte Bereitschaft',
        release_hold='Freigabe: EEF halten',release_feedback='Freigabe: Objektfeedback',guarded_bc='Veto + BC',
        guarded_hold='Veto + EEF halten',guarded_feedback='Veto + Objektfeedback')
    arms = list(labels)
    colors = ['#303030','#b06c9b','#8553a3','#377eb8','#398b66','#a7773f','#70a4ce','#79b194']
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes = plt.subplots(2,2,figsize=(12,8),layout='constrained')
    calibration = analysis['panels']['calibration']
    n = calibration['control']['n']
    successes = [calibration[a]['successes'] for a in arms]
    axes[0,0].barh(range(8),successes,color=colors)
    axes[0,0].set(yticks=range(8),yticklabels=[labels[a] for a in arms],xlim=(0,n+2),
        xlabel=f'Vollständige Aufgaben / {n} Modell-Szenen-Paare',title='Neue Kalibrierung: 12 Szenen × 3 feste Parents')
    axes[0,0].invert_yaxis()
    axes[0,0].xaxis.set_major_locator(MaxNLocator(integer=True))
    for i,count in enumerate(successes):
        axes[0,0].text(count+.3,i,str(count),va='center')
    gains = [calibration[a]['gains'] for a in arms[1:]]
    losses = [-calibration[a]['losses'] for a in arms[1:]]
    axes[0,1].barh(range(7),gains,color='#398b66',label='Gewonnene Aufgaben')
    axes[0,1].barh(range(7),losses,color='#b84f4f',label='Verlorene Aufgaben')
    axes[0,1].axvline(0,color='#777',lw=.8)
    axes[0,1].set(yticks=range(7),yticklabels=[labels[a] for a in arms[1:]],
        xlabel='Gepaarte Gewinne / Verluste gegenüber eigener Kontrolle',title='Alle Ausgänge bleiben erhalten')
    axes[0,1].invert_yaxis()
    axes[0,1].xaxis.set_major_locator(MaxNLocator(integer=True))
    axes[0,1].legend(fontsize=8)
    group = next(g for g in read('groups.json') if g['case']['id']=='release_g16_failure')
    for ax,selected,title in ((axes[1,0],['control','release_hold','release_feedback'],'Ohne Ablageveto'),
                              (axes[1,1],['guarded_bc','guarded_hold','guarded_feedback'],'Mit Ablageveto')):
        for arm,color in zip(selected,['#303030','#377eb8','#398b66']):
            result = group['arms'][arm]
            entry = result['entries'].get('2/6')
            if entry is None:
                continue
            with np.load(out/'traces'/f"{group['case']['id']}_{arm}.npz") as archive:
                trace = archive['trace']
            at = entry['frame']
            mask = (trace[:,columns['placement']]==2)&(trace[:,columns['phase']]==6)&\
                (trace[:,columns['frame']]<=at+200)
            label = labels[arm]+(' (Erfolg)' if result['success'] else ' (Fehlschlag)')
            ax.plot(trace[mask,columns['frame']]-at,1000*trace[mask,columns['post_xy_m']],color=color,label=label,lw=1.5)
        ax.axhspan(0,9,color='#398b66',alpha=.1)
        ax.axhline(9,color='#398b66',ls=':',lw=1)
        ax.axvline(20,color='#888',ls='--',lw=.8)
        ax.set(title=title+' · Parent 3 / Szene 2026189042',xlabel='Frames ab Freigabeeintritt (erste 200)',
            ylabel='XY-Abstand Quell-/Zielwürfel [mm]',ylim=(0,None))
        ax.legend(fontsize=7)
    fig.suptitle('Selektiver Abschluss und Freigabedynamik · keine Lernupdates',fontsize=13)
    fig.savefig(out/'findings.png',dpi=170)
    fig.savefig(out/'findings.pdf')
    plt.close(fig)
    proof = dict(renderer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        inputs_sha256={name:hashlib.sha256((out/name).read_bytes()).hexdigest() for name in
            ('plan.json','analysis.json','groups.json','trace_schema.json')},
        scope='Derived descriptive figure; fixed critical case, first 200 release frames, dashed line ends the 20-frame feedback window')
    (out/'figure_provenance.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    render(parser.parse_args().output.resolve())
