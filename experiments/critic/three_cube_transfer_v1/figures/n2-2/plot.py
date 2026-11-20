"""Abbildungen zu N2-2 (Critic-Vortraining und Critic-Validierung).

Quelle sind ausschließlich die verifizierten Werte aus
experiments/critic/three_cube_transfer_v1/CRITIC_VALIDATION.md, Abschnitt
"Ergebnis (Abschluss 19.11.2026)" (Monitor-verify, result_verified: true).
Die Werte sind unten unverändert und ungerundet übernommen, so wie sie dort
stehen. Gerundet wird erst bei der Anzeige. Es werden keine Rohtrajektorien,
Gewichte, Laufordner oder Testfamilien gelesen.

Aufruf aus dem Repository-Stamm:
    ./praxis/.venv/Scripts/python.exe experiments/critic/three_cube_transfer_v1/figures/n2-2/plot.py
"""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

OUT = Path(__file__).resolve().parent
SOURCE = "Quelle: CRITIC_VALIDATION.md (N2-2, verifiziert 19.11.2026)"

PARENTS = [1, 2, 3]
N_POINTS_TOTAL = 14  # Phasenpunkte je Panel

# --- Vortraining (CRITIC_VALIDATION.md, "Weitere Angaben") --------------------
PRETRAIN = {
    "updates": 20_000,
    "batch": 256,
    "seconds": [43.2, 43.4, 43.0],
    "last_mean_loss": [0.0050, 0.0026, 0.0044],
    "train_mse": [0.0027, 0.0012, 0.0022],
    "episodes_per_parent": 300,
}

# --- Validierung nach §6 (Tabellen "validation_normal" / "validation_hard") ---
VALIDATION = {
    "normal": {
        "label": "validation_normal (100 Familien, entscheidet)",
        "n": 100,
        "successes": [41, 29, 29],
        "eligible": [14, 14, 14],
        "auc": [0.853, 0.886, 0.817],
        "auc_ci": [(0.787, 0.909), (0.794, 0.951), (0.750, 0.879)],
        "mse_critic": [0.0266, 0.0210, 0.0321],
        "mse_base": [0.0462, 0.0420, 0.0448],
        "diff": [-0.0196, -0.0210, -0.0127],
        "diff_ci": [(-0.0286, -0.0081), (-0.0293, -0.0109), (-0.0213, -0.0036)],
        "ece": [0.040, 0.033, 0.039],
        "frames": [72_977, 80_749, 81_117],
        "phase_entries": [1_286, 1_213, 1_186],
    },
    "hard": {
        "label": "validation_hard (50 Familien, entscheidet nicht)",
        "n": 50,
        "successes": [23, 19, 16],
        "eligible": [14, 14, 12],
        "auc": [0.925, 0.906, 0.778],
        "auc_ci": [(0.860, 0.971), (0.849, 0.953), (0.675, 0.865)],
        "mse_critic": [0.0217, 0.0203, 0.0315],
        "mse_base": [0.0422, 0.0440, 0.0362],
        "diff": [-0.0205, -0.0237, -0.0048],
        "diff_ci": [(-0.0301, -0.0083), (-0.0322, -0.0134), (-0.0191, 0.0114)],
        "ece": [0.058, 0.048, 0.052],
        "frames": [35_012, 37_605, 39_663],
        "phase_entries": [612, 612, 554],
    },
}

# Schwellen nach PROTOCOL.md §6
AUC_MIN = 0.60
AUC_LOWER_MIN = 0.50
ECE_MAX = 0.10

PANEL_COLORS = {"normal": "#1f5a96", "hard": "#c0602a"}
BASE_COLOR = "#9a9a9a"


def de(x: float, nd: int) -> str:
    """Zahl mit deutschem Dezimalkomma, erst hier gerundet."""
    s = f"{x:.{nd}f}".replace("-", "−")
    return s.replace(".", ",")


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    """95-%-Wilson-Intervall für k Erfolge aus n (nur Szenenunsicherheit)."""
    p = k / n
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return center - half, center + half


COMMA = FuncFormatter(lambda v, _pos: f"{v:g}".replace("-", "−").replace(".", ","))


def style_axes(ax) -> None:
    ax.yaxis.set_major_formatter(COMMA)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_xticks(range(len(PARENTS)))
    ax.set_xticklabels([f"Parent {p}" for p in PARENTS])
    ax.grid(axis="y", color="#e3e3e3", linewidth=0.8)
    ax.set_axisbelow(True)


def footer(fig, text: str) -> None:
    fig.text(0.01, 0.01, text, ha="left", va="bottom", fontsize=8, color="#555555")


# -----------------------------------------------------------------------------
def fig_pretraining() -> Path:
    x = np.arange(len(PARENTS))
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.4), sharey=True)
    series = [
        ("last_mean_loss", "Letzter mittlerer Trainingsloss", "#4b6f8f"),
        ("train_mse", "MSE auf eigenen Trainingsdaten", "#7a9a5a"),
    ]
    ymax = max(max(PRETRAIN[k]) for k, _, _ in series) * 1.25
    for ax, (key, title, color) in zip(axes, series):
        vals = PRETRAIN[key]
        ax.bar(x, vals, width=0.55, color=color)
        for xi, v in zip(x, vals):
            ax.text(xi, v + ymax * 0.015, de(v, 4), ha="center", va="bottom", fontsize=9)
        ax.set_title(title, fontsize=11)
        ax.set_ylim(0, ymax)
        style_axes(ax)
    axes[0].set_ylabel("Quadratischer Fehler (Return²)")
    for xi, s in zip(x, PRETRAIN["seconds"]):
        axes[1].text(xi, -ymax * 0.17, f"{de(s, 1)} s", ha="center", fontsize=8, color="#555555")
    fig.suptitle(
        "N2-2 · Critic-Vortraining je A-Parent (Twin-Q, Regression auf diskontierten Return, γ = 0,995)",
        fontsize=11.5,
    )
    footer(
        fig,
        f"Je Parent ein Critic auf den {PRETRAIN['episodes_per_parent']} N2-1-Episoden dieses Parents; "
        f"{PRETRAIN['updates']:,}".replace(",", ".")
        + f" Updates, Batch {PRETRAIN['batch']}, Laufzeit unter den Balken rechts.\n"
        "Nur Endwerte (keine Kurve), Trainingsdaten – keine Aussage über Validierung oder Aufgabenerfolg.\n"
        f"n = 3 unabhängige Parent-Initialisierungen (Critic-Seeds 7101–7103). {SOURCE}",
    )
    fig.tight_layout(rect=(0, 0.14, 1, 0.94))
    path = OUT / "01_vortraining_loss.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


# -----------------------------------------------------------------------------
def fig_validation() -> Path:
    x = np.arange(len(PARENTS))
    fig, axes = plt.subplots(2, 4, figsize=(17, 8.6))
    for row, key in enumerate(["normal", "hard"]):
        d = VALIDATION[key]
        c = PANEL_COLORS[key]

        # (a) gewichtete AUC
        ax = axes[row, 0]
        lo = [d["auc"][i] - d["auc_ci"][i][0] for i in range(3)]
        hi = [d["auc_ci"][i][1] - d["auc"][i] for i in range(3)]
        ax.errorbar(x, d["auc"], yerr=[lo, hi], fmt="o", color=c, capsize=5, ms=7)
        ax.axhline(AUC_MIN, color="#2a2a2a", ls="--", lw=1)
        ax.axhline(AUC_LOWER_MIN, color="#2a2a2a", ls=":", lw=1)
        ax.text(2.45, AUC_MIN + 0.01, "AUC ≥ 0,60", ha="right", fontsize=8)
        ax.text(2.45, AUC_LOWER_MIN + 0.01, "untere KI-Grenze > 0,50", ha="right", fontsize=8)
        for xi, v, e in zip(x, d["auc"], d["eligible"]):
            ax.text(xi + 0.12, v, f"{de(v, 3)}\n{e}/{N_POINTS_TOTAL} Pkt.", va="center", fontsize=8)
        ax.set_ylim(0.45, 1.0)
        ax.set_xlim(-0.5, 2.6)
        ax.set_ylabel("gewichtete AUC [95-%-KI]")
        ax.set_title("Erfolgstrennung (AUC)", fontsize=10.5)

        # (b) MSE Critic vs Phasen-Baseline
        ax = axes[row, 1]
        w = 0.36
        ax.bar(x - w / 2, d["mse_critic"], w, color=c, label="Critic")
        ax.bar(x + w / 2, d["mse_base"], w, color=BASE_COLOR, label="Phasen-Baseline")
        for xi, a, b in zip(x, d["mse_critic"], d["mse_base"]):
            ax.text(xi - w / 2, a + 0.0007, de(a, 4), ha="center", fontsize=7.5)
            ax.text(xi + w / 2, b + 0.0007, de(b, 4), ha="center", fontsize=7.5)
        ax.set_ylim(0, 0.066)
        ax.set_ylabel("MSE an Phasenpunkten (Return²)")
        ax.set_title("MSE: Critic vs. Phasen-Baseline", fontsize=10.5)
        ax.legend(fontsize=8, frameon=False, loc="upper center", ncol=2)

        # (c) MSE-Differenz
        ax = axes[row, 2]
        lo = [d["diff"][i] - d["diff_ci"][i][0] for i in range(3)]
        hi = [d["diff_ci"][i][1] - d["diff"][i] for i in range(3)]
        ax.errorbar(x, d["diff"], yerr=[lo, hi], fmt="s", color=c, capsize=5, ms=6)
        ax.axhline(0, color="#2a2a2a", ls="--", lw=1)
        ax.text(2.45, 0.0008, "Bedingung: KI vollständig < 0", ha="right", fontsize=8)
        for i, xi in enumerate(x):
            txt = de(d["diff"][i], 4)
            if d["diff_ci"][i][1] >= 0:
                txt += "\nKI schließt 0 ein"
            ax.text(xi + 0.12, d["diff"][i], txt, va="center", fontsize=8,
                    color="#b00020" if d["diff_ci"][i][1] >= 0 else "black")
        ax.set_ylim(-0.035, 0.016)
        ax.set_xlim(-0.5, 2.6)
        ax.set_ylabel("MSE Critic − MSE Baseline [95-%-KI]")
        ax.set_title("MSE-Differenz (negativ = Critic besser)", fontsize=10.5)

        # (d) ECE
        ax = axes[row, 3]
        ax.bar(x, d["ece"], 0.55, color=c)
        ax.axhline(ECE_MAX, color="#2a2a2a", ls="--", lw=1)
        ax.text(2.4, ECE_MAX + 0.002, "ECE ≤ 0,10", ha="right", fontsize=8)
        for xi, v in zip(x, d["ece"]):
            ax.text(xi, v + 0.002, de(v, 3), ha="center", fontsize=8.5)
        ax.set_ylim(0, 0.12)
        ax.set_ylabel("ECE (10 Klassen auf [0, 1])")
        ax.set_title("Kalibrierung (ECE)", fontsize=10.5)

        for ax in axes[row]:
            style_axes(ax)
        axes[row, 0].annotate(
            d["label"], xy=(0, 1.13), xycoords="axes fraction", fontsize=11.5,
            fontweight="bold", color=c,
        )

    fig.suptitle(
        "N2-2 · Critic-Validierung nach §6 gegen die Phasen-Baseline (A-Rollouts, 0 Optimizerupdates)",
        fontsize=12.5,
    )
    footer(
        fig,
        "KI: 95-%-Perzentil-Bootstrap über Familien (2.000 Ziehungen, Seed 7300, je Parent und Panel); erfasst nur die Szenenunsicherheit, "
        "nicht die Streuung über neues Training (n = 3 Parents).\n"
        "Pkt.: geeignete Phasenpunkte (≥ 10 Erfolge und ≥ 10 Fehlschläge) von 14. Entscheidung nach §6: alle drei Critics bestehen auf "
        "validation_normal. validation_hard wird getrennt berichtet; Parent 3 verfehlt dort Bedingung 3 (ohne Einfluss).\n"
        f"Endlichkeit aller Criticwerte separat in Abb. 04. {SOURCE}",
    )
    fig.tight_layout(rect=(0, 0.08, 1, 0.93), h_pad=4.0)
    path = OUT / "02_critic_validierung.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


# -----------------------------------------------------------------------------
def fig_bc_success() -> Path:
    x = np.arange(len(PARENTS))
    w = 0.36
    fig, ax = plt.subplots(figsize=(9, 5))
    for off, key in [(-w / 2, "normal"), (w / 2, "hard")]:
        d = VALIDATION[key]
        rates = [k / d["n"] for k in d["successes"]]
        cis = [wilson(k, d["n"]) for k in d["successes"]]
        lo = [r - ci[0] for r, ci in zip(rates, cis)]
        hi = [ci[1] - r for r, ci in zip(rates, cis)]
        ax.bar(x + off, [100 * r for r in rates], w, color=PANEL_COLORS[key],
               yerr=[[100 * v for v in lo], [100 * v for v in hi]], capsize=4,
               error_kw={"lw": 1, "ecolor": "#333333"},
               label=d["label"].replace(", entscheidet nicht", "").replace(", entscheidet", ""))
        for xi, k, r, ci in zip(x + off, d["successes"], rates, cis):
            ax.text(xi, 100 * ci[1] + 1.5, f"{k}/{d['n']}\n{de(100 * r, 0)} %",
                    ha="center", va="bottom", fontsize=8.5)
    ax.set_ylim(0, 80)
    ax.set_ylabel("Vollständiger Aufgabenerfolg Dreierturm (%) [95-%-Wilson-KI]")
    style_axes(ax)
    ax.legend(fontsize=8.5, frameon=False, loc="upper right")
    ax.set_title(
        "N2-2 · Aufgabenerfolg der unveränderten BC-Parents (A) auf der Validierung",
        fontsize=11.5,
    )
    footer(
        fig,
        "Nenner = alle Familien des Panels, ohne Ausschlüsse; Fehlschläge endeten alle am Horizont (0 Rückzugs-Timeouts, 0 Simulatorinstabilitäten).\n"
        "Wilson-KI nur über Szenenfamilien je Parent, nicht über neues Training; n = 3 unabhängige Parent-Initialisierungen.\n"
        "Validierung, kein Test (Testfamilien geschlossen). Diese Rollouts sind die BC-Referenz und lieferten die Labels der Critic-Validierung.\n"
        f"{SOURCE}",
    )
    fig.tight_layout(rect=(0, 0.15, 1, 1))
    path = OUT / "03_bc_aufgabenerfolg.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


# -----------------------------------------------------------------------------
def fig_stability() -> Path:
    x = np.arange(len(PARENTS))
    w = 0.36
    fig, ax = plt.subplots(figsize=(9, 4.6))
    for off, key in [(-w / 2, "normal"), (w / 2, "hard")]:
        d = VALIDATION[key]
        ax.bar(x + off, [f / 1000 for f in d["frames"]], w, color=PANEL_COLORS[key],
               label=d["label"].split(" (")[0])
        for xi, f, pe in zip(x + off, d["frames"], d["phase_entries"]):
            ax.text(xi, f / 1000 + 1.0, f"{f:,}".replace(",", ".") + f"\n0 nicht endlich\n{pe:,} Pkt.".replace(",", "."),
                    ha="center", va="bottom", fontsize=7.5)
    ax.set_ylim(0, 112)
    ax.set_ylabel("Geprüfte Frames (Tausend)")
    style_axes(ax)
    ax.legend(fontsize=8.5, frameon=False, loc="upper left")
    ax.set_title("N2-2 · Technische Stabilität: Endlichkeit der Criticwerte auf allen Validierungsframes",
                 fontsize=11)
    footer(
        fig,
        "Alle Criticwerte endlich (§6, Bedingung 4). Pkt. = Phasenpunkt-Einträge; 0 Ersatzwerte der Phasen-Baseline, "
        "in keiner Bootstrapziehung entfiel ein Punkt.\n"
        "Lauf ohne Pause/Fortsetzung, Exitcode 0; verify gegen summary.json bestanden. Keine Aussage über Güte oder Aufgabenerfolg.\n"
        f"{SOURCE}",
    )
    fig.tight_layout(rect=(0, 0.13, 1, 1))
    path = OUT / "04_technische_stabilitaet.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def main() -> None:
    plt.rcParams.update({"font.size": 9.5, "font.family": "DejaVu Sans"})
    for p in (fig_pretraining(), fig_validation(), fig_bc_success(), fig_stability()):
        print(p.relative_to(OUT.parents[4]).as_posix())


if __name__ == "__main__":
    main()
