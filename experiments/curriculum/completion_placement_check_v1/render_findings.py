"""Render derived figures from completed traces; never run a simulator or train."""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def render(out):
    def read(name):
        return json.loads((out/name).read_text(encoding='utf-8'))
    if read('status.json')['state']!='COMPLETE' or read('plan.json')['technical_only']:
        raise ValueError('Require completed full diagnosis')
    analysis = read('analysis.json')
    cols = {name:i for i,name in enumerate(read('trace_schema.json'))}
    arm_labels = dict(control='Kontrolle',grasp_completion='Griff: Abschluss',place_action='Ablage: Bewegung',
        place_completion='Ablage: Abschluss',place_both='Ablage: beides',place_guard='Ablage: Veto')
    arms = list(arm_labels)
    colors = dict(zip(arms,['#252525','#c45a9c','#3478b8','#2b8b64','#8465a9','#d58026']))
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False})
    fig, axes = plt.subplots(2,2,figsize=(12,8),layout='constrained')
    panel = analysis['panels']['calibration']
    ax = axes[0,0]
    counts = [panel[a]['successes'] for a in arms]
    ax.barh(range(len(arms)),counts,color=[colors[a] for a in arms])
    ax.set(yticks=range(len(arms)),yticklabels=[arm_labels[a] for a in arms],xlim=(0,54),
        xlabel='Vollständige Aufgaben / 54 Modell-Szenen-Paare',title='Geöffnete Kalibrierung: 18 Szenen × 3 feste Parents')
    ax.invert_yaxis()
    for i,count in enumerate(counts):
        ax.text(count+.5,i,str(count),va='center')
    ax = axes[0,1]
    gains = [panel[a]['gains'] for a in arms[1:]]
    losses = [-panel[a]['losses'] for a in arms[1:]]
    ax.barh(range(5),gains,color='#2b8b64',label='Gewinn gegenüber eigener Kontrolle')
    ax.barh(range(5),losses,color='#b74e4e',label='Verlust gegenüber eigener Kontrolle')
    ax.axvline(0,color='#777',lw=.8)
    ax.set(yticks=range(5),yticklabels=[arm_labels[a] for a in arms[1:]],xlabel='Anzahl gepaarter Gewinne / Verluste',
        title='Alle Ergebnisse, einschließlich geschädigter Kontrollen')
    ax.invert_yaxis()
    ax.legend(loc='lower right',fontsize=8)
    critical = next(g for g in read('groups.json') if g['case']['panel']=='known' and
        g['case']['model']=='mixed_s3_u30000' and g['case']['seed']==2026189042)
    for arm,row in critical['arms'].items():
        with np.load(out/'traces'/f"{critical['case']['id']}_{arm}.npz") as archive:
            trace = archive['trace']
        entry = row['entries']['2/5']['frame']
        mask = (trace[:,cols['placement']]==2)&(trace[:,cols['retreat']]==0)&\
            (trace[:,cols['frame']]>=entry-1)&(trace[:,cols['frame']]<=entry+200)
        x = trace[mask,cols['frame']]-entry
        label = arm_labels[arm]+(' (Erfolg)' if row['success'] else ' (Fehlschlag)')
        axes[1,0].plot(x,1000*trace[mask,cols['height_above_target_m']],label=label,color=colors[arm],lw=1.4)
        axes[1,1].plot(x,1000*trace[mask,cols['xy_error_m']],color=colors[arm],lw=1.4)
        for event in row['events']:
            if event['placement']==2 and event['phase']==5 and event['frame']-entry<=200:
                for ax in axes[1]:
                    ax.axvline(event['frame']-entry,color=colors[arm],ls=':',alpha=.7,lw=.9)
    axes[1,0].axhspan(32,48,color='#2b8b64',alpha=.12,label='Vorab definierte Zielgeometrie')
    axes[1,1].axhspan(0,9,color='#2b8b64',alpha=.12)
    axes[1,0].set(xlabel='Frames ab Eintritt in zweite Ablage (erste 200)',ylabel='Höhenabstand Quell-/Zielwürfel [mm]',
        title='Bekannter Fall Parent 3 / Szene 2026189042')
    axes[1,1].set(xlabel='Frames ab Eintritt in zweite Ablage (erste 200)',ylabel='XY-Abstand Quell-/Zielwürfel [mm]',
        title='Gepunktet: Übergang zur Freigabe des jeweiligen Arms')
    axes[1,0].legend(fontsize=7)
    fig.suptitle('Abschluss und Ablage: Ursachenprüfung mit unveränderten Gewichten',fontsize=13)
    fig.savefig(out/'findings.png',dpi=170)
    fig.savefig(out/'findings.pdf')
    plt.close(fig)
    names = ['plan.json','groups.json','analysis.json','trace_schema.json']
    proof = dict(renderer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        inputs={name:hashlib.sha256((out/name).read_bytes()).hexdigest() for name in names},
        scope='Derived descriptive figure; known-case plots show a fixed 200-frame window, not a new endpoint')
    (out/'figure_provenance.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    render(parser.parse_args().output.resolve())
