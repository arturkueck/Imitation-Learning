# D1a · Aktionssensitivität der N2-2-Critics

19.11.2026 · Berichtende Vorwärtsdiagnose nach [Protokoll v2 §A](PROTOCOL_V2.md#a-neu-diagnose-d1-aktionssensitivität-vor-smoke-v2-keine-optimizerupdates).

Die vortrainierten Critics reagieren auf den gezogenen Aktionen bei allen drei Bindungsstufen stärker als die gepaarte Zufallsinitialisierung. Über je 1.344 Frames beträgt die typische Streuung innerhalb eines Frames das 4,83- bis 5,13-Fache. Absolut liegt der Median der Streuung je nach Bindung bei 0,000498 bis 0,000677 und damit deutlich unter der für D1b vorgesehenen Schwelle von 0,01. Die Diagnose misst Änderungen der Critic-Ausgabe. Die Aktionen wurden nicht in der Simulation ausgeführt, daher ist aus den Werten keine Aussage über die richtige Rangfolge der Aktionen oder den Dreierturmerfolg ableitbar. Über Smoke v2 entscheidet D1b auf IL-v2.

| δ_max | Median Frame-Std. IL | Median Frame-Std. neu | Verhältnis IL / neu | P90 von \|A\| IL | P90 von \|A\| neu | Eindeutig IL | Eindeutig neu |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0,05 | 0,00049846 | 0,00010318 | 4,83 | 0,00292933 | 0,00036212 | 99/1.344 | 0/1.344 |
| 0,10 | 0,00059453 | 0,00012062 | 4,93 | 0,00446765 | 0,00053376 | 138/1.344 | 0/1.344 |
| 0,20 | 0,00067657 | 0,00013192 | 5,13 | 0,00646952 | 0,00082522 | 162/1.344 | 1/1.344 |

## Messung

- Die Auswahlfunktion aus [N2-3](ac_smoke.py) liefert für jeden der drei A-Parents dieselben 64 Driftframes je Policy-Phase 0–6 aus N2-1 wie im Smoke (Seed `7400 + p`). Das ergibt 448 Frames je Parent. Validierungs- und Testframes wurden nicht verwendet.
- Die Parentaktion wird mit dem eingefrorenen Parent berechnet. Je Frame und Stufe werden 32 Aktionen gleichverteilt aus der Schnittmenge des erlaubten Aktionsintervalls mit `[−1, 1]` gezogen. Die Halbbreite pro XYZ-Koordinate ist `min(δ_max, 0,5 · |a_parent|)`, beim Greifer 0,02. Pro Parent läuft der Zufallsstrom `7500 + p` in aufsteigender Stufenreihenfolge. Beide Critics erhalten dieselben Aktionen je Frame und Stufe.
- `A = min(Q1(s,a), Q2(s,a)) − min(Q1(s,a_parent), Q2(s,a_parent))`. IL verwendet den eingefrorenen N2-2-Critic. Die zufällige Variante verwendet `7100 + p` und dieselben Normalisierungspuffer wie IL.
- Die phasenweise Standardabweichung wird über alle 2.048 Vorteile in der Gruppe berechnet. Die Median-Frame-Std. ist der Median der 64 Standardabweichungen über jeweils 32 Aktionen. P90 ist das linear interpolierte 90-%-Quantil der absoluten Vorteile. Eindeutig zählt Frames, bei denen die zwei höchsten Vorteile um mehr als 0,001 auseinanderliegen. Die Übersicht bündelt je Stufe und Variante die Frames aller Parents.

## Je Parent, Policy-Phase und Bindungsstufe

Standardabweichungen und P90 sind in Einheiten von 0,001 Q angegeben. Eindeutig ist der Zähler über die 64 Frames der jeweiligen Gruppe.

| Parent | Policy-Phase | δ_max | IL Std. | IL Median Frame-Std. | IL P90 \|A\| | IL eindeutig | Neu Std. | Neu Median Frame-Std. | Neu P90 \|A\| | Neu eindeutig |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0 | 0,05 | 2,769 | 1,336 | 4,439 | 4/64 | 0,299 | 0,270 | 0,548 | 0/64 |
| 1 | 0 | 0,10 | 4,808 | 2,274 | 7,871 | 7/64 | 0,522 | 0,419 | 0,930 | 0/64 |
| 1 | 0 | 0,20 | 8,337 | 3,721 | 13,604 | 17/64 | 0,900 | 0,641 | 1,571 | 0/64 |
| 1 | 1 | 0,05 | 0,731 | 0,272 | 1,249 | 0/64 | 0,180 | 0,087 | 0,300 | 0/64 |
| 1 | 1 | 0,10 | 1,087 | 0,286 | 1,658 | 1/64 | 0,244 | 0,090 | 0,387 | 0/64 |
| 1 | 1 | 0,20 | 1,625 | 0,303 | 1,952 | 1/64 | 0,286 | 0,091 | 0,458 | 0/64 |
| 1 | 2 | 0,05 | 0,973 | 0,415 | 1,455 | 1/64 | 0,140 | 0,064 | 0,208 | 0/64 |
| 1 | 2 | 0,10 | 1,429 | 0,439 | 1,482 | 1/64 | 0,194 | 0,066 | 0,212 | 0/64 |
| 1 | 2 | 0,20 | 2,079 | 0,425 | 1,497 | 2/64 | 0,201 | 0,062 | 0,213 | 0/64 |
| 1 | 3 | 0,05 | 2,994 | 1,067 | 3,942 | 4/64 | 0,306 | 0,272 | 0,527 | 0/64 |
| 1 | 3 | 0,10 | 3,515 | 1,420 | 5,157 | 10/64 | 0,424 | 0,346 | 0,701 | 0/64 |
| 1 | 3 | 0,20 | 4,868 | 2,025 | 7,245 | 11/64 | 0,657 | 0,516 | 1,144 | 0/64 |
| 1 | 4 | 0,05 | 1,744 | 0,069 | 2,188 | 4/64 | 0,272 | 0,104 | 0,473 | 0/64 |
| 1 | 4 | 0,10 | 2,880 | 0,067 | 3,191 | 5/64 | 0,464 | 0,121 | 0,696 | 0/64 |
| 1 | 4 | 0,20 | 5,352 | 0,077 | 4,749 | 6/64 | 0,880 | 0,114 | 1,037 | 1/64 |
| 1 | 5 | 0,05 | 5,317 | 1,700 | 8,559 | 21/64 | 0,236 | 0,199 | 0,449 | 0/64 |
| 1 | 5 | 0,10 | 7,072 | 2,319 | 11,538 | 17/64 | 0,344 | 0,287 | 0,635 | 0/64 |
| 1 | 5 | 0,20 | 9,269 | 3,383 | 16,651 | 22/64 | 0,551 | 0,403 | 1,067 | 0/64 |
| 1 | 6 | 0,05 | 0,858 | 0,096 | 0,850 | 0/64 | 0,129 | 0,078 | 0,265 | 0/64 |
| 1 | 6 | 0,10 | 0,906 | 0,094 | 0,911 | 0/64 | 0,146 | 0,075 | 0,268 | 0/64 |
| 1 | 6 | 0,20 | 0,901 | 0,097 | 0,895 | 1/64 | 0,149 | 0,075 | 0,271 | 0/64 |
| 2 | 0 | 0,05 | 2,899 | 1,513 | 4,851 | 8/64 | 0,216 | 0,182 | 0,339 | 0/64 |
| 2 | 0 | 0,10 | 5,070 | 2,478 | 8,320 | 18/64 | 0,382 | 0,315 | 0,608 | 0/64 |
| 2 | 0 | 0,20 | 8,011 | 3,436 | 11,961 | 17/64 | 0,592 | 0,438 | 0,969 | 0/64 |
| 2 | 1 | 0,05 | 1,069 | 0,075 | 1,058 | 0/64 | 0,095 | 0,037 | 0,163 | 0/64 |
| 2 | 1 | 0,10 | 1,899 | 0,066 | 1,448 | 2/64 | 0,144 | 0,036 | 0,193 | 0/64 |
| 2 | 1 | 0,20 | 2,359 | 0,070 | 1,776 | 1/64 | 0,175 | 0,038 | 0,223 | 0/64 |
| 2 | 2 | 0,05 | 0,879 | 0,300 | 1,329 | 0/64 | 0,088 | 0,062 | 0,190 | 0/64 |
| 2 | 2 | 0,10 | 1,014 | 0,285 | 1,335 | 2/64 | 0,098 | 0,059 | 0,198 | 0/64 |
| 2 | 2 | 0,20 | 1,035 | 0,295 | 1,361 | 2/64 | 0,095 | 0,060 | 0,193 | 0/64 |
| 2 | 3 | 0,05 | 1,161 | 0,473 | 2,014 | 3/64 | 0,174 | 0,097 | 0,339 | 0/64 |
| 2 | 3 | 0,10 | 1,973 | 0,701 | 3,296 | 4/64 | 0,280 | 0,123 | 0,529 | 0/64 |
| 2 | 3 | 0,20 | 3,409 | 0,816 | 5,245 | 4/64 | 0,483 | 0,171 | 0,909 | 0/64 |
| 2 | 4 | 0,05 | 2,103 | 0,116 | 1,990 | 3/64 | 0,129 | 0,047 | 0,225 | 0/64 |
| 2 | 4 | 0,10 | 3,940 | 0,141 | 3,828 | 7/64 | 0,242 | 0,047 | 0,361 | 0/64 |
| 2 | 4 | 0,20 | 6,503 | 0,140 | 6,559 | 7/64 | 0,378 | 0,047 | 0,560 | 0/64 |
| 2 | 5 | 0,05 | 5,704 | 0,799 | 7,627 | 13/64 | 0,135 | 0,111 | 0,248 | 0/64 |
| 2 | 5 | 0,10 | 7,691 | 1,313 | 10,685 | 17/64 | 0,222 | 0,146 | 0,384 | 0/64 |
| 2 | 5 | 0,20 | 11,571 | 1,915 | 14,236 | 18/64 | 0,375 | 0,208 | 0,658 | 0/64 |
| 2 | 6 | 0,05 | 0,707 | 0,045 | 0,376 | 0/64 | 0,074 | 0,026 | 0,123 | 0/64 |
| 2 | 6 | 0,10 | 0,633 | 0,045 | 0,410 | 0/64 | 0,071 | 0,028 | 0,113 | 0/64 |
| 2 | 6 | 0,20 | 0,687 | 0,041 | 0,387 | 0/64 | 0,072 | 0,026 | 0,123 | 0/64 |
| 3 | 0 | 0,05 | 2,910 | 1,677 | 4,306 | 14/64 | 0,328 | 0,302 | 0,543 | 0/64 |
| 3 | 0 | 0,10 | 5,008 | 2,620 | 6,751 | 14/64 | 0,576 | 0,486 | 0,976 | 0/64 |
| 3 | 0 | 0,20 | 9,022 | 4,291 | 12,601 | 17/64 | 0,972 | 0,756 | 1,664 | 0/64 |
| 3 | 1 | 0,05 | 1,091 | 0,119 | 1,543 | 2/64 | 0,224 | 0,048 | 0,371 | 0/64 |
| 3 | 1 | 0,10 | 1,561 | 0,131 | 2,113 | 2/64 | 0,320 | 0,049 | 0,528 | 0/64 |
| 3 | 1 | 0,20 | 2,420 | 0,121 | 2,573 | 4/64 | 0,444 | 0,053 | 0,724 | 0/64 |
| 3 | 2 | 0,05 | 1,143 | 0,433 | 1,652 | 3/64 | 0,124 | 0,064 | 0,187 | 0/64 |
| 3 | 2 | 0,10 | 1,461 | 0,423 | 1,777 | 2/64 | 0,132 | 0,063 | 0,184 | 0/64 |
| 3 | 2 | 0,20 | 1,408 | 0,454 | 1,632 | 2/64 | 0,137 | 0,064 | 0,179 | 0/64 |
| 3 | 3 | 0,05 | 2,171 | 1,045 | 3,316 | 3/64 | 0,322 | 0,258 | 0,525 | 0/64 |
| 3 | 3 | 0,10 | 2,783 | 1,317 | 4,660 | 7/64 | 0,542 | 0,388 | 0,913 | 0/64 |
| 3 | 3 | 0,20 | 3,856 | 1,961 | 6,245 | 7/64 | 0,928 | 0,615 | 1,710 | 0/64 |
| 3 | 4 | 0,05 | 1,534 | 0,071 | 0,740 | 3/64 | 0,138 | 0,052 | 0,196 | 0/64 |
| 3 | 4 | 0,10 | 2,613 | 0,080 | 1,158 | 1/64 | 0,217 | 0,050 | 0,216 | 0/64 |
| 3 | 4 | 0,20 | 4,297 | 0,071 | 1,630 | 2/64 | 0,374 | 0,052 | 0,247 | 0/64 |
| 3 | 5 | 0,05 | 5,265 | 1,700 | 8,189 | 12/64 | 0,160 | 0,121 | 0,279 | 0/64 |
| 3 | 5 | 0,10 | 7,966 | 2,295 | 12,595 | 19/64 | 0,208 | 0,155 | 0,373 | 0/64 |
| 3 | 5 | 0,20 | 12,449 | 3,434 | 19,148 | 19/64 | 0,290 | 0,190 | 0,537 | 0/64 |
| 3 | 6 | 0,05 | 0,972 | 0,310 | 1,476 | 1/64 | 0,201 | 0,075 | 0,370 | 0/64 |
| 3 | 6 | 0,10 | 1,108 | 0,292 | 1,659 | 2/64 | 0,237 | 0,071 | 0,410 | 0/64 |
| 3 | 6 | 0,20 | 1,164 | 0,289 | 1,679 | 2/64 | 0,240 | 0,070 | 0,410 | 0/64 |

## Nachweis

[Aktionsdiagnose](action_sensitivity.py) · [Lokale Zusammenfassung](../../../praxis/results/critic/three_cube_transfer_v1/action_sensitivity_d1a/summary.json) · [Lokale Vorteile je Frame und Aktion](../../../praxis/results/critic/three_cube_transfer_v1/action_sensitivity_d1a/advantages.npz).

Laufzeit 16,17 s auf CPU, Exitcode 0. 126/126 Gruppen mit je 64 Frames und 2.048 Vorteilen unabhängig aus den gespeicherten Vorteilen nachgerechnet. Insgesamt wurden 258.048 Vorteile ausgewertet. 0 Rollouts und 0 Optimizerupdates. Die N2-3-Quellen und die N2-2-Gewichte wurden vor der Messung gegen die eingefrorenen SHA-256-Werte geprüft. SHA-256 der Vorteile `5094b4290a0370013ec9e5fc5d114edc75972166008cf9e5751976f57f77b1a3`.
