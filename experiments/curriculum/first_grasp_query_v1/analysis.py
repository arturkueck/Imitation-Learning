"""Pair complete outcomes across independently trained lines and scene families."""
import numpy as np


def contrast(results, seeds, panel, control, candidate, plan):
    def values(seed, arm):
        return {r["seed"]: int(r["success"]) for r in results[str(seed)][panel][arm]}
    families = sorted(values(seeds[0], control))
    matrix = []
    for seed in seeds:
        a, b = values(seed, control), values(seed, candidate)
        if set(a) != set(families) or set(b) != set(families):
            raise ValueError("Incomplete paired outcomes")
        matrix.append([b[f] - a[f] for f in families])
    difference = np.asarray(matrix)
    rng = np.random.default_rng(plan["bootstrap_seed"])
    draws = []
    for _ in range(plan["bootstrap_draws"]):
        # Independent axes, shared pairing and one common family draw per replicate.
        i = rng.integers(len(seeds), size=len(seeds))
        j = rng.integers(len(families), size=len(families))
        draws.append(difference[np.ix_(i, j)].mean())
    return dict(n_lines=len(seeds), n_families=len(families),
        gains=int((difference == 1).sum()), losses=int((difference == -1).sum()),
        per_line_pp=(difference.mean(axis=1) * 100).tolist(),
        mean_pp=float(difference.mean() * 100),
        interval_pp=(np.quantile(draws, [.025, .975]) * 100).tolist())


def report(out, results, plan, write):
    seeds = plan["seeds"]
    comparisons = {
        panel: {f"{candidate}_minus_{control}": contrast(results, seeds, panel, control, candidate, plan)
            for control, candidate in (("random", "targeted"), ("base", "targeted"), ("timeout", "targeted"))}
        for panel in ("test_normal", "test_hard", "validation_normal", "validation_hard")
    }
    primary = comparisons["test_normal"]["targeted_minus_random"]
    supported = primary["mean_pp"] >= plan["practical_gain_pp"] and primary["interval_pp"][0] > 0
    write(out / "analysis.json", dict(technical_only=plan["technical_only"], comparisons=comparisons,
        decision="TECHNICAL_ONLY" if plan["technical_only"] else "SUPPORTED" if supported else "NOT_DEMONSTRATED"))
    lines = ["# Abschlussbericht · Expertenabfragen beim ersten Griff", "",
        f"Vollständig gepaarte Modelllinien {len(seeds)}. Technische Ausführung {plan['technical_only']}.", "",
        "Primär zählt der Dreierturm über 50 gültige Frames. Hauptvergleich ist die gezielte "
        "gegen die zufällige Abfrage im normalen Testpanel.", "",
        "| Panel | Variante gegen Referenz | Erfolge Variante | Erfolge Referenz | Gewinne / Verluste | Differenz [pp] | 95%-Intervall [pp] |",
        "|---|---|---:|---:|---:|---:|---:|"]
    for panel, entries in comparisons.items():
        for name, result in entries.items():
            candidate, control = name.split("_minus_")
            n = result["n_families"] * len(seeds)
            successes = [sum(r["success"] for seed in seeds for r in results[str(seed)][panel][arm])
                         for arm in (candidate, control)]
            lo, hi = result["interval_pp"]
            lines.append(f"| {panel} | {candidate} gegen {control} | {successes[0]}/{n} | {successes[1]}/{n} | "
                f"{result['gains']}/{result['losses']} | {result['mean_pp']:+.2f} | [{lo:+.2f}, {hi:+.2f}] |")
    lines.extend(["", "Die Streuung der modell- und szenengepaarten Ergebnisse wird gemeinsam geschätzt. "
        "Die schwierigen Szenen bilden ein bedingtes Panel. Das Ergebnis bezieht sich auf die gemeinsame "
        "Demonstrationsbasis, den festen Experten und die Simulatoraufgabe.", ""])
    (out / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
