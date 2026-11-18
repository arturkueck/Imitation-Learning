"""Read-only analysis of completed logs; no checkpoint selection or training."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
RUN = HERE / 'ready_001'
OUT = HERE / 'analysis_loss'
OUT.mkdir(exist_ok=True)
rows = [json.loads(line) for line in (RUN/'metrics.jsonl').read_text().splitlines()]
panels = {int(p.stem.split('u')[1]): json.loads(p.read_text()) for p in RUN.glob('panel_u*.json')}
updates = sorted(panels)
colors = dict(mixed='#2468b4', curriculum='#df7926')
labels = dict(mixed='BC durchmischt', curriculum='BC Curriculum')
plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False,
                     'figure.facecolor': 'white', 'savefig.facecolor': 'white'})


def decorate(ax, log=False):
    for boundary in (5000, 12000):
        ax.axvline(boundary, color='#777777', lw=.9, ls='--', alpha=.7)
    ax.set_xlabel('Optimizerupdates je Modell')
    ax.set_xlim(0, 30500)
    ax.grid(alpha=.2)
    if log:
        ax.set_yscale('log')


def smooth(values, width=11):
    # Centered mean of recorded points, with smaller windows at the edges.
    kernel = np.ones(width)
    return np.convolve(values, kernel, mode='same')/np.convolve(np.ones_like(values), kernel, mode='same')


fig, axes = plt.subplots(2, 2, figsize=(13, 8), constrained_layout=True)
for ax, field, title in zip(axes.flat[:3], ['loss', 'action_mse', 'completion_bce'],
                            ['Trainingsloss: MSE + 0,1 × BCE', 'Trainings-MSE der Aktionen',
                             'Trainings-BCE des Phasenabschlusses']):
    for arm in colors:
        series = []
        for seed in (1, 2, 3):
            subset = [r for r in rows if r['model'] == f'{arm}_seed{seed}']
            x = np.array([r['update'] for r in subset])
            y = np.array([r[field] for r in subset])
            ax.plot(x, y, color=colors[arm], alpha=.11, lw=.6)
            series.append(smooth(y))
        series = np.stack(series)
        ax.fill_between(x, series.min(0), series.max(0), color=colors[arm], alpha=.14)
        ax.plot(x, series.mean(0), color=colors[arm], lw=1.8, label=labels[arm])
    ax.set_title(title)
    ax.set_ylabel('Loss (logarithmisch)')
    decorate(ax, log=True)
    ax.legend(fontsize=9)

ax = axes.flat[3]
for arm in colors:
    values = np.array([[panels[u][f'{arm}_seed{s}']['action_mse'] for u in updates] for s in (1, 2, 3)])
    for values_seed in values:
        ax.plot(updates, values_seed, color=colors[arm], alpha=.25, lw=.8)
    ax.fill_between(updates, values.min(0), values.max(0), color=colors[arm], alpha=.14)
    ax.plot(updates, values.mean(0), 'o-', color=colors[arm], label=labels[arm], lw=1.8)
ax.set_title('Validierungs-MSE auf unveränderten Demonstrationen')
ax.set_ylabel('Aktions-MSE (logarithmisch)')
decorate(ax, log=True)
ax.legend(fontsize=9)
fig.suptitle('BC-Vergleich: Training und Validierung', fontsize=16)
fig.supxlabel('Training: dünn = protokollierte Einzelbatches; dick = Mittel über 3 Seeds, je 11 Messpunkte geglättet.\n'
               'Band = Spannweite der 3 Seeds, kein Konfidenzintervall. Gestrichelt: Curriculumwechsel bei 5.000 / 12.000.\n'
               'Validierung: 5 tatsächlich gemessene Checkpoints; nur Aktions-MSE gespeichert, kein gesamter Validierungsloss.', fontsize=9)
fig.savefig(OUT/'loss_curves.png', dpi=170)
fig.savefig(OUT/'loss_curves.pdf')
plt.close(fig)

fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), constrained_layout=True)
for ax, count in zip(axes, (2, 3)):
    for arm in colors:
        values = np.array([[100*panels[u][f'{arm}_seed{s}'][f'dev{count}']['successes']/20
                            for u in updates] for s in (1, 2, 3)])
        for values_seed in values:
            ax.plot(updates, values_seed, color=colors[arm], alpha=.28, lw=.8)
        ax.fill_between(updates, values.min(0), values.max(0), color=colors[arm], alpha=.14)
        ax.plot(updates, values.mean(0), 'o-', color=colors[arm], lw=1.8, label=labels[arm])
    decorate(ax)
    ax.set_ylim(-2, 102)
    ax.set_ylabel('Erfolgreiche Episoden (%)')
    ax.set_title(f'{count} Würfel: vollständiger stabiler Stapel')
    ax.legend(fontsize=9)
fig.suptitle('Aufgabenerfolg während des Trainings', fontsize=15)
fig.supxlabel('Entwicklungsstarts: 20 gleiche Szenen je Checkpoint und Trainingsseed. Dick: Mittel, Band: Spannweite über 3 Seeds.\n'
               'Keine Endtestkurven und kein Konfidenzintervall; Verbindungslinien sind keine zusätzlichen Messungen.', fontsize=9)
fig.savefig(OUT/'development_success.png', dpi=170)
plt.close(fig)

summary = {}
for arm in colors:
    summary[arm] = {}
    for u in updates:
        entries = [panels[u][f'{arm}_seed{s}'] for s in (1, 2, 3)]
        summary[arm][u] = dict(validation_mse=float(np.mean([e['action_mse'] for e in entries])),
                               dev2=[e['dev2']['successes'] for e in entries],
                               dev3=[e['dev3']['successes'] for e in entries])
    for low, high in ((20000, 25000), (25000, 30000)):
        subset = [r for r in rows if r['model'].startswith(arm+'_') and low < r['update'] <= high]
        summary[arm][f'train_{low}_{high}'] = {field: float(np.mean([r[field] for r in subset]))
                                              for field in ('loss', 'action_mse', 'completion_bce')}
(OUT/'curve_summary.json').write_text(json.dumps(summary, indent=2))
print(json.dumps(summary, indent=2))
