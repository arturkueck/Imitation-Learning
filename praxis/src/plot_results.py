"""Generate measured Lift figures and explicitly hypothetical trend scenarios.

All measured values come from the three committed summary JSON files. The
scenario endpoints below are illustrative assumptions, not statistical fits.
"""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


BC = "#0072B2"
EXT = "#D55E00"
CONDITIONS = [
    ("nominal", "Nominal"),
    ("offset_x_2cm", "Würfel +2 cm"),
    ("offset_x_minus_2cm", "Würfel −2 cm"),
    ("impulse_x_1", "Aktionsimpuls +1"),
    ("impulse_x_minus_1", "Aktionsimpuls −1"),
]


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(fig, directory, name):
    directory.mkdir(parents=True, exist_ok=True)
    fig.savefig(directory / f"{name}.png", dpi=240, bbox_inches="tight")
    fig.savefig(directory / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)


def measured_epochs(full20, full100, out):
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 3.9), sharey=True)
    keys = CONDITIONS[0], CONDITIONS[1], CONDITIONS[3]
    for ax, (key, label) in zip(axes, keys):
        for method, color, title in (
            ("bc", BC, "BC"),
            ("extension", EXT, "BC + Zusatzverlust"),
        ):
            values = [
                100 * report["aggregate"][key][f"{method}_success_rate"]
                for report in (full20, full100)
            ]
            ax.plot([20, 100], values, "o-", color=color, lw=2.3, ms=7, label=title)
            for epoch, report in ((20, full20), (100, full100)):
                seed_rates = [
                    100 * row[f"{method}_successes"] / row["episodes"]
                    for row in report["rows"] if row["condition"] == key
                ]
                ax.vlines(epoch, min(seed_rates), max(seed_rates), color=color,
                          lw=5, alpha=0.20, zorder=0)
        ax.set_title(label)
        ax.set_xlim(10, 110)
        ax.set_xticks([20, 100])
        ax.set_xlabel("Trainingsepochen (gemessen)")
        ax.grid(axis="y", alpha=0.25)
    axes[0].set_ylabel("Erfolgsrate (%)")
    axes[0].set_ylim(0, 105)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.08))
    fig.suptitle("Lift PH · voller Datensatz · Mittel über 3 Trainings-Seeds",
                 y=1.16, fontsize=13, weight="bold")
    fig.text(0.5, -0.05,
             "Punkte: 20 Rollouts je Seed; breite Balken: Spannweite der drei Seed-Raten. "
             "Linien verbinden nur die zwei Messzeitpunkte.",
             ha="center", fontsize=9)
    save(fig, out, "01_gemessene_lernkurven")


def measured_conditions(full100, subset100, out):
    fig, axes = plt.subplots(1, 2, figsize=(12.8, 5.4), sharey=True)
    for ax, report, label in zip(
        axes,
        (full100, subset100),
        ("180 Trainingsdemonstrationen", "36 Trainingsdemonstrationen"),
    ):
        for i, (key, name) in enumerate(CONDITIONS):
            item = report["aggregate"][key]
            b = 100 * item["bc_success_rate"]
            e = 100 * item["extension_success_rate"]
            ax.plot([b, e], [i, i], color="#8B8B8B", lw=2, zorder=1)
            ax.scatter(b, i, s=65, color=BC, zorder=2, label="BC" if i == 0 else None)
            ax.scatter(e, i, s=65, color=EXT, zorder=2,
                       label="BC + Zusatzverlust" if i == 0 else None)
            ax.text(b - 1.2, i - 0.19, f"{item['bc_successes']}/60", color=BC,
                    ha="right", va="center", fontsize=8)
            ax.text(e + 1.2, i + 0.19, f"{item['extension_successes']}/60",
                    color=EXT, ha="left", va="center", fontsize=8)
        ax.set_title(label)
        ax.set_xlabel("Erfolgsrate nach 100 Epochen (%)")
        ax.set_xlim(48, 113)
        ax.grid(axis="x", alpha=0.22)
        ax.set_ylim(len(CONDITIONS) - 0.5, -0.5)
        ax.set_yticks(range(len(CONDITIONS)), [name for _, name in CONDITIONS])
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.04))
    fig.suptitle("Gemessene Lift-Erfolge · gepaarte Rollouts, 3 Seeds × 20 Episoden",
                 y=1.12, fontsize=13, weight="bold")
    fig.text(0.5, -0.03,
             "Die zwei Datensplits wurden mit verschiedenen Rollout-Seeds ausgewertet; "
             "nur BC und Erweiterung innerhalb eines Splits sind gepaart.",
             ha="center", fontsize=9)
    save(fig, out, "02_gemessene_bedingungen")


def scenarios(full20, full100, out):
    observed = {
        method: [
            100 * report["aggregate"]["nominal"][f"{method}_success_rate"]
            for report in (full20, full100)
        ] for method in ("bc", "extension")
    }
    # Deliberately chosen scenario endpoints. They are hypotheses, not model
    # forecasts or confidence bounds. Every curve begins at the measured 100-ep
    # value and reaches its illustrative endpoint at epoch 300.
    endpoints = [
        ("A · BC holt auf", 95, 98),
        ("B · Abstand bleibt", 80, 95),
        ("C · Zusatzverlust schadet später", 90, 85),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.1), sharey=True)
    xs = np.linspace(100, 300, 101)
    smooth = (1 - np.exp(-3 * (xs - 100) / 200)) / (1 - np.exp(-3))
    for ax, (title, bc_end, ext_end) in zip(axes, endpoints):
        ax.axvspan(100, 300, color="#F1F1F1", zorder=0)
        for method, color, endpoint, label in (
            ("bc", BC, bc_end, "BC"),
            ("extension", EXT, ext_end, "BC + Zusatzverlust"),
        ):
            ax.plot([20, 100], observed[method], "o-", color=color,
                    lw=2.2, ms=6, label=label)
            projected = observed[method][1] + (endpoint - observed[method][1]) * smooth
            ax.plot(xs, projected, "--", color=color, lw=2.2)
        ax.axvline(100, color="#777777", lw=0.8)
        ax.set_title(title)
        ax.set_xlim(15, 305)
        ax.set_xticks([20, 100, 200, 300])
        ax.set_xlabel("Trainingsepochen")
        ax.grid(axis="y", alpha=0.2)
    axes[0].set_ylim(0, 105)
    axes[0].set_ylabel("Nominale Erfolgsrate (%)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.08))
    fig.suptitle("Mögliche weitere Verläufe · Hypothesen, keine Prognose aus Daten",
                 y=1.16, fontsize=13, weight="bold")
    fig.text(0.5, -0.05,
             "Durchgezogen: Messpunkte bei 20/100 Epochen. Grau und gestrichelt: "
             "frei gewählte Szenarien bis 300 Epochen; Endpunkte sind keine Schätzwerte.",
             ha="center", fontsize=9)
    save(fig, out, "03_hypothetische_trends")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", type=Path, default=Path("praxis/reports"))
    parser.add_argument("--output-dir", type=Path,
                        default=Path("praxis/reports/figures"))
    args = parser.parse_args()
    full20 = read(args.reports_dir / "lift_ph_full_20ep_summary.json")
    full100 = read(args.reports_dir / "lift_ph_full_100ep_summary.json")
    subset100 = read(args.reports_dir / "lift_ph_20pct_100ep_summary.json")
    measured_epochs(full20, full100, args.output_dir)
    measured_conditions(full100, subset100, args.output_dir)
    scenarios(full20, full100, args.output_dir)
    print(f"Wrote three PNG/PDF pairs to {args.output_dir}")


if __name__ == "__main__":
    main()
