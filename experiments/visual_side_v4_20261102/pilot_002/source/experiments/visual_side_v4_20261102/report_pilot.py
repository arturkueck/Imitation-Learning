"""Summarize actual pilot evidence; extrapolations are explicitly estimates."""
from pathlib import Path
import json,argparse,math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent
def main():
    p=argparse.ArgumentParser();p.add_argument('--name',default='pilot_001');args=p.parse_args();out=HERE/args.name
    r=json.loads((out/'report.json').read_text());rows=[json.loads(x) for x in (out/'families.jsonl').read_text().splitlines()]
    b=r['numerical'];families=list(r['view_families']);attempted=[r['view_families'][f]['attempted'] for f in families];captured=[r['view_families'][f]['captured'] for f in families]
    fig,axes=plt.subplots(1,2,figsize=(11,3.8));axes[0].bar(families,attempted,label='Wünsche',color='#8da1b3');axes[0].bar(families,captured,label='Aufgenommen',color='#20b7c8');axes[0].set(ylabel='Familien',title='Begrenzte Suche: Wunsch und Aufnahme');axes[0].legend();axes[0].tick_params(axis='x',rotation=20)
    axes[1].hist([x['seconds'] for x in rows],bins=20,color='#e6a34f');axes[1].set(xlabel='Sekunden pro Familie',ylabel='Familien',title='Datenerzeugung inkl. Blicksuche/Prüfung');fig.tight_layout();fig.savefig(out/'coverage_and_runtime.png',dpi=150);plt.close(fig)
    measured=b['median_seconds_per_update'];new=30000;scenes_per_epoch=24000;updates_per_epoch=math.ceil(scenes_per_epoch/32)
    estimates={str(epochs):dict(variants=2,seeds=3,epochs=epochs,updates=6*updates_per_epoch*epochs,optimizer_hours=6*updates_per_epoch*epochs*measured/3600) for epochs in [10,20,40]}
    estimates.update(data_generation_same_three_pose_pilot_hours=r['seconds_per_family']*new/3600,
        seven_pose_raw_array_gib=r['raw_array_bytes_per_family']*7/3*new/2**30,
        seven_pose_naive_compressed_gib=r['compressed_bytes_per_family']*7/3*new/2**30,
        caveat='Not an end-to-end quote: full bank search, all seeds, validation, heads, plotting and tests not benchmarked. Compressed storage is a rough extrapolation including duplicate blocked slots.')
    (out/'budget_estimate.json').write_text(json.dumps(estimates,indent=2),encoding='utf-8')
    coverage='\n'.join(f"| {f} | {r['view_families'][f]['attempted']} | {r['view_families'][f]['captured']} |" for f in families)
    costs='\n'.join(f"| {epochs} | {estimates[str(epochs)]['updates']:,} | {estimates[str(epochs)]['optimizer_hours']:.2f} h |" for epochs in [10,20,40])
    text=f'''# V4 Daten- und Laufzeitpilot

**Pilot abgeschlossen; Haupttraining nicht gestartet; keine Modellgewichte übernommen.**

## Tatsächlich ausgeführt

{r['families_requested']} neue Familien angefragt, {r['valid_samples']} gültige Datensätze. Neue Familien-ID-Basis 94140201; ausschließlich Pilotdaten, nicht als späterer Blindtest verwenden. Die drei ursprünglichen M2-Checkpoint-Hashes wurden vor und nach dem Pilot geprüft. Ansichten nutzen deren eingefrorenes Ensemble als Fokusquelle, keine GT-Zielposition.

Je Familie werden Ausgangsansicht, kleiner Kontrollversatz und ein zugeordneter Blickwunsch untersucht. Dies ist **kein vollständiger sechs-Kandidaten-Datensatz pro Familie**. Die Suche hat ein weiches Vier-Sekunden-Ziel, zwei IK-Ausgangshaltungen und einen Wegversuch. Einzelne nicht unterbrechbare Kollisionsprüfungen können dieses Zeitziel überschreiten; maßgeblich sind die tatsächlichen Messwerte. Nicht gefundene Lösungen beweisen keine globale Unerreichbarkeit.

| Blickfamilie | Angefragt | Aufgenommen |
| --- | ---: | ---: |
{coverage}

Alle abgelehnten Wünsche sind erhalten. Paddings für nicht aufgenommene Bilder sind als nicht verfügbar maskiert. Keine Ablehnung wird als erfundene Aufnahme gezählt. Lange/dünne Quader wurden in {r['shape_counts'].get('long_thin',0)} Familien untersucht, zunächst nur verstreut. Objektanzahlen: `{r['counts']}`. Anordnungen: `{r['kinds']}`.

## Geometrie und Sicherheit

Rückprojektion tatsächlicher Kamerastrahlen: maximal {r['calibration_max_projection_px']:.6f} Pixel Abweichung. Für erfolgreiche Wünsche ganze Armwege einschließlich Greifer/Kameraproxy erneut geprüft und native Kontakte an Replay-Zuständen geprüft. Kein aufgezeichneter Robot-Umwelt-Penetrationsfehler im erfolgreich abgeschlossenen Pilot. Referenzquelle bleibt Simulatorgeometrie; keine rein visuelle Freigabe und keine Realroboterfahrt. Diskrete Prüfungen sind keine formale kontinuierliche Sicherheitsgarantie.

Geprüft sind tatsächliche Kameraposen und Verfügbarkeitsmasken, nicht die Qualität eines trainierten V4-Modells. Bildfehlerfälle enthalten einen ausdrücklich protokollierten Weichzeichner, keine manipulierte Pose.

## Numerischer Test

* Wahrnehmung: {b['parameters']:,} Parameter; vorgeschlagener Übernahmekopf separat auf 4.291 Parameter nachgezählt.
* Drei echte Diagnose-Optimizerupdates, dazu ein wiederholtes Resume-Suffix; FP32, effektive Szenenbatch 32, Microbatch 4, zwei Präfixkontexte.
* Parameteränderung nachgewiesen: maximal {b['parameter_max_delta']:.8g}.
* Wiederaufnahme mitten in Epoche und Gradient Accumulation: Gewicht-/Optimizermomentabweichung {b['partial_epoch_and_accumulation_resume']['weight_max_difference']}/{b['partial_epoch_and_accumulation_resume']['optimizer_max_difference']}, Scheduler/RNG/Sampleroffset wiederhergestellt.
* Median Updatezeit {measured:.3f} s. Drei Messwerte: `{b['seconds_per_update']}`.
* GPU: {r['hardware']['gpu']}; Peak allocated {b['peak_cuda_allocated_gib']:.3f} GiB, reserved {b['peak_cuda_reserved_gib']:.3f} GiB; RSS am Datengenerations-Messpunkt maximal {r['peak_process_rss_gib']:.3f} GiB (kein kontinuierlicher Gesamtprozess-Peak).

Die Diagnosekopie wird nicht produktiv gespeichert oder ausgewählt. `diagnostic_partial_resume.pth` ist nur ein technischer Wiederaufnahmezustand. Die drei Losswerte in `diagnostic_loss.png` sind **keine belastbare Trainings-/Validation-Lernkurve**. Der separate feste Probe-Loss ist eine Laufzeitkontrolle; keine Aussage über Overfitting oder Generalisierung.

## Zeit-/Speicherabschätzung

Gemessene Datenerzeugung {r['data_seconds']/60:.2f} min, im Mittel {r['seconds_per_family']:.3f} s/Familie. Komprimierte Arrays im Mittel {r['compressed_bytes_per_family']/2**20:.3f} MiB/Familie für drei Poseslots. Insgesamt Pilotdauer {r['elapsed_seconds']/60:.2f} min.

Für 18.000 neue Trainingsfamilien + 6.000 Replayziehungen pro effektiver Epoche, Batch 32, zwei Varianten und drei Seeds:

| Epochen je Variante/Seed | Updates insgesamt | Nur Optimizerzeit, hochgerechnet |
| --- | ---: | ---: |
{costs}

30.000 neue Familien bei genau dieser begrenzten Drei-Pose-Pilotsuche: {estimates['data_generation_same_three_pose_pilot_hours']:.2f} h. Der vollständige Bankgenerator muss mehr Blickfamilien prüfen; diese Zahl ist keine Zusage für dessen Laufzeit. Sieben Poseslots ergeben rechnerisch etwa {estimates['seven_pose_raw_array_gib']:.1f} GiB rohe Arrays; naive Kompressionshochrechnung {estimates['seven_pose_naive_compressed_gib']:.1f} GiB ist wegen der gepaddeten blockierten Ansichten unsicher. Speicher für Replay, Optimizer, Kopfdatensätze, Rohjournale, Plots und Sicherheitsreserve kommt hinzu.

Diese Hochrechnung enthält **keine** vollständigen Validation-/Request-/Kalibrierungs-/Blindtest- oder Renderkosten. Drei Updates sind eine kleine Laufzeitstichprobe. Erst der fertig implementierte Trainer und vollständige Kandidatenbank-Pilot erlauben ein verbindlicheres End-to-End-Budget; keine pauschale 10-Stunden-Zusage.

## Nächste Freigabe und verbleibende Arbeiten

Der technische Pilot prüft Daten-/Numerikmachbarkeit. Vor einem Hauptlauf noch erforderlich: vollständige Kandidatenbank und deren Laufzeitbenchmark; definierte Kamera-/Geometrie-Holdouts mit Hashmanifest; A/B-Trainer mit festem gemeinsamem Updatebudget; Beobachtungs-/Übernahmemerkmale und Kopftrainer; Kalibrierungsgates und automatische Berichte. Die V4-Dateien sind noch kein freigegebener Haupttrainer.

Bei Freigabe zuerst den festen Update-/Zeitumfang wählen. Die gemessene Machbarkeit sagt nichts darüber aus, ob Seitenbilder die Erkennung verbessern; genau das muss der geplante A/B-Versuch zeigen. Eine nicht erreichbare Basisansicht oder unbekannter visueller Freiraum bleiben blockiert.

Artefakte: `manifest.json`, `checkpoint_hashes.json`, `families.jsonl`, `samples/`, `examples/`, `numerical.json`, `budget_estimate.json`, `coverage_and_runtime.png`, `diagnostic_loss.png`, `source/`.
'''
    (out/'REPORT.md').write_text(text,encoding='utf-8');print(json.dumps(dict(report=str(out/'REPORT.md'),estimates=estimates),indent=2))
if __name__=='__main__':main()
