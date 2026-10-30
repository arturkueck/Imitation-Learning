from pathlib import Path
p=Path('experiments/stack_transition_quality_20261024/README.md');s=p.read_text(encoding='utf-8');n='> **Aktualisierung24.10.2026:** Ausführbarer Daten-/Smoke-Kern und unabhängiges Audit liegen vor. Der konkrete erste Vergleich ist B0/B mit Score ohne Clearance; C bleibt zurückgestellt. [Neuer Laufplan und offene Startgates](TRAINING_RUN_PLAN.md) · [Audit](AUDIT_FINDINGS.md) · [Codevalidierung](IMPLEMENTATION_VALIDATION.md). Die historische Fingerkontaktmessung war fehlerhaft; siehe [Messkorrektur](../stack_five_curriculum_20261023/MEASUREMENT_CORRECTION.md).\n\n'
if not s.startswith('> **Aktualisierung'):p.write_text(n+s,encoding='utf-8')
for folder,name in [('stack_self_imitation_20261023','RESULTS.md'),('stack_phased_8h_20261023','REPORT_2.md')]:
 p=Path('experiments')/folder/name
 if p.exists():
  s=p.read_text(encoding='utf-8');notice='> **Messkorrektur24.10.2026:** Die zusätzliche Fingerkontaktfreiheitsprüfung war wegen eines Gripper-Dictionary-Fehlers nicht zuverlässig. Historische Quoten gelten für die damalige Metrik. [Details](../stack_five_curriculum_20261023/MEASUREMENT_CORRECTION.md).\n\n'
  if not s.startswith('> **Messkorrektur'):p.write_text(notice+s,encoding='utf-8')
