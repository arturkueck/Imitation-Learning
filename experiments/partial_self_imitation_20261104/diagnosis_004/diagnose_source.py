"""Read-only diagnosis of collector train/valid data. Never opens endtests/models."""
from pathlib import Path
import argparse
import collections
import hashlib
import json
import shutil
import time
import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
RUN=HERE/'run_001'
HIST=ROOT/'experiments/stack_transition_quality_20261024/native_data_v1/manifest.json'


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
    return h.hexdigest()


def dump(path,obj):
    path.write_text(json.dumps(obj,indent=2,ensure_ascii=False),encoding='utf-8')


def first_run(mask,length):
    run=0
    for j,v in enumerate(mask):
        run=run+1 if v else 0
        if run>=length:return j
    return None


def max_run(mask):
    run=best=0
    for v in mask:
        run=run+1 if v else 0;best=max(best,run)
    return best


def phase_name(a,j):
    if a['retreat'][j]:return 'retreat'
    return {0:'approach',1:'descend_to_source',2:'close_gripper',3:'lift',
            4:'transport',5:'descend_to_target',6:'release_wait'}[int(a['p'][j])]


def stage_progress(a,stage):
    pos=a['post_obs'][:,:9].reshape(-1,3,3)
    active=(a['stage']==stage)&~a['retreat'].astype(bool)
    source=stage;target=stage-1
    ids=np.flatnonzero(active)
    if not len(ids):return dict(attempted=False,held=False,lifted=False,transported=False,drop_after_lift=False)
    initial_z=a['pre_obs'][ids[0],source*3+2]
    held=a['held_post'][:,source].astype(bool)&a['held_known'].astype(bool)
    lifted=first_run(active&held&(pos[:,source,2]>=initial_z+.03),5)
    transported=first_run(active&held&(a['p']>=4)&
        (pos[:,source,2]>=initial_z+.03)&
        (np.linalg.norm(pos[:,source,:2]-pos[:,target,:2],axis=1)<=.03),5)
    drop=False
    if lifted is not None:
        # Descriptive loss of a grasp before release, not proof of a collision.
        after=(np.arange(len(active))>lifted)&active&(a['p']<=5)&~held
        drop=first_run(after,5) is not None
    return dict(attempted=True,held=first_run(active&held,5) is not None,
        lifted=lifted is not None,lift_frame=lifted,transported=transported is not None,
        transport_frame=transported,drop_after_lift=drop,
        final_phase=int(a['p'][ids[-1]]),active_frames=int(active.sum()))


def first_pair_rejection(a):
    events=np.flatnonzero(a['controller_event']==1)
    if not len(events):return 'no_release_event'
    j=int(events[0]);n=len(a['x'])
    if j<9 or j+50>=n:return 'missing_confirmation_frames'
    valid=a['prefix_valid'][j-9:j+51,0]
    contact=a['fingers'][j-9:j+51,:2].any()
    if not valid.all():return 'prefix_interrupted_with_contact' if contact else 'prefix_interrupted_without_contact'
    if contact:return 'tower_contact'
    if not (a['stage'][:j+1]==1).all() or a['retreat'][:j+1].any():return 'earlier_controller_transition'
    return 'accepted'


def transition_metrics(a,release):
    events=np.flatnonzero((a['controller_event']==2)&(np.arange(len(a['x']))>release))
    if not len(events):return None
    switch=int(events[0]);first=switch+1
    if first>=len(a['x']):return None
    obs=a['pre_obs'][first];top=obs[3:6];eef=obs[9:12]
    return dict(switch_frame=switch,retreat_frames=int(a['retreat'][release+1:switch+1].sum()),
        next_approach_eef_above_top_surface_m=float(eef[2]-top[2]-.02),
        next_approach_eef_xy_to_top_m=float(np.linalg.norm(eef[:2]-top[:2])),
        retreat_end_completion_probability=float(a['prob'][switch]),
        retreat_eef_height_gain_m=float(a['post_obs'][switch,11]-a['pre_obs'][release+1,11]),
        next_approach_head_phase=int(a['p'][first]))


def diagnose_episode(a,row):
    assert row['split'] in ('train','valid') and row['count']==3
    assert a['x'].shape==(len(a['x']),10)
    assert a['held_post'].shape==(len(a['x']),3)
    assert np.array_equal(a['post_obs'][:-1],a['pre_obs'][1:])
    success=max_run(a['valid'])>=50
    assert success==row['success']
    first,second=stage_progress(a,1),stage_progress(a,2)
    events=np.flatnonzero(a['controller_event']==1)
    release=int(events[0]) if len(events) else None
    if success:category='success'
    elif release is None:
        category=('first_pickup_not_confirmed' if not first['held'] else
                  'first_lift_not_confirmed' if not first['lifted'] else
                  'first_transport_not_confirmed' if not first['transported'] else
                  'first_placement_not_confirmed')
    elif not second['attempted']:category='retreat_without_next_pair'
    elif not second['held']:category='second_pickup_not_confirmed'
    elif not second['lifted']:category='second_lift_not_confirmed'
    elif not second['transported']:category='second_transport_not_confirmed'
    else:category='final_placement_or_stability_not_confirmed'
    result=dict(seed=row['seed'],split=row['split'],source=row['path'],success=success,
        teacher_sha256=row['teacher_sha256'],frames=len(a['x']),category=category,
        first_stage=first,second_stage=second,release_frame=release,
        first_pair_section_gate=first_pair_rejection(a),
        max_full_valid_run=max_run(a['valid']),max_first_pair_valid_run=max_run(a['prefix_valid'][:,0]),
        max_phase_steps=int(a['phase_steps'].max()),
        final_stage=int(a['stage'][-1]),final_phase=int(a['p'][-1]))
    if release is not None:
        result['transition']=transition_metrics(a,release)
        start=release+1;valid=a['prefix_valid'][start:,0].astype(bool)
        bad=np.flatnonzero(~valid)
        result['after_release']=dict(prefix_ever_invalid=bool(len(bad)),
            max_invalid_run=max_run(~valid),regained_ten_valid_frames=False)
        if len(bad):
            j=start+int(bad[0]);pos=a['post_obs'][j,:9].reshape(3,3)
            speeds=a['velocities'][j].reshape(3,6)
            result['after_release'].update(first_invalid_frame=j,
                first_invalid_delay_after_release_frames=j-release,
                first_invalid_action=phase_name(a,j),first_invalid_stage=int(a['stage'][j]),
                first_invalid_tower_contact=bool(a['fingers'][j,:2].any()),
                first_invalid_cube_contact_missing=not bool(a['contacts'][j,0]),
                first_invalid_tower_held=bool(a['held_post'][j,:2].any()),
                first_invalid_pair_xy_m=float(np.linalg.norm(pos[1,:2]-pos[0,:2])),
                first_invalid_height_error_m=float(abs(pos[1,2]-pos[0,2]-.04)),
                first_invalid_max_linear_speed=float(np.linalg.norm(speeds[:2,:3],axis=1).max()),
                first_invalid_max_angular_speed=float(np.linalg.norm(speeds[:2,3:],axis=1).max()),
                regained_ten_valid_frames=first_run(a['prefix_valid'][j+1:,0],10) is not None)
    return result


def sampling_audit(audit):
    sections=[s for s in audit['successful_sections']+audit['failed_sections'] if s['split']=='train']
    failed={s['source'] for s in audit['failed_sections'] if s['split']=='train'}
    phases={}
    for path in {s['source'] for s in sections}:
        with np.load(path,allow_pickle=False) as f:phases[path]=f['p'].copy()
    groups={}
    for s in sections:
        p=phases[s['source']];ids=np.arange(s['start'],s['end'])
        for phase in np.unique(p[ids]):
            group=groups.setdefault(int(phase),{}).setdefault(s['source'],[])
            group.append((s,ids[p[ids]==phase]))
    keys=sorted(groups);per_seed={}
    expected=np.mean([sum(p in failed for p in groups[k])/len(groups[k]) for k in keys])
    for seed in (1,2,3):
        count=0;effective=0.;families=collections.Counter();kinds=collections.Counter();phasecounts=collections.Counter()
        for update in range(1,5001):
            rng=np.random.default_rng(np.random.SeedSequence([seed,update,1]));draws=[]
            for _ in range(16):
                phase=keys[int(rng.integers(len(keys)))];paths=sorted(groups[phase])
                path=paths[int(rng.integers(len(paths)))];choices=groups[phase][path]
                s,ids=choices[int(rng.integers(len(choices)))];rng.choice(ids)
                isfailed=path in failed;draws.append((isfailed,s['weight']))
                if isfailed:
                    count+=1;families[path]+=1;kinds[s['kind']]+=1;phasecounts[phase]+=1
            effective+=sum(w for fail,w in draws if fail)/sum(w for _,w in draws)
        per_seed[str(seed)]=dict(failed_draws=count,own_draws=80000,total_actor_examples=320000,
            fraction_own=count/80000,fraction_all=count/320000,
            normalized_D_loss_share=.25*effective/5000,
            distinct_failed_families=len(families),draws_by_kind=dict(kinds),draws_by_phase=dict(phasecounts))
    weights=np.array([s['weight'] for s in sections])
    return dict(expected_failed_fraction_own=float(expected),expected_failed_fraction_all=float(.25*expected),
        exact_reconstructed_C_D_draws=per_seed,
        section_weights=dict(min=float(weights.min()),max=float(weights.max()),mean=float(weights.mean()),std=float(weights.std())),
        method='Reconstructs only deterministic phase/episode/section/frame sampler RNG; no model or test files opened.')


def summarize(rows):
    result={}
    for split in ('train','valid'):
        cohort=[r for r in rows if r['split']==split];fail=[r for r in cohort if not r['success']]
        release=[r for r in fail if r['release_frame'] is not None]
        loss=[r for r in release if r['after_release']['prefix_ever_invalid']]
        result[split]=dict(episodes=len(cohort),successes=len(cohort)-len(fail),failures=len(fail),
            failure_categories=dict(collections.Counter(r['category'] for r in fail)),
            failed_with_first_release=len(release),failed_with_prefix_loss=len(loss),
            first_prefix_loss_action=dict(collections.Counter(r['after_release']['first_invalid_action'] for r in loss)),
            first_prefix_loss_contact=sum(r['after_release']['first_invalid_tower_contact'] for r in loss),
            first_prefix_loss_stage=dict(collections.Counter(r['after_release']['first_invalid_stage'] for r in loss)),
            first_prefix_loss_speed_exceeded=sum(r['after_release']['first_invalid_max_linear_speed']>.03 for r in loss),
            first_prefix_loss_rotation_exceeded=sum(r['after_release']['first_invalid_max_angular_speed']>.3 for r in loss),
            first_prefix_loss_xy_exceeded=sum(r['after_release']['first_invalid_pair_xy_m']>.009 for r in loss),
            first_prefix_loss_missing_cube_contact=sum(r['after_release']['first_invalid_cube_contact_missing'] for r in loss),
            prefix_loss_regained=sum(r['after_release']['regained_ten_valid_frames'] for r in loss),
            failed_with_first_lift=sum(r['first_stage']['lifted'] for r in fail),
            failed_with_second_lift=sum(r['second_stage']['lifted'] for r in fail),
            first_pair_section_rejection=dict(collections.Counter(r['first_pair_section_gate'] for r in fail)))
        result[split]['transition_cohorts']={}
        for success in (False,True):
            tr=[r['transition'] for r in cohort if r['success']==success and r.get('transition')]
            if tr:
                result[split]['transition_cohorts']['success' if success else 'failure']=dict(n=len(tr),
                    retreat_one_frame=sum(t['retreat_frames']==1 for t in tr),
                    retreat_frames_quantiles=np.quantile([t['retreat_frames'] for t in tr],[0,.5,1]).tolist(),
                    retreat_height_gain_mm_quantiles=np.quantile([1000*t['retreat_eef_height_gain_m'] for t in tr],[0,.5,1]).tolist(),
                    next_approach_clearance_mm_quantiles=np.quantile([1000*t['next_approach_eef_above_top_surface_m'] for t in tr],[0,.5,1]).tolist(),
                    next_approach_clearance_below20mm=sum(t['next_approach_eef_above_top_surface_m']<.02 for t in tr))
    return result


def main(output):
    output.mkdir(parents=True,exist_ok=False)
    shutil.copy2(Path(__file__),output/'diagnose_source.py')
    manifests=[HIST,RUN/'input/manifest.json'];auditpath=RUN/'dataset_audit.json'
    hashes={str(p):sha(p) for p in manifests+[auditpath]}
    audit=json.loads(auditpath.read_text())
    rows=[]
    for p in manifests:
        m=json.loads(p.read_text());assert m['complete']
        rows.extend(r for r in m['rows'] if r['count']==3)
    assert len(rows)==340 and set(r['split'] for r in rows)=={'train','valid'}
    # Explicit allowlist precludes accidentally opening final rollout directories.
    allowed=[(HIST.parent/'n3').resolve(),(RUN/'input').resolve()]
    reports=[];family_splits={}
    fields=('x','pre_obs','post_obs','p','stage','retreat','held_post','held_known',
            'prefix_valid','valid','controller_event','fingers','contacts','velocities','phase_steps','prob')
    for r in rows:
        p=Path(r['path']).resolve();assert p.parent in allowed and r['split'] in ('train','valid')
        assert family_splits.setdefault(r['initial_sha256'],r['split'])==r['split']
        assert sha(p)==audit['sources'][r['path']]==r['sha256']
        with np.load(p,allow_pickle=False) as f:a={k:f[k].copy() for k in fields}
        reports.append(diagnose_episode(a,r))
    summary=summarize(reports);sampling=sampling_audit(audit)
    transition_cohorts=[r for s in summary.values() for r in s['transition_cohorts'].values()]
    one_frame=sum(r['retreat_one_frame'] for r in transition_cohorts)
    switched=sum(r['n'] for r in transition_cohorts)
    dump(output/'episodes.json',reports)
    dump(output/'summary.json',dict(cohorts=summary,sampling=sampling,
        definitions=dict(held='5 consecutive native-grasp frames',lift='5 held frames >=30mm above source initial stage height',
            transport='5 held+lifted frames, phase>=4, source XY <=30mm from target; descriptive diagnostic only',
            release='Existing sequencer event1 after10 contact-free valid prefix frames',
            category='Furthest observed milestone, not a causal attribution',prefix_loss='First invalid post-action prefix state after release; contact alone can invalidate'),
        scope='Collector train/valid data only. No trained-arm rollout comparison, final-test inspection, model training or simulator replay.'))
    lines=['# Fehlerdiagnose: Trainings- und Validierungsrollouts','',
        '340 eingefrorene Dreierturm-Sammelversuche (240 Train, 100 Valid). Keine Endtestdatei gelesen. Keine Modelle oder Simulatoren geladen. Alle verwendeten Rohdaten vorab per SHA-256 geprüft.','',
        '## Wichtigste Befunde','',
        f'- In {one_frame}/{switched} Episoden mit Paarwechsel endet der markierte Rückzug nach genau einem Steuerframe (20 Hz:50 ms). Das tritt auch bei Erfolgen auf und ist für sich kein kausaler Fehlernachweis.',
        '- Bei gescheiterten Episoden mit erster bestätigter Ablage verliert das untere Präfix in97/98 Train- und43/44 Valid-Episoden später seine Gültigkeit. Sämtliche ersten Verletzungen liegen nach dem Paarwechsel in Bauabschnitt2; am häufigsten im Anflug auf den nächsten Quellwürfel.',
        '- Die akzeptierten Fehlversuchabschnitte machen nur1.28–1.29% aller C-Actorbeispiele aus. Ihr Anteil an den Actor-Loss-Koeffizienten beträgt bei D1.31–1.32%. Das ist keine Messung ihrer tatsächlichen Fehler- oder Gradientenwirkung. Der bisherige Pilot setzt diesen Teil der Idee daher nur schwach ein.',
        '- Priorität: Rückzugsabschluss und Anflugkorridor getrennt auf frischen Entwicklungsfamilien prüfen. Eine Erweiterung der Policyeingaben ist noch kein belegter Reparaturbedarf.','',
        '## Beobachteter Fortschritt','',
        'Die Kategorien beschreiben den am weitesten erreichten bestätigten Meilenstein. Sie beweisen keine Ursache. „Transport“ ist eine zusätzliche Diagnoseheuristik (fünf gehaltene/angehobene Frames innerhalb 30 mm XY zum Ziel, Phase≥4), keine nachträgliche Erfolgsdefinition.','',
        '| Kategorie | Train | Valid |','|---|---:|---:|']
    categories=sorted(set(summary['train']['failure_categories'])|set(summary['valid']['failure_categories']))
    for k in categories:lines.append(f"| {k} | {summary['train']['failure_categories'].get(k,0)} | {summary['valid']['failure_categories'].get(k,0)} |")
    lines+=['',f"Train: {summary['train']['successes']}/240 erfolgreich; Valid: {summary['valid']['successes']}/100 erfolgreich.",'',
        '## Unterer Turm nach erster Freigabe','',
        '| Beobachtung, nur gescheiterte Episoden | Train | Valid |','|---|---:|---:|']
    for key in ('failed_with_first_release','failed_with_prefix_loss','first_prefix_loss_contact','prefix_loss_regained','failed_with_first_lift','failed_with_second_lift'):
        lines.append(f"| {key} | {summary['train'][key]} | {summary['valid'][key]} |")
    lines+=['','Die Bezugsgrößen unterscheiden sich: Freigabe/Lift beziehen sich auf alle Fehlschläge; erste Kontaktverluste und Wiedererholung auf Episoden mit Präfixverlust. Ein ungültiger Präfixframe ist kein nachgewiesener Einsturz. Einseitiger Fingerkontakt, Geschwindigkeitsgrenzen oder kurzzeitiger Kontaktverlust können ebenfalls auslösen.','',
        'Erste Präfixverletzung nach ausgeführter Aktionsphase (Mehrfachzählungen ausgeschlossen):','',
        '| Aktionsphase | Train | Valid |','|---|---:|---:|']
    for k in sorted(set(summary['train']['first_prefix_loss_action'])|set(summary['valid']['first_prefix_loss_action'])):
        lines.append(f"| {k} | {summary['train']['first_prefix_loss_action'].get(k,0)} | {summary['valid']['first_prefix_loss_action'].get(k,0)} |")
    lines+=['','Alle ersten Präfixverletzungen gescheiterter Episoden mit Verlust treten in Bauabschnitt2 auf, nicht während des als `retreat` markierten Rückzugs. Die schnell folgende Anflugbewegung ist deshalb der engere Diagnosefokus.','',
        '| Erste Verletzung: gleichzeitig gemessene Merkmale | Train /97 | Valid /43 |','|---|---:|---:|']
    for key in ('first_prefix_loss_speed_exceeded','first_prefix_loss_rotation_exceeded','first_prefix_loss_xy_exceeded','first_prefix_loss_missing_cube_contact'):
        lines.append(f"| {key} | {summary['train'][key]} | {summary['valid'][key]} |")
    lines+=['','Merkmale überlappen. An der ersten Verletzung bestehen die Würfelkontakte häufig noch; Geschwindigkeit und Fingerkontakt reagieren früher als ein sichtbarer Geometrieverlust. Das ist keine kausale Kollisionsrekonstruktion.','',
        '## Rückzugsabschluss vor dem nächsten Anflug','',
        'Höhenabstand ist Greiferreferenzpunkt minus Oberfläche des oberen unteren Turmwürfels. Das ist kein geometrischer Kollisionsabstand des ganzen Greifers. Quantile: Minimum / Median / Maximum.','',
        '| Split / Ausgang | N mit Paarwechsel | Davon1 Rückzugsframe | Rückzugsframes min/med/max | Höhenabstand [mm] min/med/max |','|---|---:|---:|---|---|']
    for split in ('train','valid'):
        for outcome,r in summary[split]['transition_cohorts'].items():
            lines.append(f"| {split}/{outcome} | {r['n']} | {r['retreat_one_frame']} | {r['retreat_frames_quantiles']} | {[round(v,1) for v in r['next_approach_clearance_mm_quantiles']]} |")
    lines+=['','Im eingefrorenen Sequencer (`run_001/source_snapshot/02_runner.py`, `Sequencer.advance`) wird der normale Anflugkopf für den Rückzug wiederverwendet. Sobald dessen gelernte Phasenentscheidung die Phase0 verlässt, wird ohne zusätzliches Freiraumgate zum nächsten Paar gewechselt. Der normale Phase0-Abschluss ist damit die technische Rückzugsfreigabe. Das erklärt die Einframe-Übergänge im Kontrollfluss; ob ein anderes Gate die Gesamtaufgabe verbessert, benötigt einen separaten Vergleich.','',
        'Die Diagnose verändert diesen Controller nicht. Die gespeicherten Endwahrscheinlichkeiten und Höhengewinne pro Episode stehen in episodes.json. Greiferreferenzpunkt und Würfeloberfläche beschreiben keinen vollständigen Kollisionsabstand.']
    lines+=['','## Warum so wenige übernommene Fehlversuchabschnitte?','',
        '| Erstes Paar: Gate-Ergebnis | Train | Valid |','|---|---:|---:|']
    for k in sorted(set(summary['train']['first_pair_section_rejection'])|set(summary['valid']['first_pair_section_rejection'])):
        lines.append(f"| {k} | {summary['train']['first_pair_section_rejection'].get(k,0)} | {summary['valid']['first_pair_section_rejection'].get(k,0)} |")
    lines+=['','## Tatsächlicher Trainingsanteil der Fehlversuchabschnitte','',
        'Exakte Rekonstruktion der vorhandenen C/D-Sampler für je5000 Updates. Die Gewichte ändern den Loss, nicht die Auswahl.','',
        '| Parentseed | Fehlversuchbeispiele /80000 eigene | Anteil an allen320000 Actorbeispielen | D: Anteil Actor-Loss-Koeffizienten |','|---|---:|---:|---:|']
    for seed,r in sampling['exact_reconstructed_C_D_draws'].items():
        lines.append(f"| {seed} | {r['failed_draws']} | {100*r['fraction_all']:.2f}% | {100*r['normalized_D_loss_share']:.2f}% |")
    w=sampling['section_weights'];lines+=['','Die D-Spalte und das JSON-Feld normalized_D_loss_share beschreiben ausschließlich die summierten normierten Actor-Loss-Koeffizienten, nicht den Anteil an tatsächlichem Loss oder Gradienten; letzterer hängt zusätzlich von den Fehlerwerten ab.',
        '',f"Qualitätsgewichte aller eigenen Trainingsabschnitte: min={w['min']:.4f}, max={w['max']:.4f}, Standardabweichung={w['std']:.4f}. Dies ist die Verteilung pro Abschnitt, nicht pro gesampeltem Frame.",'',
        '## Grenzen und nächste Entscheidung','',
        'Die aktuelle Policy sieht laut eingefrorenem method.py nur10 Werte: Greifer relativ zu gecachtem Anker(3), Greiferorientierung(4), Fingerstellung(2), Phasenzeit(1). Phase wählt einen separaten Kopf. Explizite restliche Turmgeometrie, aktuelle Objektpose und nativer Griffstatus fehlen. Diese Eingabenbeschränkung ist belegt; dass sie den konkreten Fehler verursacht, ist damit nicht nachgewiesen.','',
        'Der nächste gezielte Versuch sollte den Übergang vom platzierten Zweierturm zum Anflug auf Würfel3 untersuchen. Auf frischen Entwicklungsfamilien Abschluss des wiederverwendeten Rückzugskopfs, Greiferfreiraum und nächsten Bewegungskorridor instrumentieren. Erst bei nachgewiesener vorzeitiger Freigabe den Controller separat vergleichen; bei nicht unterscheidbaren Gefahrenzuständen die Turmeingaben separat ergänzen. Architektur, Controller und Datenstrategie nicht gleichzeitig ändern.','',
        'Die strengen bisherigen Aufnahmegates bleiben unverändert. Frühere gute Greif-/Anhebeabschnitte werden durch diese Diagnose sichtbar, sind aber ohne separat eingefrorene Labels und Prüfung noch keine neuen Trainingsdaten. Die Endtests bleiben für zukünftige Methoden-/Checkpointauswahl gesperrt.','',
        'Maschinenlesbare Details: summary.json und episodes.json; Hashnachweise: provenance.json.']
    (output/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    for r in rows:assert sha(r['path'])==r['sha256'],'Raw source changed during diagnosis'
    for p,h in hashes.items():assert sha(p)==h
    dump(output/'provenance.json',dict(created_unix=time.time(),source_manifests=hashes,
        source_episode_sha256={r['path']:r['sha256'] for r in rows},script_sha256=sha(__file__),
        endtest_access=False,inputs_unchanged=True,episode_count=len(rows)))
    print(json.dumps(dict(summary=summary,sampling=sampling),ensure_ascii=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args();main(args.output.resolve())
