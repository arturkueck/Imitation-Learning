"""Independent final metric checks and report for the completed A/B/C pilot."""
from pathlib import Path
import json,hashlib,collections,datetime
import numpy as np
import torch
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    assert read(P/'status.json')['state']=='COMPLETED'
    selection=read(P/'final_test/selection.json');assert len(selection)==9
    stats={};paired={};models={};episode_total=0
    for s in [1,2,3]:
        rngs=[];parents=[]
        for arm in ['A','B','C']:
            name=f'{arm}_seed{s}';q=P/'training'/name;cfg=read(q/'config.json');state=read(q/'status.json');assert state['updates']==30000
            ck=torch.load(q/'latest.pth',map_location='cpu',weights_only=False);rngs.append(ck['original_rng']);parents.append(cfg['parent_sha256'])
            assert sha(cfg['parent'])==cfg['parent_sha256'];assert sha(selection[name]['path'])==selection[name]['sha256']
            models[name]=dict(best=read(q/'best.json'),elapsed=state['elapsed_seconds'],initial_self_mse=cfg['new_action_mse_before_training'])
            for count in [2,3]:
                f=P/'final_test'/f'{name}_stack{count}.json';d=read(f);n=100 if count==3 else 50;assert d['complete'] and d['n']==n
                counter=collections.Counter();errors=[]
                for r in d['rows']:
                    a=np.load(f.parent/(f.stem+'_traces')/(str(r['seed'])+'.npz'))['trace'];assert np.isfinite(a).all();assert len(a)==r['steps']
                    valid_index=4+count*3+3+7+count+1;tail=0;maximum=0
                    for ok in a[:,valid_index]:tail=tail+1 if ok else 0;maximum=max(maximum,tail)
                    assert r['success']==(maximum>=50);counter['success']+=r['success'];counter['first_stack']+=r['first_stack_step'] is not None
                    if count==3:
                        if r['success']:
                            pos=a[-1,4:13].reshape(3,3);errors.append(float(np.linalg.norm(pos[2,:2]-pos[1,:2])*1000))
                        else:
                            counter[f"failed_stage{r['stage']}_phase{r['phase']}"]+=1
                            if r['first_stack_step'] is not None:
                                z=a[a[:,0]>=r['first_stack_step']];pos=z[:,4:13].reshape(-1,3,3);bad=(np.linalg.norm(pos[:,1,:2]-pos[:,0,:2],axis=1)>.009)|(np.abs(pos[:,1,2]-pos[:,0,2]-.04)>.008)
                                counter['failed_lower_geometry_lost']+=bool(bad.any())
                assert counter['success']==d['successes'];episode_total+=n
                stats[f'{name}_stack{count}']=dict(n=n,**dict(counter),successful_xy_mean_mm=float(np.mean(errors)) if errors else None)
                if count==3:
                    for r in d['rows']:
                        key=r['seed'];entry=paired.setdefault(key,{});entry[name]=r['success']
        assert len(set(parents))==1 and rngs[0]==rngs[1]==rngs[2]
    gains={}
    for s in [1,2,3]:
        for other in ['A','B']:
            gains[f'C_minus_{other}_seed{s}']=dict(gained=sum(v[f'C_seed{s}'] and not v[f'{other}_seed{s}'] for v in paired.values()),lost=sum(v[f'{other}_seed{s}'] and not v[f'C_seed{s}'] for v in paired.values()))
    original=P.parents[1]/'experiments/additional_tasks/stack_two/data/image_demonstrations.hdf5';assert sha(original)==read(P/'protocol.json')['original_dataset_sha256']
    report=dict(episodes=episode_total,stats=stats,models=models,paired=gains,all_successes_recomputed=True,finite=True,parent_pairing=True,original_sampler_rng_equal=True,original_dataset_unchanged=True)
    (P/'analysis.json').write_text(json.dumps(report,indent=2))
    fig,axes=plt.subplots(1,2,figsize=(11,4.4));colors={'A':'#888888','B':'#d4a14a','C':'#007a8a'}
    for j,arm in enumerate(['A','B','C']):
        axes[0].bar(np.arange(3)+(j-1)*.25,[stats[f'{arm}_seed{s}_stack3']['success'] for s in [1,2,3]],.25,color=colors[arm],label=arm)
        axes[1].bar(np.arange(3)+(j-1)*.25,[stats[f'{arm}_seed{s}_stack2']['success']*2 for s in [1,2,3]],.25,color=colors[arm],label=arm)
    for ax,title in zip(axes,['Drei Wuerfel:100 neue Starts je Modell','Zwei Wuerfel:50 neue Starts je Modell']):
        ax.set(xticks=[0,1,2],xticklabels=[1,2,3],xlabel='Parent-/Trainingsseed',ylabel='Stabiler Erfolg [%]',ylim=(0,105),title=title);ax.legend();ax.grid(axis='y',alpha=.15)
    axes[0].axhline(90,color='red',ls='--');fig.tight_layout();fig.savefig(P/'results.png',dpi=160);plt.close(fig)
    lines=['# Self-Imitation-Pilot: Ergebnis und Entscheidung','',
    '**Begrenzter positiver Effekt eigener Dreierdaten,90%-Ziel verfehlt.** Alle neun Modelle absolvierten30.000 zusaetzliche Updates. Alle1350 Endtestepisoden sind vollstaendig,900 davon Dreiertests. ArmC erreicht im Dreiertest62/58/49%, gegenueber55/51/49% inA und56/50/47% inB. Mittelwerte:C56,3%,A51,7%,B51,0%.',
    '', 'A:100% Originaldaten. B:75%Original+25% erfolgreiche eigene Zweier. C:75%Original+25% erfolgreiche eigene Dreier. Frischer gleicher AdamW pro gepaartem Arm,3e-5, Batch64; identische Ausgangsgewichte innerhalb jedes Parentseeds. Der Abschlussklassifikator wird ausschliesslich aus Originalexpertendaten weitertrainiert. Alle Arme nutzen denselben Controller samt Rueckzug.',
    '', '![Endtests](results.png)','',
    '| Arm | Dreier Seed1 /100 | Seed2 /100 | Seed3 /100 | Zweier Seed1 /50 | Seed2 /50 | Seed3 /50 |','|---|---:|---:|---:|---:|---:|---:|']
    for arm in ['A','B','C']:
        values=[stats[f'{arm}_seed{s}_stack{k}']['success'] for k in [3,2] for s in [1,2,3]];lines.append('| '+arm+' | '+' | '.join(map(str,values))+' |')
    lines+=['','## Was ist durch den Vergleich gedeckt?','',
    'C gegenA:+7,+7,0 Prozentpunkte. C gegenB:+6,+8,+2 Prozentpunkte. Eigene Zweierdaten allein zeigen mit+1,-1,-2 Punkten gegenA keinen konsistenten Vorteil. Eigene Dreierdaten helfen in diesem konkreten Pilot eher als allgemeine zusaetzliche Selbstdaten; der Unterschied ist klein und nicht bei allen Parents gegenA positiv. Drei Parentmodelle sind keine Grundlage fuer eine breite Signifikanzbehauptung. Starts sind innerhalb der Modelle gepaart, nicht zusaetzliche unabhaengige Trainingsreplikate.',
    '', 'Gepaarte gewonnene/verlorene Dreierstarts mitC:']
    for k,v in gains.items():lines.append(f"- {k}: {v['gained']} gewonnen, {v['lost']} verloren.")
    lines+=['', 'Die Zweier-Erfolge liegen bei96–98% in allen Armen. In diesen50 Tests pro Modell ist keine grosse Zweierregression erkennbar; eine Verschlechterung um einzelne Episoden bleibt moeglich. Das ist kein Beweis vollstaendiger Nichtverschlechterung.',
    '', '## Teacher und Modellauswahl','',
    'Die unveraenderten Teacher wurden auf denselben50 Entwicklungsstarts bewertet, nicht auf den finalen100 Teststarts dieses Piloten. Vergleich daher nur innerhalb der Entwicklung, kein unbelegter Testvergleich mit historischen62/48/50% auf anderen Szenen.',
    '', '| Seed | Teacher Dev /50 | A best Dev /50 (Updates) | B best Dev /50 (Updates) | C best Dev /50 (Updates) |','|---|---:|---|---|---|']
    for s in [1,2,3]:
        teacher=read(P/'teacher_baseline'/f'teacher{s}_stack3.json')['successes'];values=[]
        for arm in ['A','B','C']:
            b=models[f'{arm}_seed{s}']['best'];values.append(f"{b['dev3']} ({b['update']})")
        lines.append(f'| {s} | {teacher} | '+' | '.join(values)+' |')
    lines+=['', 'Checkpoints wurden nach Dreier-Dev-Erfolg, bei Gleichstand Zweier-Erfolg und dann frueherem Update gewaehlt. Alle neun Gewichte wurden vor dem ersten Endtest kopiert und gehasht. Die gespeicherten Endhashes stimmen weiterhin. Dass fruehe Checkpoints teilweise besser sind als30.000 Updates, spricht gegen blindes Weitertrainieren. Die gesamte bezahlte Trainingsmenge ist270.000 Updates, auch wenn ein frueherer Checkpoint zum Endtest gewaehlt wurde.',
    '', '## Datenqualitaet und tatsaechlicher Lernimpuls','',
    'Neue Daten:286 erfolgreiche Zweier-Trainingsepisoden und99 Zweier-Validierungsepisoden;154 erfolgreiche Dreier-Trainingsepisoden und56 Dreier-Validierungsepisoden.800 feste Sammelversuche, alle Fehlschlaege archiviert. Pre-action-Inputs, zeitliche Verkettung, endliche Werte und Erfolg wurden unabhaengig geprueft; keine identischen Initialzustand-Hashes zwischen Training und Validierung. DATASET_REPORT.md dokumentiert die Aufschluesselung pro Teacher.',
    '', 'Die Teacher liefern erfolgreiche Policy-Daten, keinen neuen unabhaengigen Experten. Das Ergebnis ist Self-Imitation/Teacherpool-Destillation nach einem Start aus Zweier-Expertendaten. SobaldC mitDreierrollouts trainiert wird, ist seine Datenbedingung keine reine Zero-shot-Generalisation ausschliesslich aus Zweier-Trainingsdemos mehr.',
    '', 'Die Aktions-MSE auf neuen Beispielen vor Update1 ist nicht null, weil der Datensatz von drei unterschiedlichen Teachern stammt. B liegt je Parent bei ca.5,1e-5 bis8,5e-5, C bei5,34e-4 bis2,16e-3. Der Lernimpuls ist daher unter anderem Nachahmung anderer Teacher auf neuen Zustaenden; der Versuch isoliert keinen Vorteil einer exakten Selbstkopie. Bei denselben Inputs und identischem Teacher waere der anfängliche Actorgradient exakt null. Die Erfolgsfilterung und ihr Selektionsbias sind ebenfalls nicht durch einen ungefilterten Kontrollarm isoliert.',
    '', '## Fehler und Platzierungsqualitaet','',
    'Die Einzelzeitreihen wurden auf endliche Werte geprueft und alle1350 Erfolge aus mindestens50 kontinuierlichen valid-Frames erneut berechnet. Folgende Werte beschreiben erste Paarplatzierung, Fehlschlaege mit zeitweisem Verlust der unteren Geometrie und mittleren C–B-Mittenversatz am Ende erfolgreicher Tuerme. Geometrieverlust beweist keine konkrete Kollisionsursache; der Versatz gilt ausschliesslich fuer Erfolge.',
    '', '| Modell | Erster Stapel /100 | Fehler mit unterem Geometrieverlust | XY-Mittel erfolgreicher Tuerme [mm] |','|---|---:|---:|---:|']
    for arm in ['A','B','C']:
        for s in [1,2,3]:
            r=stats[f'{arm}_seed{s}_stack3'];lines.append(f"| {arm}_seed{s} | {r['first_stack']} | {r.get('failed_lower_geometry_lost',0)} | {r['successful_xy_mean_mm']:.2f} |")
    duration=(P/'supervisor_status.json').stat().st_mtime-(P/'protocol.json').stat().st_mtime
    lines+=['', '## Aufwand, Grenzen und naechster Schritt','',
    f"Zeit von Protokollanlage bis Supervisorabschluss ca.{duration/3600:.2f}h inklusive Vorbereitung, Unterbrechung/Reparatur und Warte-/Evaluationszeiten. Summe der neun Trainingslaeufe inklusive ihrer Entwicklungsbewertungen:{sum(v['elapsed'] for v in models.values())/3600:.2f}h. Das sind keine reinen GPU-Optimierungsstunden. Ausgefuehrt wurden800 Sammelversuche,300 Teacher-Baselineepisoden,2700 Entwicklungsbewertungen und1350 Endtests, zuzueglich technischer Vorpruefungen. Die urspruengliche Deadline wurde nicht verlaengert. Ein technischer Abbruch der batched Aktionsvalidierung wurde nach exakter Einzelbildreproduktion behoben; keine wissenschaftliche Gateanpassung und keine alten Trainingsdaten ersetzt.",
    '', 'Ergebnisentscheidung: C ist ein sinnvoller neuer Ausgangspunkt fuer weitere kontrollierte Entwicklung, aber die einfache Aggregation erfolgreicher Episoden schliesst die Zuverlaessigkeitsluecke nicht. Eine weitere blinde Sammel-/Trainingsrunde ist durch diesen Pilot nicht begruendet. Zuerst die erhaltenen Fehlerstarts mit Kontakt-/Bahnverlaeufen untersuchen und pruefen, ob eine Turm-/Freiraumdarstellung oder kompetente Korrekturlabels fuer die Fehlzustaende erforderlich sind. Eine solche Aenderung waere ein neuer Methodenversuch. Kein weiterer Trainingslauf wurde hier gestartet.',
    '', 'Die Modelle sehen nur Ankerrelativlage, Orientierung, Finger und Phasenzeit; Lage des restlichen Turms und Hindernisse fehlen als explizite Eingaben. Eine passende Bahn kann kopiert werden, aber eine nicht im Input unterscheidbare Gefahr nicht automatisch erkannt werden. Feste Phasen-/Paarreihenfolge, Rueckzugsregel, privilegierte Simulatorzustaende und physische Gates bleiben Bestandteil aller Resultate.',
    '', 'Die finalen125000er/126000er Szenen sind nach dieser Auswertung verbrauchte Endtests. Bei weiterer Methodenwahl neue Tests reservieren.90% wurden von keinem der neun Modelle erreicht; weniger Updates bis90% sind folglich ebenfalls nicht nachgewiesen. Originaldatensatz und Parentcheckpoint-Hashes wurden nochmals geprueft und sind unveraendert. Sampler-Endzustaende des Originaldatensamplers sind ueberA/B/C je Parent identisch. Vergleichbarkeit der Ausgangsgewichte und Updatebudgets ist geprueft.',
    '', 'Nachweise: analysis.json, training_verification.json, dataset_audit.json, final_test/selection.json, alle Konfigurationen/Checkpoints/NPZ-Rollouts. Ein abschliessender Prozesscheck steht in process_closeout.json.']
    (P/'RESULTS.md').write_text('\n'.join(lines),encoding='utf-8');print(json.dumps({k:v for k,v in stats.items() if k.endswith('stack3')},indent=2))
if __name__=='__main__':main()
