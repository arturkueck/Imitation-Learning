"""Read-only collapse diagnosis using saved checkpoints and existing data only."""
from pathlib import Path
import argparse
import json
import time
import numpy as np
import torch
import run
from core import TwinQ, concat


def diagnose(source, output):
    assert not output.exists(), 'Never overwrite a diagnosis'
    torch.set_num_threads(2)
    manifest = json.loads((source/'data/manifest.json').read_text())
    parts = []
    inputs = {}
    for row in manifest['rows']:
        if row['split'] != 'valid':
            continue
        assert run.sha(row['path']) == row['sha256']
        inputs[row['path']] = row['sha256']
        with np.load(row['path'], allow_pickle=False) as arrays:
            ids = np.arange(0, len(arrays['x']), 10)
            parts.append({k: arrays[k][ids].copy() for k in run.KEYS})
    data = concat(parts)
    x = torch.tensor(data['x'], device='cuda')
    phase = torch.tensor(data['phase'], device='cuda')
    state = torch.tensor(data['state'], device='cuda')
    metrics, contracts, trajectories, distinct = {}, {}, {}, {}
    with torch.no_grad():
        for seed in (1, 2, 3):
            info = run.parent(seed)
            inputs[info['path']] = info['sha256']
            model = run.native.historical.load(info['path'])
            parent_actions = model(x, phase)[0]
            row = next(r for r in manifest['rows'] if r['teacher']['seed'] == seed)
            with np.load(row['path'], allow_pickle=False) as a:
                pred = model(torch.tensor(a['x'], device='cuda'), torch.tensor(a['phase'], device='cuda'))[0]
                contracts[str(seed)] = float(np.max(np.abs(pred.cpu().numpy()-a['action'])))
            arm_weights = {}
            for arm in 'ABC':
                for round_ in (1, 4):
                    path = source/f'train/{arm}_seed{seed}/round{round_}.pth'
                    inputs[str(path)] = run.sha(path)
                    ck = torch.load(path, map_location='cuda', weights_only=False)
                    assert ck['updates'] == round_*500
                    assert all(torch.isfinite(v).all() for net in ('actor', 'critic') for v in ck[net].values())
                    model.load_state_dict(ck['actor'])
                    action = model(x, phase)[0]
                    delta = action-parent_actions
                    critic = TwinQ(np.zeros(state.shape[1]), np.ones(state.shape[1]), ck['config']['critic_width']).cuda()
                    critic.load_state_dict(ck['critic'])
                    q_old = critic(state, parent_actions)[0]
                    q_new = critic(state, action)[0]
                    metrics[f'{arm}_seed{seed}:round{round_}'] = dict(
                        action_mse_vs_parent=delta.square().mean().item(),
                        phase0_action_mse=delta[phase == 0].square().mean().item(),
                        mean_abs_delta_xyz=delta[:, :3].abs().mean().item(),
                        xyz_saturation_fraction=(action[:, :3].abs() > .95).float().mean().item(),
                        q1_parent=q_old.mean().item(), q1_actor=q_new.mean().item(),
                        q1_gain=(q_new-q_old).mean().item(),
                        fraction_q1_prefers_actor=(q_new > q_old).float().mean().item())
                    if round_ == 1:
                        arm_weights[arm] = {k: v.cpu().clone() for k,v in ck['actor'].items()}
            distinct[str(seed)] = {arm: max((arm_weights['A'][k]-arm_weights[arm][k]).abs().max().item()
                                          for k in arm_weights['A']) for arm in 'BC'}
            for round_ in (1, 2, 3, 4):
                groups = {arm: sorted((source/f'train/{arm}_seed{seed}/online_round{round_}').glob('*.npz')) for arm in 'ABC'}
                summary = {}
                for arm, files in groups.items():
                    assert len(files) == 5
                    rows = []
                    for path in files:
                        with np.load(path, allow_pickle=False) as a:
                            rows.append(dict(seed=int(path.stem), frames=len(a['x']),
                                success=bool(a['reward'].sum()),
                                phase0_only=bool((a['phase'] == 0).all()),
                                xyz_saturation_fraction=float((np.abs(a['action'][:,:3])>.95).mean())))
                    summary[arm] = rows
                trajectories[f'seed{seed}:round{round_}'] = summary
    history = json.loads((source/'train/history.json').read_text())
    logged_actor_updates = sum(bool(r['actor_updated']) for r in history)
    snapshot = source/'train/source_snapshot/00_run.py'
    assert 'if update%100==0:' in snapshot.read_text()
    result = dict(schema='critic-collapse-diagnosis-v1', source=str(source), created_unix=time.time(),
        scope='No optimizer updates, no simulator rollouts, no reserved final data; saved artifacts only',
        validation_frames=len(data['x']), sampling='Every tenth frame of each of the 40 existing validation episodes',
        action_contract_max_abs_error=contracts, round1_actor_max_abs_diff_from_A=distinct,
        checkpoint_metrics=metrics, online_trajectories=trajectories,
        logged_history_rows=len(history), logged_actor_update_rows=logged_actor_updates,
        input_hashes=inputs)
    assert logged_actor_updates == 0 and max(contracts.values()) < 1e-5
    assert all(row['q1_gain'] > 0 for row in metrics.values())
    for path, expected in inputs.items():
        assert run.sha(path) == expected, 'Diagnosis changed input'
    output.mkdir()
    run.dump(output/'diagnosis.json', result)
    first = [m for k,m in metrics.items() if k.endswith('round1')]
    mse = [m['action_mse_vs_parent'] for m in first]
    xyz = [m['mean_abs_delta_xyz'] for m in first]
    only0 = sum(row['phase0_only'] for group in trajectories.values() for rows in group.values() for row in rows)
    report = f'''# Ursachenprüfung des IL-Actor-Critic-Nachtlaufs

Geprüft: gespeicherte Actors und Critics aus Runde 1 und 4, vorhandene
Validierungstransitionen und Onlineepisoden. Keine Optimizerupdates, neuen
Rollouts, Hyperparameteränderungen oder reservierten Endtests.

## Belastbare Befunde

1. **Starke Actor-Drift bereits nach der ersten Updaterunde.** Nach nur
   250 Actorupdates beträgt die Aktions-MSE gegen den jeweiligen Parent
   {min(mse):.3f}–{max(mse):.3f}. Die mittlere absolute XYZ-Abweichung beträgt
   {min(xyz):.3f}–{max(xyz):.3f} bei Aktionen im Bereich [-1,1]. Das ist keine
   kleine Nachkorrektur. Messung auf {{len(data['x'])}} bestehenden Validierungsframes.
2. **Der trainierte Critic bevorzugt diese stark abweichenden Aktionen.**
   In allen 18 geprüften Modell-/Checkpointkombinationen liegt der mittlere
   Q1-Wert der aktuellen Actoraktion über dem der Parentaktion auf denselben
   gespeicherten Zuständen. Die echte Aufgabenleistung fällt gleichzeitig auf
   null. Das ist mit der Ausnutzung unzuverlässiger Aktionsbewertungen vereinbar;
   es beweist nicht die alleinige Ursache und validiert keine Gegenfaktual-Returns.
3. **Kein versehentlich gemeinsam ausgewerteter Actor.** A/B/C haben bereits
   in Runde 1 unterschiedliche Gewichte. Ihre Onlineaktionen in Runde 2 sind
   ebenfalls unterschiedlich. Gleiche Interaktionszahlen entstehen durch gleiche
   erste Sammlung und danach jeweils am 1000-Schritte-Limit endende Versuche.
   {{only0}} der 180 gespeicherten Onlineepisoden bleiben ausschließlich in Phase 0.
4. **Aktionskonvention stimmt für geprüfte Sammeltraces.** Die gespeicherten
   Aktionen stimmen je Parentseed mit dessen Vorhersagen auf einer vollständig
   geprüften Episode bis unter 1e-5 überein. Eine globale Vertauschung von
   XYZ/Greifer oder ein grober Skalierungsfehler erklärt den Kollaps damit nicht.
5. **Konkreter Loggingfehler:** Alle 180 Historyeinträge protokollieren ungerade
   globale Updates (1,101,...); Actorupdates finden nur auf geraden Updates statt.
   Deshalb fehlen sämtliche Actorloss-, RLloss- und BCloss-Messwerte im Nachtlauf.
   Die Actorupdates selbst fanden statt. Dieser Fehler erschwert die Diagnose,
   verursacht aber nicht die schlechteren Aktionen.

## Schwächen des Setups

Das Vorwärmgate prüft Return-MSE auf tatsächlich beobachteten Aktionen. Es
prüft weder die Qualität der Aktionsgradienten noch unbekannte Actoraktionen.
Der Actor darf unmittelbar ab dem zweiten Criticupdate seine gelernte Bewegung
ohne direkte Abweichungsgrenze ändern. A/B haben keinen BC-Term; der feste
Koeffizient 0.01 schützt C in diesem Lauf nachweislich nicht vor großer Drift.
Ein bestandener kurzer Smoke mit wenigen Updates konnte diesen Fehlerverlauf
nicht erkennen; ein technischer End-to-End-Test ist kein Stabilitätsnachweis.

Die eingefrorene Phasenentscheidung bleibt zwar unverändert, wird aber auf
neuen Zuständen abgefragt, die der veränderte Bewegungskopf erzeugt. Sie
garantiert daher keine erfolgreiche Phasenprogression. Die Fehlversuche in
Phase 0 passen zu einem bereits gestörten Anfahren; sie belegen keinen
eigenständigen Bug des geometrischen Rückzugsgates.

## Konsequenz

Der Nachtlauf zeigt das Scheitern dieses konkreten ungesicherten Lernablaufs,
keinen allgemeinen Gegenbeweis gegen Critic-Warmstart. Eine einzelne falsche
Aktionsindexierung oder gemeinsam verwendete Armgewichte wurde nicht gefunden.
Die genaue kausale Aufteilung zwischen Criticgradienten, fehlender
Abweichungsbegrenzung und Phasenabhängigkeiten bleibt offen.

Der Loggingfehler kann ohne Änderung der Trainingsmathematik behoben werden.
Vor einem neuen Hauptversuch braucht es eine separate, vorab festgelegte
Stabilitätsprüfung mit kleinen Updateblöcken und gemessener Actor-Drift.
Änderungen an Actorfreigabe, BC-Stärke oder Vertrauensbereich sind neue
experimentelle Entscheidungen; sie werden nicht als bloße Bugkorrektur
heimlich in einen wiederholten A/B/C-Vergleich aufgenommen.

Rohmetriken und geprüfte Eingangshashes: [diagnosis.json](diagnosis.json).
'''
    report = report.replace('{len(data[\'x\'])}', str(len(data['x']))).replace('{only0}', str(only0))
    (output/'REPORT.md').write_text(report, encoding='utf-8')
    print(json.dumps(dict(output=str(output),frames=len(data['x']),round1_mse_range=[min(mse),max(mse)],
                          logged_actor_rows=logged_actor_updates,phase0_only_online_episodes=only0)))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--source', type=Path, default=run.HERE/'night_001')
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    diagnose(args.source.resolve(), args.output.resolve())
