"""Export every diagnostic sample and generate a report from completed cells only."""
import csv,gzip,re
import numpy as np
from common import *
from replication_common import checkpoint as baseline_checkpoint, rollouts as baseline_rollouts
from transport_data import summary
OLD=ROOT/'experiments/stack_diagnostics/stack_direct_20261001';PRIOR=ROOT/'experiments/stack_diagnostics/stack_switch_20261001'
meta=read(PRIOR/'panel.json');panel=np.load(PRIOR/'panel.npz');offsets=np.array([r['offset'] for r in meta]);names=np.array([r['demo'] for r in meta])
goal=panel['object'][:,-1,:2]-panel['robot0_eef_pos'][:,-1,:2];expert=panel['expected'][:,1]
def csvwrite(path,rows):
    if not rows:return
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with Path(path).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader()
        w.writerows({k:json.dumps(v,allow_nan=False) if isinstance(v,(dict,list)) else v for k,v in r.items()} for r in rows)
def training(v,kind,seed,dest):
    if v!='A':
        t=read(dest/'training_complete.json');path=dest/'training_audit.npz';z=np.load(path)
        return dict(updates=t['optimizer_updates'],seconds=t['training_seconds'],time_scope='trainer wall time, including validation/checkpoint writes for diffusion',loss_last500=float(z['loss'][-500:].mean()),loss_last=float(z['loss'][-1]),audit=str(path.relative_to(ROOT)),loss_definition='raw or normalized chunk MSE' if kind=='direct' else 'epsilon MSE'),[dict(update=i+1,loss=float(loss),lr=float(lr)) for i,(loss,lr) in enumerate(zip(z['loss'],z['lr']))]
    if kind=='direct':
        z=np.load(dest/'training_audit.npz');t=read(dest/'status.json')
        return dict(updates=30000,seconds=t['elapsed_seconds'],time_scope='historical trainer wall time',loss_last500=float(z['loss'][-500:].mean()),loss_last=float(z['loss'][-1]),audit=str((dest/'training_audit.npz').relative_to(ROOT)),loss_definition='raw chunk MSE'),[dict(update=i+1,loss=float(loss),lr=float(lr)) for i,(loss,lr) in enumerate(zip(z['loss'],z['lr']))]
    ck=Path(baseline_checkpoint(kind,seed));log=ck.parent.parent/'logs/log.txt';text=log.read_text(errors='replace')
    epochs=[dict(epoch=int(m[1]),**json.loads(m[2])) for m in re.finditer(r'Train Epoch (\d+)\s*(\{.*?\})',text,re.S)]
    assert len(epochs)==300
    seconds=read(dest/'training_complete.json')['elapsed_seconds'] if (dest/'training_complete.json').exists() else sum(x['Time_Epoch']*60 for x in epochs)
    return dict(updates=30000,seconds=seconds,time_scope='historical process wall time' if seed>1 else 'sum of training epoch wall times; historical whole-process time unavailable',loss_last500=float(np.mean([x['Loss'] for x in epochs[-5:]])),loss_last=epochs[-1]['Loss'],audit=str(log.relative_to(ROOT)),loss_definition='epsilon MSE; historical per-update losses unavailable, epoch means exported'),[dict(epoch=x['epoch'],updates_in_epoch=100,loss=x['Loss'],lr=x['Optimizer/policy0_lr'],seconds=x['Time_Epoch']*60) for x in epochs]
def offline(v,kind,seed,dest):
    tag=dict(variant=v,model_class=kind,training_seed=seed)
    if kind=='direct':
        chunks=np.load(dest/'offline_predictions.npz')['chunks'];idx=np.arange(len(meta));draw=np.zeros(len(meta),int)
        pi=idx[np.isin(offsets,[-1,0])];pd=np.zeros(len(pi),int);pa=chunks[pi,1,:3]
    else:
        z=np.load(PRIOR/'source/ddim10.npz' if v=='A' and seed==1 else dest/'common_offline.npz');mask=z['draw']<8
        idx=z['panel_index'][mask];draw=z['draw'][mask];chunks=z['chunks'][mask]
        z=np.load(PRIOR/'source/paired_ddim10.npz' if v=='A' and seed==1 else dest/'paired_offline.npz');pi=z['panel_index'];pd=z['draw'];pa=z['chunks'][:,1,:3]
    a=chunks[:,1];xy=np.linalg.norm(a[:,:2],axis=1);em=np.linalg.norm(expert[idx,:2],axis=1)
    gc=(a[:,:2]*goal[idx]).sum(1)/np.maximum(xy*np.linalg.norm(goal[idx],axis=1),1e-9)
    ec=(a[:,:2]*expert[idx,:2]).sum(1)/np.maximum(xy*em,1e-9)
    rows=[];pairs=[];onsets=[]
    for i,j in enumerate(idx):
        rows.append(dict(**tag,panel_index=int(j),demo=meta[j]['demo'],frame=meta[j]['step'],offset=int(offsets[j]),draw=int(draw[i]),xy_magnitude=float(xy[i]),expert_xy_magnitude=float(em[i]),xy_over_expert=float(xy[i]/em[i]) if em[i]>1e-9 else None,goal_cosine=float(gc[i]),expert_direction_cosine=float(ec[i]),**{f'action_{k}':float(a[i,k]) for k in range(7)},**{f'expert_{k}':float(expert[j,k]) for k in range(7)}))
    for d in np.unique(pd):
        for name in sorted(set(names)):
            ii=np.flatnonzero((pd==d)&(names[pi]==name));ii=ii[np.argsort(offsets[pi[ii]])];assert len(ii)==2
            delta=pa[ii[1]]-pa[ii[0]];need=expert[pi[ii[1]],:3]-expert[pi[ii[0]],:3]
            pairs.append(dict(**tag,demo=name,draw=int(d),boundary_response=float(np.linalg.norm(delta)/np.linalg.norm(need)),aligned_boundary_response=float(delta@need/(need@need)),prediction_delta_xyz=delta.tolist(),expert_delta_xyz=need.tolist()))
    for d in np.unique(draw):
        for name in sorted(set(names)):
            ii=np.flatnonzero((draw==d)&(names[idx]==name));ii=ii[np.argsort(offsets[idx[ii]])]
            mask=(xy[ii]>.25)&(gc[ii]>.5);runs=np.flatnonzero(np.convolve(mask.astype(int),np.ones(3,int),'valid')==3)
            onset=int(offsets[idx[ii[runs[0]]]]) if len(runs) else None
            onsets.append(dict(**tag,demo=name,draw=int(d),onset_offset=onset,classification='missing' if onset is None else 'early' if onset<-2 else 'late' if onset>2 else 'on_time'))
    mask=np.isin(offsets[idx],range(6,11));o=dict(boundary_response=summary([r['boundary_response'] for r in pairs]),aligned_boundary_response=summary([r['aligned_boundary_response'] for r in pairs]),xy_over_expert=summary(xy[mask]/em[mask]),goal_cosine=summary(gc[mask]),expert_direction_cosine=summary(ec[mask]),wrong_direction_fraction=float((ec[mask]<0).mean()),onset_counts={c:sum(r['classification']==c for r in onsets) for c in ('early','on_time','late','missing')},onset_n=len(onsets))
    return o,rows,pairs,onsets
def main():
    cells=[];rollout_rows=[];offline_rows=[];boundary_rows=[];onset_rows=[];loss_rows=[];failures=[];partial_rollouts=[]
    for v in ('A','B','C','D'):
        for kind in ('direct','diffusion'):
            for seed in (1,2,3):
                dest=(OLD if seed==1 else ROOT/f'experiments/stack_diagnostics/stack_replication_20261001/{kind}/seed_{seed}') if v=='A' else folder(v,kind,seed)
                if v!='A' and not (dest/'evaluation_complete.json').exists():
                    if (dest/'aborted.json').exists():
                        failures.append(dict(variant=v,model_class=kind,training_seed=seed,**read(dest/'aborted.json')))
                        if (dest/'rollouts/results.json').exists():partial_rollouts.extend({**r,'variant':v,'model_class':kind,'training_seed':seed,'run_incomplete':True} for r in read(dest/'rollouts/results.json'))
                        if (dest/'training_audit_partial.npz').exists():
                            z=np.load(dest/'training_audit_partial.npz')
                            loss_rows.extend(dict(variant=v,model_class=kind,training_seed=seed,run_incomplete=True,update=i+1,loss=float(loss),lr=float(lr)) for i,(loss,lr) in enumerate(zip(z['loss'],z['lr'])))
                        elif (dest/'training_complete.json').exists():
                            _,lr=training(v,kind,seed,dest)
                            loss_rows.extend(dict(variant=v,model_class=kind,training_seed=seed,run_incomplete=True,**r) for r in lr)
                    continue
                rd=baseline_rollouts(kind,seed) if v=='A' else dest/'rollouts';rows=read(rd/'results.json');assert len(rows)==40
                o,orr,brr,ons=offline(v,kind,seed,dest);offline_rows+=orr;boundary_rows+=brr;onset_rows+=ons
                t,lr=training(v,kind,seed,dest);loss_rows.extend(dict(variant=v,model_class=kind,training_seed=seed,**r) for r in lr)
                counts={k:sum(r[k] for r in rows) for k in ('grasp','lift','correct_lift','transport_started','premature_transport','near','position','lower','release','sustained_success')}
                cell=dict(variant=v,model_class=kind,training_seed=seed,rollout=dict(n=40,counts=counts,max_height=summary([r['max_cube_height_m'] for r in rows])),offline=o,training=t)
                cells.append(cell)
                for r in rows:
                    rollout_rows.append({**r,'variant':v,'model_class':kind,'training_seed':seed})
    allvalues=dict(cells=cells,rollouts=rollout_rows,partial_rollouts_from_aborted_runs=partial_rollouts,offline_frames=offline_rows,boundary_pairs=boundary_rows,onsets=onset_rows,aborted_runs=failures,loss_csv='training_losses.csv',normalization=read(OUT/'normalization_stats.json'),protocol=read(OUT/'protocol.json'))
    write(OUT/'results_normalization.json',allvalues)
    csvwrite(OUT/'rollout_metrics.csv',rollout_rows);csvwrite(OUT/'offline_metrics.csv',offline_rows);csvwrite(OUT/'boundary_metrics.csv',boundary_rows);csvwrite(OUT/'onset_metrics.csv',onset_rows);csvwrite(OUT/'training_losses.csv',loss_rows)
    csvwrite(OUT/'partial_rollout_metrics.csv',partial_rollouts)
    table=[]
    for c in cells:
        r=c['rollout'];o=c['offline'];t=c['training'];co=r['counts']
        table.append(dict(variant=c['variant'],model_class=c['model_class'],training_seed=c['training_seed'],stable_stacks=co['sustained_success'],**{k:co[k] for k in ('grasp','lift','transport_started','position','lower','release')},xy_over_expert_median=o['xy_over_expert']['q'][2],goal_cosine_mean=o['goal_cosine']['mean'],expert_direction_cosine_mean=o['expert_direction_cosine']['mean'],boundary_response_median=o['boundary_response']['q'][2],max_height_median_m=r['max_height']['q'][2],loss_last500=t['loss_last500'],training_seconds=t['seconds']))
    csvwrite(OUT/'summary.csv',table)
    rows=['# Normalisierung: kontrollierter 2×2-Vergleich','', 'A = keine Normalisierung (bestehende Läufe wiederverwendet), B = nur Actions, C = nur Observations, D = beides. Alle neuen Läufe beginnen mit frischer Initialisierung und haben ein festes Budget von 30.000 echten Optimizer-Updates. Die Tabellen enthalten ausschließlich vollständig trainierte und ausgewertete Läufe.','', '| Variante | Modell | Seed | Stabil /40 | Greifen | Lift | Transport | Position | Absenken | Release |','|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for c in cells:
        k=c['rollout']['counts'];rows.append(f"| {c['variant']} | {c['model_class']} | {c['training_seed']} | {k['sustained_success']} | {k['grasp']} | {k['lift']} | {k['transport_started']} | {k['position']} | {k['lower']} | {k['release']} |")
    rows+=['','## Offline-Diagnosen und Aufwand','','XY/Expert und Grenzreaktion: Median; Cosinus: Mittelwert. Alle Actions vor Messung zurück in ursprüngliche Controller-Einheiten skaliert. Maximalhöhe: Median über 40 Rollouts; einzelne maximale Höhen in CSV/JSON.','', '| Variante/Modell/Seed | XY / Expert | Ziel-Cosinus | Expert-Cosinus | Grenzreaktion / Expert | Maximalhöhe m | Loss letzte 500 | Zeit min |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for c in cells:
        o=c['offline'];t=c['training'];rows.append(f"| {c['variant']}/{c['model_class']}/{c['training_seed']} | {o['xy_over_expert']['q'][2]:.2%} | {o['goal_cosine']['mean']:.4f} | {o['expert_direction_cosine']['mean']:.4f} | {o['boundary_response']['q'][2]:.2%} | {c['rollout']['max_height']['q'][2]:.4f} | {t['loss_last500']:.6f} | {t['seconds']/60:.1f} |")
    rows+=['','## Unveränderte Kontrollen','', 'Identische 180/20 Demonstrationen, zwei Beobachtungsframes mit 15 Kanälen, 16×7 Action-Chunks, ausgeführt werden Chunkpositionen 1 und 2. Batch 8, uniforme historische Sampler je Modellklasse, AdamW 1e−4 / Weight Decay 1e−6, 500 Warmup-Updates, Cosine über 30.000 Updates, EMA 0,75. Direct: ursprünglicher Residual-MLP mit Tanh und Chunk-MSE. Diffusion: ursprünglicher UNet, Epsilon-MSE, DDIM mit zehn Schritten und unverändertem Clip-Sample. Keine zusätzlichen Merkmale, Loss-Gewichte, Heuristiken, Datenänderungen oder Zwischencheckpoint-Auswahl.','', 'Präzisierung der historischen Sampling-Beschreibung aus dem installierten Quellcode: Direct verwendet numpy.default_rng mit Zurücklegen. Beim einzelnen Diffusion-Dataset liefert get_dataset_sampler() dagegen None; der bestehende DataLoader mischt ohne Zurücklegen innerhalb des jeweils neu gestarteten Epoch-Iterators, von dem 100 Batches genutzt werden. Diese tatsächlichen historischen Verfahren bleiben jeweils erhalten. Für neue Diffusion-Läufe werden die tatsächlich konsumierten Indexfolgen gespeichert; die neuen Normalisierungszellen sind bei gleichem Seed gepaart. Historische Diffusion-Batchindizes sind nicht verfügbar.','', '40 Startseeds 46000–46039; jeder Simulator-Startzustand muss denselben SHA-256 wie in der Baseline haben. Phasenindikatoren bleiben exakt unverändert und sind separat gezählte Diagnosen. Stabiler Stack verlangt Success in 40 zusätzlichen Frames, Kontakt und keinen Grasp. Greifen: natives Prädikat; Lift B-z>0,88 m; Transport: gehalten, B-z>0,98 m, XY-Geschwindigkeit>0,02 m/s und Ziel-Cosinus>0,5 für drei Frames. Position: XY<9 mm bei B−A-z>3,2 cm; Absenken zusätzlich B−A-z=4 cm ±8 mm; Release zusätzlich Kontakt und kein Grasp.','', 'Offline: dieselben 20 Validierungsdemos, −10 bis +10 Frames am Expert-Umschaltpunkt; Aktion an Chunkposition 1. Diffusion: dieselben acht Initialrausch-Samples je Beobachtung, 32 gepaarte Samples je Grenzpaar −1/0. XY/Expert und Cosinus werden im Transportfenster +6 bis +10 gemessen. Grenzreaktion = Norm des vorhergesagten XYZ-Sprungs / Norm des Expert-Sprungs.','', 'Alle neuen Losses pro Update werden exportiert. Direct-MSE ist bei Action-Normalisierung in transformierten Einheiten; Diffusion-Loss misst Epsilon und ist nicht unmittelbar mit Direct-Loss vergleichbar. A/Diffusion hat historisch nur Epochmittelwerte; A/Diffusion/1-Zeit ist die Summe der Trainingsepochen und schließt Checkpoint-I/O sowie Validierung aus. Andere Zeiten sind Laufzeiten mit den im JSON benannten Grenzen.','', 'Normalisierungsstatistiken werden ausschließlich auf den 27.322 ungepaddeten Trainingsframes angepasst. Dieselben Werte gelten für beide Historyslots, alle Chunkpositionen, Validierung und Rollout. Im nativen Dataset wird auch der Validierungs-Action-Cache mit den Trainingsstatistiken aufgebaut.','', '## Kanalstatistiken und Transformation','', 'Observations: (x−Mean)/(Population-Std+0,001), ohne Clipping. Actions: native Robomimic-Min-Max-Abbildung auf ±0,999999. Bei Spannweite<0,0001: Scale=1 und Offset=Minimum, damit konstante Kanäle keine Division durch null verursachen. Inverse Actions: raw=normalized×Scale+Offset. Tanh und DDIM-Clipping bleiben erhalten.','', '| Typ/Schlüssel/Kanal | Min | Max | Mean | Std |','|---|---:|---:|---:|---:|']
    s=read(OUT/'normalization_stats.json')
    for r in s['raw_channel_statistics']:rows.append(f"| {r['group']}/{r['key']}/{r['channel']} | {r['min']:.7g} | {r['max']:.7g} | {r['mean']:.7g} | {r['std']:.7g} |")
    rows+=['','Actions sind [X,Y,Z,Rot-X,Rot-Y,Rot-Z,Gripper] in den ursprünglichen Controller-Einheiten. Translation und Gripper erreichen bereits ±1; die drei Rotationskanäle sind konstant null. Die Gripper-Std ist etwa 3,47× X-Std, 4,03× Y-Std und 2,01× Z-Std. Min-Max gleicht diese Varianzen hier praktisch nicht an: Scale≈1,000001 für X/Y/Z/Gripper, Scale=1 für Rotation, Offset=0. B ist somit ein nahezu identischer Action-Skalierungsarm. Eine Action-Z-Standardisierung wäre unter den unveränderten Tanh-/DDIM-Grenzen inkompatibel (Expert-Ziele außerhalb ±1) und wurde nicht gleichzeitig eingeführt.','', '## Interpretation','']
    seed1={ (c['variant'],c['model_class']):c['rollout']['counts']['sustained_success'] for c in cells if c['training_seed']==1}
    finished=all((v,k) in seed1 for v in VARIANTS for k in ('direct','diffusion'))
    if not finished:rows+=['Vergleich noch nicht vollständig abgeschlossen. Skalierungshypothese und Erklärung des ursprünglichen 0%-Resultats bleiben offen. Keine fehlenden Laufwerte werden als Nullerfolge gezählt.']
    else:
        effects={}
        rows += ['Deskriptive 2×2-Effekte für Trainingsseed 1 (Prozentpunkte; keine Signifikanztests):','', '| Modell | Observation-Effekt, über beide Action-Arme gemittelt | Action-Effekt, über beide Observation-Arme gemittelt | Interaktion D−C−B+A |','|---|---:|---:|---:|']
        for kind in ('direct','diffusion'):
            a,b,c,d=[seed1[x,kind]/40 for x in ('A','B','C','D')]
            effects[kind]=dict(observation_effect=(c+d-a-b)/2,action_effect=(b+d-a-c)/2,interaction=d-c-b+a)
            e=effects[kind];rows.append(f"| {kind} | {100*e['observation_effect']:+.1f} | {100*e['action_effect']:+.1f} | {100*e['interaction']:+.1f} |")
        write(OUT/'factorial_effects.json',dict(training_seed=1,effects=effects,interpretation='descriptive only; min_max action transformation nearly identity'))
        rows+=['']
        dc={c['variant']:c for c in cells if c['model_class']=='diffusion' and c['training_seed']==1}
        rows+=['Diffusion-Diagnosen für Seed 1: '+ '; '.join(f"{v}: XY/Expert {dc[v]['offline']['xy_over_expert']['q'][2]:.1%}, Ziel-Cosinus {dc[v]['offline']['goal_cosine']['mean']:.3f}, Transport {dc[v]['rollout']['counts']['transport_started']}/40, Position {dc[v]['rollout']['counts']['position']}/40, Release {dc[v]['rollout']['counts']['release']}/40" for v in ('A','B','C','D'))+'. Verbesserungen dieser Teilindikatoren zeigen einen Einfluss auf die Steuerung; sie ersetzen den Nachweis stabiler Stacks über mehrere Trainingsseeds nicht.','', 'Vor Auswertung der neuen Läufe wurde die Erweiterungsschwelle auf mindestens 8/40 stabile Diffusion-Stacks (20 Prozentpunkte über der Baseline) festgelegt. Jeder qualifizierte Arm wird für beide Modellklassen mit Seeds 2 und 3 wiederholt.','']
        qualified=[v for v in VARIANTS if seed1[v,'diffusion']>=8]
        if qualified:
            details=[];robust_variants=[];replication_complete=True
            for v in qualified:
                ss=[c for c in cells if c['variant']==v and c['model_class']=='diffusion']
                nums=[c['rollout']['counts']['sustained_success'] for c in ss];details.append(f"{v}: {', '.join(str(x)+'/40' for x in nums)}")
                replication_complete &= len(ss)==3
                if len(ss)==3 and min(nums)>=8:robust_variants.append(v)
            verdict='unterstützt' if robust_variants else 'offen (Seed-1-Verbesserung nicht durchgehend repliziert)' if replication_complete else 'offen (positive Seed-1-Befunde, Replikation läuft)'
            rows += [f"**Skalierungshypothese: {verdict}.** {'; '.join(details)} gegenüber 0/40 in allen drei unnormalisierten Diffusion-Seeds. Da B nahezu die Identität ist, betrifft eine C/D-Verbesserung primär die Zentrierung und Skalierung der Observations. Die sieben Action-Varianzen wurden durch Min-Max praktisch nicht verändert.", '', 'Die fehlende Observation-Normalisierung kann den ursprünglichen Nullerfolg unter dieser Architektur und diesem festen Trainingsbudget als kontrolliert veränderte Ursache erklären, sofern die Verbesserung über Seeds bestehen bleibt. Sie erklärt damit keine allgemeine Unterlegenheit von Diffusion und trennt Zentrierung nicht von Skalierung.']
        else:rows += [f"**Skalierungshypothese: offen; durch diesen Versuch nicht unterstützt.** Diffusion Seed 1: B {seed1['B','diffusion']}/40, C {seed1['C','diffusion']}/40, D {seed1['D','diffusion']}/40. Keine Variante erreicht die vorab festgelegte Schwelle von 8/40; daher keine zusätzlichen Seeds. Die fehlende native Normalisierung erklärt den ursprünglichen 0%-Befund anhand dieses Versuchs nicht überzeugend. Eine starke Hypothese, nach der Standard-Observation-Normalisierung allein das Versagen behebt, wird damit geschwächt. Eine andere Action-Varianzskalierung bleibt ungetestet, weil B nahezu identisch ist."]
        rows+=['',f"**Direct verändert sich ebenfalls:** A Seed 1 {seed1['A','direct']}/40; B {seed1['B','direct']}/40; C {seed1['C','direct']}/40; D {seed1['D','direct']}/40. Bei nur einem Seed pro nicht repliziertem Arm beschreibt dieser Unterschied den beobachteten Lauf; er ist keine belastbare Schätzung des mittleren Effekts."]
        repeated=[(v,k,[c['rollout']['counts']['sustained_success'] for c in cells if c['variant']==v and c['model_class']==k]) for v in ('A','B','C','D') for k in ('direct','diffusion')]
        rows+=['','Replikate je Variante:','']
        for v,k,nums in repeated:
            if len(nums)>1:rows.append(f"- {v}/{k}: {', '.join(str(x)+'/40' for x in nums)}; Mittel {np.mean(nums)/40:.1%}, Stichproben-SD {np.std(nums,ddof=1)/40*100:.1f} Prozentpunkte.")
    rows+=['','Die Trainingsseeds sind die unabhängigen Replikate. Die 40 gepaarten Starts und Offline-Rausch-Samples sind keine zusätzlichen Trainingsreplikate. Keine Signifikanzbehauptungen; insbesondere kleine Unterschiede zwischen C und D können bei nahezu identischer Action-Transformation durch empfindliche Optimierungsdynamik entstehen. Die Laufzeiten wurden auf dem vorhandenen Desktop erfasst; GPU-Auslastung durch andere Prozesse und Dateisystem-I/O waren nicht isoliert. Sie sind Aufwandsmessungen, keine kontrollierten Geschwindigkeitsvergleiche.','', '## Abbrüche','']
    rows += [f"- {r['variant']}/{r['model_class']}/Seed {r['training_seed']}, {r['stage']}: `{r['cause'].splitlines()[-1]}`" for r in failures] or ['Keine dokumentierten Abbrüche. Jeder Update prüft endlichen Loss und Gradienten vor Optimizer.step; jeder Rollout prüft endliche Actions, ursprüngliche Controllergrenzen und korrekte Denormalisierung.']
    rows+=['','## Artefakte','', '- `results_normalization.json`: Einzelwerte der Rollouts, Offline-Frames, Grenzpaare und Onsets sowie Protokoll und Kanalstatistiken.','- `summary.csv`, `rollout_metrics.csv`, `offline_metrics.csv`, `boundary_metrics.csv`, `onset_metrics.csv`, `training_losses.csv`, `channel_statistics.csv`.','- Pro Lauf: unveränderte Modellkonfiguration plus Normalisierungsschalter, finaler Checkpoint, Initialisierungshash, Trainingsaudit, Offline-Chunks, Rollout-Zustände und Actions als NPZ, Zeit- und Verifikationsdateien.','- `verification.json` und `hashes.json`: Update-/Scheduler-/EMA-Zähler, Baseline-Vergleich, Daten-/Startzustandskontrollen, SHA-256. Finalcheckpoint bleibt erhalten; Intermediate- und doppelte Resume-Checkpoints werden nach Hashsicherung aus Platzgründen entfernt.','- `replication_decision.json`: vorab festgelegte Erweiterungsschwelle und qualifizierte Varianten.']
    from plots import make
    make(cells)
    rows+=['','Zusätzliche Nachweise: `channel_distributions.csv/json` enthält alle Roh- und transformierten Kanalstatistiken getrennt für Train/Valid; `environment_frozen.txt` hält die Paketversionen fest. Bei Abbrüchen bleiben vorhandene Teil-Losses und abgeschlossene Einzelrollouts separat erhalten und werden nicht als vollständige 40er-Auswertung interpretiert.','',f'![Erfolg je Normalisierungszelle und Trainingsseed](<{(OUT/"normalization_success.png").as_posix()}>)','', f'![Standardabweichung der sieben Action-Kanäle](<{(OUT/"action_channel_std.png").as_posix()}>)']
    rows=[r.replace('EMA 0,75.','EMA-Power 0,75.').replace('**Skalierungshypothese: offen; durch diesen Versuch nicht unterstützt.**','**Skalierungshypothese: offen; als hinreichende Erklärung des Stack-Versagens nicht unterstützt.**') for r in rows]
    (OUT/'results_normalization.md').write_text('\n'.join(rows)+'\n',encoding='utf-8')
    print(json.dumps(table,indent=2))
if __name__=='__main__':main()
