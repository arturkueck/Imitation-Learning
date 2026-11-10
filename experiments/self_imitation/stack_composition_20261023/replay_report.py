"""Analyze stored trajectories without changing checkpoints or training data."""
import json
import numpy as np
import h5py
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from replay_diagnosis import DEST,OUT,CASES
from audit import DATA

def main():
    results=json.loads((DEST/'results.json').read_text());assert len(results)==30
    with h5py.File(DATA,'r') as f:
        ds=[f['data'][n.decode()]['obs/object'][:] for n in f['mask/train'][:]]
        dz=np.concatenate([d[:,2]-d[:,5] for d in ds])
    grouped=[];detail=[]
    for case,u in CASES:
        for mode in ['continuous','prebuilt']:
            rs=[r for r in results if r['case']==case and r['update']==u and r['mode']==mode]
            g=dict(case=case,update=u,mode=mode,n=len(rs),second=sum(r['second_steps']>0 for r in rs))
            for k in ['grasp_c','lift_c','near_target','contact_at_target','released_at_target','success','lower_geometry_lost']:
                g[k]=sum(r.get(k,False) for r in rs)
            grouped.append(g)
            for r in rs:
                a=np.load(DEST/f'{case}_u{u}'/f"{mode}_{r['seed']}.npz")['trace'];s=a[a[:,1]==2]
                if not len(s):continue
                p=s[:,2:11].reshape(-1,3,3);xy=np.linalg.norm(p[:,2,:2]-p[:,1,:2],axis=1)
                lifted=p[:,2,2]>.88;held=s[:,23]>0
                opening=lifted&(s[:,20]<-.5)&(xy>.03)
                detail.append(dict(case=case,update=u,mode=mode,seed=r['seed'],
                    start_target_minus_source_z=float(p[0,1,2]-p[0,2,2]),
                    opening_while_lifted_far=bool(opening.any()),
                    first_opening_far_step=int(s[np.flatnonzero(opening)[0],0]) if opening.any() else None,
                    final_lower_xy=float(np.linalg.norm(p[-1,1,:2]-p[-1,0,:2])),
                    final_lower_dz=float(p[-1,1,2]-p[-1,0,2]),
                    held_frames=int(held.sum())))
    write_data=dict(groups=grouped,details=detail,train_target_minus_source_z_range=[float(dz.min()),float(dz.max())])
    (DEST/'analysis.json').write_text(json.dumps(write_data,indent=2))
    # One fixed case with natural transition; both traces shown at simulator time.
    fig,axes=plt.subplots(3,2,figsize=(12,8),sharex='col')
    for col,mode in enumerate(['continuous','prebuilt']):
        a=np.load(DEST/'relative_seed1_u30000'/f'{mode}_61001.npz')['trace'];t=a[:,0]/20;p=a[:,2:11].reshape(-1,3,3)
        for j,c in enumerate('ABC'):axes[0,col].plot(t,p[:,j,2],label=c)
        axes[0,col].set_title(f'Seed 1, 30k, Start 61001: {mode}');axes[0,col].set_ylabel('Wuerfelhoehe [m]');axes[0,col].legend()
        axes[1,col].plot(t,np.linalg.norm(p[:,2,:2]-p[:,1,:2],axis=1)*100,label='C zu B')
        axes[1,col].axhline(3,color='gray',ls='--');axes[1,col].set_ylabel('XY-Abstand C–B [cm]')
        axes[2,col].plot(t,a[:,20],label='Greiferaktion');axes[2,col].plot(t,a[:,23],label='C gehalten',alpha=.6)
        axes[2,col].set(xlabel='Simulationszeit [s]',ylabel='Greifer (-1 offen)');axes[2,col].legend()
        switches=np.flatnonzero(a[:,1]==2)
        if len(switches):
            for ax in axes[:,col]:ax.axvline(t[switches[0]],color='red',ls=':',alpha=.7);ax.grid(alpha=.15)
    fig.tight_layout();fig.savefig(DEST/'trace_comparison.png',dpi=160);plt.close(fig)
    lines=['# Replay-Diagnose: Zwei-zu-Drei-Komposition','',
    '30 Diagnoseepisoden, keine Trainingsupdates. Drei vorhandene Checkpoints, fuenf vorab festgelegte Entwicklungsstarts (61000–61004), zwei Bedingungen. Keine neuen Teststarts zur Modellwahl verwendet.',
    '', '## Ergebnisse','',
    '| Modell | Bedingung | Zweite Fertigkeit | C gegriffen | C angehoben | Naeher als 3 cm* | Kontakt am Ziel* | Stabil |',
    '|---|---|---:|---:|---:|---:|---:|---:|']
    for g in grouped:
        vals=[g[k] for k in ['second','grasp_c','lift_c','near_target','contact_at_target','success']]
        lines.append(f"| {g['case']} / {g['update']} | {g['mode']} | "+' | '.join(f'{v}/5' for v in vals)+' |')
    lines+=['','* Nach Anheben von C ueber z=0,88 m. Zielkontakt verlangt zusaetzlich XY <9 mm, Hoehendifferenz 40 mm ±8 mm und echten B–C-Kontakt. Ereignisse gelten waehrend der zweiten Fertigkeit; die Tabellenzaehler sind keine zwingend verschachtelte Fehlerklassifikation.',
    '', '## Interpretation','',
    'Der vorbereitete Zweierstapel loest das Problem nicht: auch diese zweite Teilaufgabe scheitert in allen 15 Episoden. Ein ausschliesslich fehlerhafter Uebergang von der ersten zur zweiten Fertigkeit erklaert die beobachteten Ergebnisse deshalb nicht. Das beweist jedoch keine einzelne Ursache: Vorbereitung aendert Objektpositionen, Vorgeschichte und Roboterstartpose gleichzeitig. Fuenf Starts pro Checkpoint sind eine begrenzte Entwicklungsdiagnose.',
    '',f"Die Trainingsdaten enthalten fuer Ziel-z minus Quellwuerfel-z Werte von {dz.min()*100:.2f} bis {dz.max()*100:.2f} cm; an jedem Demostart ist die Differenz null. Die vorbereitete zweite Teilaufgabe beginnt dagegen mit rund +4 cm. Diese relative Hoehenbeziehung liegt ausserhalb des beobachteten Trainingsbereichs. Relative Koordinaten allein entfernen diese Verteilungsverschiebung nicht. Dies ist ein nachgewiesener Abdeckungsunterschied, noch kein isolierter kausaler Beweis.",
    '', 'Die Fehler treten bereits beim Greifen/Anheben und beim Transport auf. Daher waere eine ausschliessliche Optimierung des Loslassens zu eng. Teilweise wird der untere Stapel aus seiner Geometrietoleranz gebracht; das darf ohne weitere Kontakt-/Kraftanalyse nicht pauschal als Greiferkollision bezeichnet werden.',
    '', 'Konkretes Beispiel: relative Seed 1, 30.000 Updates, Start 61001. Im kontinuierlichen Ablauf beginnt die zweite Fertigkeit nach 6,25 s. C wird angehoben, bleibt nach dem Anheben aber mindestens 8,16 cm horizontal vom Ziel entfernt. Ab Schritt 291 (etwa 14,6 s) wird der Greifer deutlich geoeffnet, obwohl C noch angehoben und weit vom Ziel entfernt ist; danach geht der Grasp verloren und C faellt auf den Tisch. Mit vorbereitetem Stapel tritt bei demselben Start ein aehnlicher Ablauf auf (minimal 7,80 cm Abstand nach Lift). Das ist ein direkt beobachtetes vorzeitiges Oeffnen ohne vorherige Zielpositionierung; nicht alle anderen Fehlversuche folgen diesem Muster.',
    '', '[Video: kompletter Ablauf, Start 61001](illustration_seed1_u30000/continuous_61001.mp4) · [Video: vorbereiteter Stapel, gleicher Start](illustration_seed1_u30000/prebuilt_61001.mp4). Die beiden Zusatzreplays illustrieren bereits enthaltene Faelle und werden nicht als weitere unabhaengige Episoden gezaehlt.',
    '', '![Zeitverlaeufe](trace_comparison.png)',
    '', '## Reproduzierbarkeit und Artefakte','',
    '- Alle 15 kontinuierlichen Replays stimmen bei Initialzustand-Hash, erstem Paarwechsel und Gesamterfolg mit den gespeicherten Originalepisoden ueberein.',
    '- Alle 15 vorbereiteten Tuerme wurden nach 40 neutralen Simulationsschritten auf den vorhandenen Kontakt-/Stabilitaetscheck geprueft.',
    '- Checkpoint-Hashes vor und nach der Untersuchung unveraendert. Datensatz nur lesend geoeffnet.',
    '- NPZ je Episode enthaelt Initialzustand, Startzustand nach Vorbereitung und pro Schritt Positionen, EEF, Aktionen, Grasp, Greiferkontakte, Objektkontakte, Stabilitaet und Geschwindigkeiten. Spaltenschema in protocol.json.',
    '- MP4 und Bildstreifen fuer den vorab festgelegten Start 61000 pro Checkpoint/Bedingung. Zusatzvideo fuer Start 61001 kann den Uebergang illustrieren; keine zusaetzlichen unabhaengigen Versuche.',
    '', '## Konsequenz fuer den naechsten Methodenversuch','',
    'Zuerst eine Hoehenablation mit kontrolliert gleicher Quellposition und Roboterstartpose sowie separat einen Uebergang mit zurueckgezogenem Greifer pruefen. Das trennt Einfluesse besser als der hier verwendete grobe Vorbereitungseingriff. Kein Erfolg dieser Diagnose darf als vollstaendige Dreier-Loesung gezaehlt werden.',
    '', 'Fuer das unveraenderte Ziel (nur Zwei-Wuerfel-Demos) ist anschliessend eine explizit getrennte, gelernte Greif-/Transport-/Platzierdarstellung eine begruendete Hypothese: Die Greifphase sollte nicht unnoetig von der unbekannten Zielhoehe abhaengen, die Platzierphase muss relativ zum Ziel arbeiten. Phasenlabels koennten ausschliesslich aus vorhandenen Demos abgeleitet werden; Controlleranteile und Regeln muessen ausgewiesen und gegen dieselbe BC-Baseline getestet werden. Dies ist ein Vorschlag, keine bereits implementierte oder nachgewiesen erfolgreiche Methode.',
    '', 'Mehr Updates allein sind durch diese Befunde nicht als Loesung begruendet. Das 90%-Ziel bleibt unerreicht.']
    (DEST/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(grouped,indent=2))

if __name__=='__main__':main()
