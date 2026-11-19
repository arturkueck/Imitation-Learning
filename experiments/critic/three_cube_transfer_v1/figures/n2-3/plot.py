"""Abbildungen zu N2-3 (technischer Actor-Critic-Smoke, Stufe δ_max = 0,05).

Quelle sind ausschließlich die verifizierten Werte aus
experiments/critic/three_cube_transfer_v1/AC_SMOKE.md, Abschnitt
"Ergebnis (Abschluss 19.11.2026)" (Monitor: result_verified). Die Werte sind
unten so übernommen, wie sie dort stehen (Berichtsgenauigkeit). Gerundet wird
erst bei der Anzeige. Es werden keine Rohtrajektorien, Gewichte, Laufordner
oder Testfamilien gelesen; der Generator liest überhaupt keine Dateien.

Aufruf aus dem Repository-Stamm:
    ./praxis/.venv/Scripts/python.exe experiments/critic/three_cube_transfer_v1/figures/n2-3/plot.py
"""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

OUT = Path(__file__).resolve().parent
SOURCE = "Quelle: AC_SMOKE.md (N2-3, Stufe δ_max = 0,05, result_verified 19.11.2026)"

PARENTS = [1, 2, 3]
VARIANTS = ["AC-IL", "AC-neu"]
ROUNDS = [0, 1, 2]

# --- Grenzen nach PROTOCOL.md §7 / AC_SMOKE.md --------------------------------
DELTA_MAX = 0.05
Q_LOW, Q_HIGH = -0.05, 1.05
BATCH = 256
ESS_MIN = 25.6  # 10 % von 256
W_CAP = 20
LOST_PER_PARENT_MAX = 2
LOST_TOTAL_MAX = 3
N_DEV = 20  # constraint_development, 2100003650–2100003669
N_ONLINE_ROUND = 10  # smoke_interaction je Runde

# --- Tabelle "Lauf" (Ergebnis) ------------------------------------------------
# Schlüssel (Variante, Parent)
RUNS = {
    ("AC-IL", 1): dict(q_after=(-0.153, 1.006), q_updates=(-0.464, 1.100), ess=255.9, dev=5, lost=[], online=8),
    ("AC-IL", 2): dict(q_after=(-0.163, 1.013), q_updates=(-0.284, 1.323), ess=255.8, dev=3, lost=[2100003658], online=8),
    ("AC-IL", 3): dict(q_after=(-0.173, 1.016), q_updates=(-0.223, 1.059), ess=255.9, dev=6, lost=[], online=7),
    ("AC-neu", 1): dict(q_after=(-0.082, 0.173), q_updates=(-0.127, 0.161), ess=256.0, dev=5, lost=[], online=8),
    ("AC-neu", 2): dict(q_after=(-0.058, 0.055), q_updates=(-0.094, 0.122), ess=256.0, dev=3, lost=[2100003658], online=9),
    ("AC-neu", 3): dict(q_after=(-0.203, 0.068), q_updates=(-0.102, 0.131), ess=256.0, dev=6, lost=[], online=7),
}
PARENT_BASELINE = {1: 5, 2: 4, 3: 6}  # k/20 auf constraint_development
GAINED = 0  # neue Erfolge: keine
BOUND_VIOLATIONS = 0  # alle Läufe
ALL_FINITE = True  # alle Läufe

# --- Tabelle "Verlauf je Runde" -----------------------------------------------
# je Runde: online k/10, Critic-Loss (Mittel), Replay-Q, Probe-Q (Parentaktion),
# Drift XYZ Mittel / Max (begrenzt), Max unbegrenzt, w_max.
# Runde 0: vor dem ersten Update; kein Online/Loss/Replay/w_max.
# Unbegrenzte Drift in Runde 0 ist 0, weil der Actor vor dem ersten Update
# identisch mit dem Parent ist (PROTOCOL.md §8, Prüfung in ac_smoke.py).
HISTORY = {
    ("AC-IL", 1): [
        dict(online=None, loss=None, replay=None, probe=(-0.084, 0.873), mean=0.0, max=0.0, raw_max=0.0, w_max=None),
        dict(online=5, loss=0.00124, replay=(-0.125, 1.006), probe=(-0.125, 0.823), mean=0.0035, max=0.0302, raw_max=0.0392, w_max=1.27),
        dict(online=3, loss=0.00067, replay=(-0.153, 1.005), probe=(-0.106, 0.837), mean=0.0037, max=0.0276, raw_max=0.0330, w_max=1.30),
    ],
    ("AC-IL", 2): [
        dict(online=None, loss=None, replay=None, probe=(-0.123, 0.954), mean=0.0, max=0.0, raw_max=0.0, w_max=None),
        dict(online=5, loss=0.00119, replay=(-0.095, 1.013), probe=(-0.162, 0.886), mean=0.0037, max=0.0403, raw_max=0.0896, w_max=1.54),
        dict(online=3, loss=0.00054, replay=(-0.080, 1.013), probe=(-0.139, 0.860), mean=0.0041, max=0.0373, raw_max=0.0636, w_max=1.55),
    ],
    ("AC-IL", 3): [
        dict(online=None, loss=None, replay=None, probe=(-0.091, 0.902), mean=0.0, max=0.0, raw_max=0.0, w_max=None),
        dict(online=5, loss=0.00094, replay=(-0.049, 1.016), probe=(-0.173, 0.876), mean=0.0038, max=0.0307, raw_max=0.0389, w_max=1.34),
        dict(online=2, loss=0.00048, replay=(-0.071, 1.007), probe=(-0.145, 0.899), mean=0.0032, max=0.0396, raw_max=0.0544, w_max=1.29),
    ],
    ("AC-neu", 1): [
        dict(online=None, loss=None, replay=None, probe=(-0.200, 0.122), mean=0.0, max=0.0, raw_max=0.0, w_max=None),
        dict(online=5, loss=0.00202, replay=(-0.031, 0.085), probe=(-0.082, 0.173), mean=0.0031, max=0.0287, raw_max=0.0360, w_max=1.01),
        dict(online=3, loss=0.00174, replay=(-0.032, 0.080), probe=(-0.026, 0.107), mean=0.0033, max=0.0352, raw_max=0.0438, w_max=1.01),
    ],
    ("AC-neu", 2): [
        dict(online=None, loss=None, replay=None, probe=(-0.214, 0.097), mean=0.0, max=0.0, raw_max=0.0, w_max=None),
        dict(online=5, loss=0.00191, replay=(-0.018, 0.038), probe=(-0.058, 0.051), mean=0.0043, max=0.0361, raw_max=0.0693, w_max=1.01),
        dict(online=4, loss=0.00145, replay=(-0.014, 0.053), probe=(-0.034, 0.055), mean=0.0043, max=0.0408, raw_max=0.0597, w_max=1.01),
    ],
    ("AC-neu", 3): [
        dict(online=None, loss=None, replay=None, probe=(-0.235, 0.068), mean=0.0, max=0.0, raw_max=0.0, w_max=None),
        dict(online=5, loss=0.00169, replay=(-0.028, 0.039), probe=(-0.203, 0.068), mean=0.0032, max=0.0257, raw_max=0.0293, w_max=1.01),
        dict(online=2, loss=0.00132, replay=(-0.020, 0.040), probe=(-0.150, 0.035), mean=0.0033, max=0.0297, raw_max=0.0363, w_max=1.01),
    ],
}

VARIANT_COLORS = {"AC-IL": "#1f5a96", "AC-neu": "#c0602a"}
PARENT_MARKERS = {1: "o", 2: "s", 3: "^"}
PARENT_LS = {1: "-", 2: "--", 3: ":"}
BASE_COLOR = "#8a8a8a"
FAIL = "#b00020"
PASS = "#2e7d32"
BAND = "#d8ecd9"


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


def tidy(ax) -> None:
    ax.yaxis.set_major_formatter(COMMA)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="#e3e3e3", linewidth=0.8)
    ax.set_axisbelow(True)


def footer(fig, text: str) -> None:
    fig.text(0.01, 0.01, text, ha="left", va="bottom", fontsize=8, color="#555555")


def spread(values: list[float], min_gap: float) -> list[float]:
    """Labelpositionen mit Mindestabstand (nur Anzeige, Werte bleiben unverändert)."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    pos = [0.0] * len(values)
    last = -math.inf
    for i in order:
        pos[i] = max(values[i], last + min_gap)
        last = pos[i]
    shift = (sum(pos) - sum(values)) / len(values)
    return [p - shift for p in pos]


def run_order() -> list[tuple[str, int]]:
    return [(v, p) for v in VARIANTS for p in PARENTS]


def run_label(key: tuple[str, int]) -> str:
    return f"{key[0]}\nP{key[1]}"


# -----------------------------------------------------------------------------
def fig_drift() -> Path:
    cols = [
        ("mean", "Mittlere |Δa| XYZ, begrenzt", "mittlere Abweichung vom Parent"),
        ("max", "Maximale |Δa| XYZ, begrenzt (ausgeführt)", "maximale Abweichung vom Parent"),
        ("raw_max", "Maximale |Δa| XYZ, unbegrenzte Actorausgabe", "maximale Abweichung vom Parent"),
    ]
    ylims = {"mean": 0.006, "max": 0.105, "raw_max": 0.105}
    fig, axes = plt.subplots(2, 3, figsize=(15, 8.2), sharex=True)
    for r, variant in enumerate(VARIANTS):
        for c, (key, title, ylab) in enumerate(cols):
            ax = axes[r, c]
            finals = []
            for p in PARENTS:
                ys = [h[key] for h in HISTORY[(variant, p)]]
                ax.plot(ROUNDS, ys, color=VARIANT_COLORS[variant], ls=PARENT_LS[p],
                        marker=PARENT_MARKERS[p], ms=6, lw=1.6, label=f"Parent {p}")
                finals.append(ys[-1])
            for p, y, yl in zip(PARENTS, finals, spread(finals, ylims[key] * 0.06)):
                ax.text(2.07, yl, f"P{p}: {de(y, 4)}", va="center", fontsize=8,
                        color=VARIANT_COLORS[variant])
            if key in ("max", "raw_max"):
                ax.axhline(DELTA_MAX, color="#2a2a2a", ls="--", lw=1, label="δ_max = 0,05 (Grenze je Achse)")
            ax.legend(fontsize=8, frameon=False, loc="upper left")
            ax.set_ylim(0, ylims[key])
            ax.set_xlim(-0.2, 2.6)
            ax.set_xticks(ROUNDS)
            ax.set_xticklabels(["0\n(vor Update)", "1\n(250 C / 125 A)", "2\n(500 C / 250 A)"])
            ax.set_ylabel(f"{ylab}\n(normierte Aktionseinheiten)")
            ax.set_title(title, fontsize=10.5)
            tidy(ax)
            if r == 1:
                ax.set_xlabel("Runde (kumulierte Critic- / Actorupdates)")
        axes[r, 0].annotate(f"{variant}", xy=(0, 1.12), xycoords="axes fraction", fontsize=12,
                            fontweight="bold", color=VARIANT_COLORS[variant])
    fig.suptitle(
        "N2-3 · Actor-Drift gegenüber dem eingefrorenen A-Parent über die beiden Runden (Stufe δ_max = 0,05, λ = 0,1)",
        fontsize=12.5,
    )
    footer(
        fig,
        "|Δa| = Betrag der Abweichung je XYZ-Komponente (Aktionsraum [−1; 1]) zwischen Actor- und Parentaktion auf festen Probeframes "
        "(64 Critic-Datenframes je Policy-Phase des Parents, Seed 7400 + p).\n"
        "Begrenzt: nach Projektion b_xyz = min(δ_max, 0,5·|a_p|); unbegrenzt: rohe Actorausgabe vor der Projektion. "
        "Runde 0: Actor = Parent, alle Abweichungen 0 (vor dem ersten Update geprüft).\n"
        "Drift ist ein technisches Maß der Bindung an den Parent, kein Loss und kein Aufgabenerfolg. n = 3 Parents je Variante; "
        f"keine Intervalle (je Lauf ein Wert).\n{SOURCE}",
    )
    fig.tight_layout(rect=(0, 0.1, 1, 0.94), h_pad=3.5)
    path = OUT / "01_actor_drift.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


# -----------------------------------------------------------------------------
def fig_q_range() -> Path:
    keys = run_order()
    x = np.arange(len(keys), dtype=float)
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.axhspan(Q_LOW, Q_HIGH, color=BAND, zorder=0)
    ax.axhline(Q_LOW, color=PASS, lw=1)
    ax.axhline(Q_HIGH, color=PASS, lw=1)
    off = 0.14
    for xi, key in zip(x, keys):
        d = RUNS[key]
        col = VARIANT_COLORS[key[0]]
        lo, hi = d["q_after"]
        ax.vlines(xi - off, lo, hi, color=col, lw=9, zorder=3)
        ulo, uhi = d["q_updates"]
        ax.vlines(xi + off, ulo, uhi, color=col, lw=3, alpha=0.55, zorder=3)
        ax.text(xi - off - 0.07, lo, de(lo, 3), ha="right", va="center", fontsize=8,
                color=FAIL if lo < Q_LOW else "black")
        ax.text(xi - off - 0.07, hi, de(hi, 3), ha="right", va="center", fontsize=8,
                color=FAIL if hi > Q_HIGH else "black")
        ax.text(xi + off + 0.07, ulo, de(ulo, 3), ha="left", va="center", fontsize=7.5, color="#555555")
        ax.text(xi + off + 0.07, uhi, de(uhi, 3), ha="left", va="center", fontsize=7.5, color="#555555")
        ok = Q_LOW <= lo and hi <= Q_HIGH
        ax.text(xi, -0.6, "im Bereich" if ok else "verletzt", ha="center", fontsize=8.5,
                color=PASS if ok else FAIL, fontweight="bold")
    ax.text(-0.75, Q_HIGH + 0.012, "1,05", fontsize=8, color=PASS, va="bottom", ha="left")
    ax.text(-0.75, Q_LOW - 0.012, "−0,05", fontsize=8, color=PASS, va="top", ha="left")
    ax.set_xticks(x)
    ax.set_xticklabels([run_label(k) for k in keys])
    ax.set_xlim(-0.8, len(keys) - 0.4)
    ax.set_ylim(-0.66, 1.6)
    ax.set_yticks([-0.5, -0.25, 0, 0.25, 0.5, 0.75, 1.0, 1.25])
    ax.set_ylabel("Q (min. Twin-Critic; diskontierter Erfolgsreturn, dimensionslos)")
    tidy(ax)
    handles = [
        Patch(color=BAND, label="zulässiger Bereich [−0,05; 1,05] (§7)"),
        Line2D([], [], color="#444444", lw=9, label="nach Runde 1 und 2: Replay + Probeframes (entscheidend)"),
        Line2D([], [], color="#444444", lw=3, alpha=0.55, label="während der Updates inkl. Initialisierung (nur berichtet)"),
    ]
    ax.legend(handles=handles, fontsize=8.5, frameon=False, loc="upper center", ncol=3,
              bbox_to_anchor=(0.5, 1.0))
    ax.set_title("N2-3 · Technische Stabilität: Q-Bereichsprüfung je Lauf – alle 6 Läufe verfehlen sie, Stufe 0,05 nicht bestanden",
                 fontsize=11.5)
    footer(
        fig,
        "Balken = [min; max] über alle Prüfwerte eines Laufs (Runde 1 und 2: Replay mit ausgeführten Aktionen, Probeframes mit Parent- und begrenzter Actoraktion). "
        "Runde 0 geht nicht ein (Verlauf in Abb. 03).\n"
        "Alle Q-Werte endlich. Farbe = Variante (AC-IL: N2-2-Critic, AC-neu: frischer Critic). Q ist eine Criticausgabe, kein Loss und kein Aufgabenerfolg.\n"
        f"{SOURCE}",
    )
    fig.tight_layout(rect=(0, 0.09, 1, 1))
    path = OUT / "02_q_bereich.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


# -----------------------------------------------------------------------------
def fig_q_rounds() -> Path:
    fig, axes = plt.subplots(2, 3, figsize=(14, 8), sharey=True)
    off = 0.11
    for r, variant in enumerate(VARIANTS):
        col = VARIANT_COLORS[variant]
        for c, p in enumerate(PARENTS):
            ax = axes[r, c]
            ax.axhspan(Q_LOW, Q_HIGH, color=BAND, zorder=0)
            ax.axhline(Q_LOW, color=PASS, lw=0.9)
            ax.axhline(Q_HIGH, color=PASS, lw=0.9)
            ax.axvspan(-0.4, 0.4, color="#f1f1f1", zorder=0.5)
            for rd, h in zip(ROUNDS, HISTORY[(variant, p)]):
                lo, hi = h["probe"]
                ax.vlines(rd - off, lo, hi, color=col, lw=7, zorder=3)
                ax.text(rd - off - 0.06, lo, de(lo, 3), ha="right", va="center", fontsize=7.5,
                        color=FAIL if lo < Q_LOW else "black")
                if h["replay"] is not None:
                    rlo, rhi = h["replay"]
                    ax.vlines(rd + off, rlo, rhi, color="#555555", lw=4, zorder=3)
                    ax.text(rd + off + 0.06, rlo, de(rlo, 3), ha="left", va="center", fontsize=7.5,
                            color=FAIL if rlo < Q_LOW else "black")
            ax.text(0, 1.33, "nicht bewertet", ha="center", fontsize=8, color="#666666")
            ax.set_xticks(ROUNDS)
            ax.set_xticklabels(["0\n(vor Update)", "1", "2"])
            ax.set_xlim(-0.5, 2.5)
            ax.set_ylim(-0.32, 1.42)
            ax.set_title(f"{variant} · Parent {p}", fontsize=10.5, color=col)
            tidy(ax)
            if c == 0:
                ax.set_ylabel("Q [min; max] (diskontierter Erfolgsreturn)")
            if r == 1:
                ax.set_xlabel("Runde")
    handles = [
        Patch(color=BAND, label="zulässig [−0,05; 1,05]"),
        Line2D([], [], color=VARIANT_COLORS["AC-IL"], lw=7, label="Probeframes, Parentaktion (AC-IL)"),
        Line2D([], [], color=VARIANT_COLORS["AC-neu"], lw=7, label="Probeframes, Parentaktion (AC-neu)"),
        Line2D([], [], color="#555555", lw=4, label="Replay, ausgeführte Aktionen (ab Runde 1)"),
    ]
    fig.legend(handles=handles, fontsize=8.5, frameon=False, loc="upper center", ncol=4,
               bbox_to_anchor=(0.5, 0.955))
    fig.suptitle("N2-3 · Q-Spannen je Runde: Unterschreitungen von −0,05 bestehen schon vor dem ersten Update",
                 fontsize=12.5)
    footer(
        fig,
        "Runde 0 (grau hinterlegt): AC-IL = eingefrorener N2-2-Critic, AC-neu = zufällige Initialisierung (Seed 7100 + p); geht nach der eingefrorenen Regel nicht in die Bewertung ein.\n"
        "Probe-Q an der begrenzten Actoraktion weicht laut Bericht höchstens 0,001 von der Parentaktion ab und ist daher nicht getrennt gezeichnet. "
        "Zahlen = jeweiliges Minimum (rot: < −0,05).\nTechnische Stabilität, kein Loss und kein Aufgabenerfolg. "
        f"{SOURCE}",
    )
    fig.tight_layout(rect=(0, 0.09, 1, 0.92), h_pad=2.5)
    path = OUT / "03_q_verlauf_runden.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


# -----------------------------------------------------------------------------
def fig_stability_criteria() -> Path:
    keys = run_order()
    x = np.arange(len(keys), dtype=float)
    fig = plt.figure(figsize=(15, 5.6))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.0, 1.0, 1.25])

    # (a) ESS
    ax = fig.add_subplot(gs[0])
    ax.bar(x, [RUNS[k]["ess"] for k in keys], 0.6, color=[VARIANT_COLORS[k[0]] for k in keys])
    ax.axhline(ESS_MIN, color="#2a2a2a", ls="--", lw=1)
    ax.axhline(BATCH, color="#999999", ls=":", lw=1)
    ax.text(-0.4, ESS_MIN + 4, "Grenze ≥ 25,6 (10 % von 256)", fontsize=8,
            bbox=dict(facecolor="white", edgecolor="none", alpha=0.9, pad=1.5))
    ax.text(-0.4, BATCH + 4, "Batchgröße 256 = gleichförmige Gewichte", fontsize=8, color="#666666")
    for xi, k in zip(x, keys):
        ax.text(xi, RUNS[k]["ess"] - 22, de(RUNS[k]["ess"], 1), ha="center", fontsize=8, color="white",
                rotation=90, va="top")
    ax.set_ylim(0, 290)
    ax.set_xticks(x)
    ax.set_xticklabels([run_label(k) for k in keys], fontsize=8.5)
    ax.set_ylabel("ESS = (Σw)²/Σw² (Mittel über 250 Actorupdates)")
    ax.set_title("(a) Effektive Stichprobengröße", fontsize=10.5)
    tidy(ax)

    # (b) w_max je Runde
    ax = fig.add_subplot(gs[1])
    w = 0.36
    for j, rd in enumerate([1, 2]):
        vals = [HISTORY[k][rd]["w_max"] for k in keys]
        ax.bar(x + (j - 0.5) * w, vals, w, color=[VARIANT_COLORS[k[0]] for k in keys],
               alpha=0.55 if rd == 1 else 1.0, edgecolor="white")
        for xi, v in zip(x + (j - 0.5) * w, vals):
            ax.text(xi, v + 0.02, de(v, 2), ha="center", fontsize=7, rotation=90, va="bottom")
    ax.axhline(1.0, color="#999999", ls=":", lw=1)
    ax.set_ylim(0, 2.0)
    ax.set_xticks(x)
    ax.set_xticklabels([run_label(k) for k in keys], fontsize=8.5)
    ax.set_ylabel("größtes AWAC-Gewicht w_max je Runde")
    ax.set_title(f"(b) w_max (Kappung bei {W_CAP}, 0 % gekappt)", fontsize=10.5)
    ax.legend(handles=[Patch(color="#777777", alpha=0.55, label="Runde 1"), Patch(color="#777777", label="Runde 2")],
              fontsize=8, frameon=False, loc="upper right")
    tidy(ax)

    # (c) Matrix der technischen §7-Kriterien
    ax = fig.add_subplot(gs[2])
    rows = [
        ("Alle Losses, Q, Gewichte,\nAktionen endlich", [ALL_FINITE] * 6),
        ("Q in [−0,05; 1,05]\n(Replay + Probe, R1–R2)",
         [Q_LOW <= RUNS[k]["q_after"][0] and RUNS[k]["q_after"][1] <= Q_HIGH for k in keys]),
        (f"Grenzverletzungen = 0\n(gezählt: {BOUND_VIOLATIONS})", [BOUND_VIOLATIONS == 0] * 6),
        ("ESS ≥ 25,6", [RUNS[k]["ess"] >= ESS_MIN for k in keys]),
    ]
    for i, (_, flags) in enumerate(rows):
        for j, ok in enumerate(flags):
            ax.add_patch(plt.Rectangle((j - 0.45, i - 0.4), 0.9, 0.8, color=PASS if ok else FAIL, alpha=0.85))
            ax.text(j, i, "erfüllt" if ok else "verfehlt", ha="center", va="center", color="white",
                    fontsize=8, fontweight="bold")
    ax.set_xlim(-0.5, 5.5)
    ax.set_ylim(len(rows) - 0.5, -0.5)
    ax.set_xticks(range(6))
    ax.set_xticklabels([run_label(k) for k in keys], fontsize=8.5)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows], fontsize=8.5)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title("(c) Technische Kriterien nach §7 je Lauf", fontsize=10.5)

    fig.suptitle("N2-3 · Technische Stabilität der Stufe δ_max = 0,05 (je Lauf, 500 Critic- / 250 Actorupdates)",
                 fontsize=12.5)
    footer(
        fig,
        "Farbe in (a)/(b) = Variante (blau AC-IL, orange AC-neu). Gewichte w = min(exp(A/λ), 20), λ = 0,1: praktisch gleichförmig, "
        "das Actorupdate wirkt nahezu wie ungewichtete Regression.\n"
        "Das vierte §7-Kriterium (verlorene Parent-Erfolge) betrifft den Aufgabenerfolg und steht getrennt in Abb. 05 (erfüllt). "
        "Entscheidend für das Nichtbestehen ist allein der Q-Bereich.\n"
        f"Keine Intervalle: je Lauf ein Wert, n = 3 Parents je Variante. {SOURCE}",
    )
    fig.tight_layout(rect=(0, 0.11, 1, 0.94))
    path = OUT / "04_stabilitaetskriterien.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


# -----------------------------------------------------------------------------
def fig_parent_success() -> Path:
    fig = plt.figure(figsize=(15.5, 6.0))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.55, 0.85, 1.0])

    # (a) Entwicklungserfolg k/20 je Parent: Baseline, AC-IL, AC-neu
    ax = fig.add_subplot(gs[0])
    x = np.arange(len(PARENTS), dtype=float)
    w = 0.26
    series = [("Parent (unverändert)", BASE_COLOR, lambda p: PARENT_BASELINE[p], -w),
              ("AC-IL nach Runde 2", VARIANT_COLORS["AC-IL"], lambda p: RUNS[("AC-IL", p)]["dev"], 0.0),
              ("AC-neu nach Runde 2", VARIANT_COLORS["AC-neu"], lambda p: RUNS[("AC-neu", p)]["dev"], w)]
    for label, color, get, o in series:
        ks = [get(p) for p in PARENTS]
        rates = [100 * k / N_DEV for k in ks]
        cis = [wilson(k, N_DEV) for k in ks]
        lo = [r - 100 * ci[0] for r, ci in zip(rates, cis)]
        hi = [100 * ci[1] - r for r, ci in zip(rates, cis)]
        ax.bar(x + o, rates, w, color=color, label=label, yerr=[lo, hi], capsize=3,
               error_kw={"lw": 0.9, "ecolor": "#333333"})
        for xi, k, ci, p in zip(x + o, ks, cis, PARENTS):
            lost = RUNS[(label.split()[0], p)]["lost"] if label.startswith("AC") else []
            txt = f"{k}/{N_DEV}" + (f"\n−{len(lost)} verl." if lost else "")
            ax.text(xi, 100 * ci[1] + 1.5, txt, ha="center", fontsize=8.5,
                    color=FAIL if lost else "black")
    ax.set_xticks(x)
    ax.set_xticklabels([f"Parent {p}" for p in PARENTS])
    ax.set_ylim(0, 72)
    ax.set_ylabel("Vollständiger Erfolg Dreierturm (%) [95-%-Wilson-KI]")
    ax.set_title("(a) constraint_development, 20 Familien, deterministisch ohne Rauschen", fontsize=10.5)
    ax.legend(fontsize=8.5, frameon=False, loc="upper left")
    tidy(ax)

    # (b) verlorene Parent-Erfolge, Lesart B (je Parent über beide Varianten)
    ax = fig.add_subplot(gs[1])
    bottom = np.zeros(len(PARENTS))
    for v in VARIANTS:
        vals = np.array([len(RUNS[(v, p)]["lost"]) for p in PARENTS], dtype=float)
        ax.bar(x, vals, 0.55, bottom=bottom, color=VARIANT_COLORS[v], label=f"verloren in {v}")
        bottom += vals
    ax.axhline(LOST_PER_PARENT_MAX, color="#2a2a2a", ls="--", lw=1)
    ax.text(-0.4, LOST_PER_PARENT_MAX + 0.06, "≤ 2 je Parent", fontsize=8)
    for xi, b in zip(x, bottom):
        ax.text(xi, b + 0.06, f"{int(b)}", ha="center", fontsize=9)
    total_b = int(bottom.sum())
    ax.set_xticks(x)
    ax.set_xticklabels([f"Parent {p}" for p in PARENTS])
    ax.set_ylim(0, 3.4)
    ax.set_yticks([0, 1, 2, 3])
    ax.set_ylabel("Anzahl verlorener Parent-Erfolge (Familien)")
    ax.set_title(f"(b) Verluste, Lesart B: Summe {total_b} (≤ {LOST_TOTAL_MAX})", fontsize=10.5)
    ax.legend(fontsize=8, frameon=False, loc="upper right")
    tidy(ax)
    lost_a = {v: sum(len(RUNS[(v, p)]["lost"]) for p in PARENTS) for v in VARIANTS}
    ax.text(0.5, -0.2, "Lesart A (je Variante): " + ", ".join(f"{v} {n} (≤ 3)" for v, n in lost_a.items())
            + f"\nNeue Erfolge: {GAINED} (würden Verluste nicht verrechnen)",
            transform=ax.transAxes, ha="center", va="top", fontsize=8)

    # (c) Online-Erfolge je Runde (Exploration, kein Leistungsmaß)
    ax = fig.add_subplot(gs[2])
    keys = run_order()
    xk = np.arange(len(keys), dtype=float)
    for j, rd in enumerate([1, 2]):
        vals = [HISTORY[k][rd]["online"] for k in keys]
        ax.bar(xk + (j - 0.5) * 0.36, vals, 0.36, color=[VARIANT_COLORS[k[0]] for k in keys],
               alpha=0.55 if rd == 1 else 1.0, edgecolor="white")
        for xi, v in zip(xk + (j - 0.5) * 0.36, vals):
            ax.text(xi, v + 0.15, f"{v}", ha="center", fontsize=7.5)
    ax.set_xticks(xk)
    ax.set_xticklabels([run_label(k) for k in keys], fontsize=8.5)
    ax.set_ylim(0, N_ONLINE_ROUND)
    ax.set_ylabel(f"Online-Erfolge je Runde (k von {N_ONLINE_ROUND})")
    ax.set_title("(c) Online-Runden mit Rauschen\n(smoke_interaction, kein Leistungsmaß)", fontsize=10.5)
    ax.legend(handles=[Patch(color="#777777", alpha=0.55, label="Runde 1 (2100003670–79)"),
                       Patch(color="#777777", label="Runde 2 (2100003680–89)")],
              fontsize=8, frameon=False, loc="upper right")
    tidy(ax)

    fig.suptitle("N2-3 · Erhalt der Parent-Erfolge (§7-Kriterium erfüllt) – getrennt von Loss und technischer Stabilität",
                 fontsize=12.5)
    footer(
        fig,
        "Gepaart: Parent und beide Varianten auf denselben 20 Familien 2100003650–2100003669, Nenner = alle 20 ohne Ausschlüsse. "
        "Verloren (rot, „verl.“) = Parent erfolgreich, Lauf nicht; in P2 beide Male Familie 2100003658.\n"
        "Wilson-KI nur über Szenenfamilien je Parent, nicht über neues Training (n = 3 Parents); bei gepaarten Familien überschätzen sie die Unsicherheit der Differenz. "
        "Nach §7 werden AC-IL und AC-neu nicht verglichen.\n"
        f"Technischer Smoke ohne Wirksamkeitsaussage; Testfamilien geschlossen. {SOURCE}",
    )
    fig.tight_layout(rect=(0, 0.1, 1, 0.94))
    path = OUT / "05_parent_erfolge.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


# -----------------------------------------------------------------------------
def fig_critic_loss() -> Path:
    fig, ax = plt.subplots(figsize=(9, 5.4))
    keys = run_order()
    first = [HISTORY[k][1]["loss"] for k in keys]
    last = [HISTORY[k][2]["loss"] for k in keys]
    for k in keys:
        v, p = k
        ax.plot([1, 2], [HISTORY[k][1]["loss"], HISTORY[k][2]["loss"]], color=VARIANT_COLORS[v],
                ls=PARENT_LS[p], marker=PARENT_MARKERS[p], ms=6, lw=1.5)
    for k, y, yl in zip(keys, first, spread(first, 0.00008)):
        ax.text(0.96, yl, de(y, 5), va="center", ha="right", fontsize=7.5, color=VARIANT_COLORS[k[0]])
    for k, y, yl in zip(keys, last, spread(last, 0.00008)):
        ax.text(2.04, yl, f"{k[0]} P{k[1]}: {de(y, 5)}", va="center", fontsize=7.5, color=VARIANT_COLORS[k[0]])
    ax.set_xticks([1, 2])
    ax.set_xticklabels(["Runde 1\n(Updates 1–250)", "Runde 2\n(Updates 251–500)"])
    ax.set_xlim(0.75, 2.55)
    ax.set_ylim(0, 0.0023)
    ax.set_ylabel("Critic-TD-Loss, Mittel über die Runde (Q-Einheiten²)")
    tidy(ax)
    handles = [Line2D([], [], color=VARIANT_COLORS[v], lw=2, label=v) for v in VARIANTS] + [
        Line2D([], [], color="#444444", ls=PARENT_LS[p], marker=PARENT_MARKERS[p], label=f"Parent {p}") for p in PARENTS]
    ax.legend(handles=handles, fontsize=8, frameon=False, loc="upper center", ncol=5, bbox_to_anchor=(0.45, 1.0))
    ax.set_title("N2-3 · Critic-Loss je Runde (nur Loss)", fontsize=11.5)
    footer(
        fig,
        "Mittlerer Critic-Loss der 250 Critic-Updates je Runde auf dem eigenen Online-Replay (TD-Ziel auf [0, 1] geklemmt).\n"
        "Kleiner, sinkender Loss belegt weder den Q-Bereich (Abb. 02/03) noch Aufgabenerfolg (Abb. 05).\n"
        "AC-IL startet vortrainiert, AC-neu zufällig – Niveaus nicht als Gütevergleich lesen. Keine Intervalle (je Lauf ein Wert).\n"
        f"{SOURCE}",
    )
    fig.tight_layout(rect=(0, 0.15, 1, 1))
    path = OUT / "06_critic_loss.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def main() -> None:
    plt.rcParams.update({"font.size": 9.5, "font.family": "DejaVu Sans"})
    for p in (fig_drift(), fig_q_range(), fig_q_rounds(), fig_stability_criteria(), fig_parent_success(),
              fig_critic_loss()):
        print(p.relative_to(OUT.parents[4]).as_posix())


if __name__ == "__main__":
    main()
