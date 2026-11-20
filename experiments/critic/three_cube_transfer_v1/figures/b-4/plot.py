"""B-4: Abbildungen zum Critic-Vergleich N2-2 gegen IL-v2 (N2-2b).

Quellen sind ausschließlich bereits verifizierte Berichtswerte:

- CRITIC_VALIDATION.md, Abschnitt "Ergebnis (Abschluss 19.11.2026)" (N2-2,
  Monitor-verify, result_verified: true),
- CRITIC_VALIDATION_V2.md, Abschnitt "Ergebnis und Abschlussprüfung am
  20.11.2026" (N2-2b, VERIFY OK gegen summary.json 767bccfc…2e94),
- ACTION_SENSITIVITY.md, D1a-Tabelle und D1b-Tabelle (beide nachgerechnet,
  126/126 Gruppen).

Die Werte stehen unverändert als Konstanten unten. Gerundet wird erst bei der
Beschriftung. Es werden keine Laufordner, Rohtrajektorien, Gewichte oder
Testfamilien gelesen, keine Simulation und kein Training gestartet.

Aufruf aus dem Repository-Stamm:
    ./praxis/.venv/Scripts/python.exe experiments/critic/three_cube_transfer_v1/figures/b-4/plot.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

OUT = Path(__file__).resolve().parent
PARENTS = [1, 2, 3]
CRITICS = ["N2-2", "IL-v2"]
COLORS = {"N2-2": "#1f5a96", "IL-v2": "#c0602a", "Zufall": "#9a9a9a"}
SRC_VAL = "Quellen: CRITIC_VALIDATION.md (N2-2), CRITIC_VALIDATION_V2.md (N2-2b)"
SRC_ACT = "Quelle: ACTION_SENSITIVITY.md (D1a, D1b)"

# --- Critic-Güte nach §6 auf denselben 450 gespeicherten N2-2-Rollouts --------
# Zählungen A-Erfolge und geeignete Punkte sind in beiden Berichten identisch.
VALIDATION = {
    "normal": {
        "label": "validation_normal (100 Familien, entscheidet)",
        "successes": [41, 29, 29],
        "eligible": [14, 14, 14],
        "N2-2": {
            "auc": [0.853, 0.886, 0.817],
            "auc_ci": [(0.787, 0.909), (0.794, 0.951), (0.750, 0.879)],
            "diff": [-0.0196, -0.0210, -0.0127],
            "diff_ci": [(-0.0286, -0.0081), (-0.0293, -0.0109), (-0.0213, -0.0036)],
            "ece": [0.040, 0.033, 0.039],
        },
        "IL-v2": {
            "auc": [0.885, 0.916, 0.882],
            "auc_ci": [(0.826, 0.936), (0.835, 0.973), (0.823, 0.931)],
            "diff": [-0.0285, -0.0284, -0.0175],
            "diff_ci": [(-0.0349, -0.0208), (-0.0349, -0.0198), (-0.0286, -0.0005)],
            "ece": [0.022, 0.024, 0.028],
        },
    },
    "hard": {
        "label": "validation_hard (50 Familien, nur berichtet)",
        "successes": [23, 19, 16],
        "eligible": [14, 14, 12],
        "N2-2": {
            "auc": [0.925, 0.906, 0.778],
            "auc_ci": [(0.860, 0.971), (0.849, 0.953), (0.675, 0.865)],
            "diff": [-0.0205, -0.0237, -0.0048],
            "diff_ci": [(-0.0301, -0.0083), (-0.0322, -0.0134), (-0.0191, 0.0114)],
            "ece": [0.058, 0.048, 0.052],
        },
        "IL-v2": {
            "auc": [0.951, 0.933, 0.954],
            "auc_ci": [(0.894, 0.987), (0.867, 0.983), (0.902, 0.991)],
            "diff": [-0.0284, -0.0283, -0.0236],
            "diff_ci": [(-0.0363, -0.0194), (-0.0366, -0.0179), (-0.0307, -0.0160)],
            "ece": [0.029, 0.047, 0.024],
        },
    },
}
AUC_MIN, AUC_LOWER_MIN, ECE_MAX = 0.60, 0.50, 0.10  # PROTOCOL.md §6

# --- Vortraining (getrennte Größen, nicht direkt vergleichbar) ----------------
PRETRAIN = {
    "N2-2": {
        "episodes": 300,  # nur N2-1
        "updates": 20_000,
        "seconds": [43.2, 43.4, 43.0],
        "last_mean_loss": [0.0050, 0.0026, 0.0044],
        "train_mse": [0.0027, 0.0012, 0.0022],
    },
    "IL-v2": {
        "episodes": 600,  # N2-1 + N2-1b
        "updates": 20_000,
        "seconds_approx": 37.0,  # "etwa 37 s je Parent"
        "train_frames": [423_107, 461_647, 448_109],
        "first_window_loss": [0.0435, 0.0341, 0.0408],
        "last_window_loss": [0.0087, 0.0064, 0.0103],
    },
}

# --- Technische Stabilität -----------------------------------------------------
FRAMES_N2_2 = {  # je Parent 1/2/3, CRITIC_VALIDATION.md "Endlichkeit"
    "normal": [72_977, 80_749, 81_117],
    "hard": [35_012, 37_605, 39_663],
}
FRAMES_IL_V2_TOTAL = 347_123  # CRITIC_VALIDATION_V2.md, alle endlich
NONFINITE = {"N2-2": 0, "IL-v2": 0}
CRITIC_UPDATES = {"N2-2": 60_000, "IL-v2": 60_000}

# --- Aktionssensitivität D1a (N2-2) und D1b (IL-v2), je 1.344 Frames/Stufe -----
DELTAS = [0.05, 0.10, 0.20]
N_FRAMES = 1_344
SENS = {
    "N2-2": {
        "median_std": [0.00049846, 0.00059453, 0.00067657],
        "ratio": [4.83, 4.93, 5.13],
        "p90": [0.00292933, 0.00446765, 0.00646952],
        "unique": [99, 138, 162],
    },
    "IL-v2": {
        "median_std": [0.00039805, 0.00049234, 0.00058884],
        "ratio": [3.86, 4.08, 4.46],
        "p90": [0.00283096, 0.00418074, 0.00619486],
        "unique": [99, 121, 139],
    },
    "Zufall": {
        "median_std": [0.00010318, 0.00012062, 0.00013192],
        "p90": [0.00036212, 0.00053376, 0.00082522],
        "unique": [0, 0, 1],
    },
}
STD_MIN, RATIO_MIN = 0.01, 1.5  # PROTOCOL_V2.md §A

# Median Frame-Std. je Parent und Policy-Phase 0–6 bei δ_max = 0,20,
# Einheiten 0,001 Q (Tabellen "je Parent, Policy-Phase und Bindungsstufe").
PHASE_STD_020 = {
    "N2-2": {
        1: [3.721, 0.303, 0.425, 2.025, 0.077, 3.383, 0.097],
        2: [3.436, 0.070, 0.295, 0.816, 0.140, 1.915, 0.041],
        3: [4.291, 0.121, 0.454, 1.961, 0.071, 3.434, 0.289],
    },
    "IL-v2": {
        1: [2.339, 0.140, 0.358, 2.037, 0.040, 2.621, 0.042],
        2: [2.838, 0.065, 0.302, 0.783, 0.063, 2.155, 0.030],
        3: [3.011, 0.088, 0.419, 1.840, 0.032, 3.974, 0.163],
    },
}


def de(x: float, nd: int) -> str:
    """Zahl mit deutschem Dezimalkomma und typografischem Minus."""
    return f"{x:.{nd}f}".replace("-", "−").replace(".", ",")


def _de_axis(ax, nd: int, axis: str = "y") -> None:
    fmt = matplotlib.ticker.FuncFormatter(lambda v, _: de(v, nd))
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(fmt)


def _errbars(ax, key: str, panel: dict, offsets: dict, show_values: bool, nd: int) -> None:
    for critic in CRITICS:
        vals = panel[critic][key]
        ci = panel[critic].get(f"{key}_ci")
        xs = np.array(PARENTS, dtype=float) + offsets[critic]
        if ci is None:
            ax.bar(xs, vals, width=0.34, color=COLORS[critic], label=critic)
        else:
            lo = [v - c[0] for v, c in zip(vals, ci)]
            hi = [c[1] - v for v, c in zip(vals, ci)]
            ax.errorbar(xs, vals, yerr=[lo, hi], fmt="o", ms=6, capsize=4,
                        color=COLORS[critic], label=f"{critic} [95-%-KI]")
        if show_values:
            for x, v in zip(xs, vals):
                ax.annotate(de(v, nd), (x, v), textcoords="offset points",
                            xytext=(0, 6 if v >= 0 else -12), ha="center", fontsize=7.5)


def fig_critic_quality() -> Path:
    fig, axes = plt.subplots(2, 3, figsize=(15, 9.0))
    offsets = {"N2-2": -0.17, "IL-v2": 0.17}
    for row, (pkey, panel) in enumerate(VALIDATION.items()):
        ax_auc, ax_diff, ax_ece = axes[row]
        _errbars(ax_auc, "auc", panel, offsets, True, 3)
        ax_auc.axhline(AUC_MIN, color="k", ls="--", lw=1, label="Schwelle 0,60")
        ax_auc.axhline(AUC_LOWER_MIN, color="k", ls=":", lw=1, label="untere Grenze > 0,50")
        ax_auc.set_ylim(0.45, 1.02)
        ax_auc.set_ylabel("gewichtete AUC")
        _de_axis(ax_auc, 2)

        _errbars(ax_diff, "diff", panel, offsets, True, 4)
        ax_diff.axhline(0, color="k", lw=1, label="0 (Intervall muss darunter liegen)")
        ax_diff.set_ylim(-0.042, 0.016)
        ax_diff.set_ylabel("MSE Critic − Phasen-Baseline")
        _de_axis(ax_diff, 3)

        _errbars(ax_ece, "ece", panel, offsets, True, 3)
        ax_ece.axhline(ECE_MAX, color="k", ls="--", lw=1, label="Schwelle 0,10")
        ax_ece.set_ylim(0, 0.15)
        ax_ece.set_ylabel("ECE")
        _de_axis(ax_ece, 2)

        ticks = [f"Parent {p}\n{s}/{100 if pkey == 'normal' else 50} Erfolge\n{e}/14 Punkte"
                 for p, s, e in zip(PARENTS, panel["successes"], panel["eligible"])]
        for ax in (ax_auc, ax_diff, ax_ece):
            ax.set_xticks(PARENTS)
            ax.set_xticklabels(ticks, fontsize=8)
            ax.grid(axis="y", alpha=0.3)
        ax_auc.set_title(f"{panel['label']}\nAUC innerhalb der Phasenpunkte", fontsize=10)
        ax_diff.set_title("Fehler gegenüber Phasen-Baseline", fontsize=10)
        ax_ece.set_title("Kalibrierungsfehler", fontsize=10)
        if row == 0:
            for ax in (ax_auc, ax_diff, ax_ece):
                ax.legend(fontsize=7.5, loc={id(ax_auc): "lower right", id(ax_diff): "upper left",
                                             id(ax_ece): "upper left"}[id(ax)])
    fig.suptitle("Critic-Güte nach §6: N2-2 (nur N2-1) gegen IL-v2 (N2-1 + N2-1b), "
                 "gleiche 450 gespeicherte A-Rollouts", fontsize=12)
    fig.text(0.01, 0.008,
             f"{SRC_VAL}. Intervalle: Familienbootstrap, 2.000 Ziehungen, Seed 7300, nur Szenenunsicherheit je Parent.\n"
             "n = 3 Parents, kein Mittelwert. Das schwierige Panel entscheidet nicht (N2-2 Parent 3 verfehlt dort Bedingung 3).",
             fontsize=7.5)
    fig.tight_layout(rect=(0, 0.035, 1, 0.96))
    path = OUT / "01_critic_guete.png"
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def fig_action_sensitivity() -> Path:
    fig, axes = plt.subplots(1, 4, figsize=(17, 4.8))
    x = np.arange(len(DELTAS))
    dlab = [de(d, 2) for d in DELTAS]

    ax = axes[0]
    for i, c in enumerate(["N2-2", "IL-v2", "Zufall"]):
        ax.bar(x + (i - 1) * 0.26, SENS[c]["median_std"], width=0.26, color=COLORS[c],
               label={"Zufall": "Zufallsinit. (gleich in D1a/D1b)"}.get(c, c))
        for xi, v in zip(x + (i - 1) * 0.26, SENS[c]["median_std"]):
            ax.annotate(de(v * 1000, 3), (xi, v), textcoords="offset points", xytext=(0, 3),
                        ha="center", fontsize=7)
    ax.axhline(STD_MIN, color="k", ls="--", lw=1, label="Schwelle 0,01 (v2 §A)")
    ax.set_yscale("log")
    ax.set_ylim(5e-5, 2e-2)
    ax.set_xticks(x, dlab)
    ax.set_xlabel("Bindungsstufe δ_max")
    ax.set_ylabel("Median Frame-Std. von A (log)")
    ax.set_title("Absolute Sensitivität\n(Beschriftung in 0,001 Q)", fontsize=10)
    ax.legend(fontsize=7.5, loc="upper left")

    ax = axes[1]
    for i, c in enumerate(CRITICS):
        xs = x + (i - 0.5) * 0.34
        ax.bar(xs, SENS[c]["ratio"], width=0.34, color=COLORS[c], label=c)
        for xi, v in zip(xs, SENS[c]["ratio"]):
            ax.annotate(de(v, 2), (xi, v), textcoords="offset points", xytext=(0, 3),
                        ha="center", fontsize=7.5)
    ax.axhline(RATIO_MIN, color="k", ls="--", lw=1, label="Schwelle 1,5 (v2 §A)")
    ax.set_xticks(x, dlab)
    ax.set_xlabel("Bindungsstufe δ_max")
    ax.set_ylabel("Verhältnis zur Zufallsinitialisierung")
    ax.set_title("Relative Sensitivität", fontsize=10)
    ax.legend(fontsize=7.5, loc="upper left")
    ax.set_ylim(0, 7.5)
    _de_axis(ax, 1)

    ax = axes[2]
    for i, c in enumerate(["N2-2", "IL-v2", "Zufall"]):
        xs = x + (i - 1) * 0.26
        ax.bar(xs, SENS[c]["unique"], width=0.26, color=COLORS[c], label=c)
        for xi, v in zip(xs, SENS[c]["unique"]):
            ax.annotate(f"{v}", (xi, v), textcoords="offset points", xytext=(0, 3),
                        ha="center", fontsize=7.5)
    ax.set_xticks(x, dlab)
    ax.set_xlabel("Bindungsstufe δ_max")
    ax.set_ylabel(f"Frames von {N_FRAMES:,}".replace(",", "."))
    ax.set_title("Eindeutige Rangfolge\n(Abstand der zwei höchsten A > 0,001)", fontsize=10)
    ax.set_ylim(0, N_FRAMES * 0.16)
    ax.legend(fontsize=7.5, loc="upper left")

    ax = axes[3]
    markers = {1: "o", 2: "s", 3: "^"}
    for p in PARENTS:
        ax.scatter(PHASE_STD_020["N2-2"][p], PHASE_STD_020["IL-v2"][p], marker=markers[p],
                   color="#555555", label=f"Parent {p}", s=30)
    lim = (0.02, 15)
    ax.plot(lim, lim, color="k", lw=0.8, label="gleich")
    ax.axhline(STD_MIN * 1000, color="k", ls="--", lw=1, label="Schwelle 0,01 = 10")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(*lim)
    ax.set_ylim(*lim)
    ax.set_xlabel("N2-2: Median Frame-Std. [0,001 Q]")
    ax.set_ylabel("IL-v2: Median Frame-Std. [0,001 Q]")
    ax.set_title("δ_max = 0,20 je Parent und Policy-Phase\n(21 Gruppen à 64 Frames)", fontsize=10)
    ax.legend(fontsize=7.5, loc="lower right")

    fig.suptitle("Aktionssensitivität auf denselben 1.344 Driftframes je Stufe: "
                 "D1a (N2-2) gegen D1b (IL-v2). Beide verfehlen 0,01 auf jeder Stufe.", fontsize=12)
    fig.text(0.01, 0.01,
             f"{SRC_ACT}. Reine Vorwärtsdurchläufe, 32 Aktionen je Frame, keine Ausführung in der Simulation: "
             "keine Aussage über die Güte der Aktionen oder den Turmerfolg. Gruppen nach Policy-Phase, nicht nach Phasenpunkt.",
             fontsize=7.5)
    fig.tight_layout(rect=(0, 0.04, 1, 0.92))
    path = OUT / "02_aktionssensitivitaet.png"
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def fig_pretraining() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
    x = np.array(PARENTS, dtype=float)

    ax = axes[0]
    d = PRETRAIN["N2-2"]
    ax.bar(x - 0.18, d["last_mean_loss"], width=0.36, color=COLORS["N2-2"], label="letzter mittlerer Loss")
    ax.bar(x + 0.18, d["train_mse"], width=0.36, color=COLORS["N2-2"], alpha=0.45,
           label="MSE auf eigenen Trainingsdaten")
    for xi, v in zip(x - 0.18, d["last_mean_loss"]):
        ax.annotate(de(v, 4), (xi, v), textcoords="offset points", xytext=(0, 3), ha="center", fontsize=7.5)
    for xi, v in zip(x + 0.18, d["train_mse"]):
        ax.annotate(de(v, 4), (xi, v), textcoords="offset points", xytext=(0, 3), ha="center", fontsize=7.5)
    ax.set_title(f"N2-2 · {d['episodes']} Episoden (N2-1) je Parent, 20.000 Updates\n"
                 f"Laufzeit {de(d['seconds'][0], 1)} / {de(d['seconds'][1], 1)} / {de(d['seconds'][2], 1)} s",
                 fontsize=10)
    ax.legend(fontsize=8)

    ax = axes[1]
    d = PRETRAIN["IL-v2"]
    ax.bar(x - 0.18, d["first_window_loss"], width=0.36, color=COLORS["IL-v2"], alpha=0.45,
           label="mittlerer Batch-Loss, erstes 500er-Fenster")
    ax.bar(x + 0.18, d["last_window_loss"], width=0.36, color=COLORS["IL-v2"],
           label="mittlerer Batch-Loss, letztes 500er-Fenster")
    for xi, v in zip(x - 0.18, d["first_window_loss"]):
        ax.annotate(de(v, 4), (xi, v), textcoords="offset points", xytext=(0, 3), ha="center", fontsize=7.5)
    for xi, v in zip(x + 0.18, d["last_window_loss"]):
        ax.annotate(de(v, 4), (xi, v), textcoords="offset points", xytext=(0, 3), ha="center", fontsize=7.5)
    frames = " / ".join(f"{f:,}".replace(",", ".") for f in d["train_frames"])
    ax.set_title(f"IL-v2 · {d['episodes']} Episoden (N2-1 + N2-1b) je Parent, 20.000 Updates\n"
                 f"Trainingsframes {frames}, etwa {de(d['seconds_approx'], 0)} s je Parent", fontsize=10)
    ax.legend(fontsize=8)

    for ax in axes:
        ax.set_xticks(PARENTS, [f"Parent {p}" for p in PARENTS])
        ax.set_ylabel("Loss (Return²)")
        ax.grid(axis="y", alpha=0.3)
        _de_axis(ax, 3)
    ymax = max(max(PRETRAIN["IL-v2"]["first_window_loss"]), max(PRETRAIN["N2-2"]["last_mean_loss"])) * 1.35
    for ax in axes:
        ax.set_ylim(0, ymax)

    fig.suptitle("Vortraining: Loss auf den jeweils eigenen Trainingsdaten (getrennt, nicht direkt vergleichbar)",
                 fontsize=12)
    fig.text(0.01, 0.01,
             f"{SRC_VAL}. Unterschiedliche Trainingsdaten (IL-v2 mit verrauschten Returns)\n"
             "und unterschiedlich berichtete Lossgrößen. Loss sagt nichts über Validierung oder Aufgabenerfolg, dafür Abb. 01.",
             fontsize=7.5)
    fig.tight_layout(rect=(0, 0.07, 1, 0.92))
    path = OUT / "03_vortraining_loss.png"
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def fig_stability() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    total_n22 = sum(FRAMES_N2_2["normal"]) + sum(FRAMES_N2_2["hard"])
    assert total_n22 == FRAMES_IL_V2_TOTAL, "Framesumme N2-2 weicht von IL-v2 ab"

    ax = axes[0]
    vals = [total_n22, FRAMES_IL_V2_TOTAL]
    ax.bar([0, 1], vals, color=[COLORS[c] for c in CRITICS], width=0.5)
    for xi, (c, v) in enumerate(zip(CRITICS, vals)):
        ax.annotate(f"{v:,}".replace(",", ".") + f" Frames\n{NONFINITE[c]} nicht endlich",
                    (xi, v), textcoords="offset points", xytext=(0, 4), ha="center", fontsize=8.5)
    ax.set_xticks([0, 1], CRITICS)
    ax.set_ylim(0, total_n22 * 1.25)
    ax.set_ylabel("vorhergesagte Validierungsframes")
    ax.set_title("Endlichkeit (§6 Bedingung 4), beide Panels", fontsize=10)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}".replace(",", ".")))

    ax = axes[1]
    vals = [CRITIC_UPDATES[c] for c in CRITICS]
    ax.bar([0, 1], vals, color=[COLORS[c] for c in CRITICS], width=0.5)
    for xi, v in enumerate(vals):
        ax.annotate(f"{v:,}".replace(",", ".") + "\n(3 × 20.000)", (xi, v), textcoords="offset points",
                    xytext=(0, 4), ha="center", fontsize=8.5)
    ax.set_xticks([0, 1], CRITICS)
    ax.set_ylim(0, 75_000)
    ax.set_ylabel("Critic-Updates")
    ax.set_title("Optimizerupdates nur im Critic-Vortraining", fontsize=10)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}".replace(",", ".")))

    fig.suptitle("Technische Stabilität: N2-2 gegen IL-v2", fontsize=12)
    fig.text(0.01, 0.01,
             f"{SRC_VAL}. Gleicher Eingabedatensatz (dataset_sha256 fac1e51d…e570).\n"
             "N2-2: 450 A-Rollouts mit 0 Optimizerupdates; N2-2b: 0 Rollouts. Keine Güte- oder Erfolgsaussage.",
             fontsize=7.5)
    fig.tight_layout(rect=(0, 0.08, 1, 0.92))
    path = OUT / "04_technische_stabilitaet.png"
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def main() -> None:
    for fn in (fig_critic_quality, fig_action_sensitivity, fig_pretraining, fig_stability):
        print(fn().name)


if __name__ == "__main__":
    main()
