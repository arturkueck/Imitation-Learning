"""Read-only independent audit of the completed rollout corpus."""
from pathlib import Path
import json,hashlib,collections
import numpy as np
P=Path(__file__).resolve().parent

def main():
    manifest=json.loads((P/'dataset_manifest.json').read_text());assert manifest['complete'];rows=manifest['rows'];assert len(rows)==800
    stats={};hashes={};phase=collections.Counter();events=collections.Counter();total_frames=0
    for r in rows:
        count=r['count'];key=f"stack{count}_{r['split']}";s=stats.setdefault(key,dict(attempts=0,successes=0,accepted_frames=0,teachers={}))
        s['attempts']+=1;s['successes']+=int(r['success']);t=s['teachers'].setdefault(str(r['teacher']),dict(attempts=0,successes=0));t['attempts']+=1;t['successes']+=int(r['success'])
        hashes.setdefault((count,r['split']),set()).add(r['initial_sha256'])
        with np.load(r['path']) as a:
            n=len(a['x']);assert n==r['frames'];total_frames+=n
            assert all(np.isfinite(a[k]).all() for k in a.files)
            assert a['x'].shape==(n,10) and a['a'].shape==(n,7)
            assert np.array_equal(a['post_obs'][:-1],a['pre_obs'][1:])
            e=count*3
            x=np.c_[(a['pre_obs'][:,e:e+3]-a['anchor'])/.1,a['pre_obs'][:,e+3:e+7],a['pre_obs'][:,e+7:e+9]/.04,np.minimum(a['phase_steps'],100)/20]
            assert np.allclose(x,a['x'],atol=1e-6,rtol=1e-6)
            assert np.array_equal(a['y'],((a['prob']>=.8)&(a['p']<6)).astype(int))
            assert not a['a'][:,3:6].any();tail=0;maximum=0
            for ok in a['valid']:tail=tail+1 if ok else 0;maximum=max(maximum,tail)
            assert (maximum>=50)==r['success']
            if r['success']:
                s['accepted_frames']+=n
                for k,v in zip(*np.unique(a['p'],return_counts=True)):phase[(count,r['split'],int(k))]+=int(v)
            for k,v in zip(*np.unique(a['controller_event'],return_counts=True)):events[int(k)]+=int(v)
    for count in [2,3]:assert not hashes[(count,'train')]&hashes[(count,'valid')]
    report=dict(episodes=800,all_frames=total_frames,stats=stats,accepted_phase_counts={str(k):v for k,v in phase.items()},controller_events=dict(events),
        finite=True,pre_post_continuity_exact=True,features_reconstructed=True,success_recomputed=True,split_initial_states_disjoint=True,
        action_teacher_check='Collector verified20 single-frame predictions per episode with exact equality; batching-induced false alarm repaired before continuation.')
    (P/'dataset_audit.json').write_text(json.dumps(report,indent=2))
    text=['# Datensatzbericht: neue Self-Imitation-Daten','',
    '800 feste Sammelversuche abgeschlossen. Alle erfolgreichen und fehlgeschlagenen Episoden sind archiviert; fuer BC sind nur erfolgreiche Episoden vorgesehen. Keine alten Endtestrollouts wurden in diesen Datensatz kopiert.','',
    '| Aufgabe / Split | Versuche | Erfolgreiche Episoden | Akzeptierte Frames |','|---|---:|---:|---:|']
    for key,s in stats.items():text.append(f"| {key} | {s['attempts']} | {s['successes']} | {s['accepted_frames']} |")
    text+=['','## Auswahl pro Teacher','', '| Aufgabe / Split | Teacher | Versuche | Erfolge |','|---|---:|---:|---:|']
    for key,s in stats.items():
        for t,v in s['teachers'].items():text.append(f"| {key} | {t} | {v['attempts']} | {v['successes']} |")
    text+=['',f"Unabhaengige Nachpruefung: {total_frames} Frames aller800 Episoden auf endliche Werte geprueft. Zehn Modelleingaben aus Prae-Aktionsbeobachtung, Anker und Phasenschritten nachgerechnet. Exakte Verkettung post_obs[t]=pre_obs[t+1] nachgewiesen. Gespeicherte Phasen-Pseudolabels passen zur Teacherentscheidung; sie werden nicht fuer den Abschlussloss verwendet. Erfolg aus50 aufeinanderfolgenden valid-Frames neu berechnet. Keine identischen Initialzustand-Hashes zwischen Train und Valid innerhalb derselben Aufgabe.",
    '', 'Die Teacherzuweisung erfolgte zyklisch vor dem Versuchsausgang. Die ersten300 Versuche pro Aufgabe bilden Training, die weiteren100 Validierung. Unterschiede zwischen den Erfolgsquoten zeigen Selektionsbias; ein erfolgreicher Endzustand garantiert keine optimale oder durchgehend kollisionsfreie Bahn. Phasen-/Controllerstruktur und privilegierte Simulatorzustaende bleiben Teil der Methode.',
    '', 'Bei Zweier-Versuch121063 stoppte die erste Aktionsnachrechnung: batched CUDA-Inferenz wich um2,503395e-6 von der tatsaechlichen Einzelbild-Inferenz ab. Wiederholung mit exakt demselben Einzelbildpfad liefert0,0 Abweichung. Nach Reparatur wurde exakte Gleichheit statt einer groesseren Toleranz geprueft; absichtlich korrumpierte Aktion wurde im Negativtest abgewiesen. Die ersten63 Episoden wurden erhalten und vor Fortsetzung nochmals geprueft. Dokumentation in repair_001/.',
    '', 'Trainingsarme: AOriginal; B75%Original+25%eigeneZweier; C75%Original+25%eigeneDreier. Neue Daten beeinflussen den Actor-MSE, Abschlussloss bleibt an die Originalexpertendaten gebunden. Validierung ist nicht Training. Ergebnisse stehen nach Laufende in RESULTS.md; dieser Bericht behauptet keinen Trainingsvorteil.',
    '', 'Maschinenlesbare Nachweise: dataset_manifest.json, dataset_audit.json, datasets/stack*/manifest.json und die NPZ-Dateien samt Modell-XML. Der neue Datensatz enthaelt Drei-Wuerfel-Episoden; die anschliessenden Ergebnisse sind keine reine Zero-shot-Generalisation ausschliesslich aus Zwei-Wuerfel-Trainingsdaten.']
    (P/'DATASET_REPORT.md').write_text('\n'.join(text),encoding='utf-8');print(json.dumps(stats,indent=2))
if __name__=='__main__':main()
