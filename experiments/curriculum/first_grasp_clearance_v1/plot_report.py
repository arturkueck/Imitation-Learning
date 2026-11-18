"""Plot the frozen comparison and the prespecified finger-contact anchor."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np


def plot(out):
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    schema = json.loads((out / "trace_schema.json").read_text(encoding="utf-8"))
    fields = {name: i for i, name in enumerate(schema)}
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), layout="constrained")
    panels = {"known_grasp_failure": "Bekannte Fehler", "normal": "Neue normale Fälle",
              "critical": "Neue kritische Fälle"}
    entries = [(label, summary["outcomes"][key]) for key, label in panels.items()
               if key in summary["outcomes"]]
    pos = np.arange(len(entries))
    for offset, arm, label, color in (
        (-.17, "grasp_timeout", "Timeout", "#8585a6"),
        (.17, "grasp_ready", "Späte Bereitschaft", "#396c98"),
    ):
        y = [100 * (r[arm]["gains"] - r[arm]["losses"]) / r[arm]["n"] for _, r in entries]
        axes[0].barh(pos + offset, y, height=.31, label=label, color=color)
        for at, val, (_, r) in zip(pos, y, entries):
            b = r[arm]
            axes[0].annotate(f"+{b['gains']} / −{b['losses']}", (val, at + offset),
                xytext=(4 if val >= 0 else -4, 0), textcoords="offset points",
                va="center", ha="left" if val >= 0 else "right", fontsize=9)
    axes[0].set_yticks(pos, [f"{label} (n={r['grasp_ready']['n']})" for label, r in entries])
    axes[0].margins(x=.35)
    axes[0].axvline(0, color="#666666", lw=.8)
    axes[0].invert_yaxis()
    axes[0].set(xlabel="Differenz im vollständigen Aufgabenerfolg [Prozentpunkte]",
                title="Erster Griff · Gewinne und Verluste")
    axes[0].legend(fontsize=9)
    for arm, name, color in (("guarded_feedback", "Halten", "#9f5147"),
                             ("withdraw", "Rückzug", "#397b63")):
        with np.load(out / "main/traces" / f"release_g16_failure_{arm}.npz") as archive:
            trace = archive["trace"]
        release = trace[(trace[:, fields["placement"]] == 2) & (trace[:, fields["phase"]] == 6)]
        frame = release[:, fields["steps"]]
        show = frame < 100
        axes[1].plot(frame[show], 1000 * release[show, fields["post_xy"]],
                     label=name, color=color)
        mask = release[show, fields["post_source_finger"]].astype(bool)
        level = 1.0 if arm == "guarded_feedback" else 0.35
        axes[1].fill_between(frame[show], level, level+.4, where=mask,
                             color=color, alpha=.5, step="mid")
        withdrawal = np.flatnonzero(release[:, fields["withdrawing"]])
        if len(withdrawal):
            axes[1].axvline(frame[withdrawal[0]], color=color, ls=":", lw=1, label="Beginn Rückzug")
    axes[1].axhline(9, color="#5f5f5f", ls="--", lw=1, label="XY-Grenze")
    axes[1].set(xlabel="Schritte ab zweiter Freigabe", ylabel="Seitlicher Versatz [mm]",
                title="Bekannter Freigabefehler · Szene 2026189042")
    handles, labels = axes[1].get_legend_handles_labels()
    axes[1].legend(handles + [Patch(facecolor="#777777", alpha=.5)], labels + ["Fingerkontakt je Arm"],
                   fontsize=8)
    fig.savefig(out / "befunde.png", dpi=170)
    fig.savefig(out / "befunde.pdf")
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    plot(parser.parse_args().output)
