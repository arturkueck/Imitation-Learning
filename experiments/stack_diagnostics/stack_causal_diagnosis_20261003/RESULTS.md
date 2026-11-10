# Exp0 und Exp1: gemessene Ergebnisse

Unveränderte C-Diffusion-Baseline: 2/40 stabile Stacks.

| Phase | Modell | n | Stabile Stacks | Position gehalten | Absenken gehalten | Release |
|---|---|---:|---:|---:|---:|---:|
| A_after_grasp | expert | 5 | 5 | 5 | 5 | 5 |
| A_after_grasp | direct | 5 | 1 | 4 | 4 | 2 |
| A_after_grasp | diffusion | 5 | 0 | 1 | 1 | 1 |
| B_after_lift | expert | 5 | 5 | 5 | 5 | 5 |
| B_after_lift | direct | 5 | 2 | 5 | 5 | 3 |
| B_after_lift | diffusion | 5 | 0 | 0 | 0 | 0 |
| C_mid_transport | expert | 5 | 5 | 5 | 5 | 5 |
| C_mid_transport | direct | 5 | 4 | 5 | 5 | 5 |
| C_mid_transport | diffusion | 5 | 1 | 1 | 1 | 1 |
| D_end_transport | expert | 5 | 5 | 5 | 5 | 5 |
| D_end_transport | direct | 5 | 5 | 5 | 5 | 5 |
| D_end_transport | diffusion | 5 | 2 | 5 | 5 | 3 |
| E_before_lowering | expert | 5 | 5 | 5 | 5 | 5 |
| E_before_lowering | direct | 5 | 5 | 5 | 5 | 5 |
| E_before_lowering | diffusion | 5 | 2 | 5 | 5 | 3 |
| F_before_release | expert | 5 | 5 | 5 | 5 | 5 |
| F_before_release | direct | 5 | 5 | 5 | 5 | 5 |
| F_before_release | diffusion | 5 | 2 | 5 | 5 | 4 |

Bereits initial erfüllte Position-/Absenkgeometrie wird in den Einzelwerten ausgewiesen. Teilindikatoren können bereits am Start erfüllt sein; nur vollständiger stabiler Stack zählt als primärer Erfolg. Ein Seed, fünf Demos je Phase; keine robuste Methodenaussage.
Expert-Prefix-Replay erhält die Controller-/Gripper-Erinnerung. Alle Paare werden auf identische replayte Startzustände geprüft.
Es wurden keine weiteren Experimente oder Trainings automatisch gestartet. Interpretation der Failure Points erfolgt erst anhand dieser Ergebnisse.
