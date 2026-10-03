# Gezielter Stapel-Vergleich

Status: COMPLETED

Dieser Lauf wartet auf das Ende des bestehenden Diffusion-Prozesses. Er unterbricht ihn nicht.
Vergleich: bisheriger State-Diffusion-Checkpoint vs. neu trainiertes State-Modell mit korrigiertem Scheduler; jeweils 8 oder 2 ausgeführte Aktionen pro Neuplanung.
Training unverändert 300 Epochen / 100 Batches / Batchgröße 8 / Seed 1; identische Daten und Architektur. Die Trainingsänderung betrifft ausschließlich die Scheduler-Schritte. Inferenzhorizonte werden auf denselben Gewichten verglichen.
Je Variante 20 Tests ab Seed 46000. Eine Trainingsinitialisierung; kleine Unterschiede sind noch kein belastbarer Nachweis.

| Modell | Ausführungsblock | Erfolg | Nachlauf stabil | B gegriffen | B angehoben | Paar abgelegt |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 8 | 0% | 0% | 45% | 25% | 0% |
| baseline | 2 | 0% | 0% | 25% | 10% | 0% |
| fixed_scheduler | 8 | 0% | 0% | 70% | 55% | 0% |
| fixed_scheduler | 2 | 0% | 0% | 85% | 70% | 0% |

Fehler:
Keine bisher.