from pathlib import Path
p=Path('experiments/self_imitation/stack_five_curriculum_20261023/MEASUREMENT_CORRECTION.md');p.write_text(p.read_text(encoding='utf-8').replace('ableiteniten','ableiten'),encoding='utf-8')
for name in ['RESULTS.md','DATASET_REPORT.md']:
 p=Path('experiments/self_imitation/stack_five_curriculum_20261023')/name;s=p.read_text(encoding='utf-8');notice='> **Messkorrektur24.10.2026:** Die zusätzliche Prüfung vollständiger Fingerkontaktfreiheit war wegen eines Gripper-Dictionary-Fehlers unwirksam. Historische Quoten gelten für die damalige implementierte Metrik. [Details und Grenzen](MEASUREMENT_CORRECTION.md).\n\n'
 if not s.startswith('> **Messkorrektur'):p.write_text(notice+s,encoding='utf-8')
