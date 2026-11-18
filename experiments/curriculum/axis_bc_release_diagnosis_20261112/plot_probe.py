"""Plot the matched release intervention without modifying training artifacts."""
from pathlib import Path
import os
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
OUT = HERE/'probe_001'
files = [('Unveränderte Policy', OUT/'verified_baseline.npz', '#2468b4'),
         ('Zeitmerkmal begrenzt', OUT/'mixed_seed1_loss_2026115004.npz', '#df7926')]
plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
fig, axes = plt.subplots(2, 2, figsize=(11.5, 7), constrained_layout=True)
for label, path, color in files:
    with np.load(path) as archive:
        t, extra, inputs = archive['trace'], archive['extra'], archive['inputs']
    first = int(np.flatnonzero((t[:,1] == 2) & (t[:,2] == 6))[0])
    last = min(len(t), first+81)
    steps = np.arange(last-first)
    axes[0,0].plot(steps, inputs[first:last, 9], color=color, label=label, lw=2)
    axes[0,1].plot(steps, t[first:last, 22], color=color, label=label, lw=2)
    axes[1,0].plot(steps, t[first:last, 6], color=color, label=label, lw=2)
    axes[1,1].step(steps, extra[first:last, 4], color=color, label=label, lw=2, where='post')
for ax in axes.flat:
    ax.axvline(17, color='#666666', ls=':', label='Trainingsbereich endet', lw=1)
    ax.set_xlabel('Steuerschritte seit Beginn der letzten Freigabephase')
    ax.set_xlim(0,80)
    ax.grid(alpha=.2)
axes[0,0].axhline(.85, color='#777777', ls=':', lw=.8)
axes[0,0].set(title='Zeitmerkmal am Eingang der Policy', ylabel='Normierte Zeit (Schritte / 20)')
axes[0,0].legend(fontsize=8)
axes[0,1].set(title='Vorhergesagte Z-Aktion', ylabel='Z-Steuerbefehl\n(negativ: nach unten)')
axes[1,0].axhline(50, color='#555555', ls='--', lw=1)
axes[1,0].set(title='Aufeinanderfolgende gültige Turmzustände', ylabel='Stabile Steuerschritte')
axes[1,1].set(title='Fingerkontakt am obersten Würfel', ylabel='Kontakt ja / nein', yticks=[0,1])
fig.suptitle('Gleiche Gewichte, gleiche Szene – nur das letzte Zeitmerkmal begrenzt', fontsize=14)
fig.supxlabel('Beispiel: mixed, Trainingsseed 1, Szenenseed 2026115004. Blaue Basisaufnahme exakt historisch reproduziert.\n'
               'Bis zum Eingriff identische Trajektorie. Erfolgskriterium bleibt bei 50 gültigen Frames; keine Trainingsupdates.', fontsize=9)
fig.savefig(OUT/'release_clock_probe.png', dpi=160)
fig.savefig(OUT/'release_clock_probe.pdf')
print(str((OUT/'release_clock_probe.png').resolve()))
