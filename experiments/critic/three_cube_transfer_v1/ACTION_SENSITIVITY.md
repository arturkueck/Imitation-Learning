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

## D1b · Entscheidung für IL-v2

20.11.2026 · **D1b abgeschlossen, nicht bestanden. Gesamtpause nach [Protokoll v2 §A](PROTOCOL_V2.md#a-neu-diagnose-d1-aktionssensitivität-vor-smoke-v2-keine-optimizerupdates).** Smoke v2 bleibt gesperrt. Der Nutzer entscheidet über das weitere Vorgehen.

Der Median der Streuung von A über die 32 Aktionen je Frame erreichte höchstens 0,000589. Das sind 5,9 % der geforderten 0,01. Der Faktor gegenüber der Zufallsinitialisierung lag auf allen drei Stufen über der geforderten 1,5. Beide Kriterien müssen auf derselben Stufe erfüllt sein. Auf diesen festen Frames lag der Median von IL-v2 auf jeder Stufe auch unter dem von D1a.

| δ_max | Median Frame-Std. IL-v2 | Median Frame-Std. neu | Verhältnis IL-v2 / neu | P90 von \|A\| IL-v2 | P90 von \|A\| neu | Eindeutig IL-v2 | Eindeutig neu |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0,05 | 0,00039805 | 0,00010318 | 3,86 | 0,00283096 | 0,00036212 | 99/1.344 | 0/1.344 |
| 0,10 | 0,00049234 | 0,00012062 | 4,08 | 0,00418074 | 0,00053376 | 121/1.344 | 0/1.344 |
| 0,20 | 0,00058884 | 0,00013192 | 4,46 | 0,00619486 | 0,00082522 | 139/1.344 | 1/1.344 |

Pro Stufe gehen 1.344 Driftframes (3 Parents × 7 Policy-Phasen × 64 Frames) aus N2-1 in die Entscheidung ein. Die Aktionsgrenzen, Seeds und Kennzahlen entsprechen D1a. IL-v2 verwendet seine in N2-2b auf beiden Datensätzen erlernte Normierung. Die Zufallsinitialisierung behält die Normierung aus D1a und liefert exakt dieselben Vorteile wie dort. Das bestandene Kriterium aus N2-2b betrifft die Vorhersagen auf gespeicherten Parent-Rollouts. D1b misst die Änderung der Critic-Ausgabe bei alternativen Aktionen auf denselben Driftframes. Über die tatsächliche Qualität dieser Aktionen gibt der Befund keine Auskunft.

### D1b je Parent, Policy-Phase und Bindungsstufe

Die Streuungen und Quantile stehen in Einheiten von 0,001 Q. Die Kennzahlen der Zufallsreferenz stehen unverändert in der D1a-Tabelle oben.

| Parent | Policy-Phase | δ_max | IL-v2 Std. | IL-v2 Median Frame-Std. | IL-v2 P90 \|A\| | IL-v2 eindeutig |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0 | 0,05 | 2,367 | 1,129 | 3,667 | 3/64 |
| 1 | 0 | 0,10 | 4,170 | 1,963 | 6,140 | 8/64 |
| 1 | 0 | 0,20 | 7,260 | 2,339 | 10,582 | 13/64 |
| 1 | 1 | 0,05 | 0,768 | 0,166 | 1,307 | 0/64 |
| 1 | 1 | 0,10 | 1,158 | 0,160 | 1,718 | 2/64 |
| 1 | 1 | 0,20 | 1,456 | 0,140 | 2,266 | 0/64 |
| 1 | 2 | 0,05 | 0,654 | 0,343 | 0,983 | 0/64 |
| 1 | 2 | 0,10 | 0,766 | 0,352 | 1,002 | 1/64 |
| 1 | 2 | 0,20 | 0,852 | 0,358 | 1,052 | 1/64 |
| 1 | 3 | 0,05 | 2,706 | 1,005 | 3,879 | 4/64 |
| 1 | 3 | 0,10 | 3,178 | 1,621 | 4,648 | 7/64 |
| 1 | 3 | 0,20 | 4,451 | 2,037 | 6,259 | 9/64 |
| 1 | 4 | 0,05 | 1,702 | 0,038 | 1,622 | 3/64 |
| 1 | 4 | 0,10 | 2,579 | 0,043 | 2,455 | 2/64 |
| 1 | 4 | 0,20 | 5,025 | 0,040 | 3,721 | 6/64 |
| 1 | 5 | 0,05 | 5,582 | 1,844 | 9,392 | 17/64 |
| 1 | 5 | 0,10 | 7,557 | 2,651 | 13,447 | 21/64 |
| 1 | 5 | 0,20 | 10,596 | 2,621 | 19,518 | 20/64 |
| 1 | 6 | 0,05 | 0,850 | 0,044 | 0,737 | 1/64 |
| 1 | 6 | 0,10 | 0,933 | 0,040 | 0,759 | 1/64 |
| 1 | 6 | 0,20 | 0,927 | 0,042 | 0,736 | 1/64 |
| 2 | 0 | 0,05 | 2,924 | 1,378 | 4,938 | 9/64 |
| 2 | 0 | 0,10 | 4,863 | 2,087 | 8,373 | 14/64 |
| 2 | 0 | 0,20 | 7,801 | 2,838 | 12,119 | 14/64 |
| 2 | 1 | 0,05 | 1,012 | 0,058 | 1,103 | 0/64 |
| 2 | 1 | 0,10 | 1,567 | 0,059 | 1,108 | 2/64 |
| 2 | 1 | 0,20 | 1,932 | 0,065 | 1,459 | 2/64 |
| 2 | 2 | 0,05 | 0,671 | 0,299 | 1,031 | 1/64 |
| 2 | 2 | 0,10 | 0,721 | 0,303 | 1,067 | 0/64 |
| 2 | 2 | 0,20 | 0,745 | 0,302 | 1,060 | 0/64 |
| 2 | 3 | 0,05 | 1,533 | 0,443 | 2,194 | 1/64 |
| 2 | 3 | 0,10 | 2,532 | 0,616 | 3,382 | 4/64 |
| 2 | 3 | 0,20 | 4,339 | 0,783 | 5,791 | 3/64 |
| 2 | 4 | 0,05 | 1,959 | 0,056 | 1,583 | 4/64 |
| 2 | 4 | 0,10 | 3,906 | 0,059 | 3,128 | 5/64 |
| 2 | 4 | 0,20 | 6,501 | 0,063 | 5,423 | 9/64 |
| 2 | 5 | 0,05 | 6,424 | 0,935 | 8,802 | 14/64 |
| 2 | 5 | 0,10 | 8,799 | 1,467 | 12,154 | 12/64 |
| 2 | 5 | 0,20 | 12,893 | 2,155 | 17,239 | 14/64 |
| 2 | 6 | 0,05 | 0,759 | 0,032 | 0,389 | 0/64 |
| 2 | 6 | 0,10 | 0,694 | 0,034 | 0,386 | 2/64 |
| 2 | 6 | 0,20 | 0,774 | 0,030 | 0,389 | 0/64 |
| 3 | 0 | 0,05 | 2,506 | 1,268 | 3,415 | 11/64 |
| 3 | 0 | 0,10 | 5,086 | 2,041 | 6,360 | 11/64 |
| 3 | 0 | 0,20 | 9,753 | 3,011 | 10,937 | 17/64 |
| 3 | 1 | 0,05 | 0,925 | 0,084 | 1,062 | 1/64 |
| 3 | 1 | 0,10 | 1,367 | 0,083 | 1,568 | 3/64 |
| 3 | 1 | 0,20 | 2,550 | 0,088 | 2,060 | 1/64 |
| 3 | 2 | 0,05 | 1,058 | 0,402 | 1,461 | 5/64 |
| 3 | 2 | 0,10 | 1,210 | 0,418 | 1,504 | 0/64 |
| 3 | 2 | 0,20 | 1,174 | 0,419 | 1,480 | 1/64 |
| 3 | 3 | 0,05 | 2,839 | 0,868 | 4,766 | 9/64 |
| 3 | 3 | 0,10 | 4,128 | 1,050 | 6,667 | 9/64 |
| 3 | 3 | 0,20 | 6,581 | 1,840 | 8,710 | 11/64 |
| 3 | 4 | 0,05 | 1,185 | 0,028 | 0,726 | 1/64 |
| 3 | 4 | 0,10 | 1,851 | 0,029 | 0,999 | 2/64 |
| 3 | 4 | 0,20 | 3,038 | 0,032 | 1,297 | 2/64 |
| 3 | 5 | 0,05 | 5,655 | 1,662 | 9,174 | 15/64 |
| 3 | 5 | 0,10 | 8,241 | 2,469 | 13,440 | 15/64 |
| 3 | 5 | 0,20 | 13,378 | 3,974 | 21,509 | 15/64 |
| 3 | 6 | 0,05 | 0,623 | 0,174 | 0,928 | 0/64 |
| 3 | 6 | 0,10 | 0,732 | 0,159 | 1,046 | 0/64 |
| 3 | 6 | 0,20 | 0,728 | 0,163 | 1,002 | 0/64 |

### Nachweis D1b

[Aktionsdiagnose mit Prüfbefehl](action_sensitivity_v2.py) · [Lokale Zusammenfassung mit allen 126 Gruppen](../../../praxis/results/critic/three_cube_transfer_v1/action_sensitivity_d1b/summary.json) · [Lokale Vorteile je Frame und Aktion](../../../praxis/results/critic/three_cube_transfer_v1/action_sensitivity_d1b/advantages.npz).

CPU-Lauf am 20.11. um 04:05 Uhr, 7,58 s, Exitcode 0. Erneute Prüfung mit `action_sensitivity_v2.py --verify` ergab `VERIFY OK`. Alle 126 Gruppen mit zusammen 258.048 Vorteilen wurden aus dem gespeicherten Array nachgerechnet. Die Prüfung glich die Zufallsreferenz exakt mit D1a ab und bestätigte die Entscheidung. Die Gewichte von IL-v2 wurden gegen den geprüften Abschluss von N2-2b abgeglichen. 0 Rollouts, 0 Optimizerupdates, Testfamilien geschlossen.

| Artefakt | SHA-256 |
|---|---|
| `advantages.npz` | `f443664b1bc794c060804dec80a726bbfde9a40dd3f608de8201703e56b224d3` |
| `summary.json` | `74ea5eaed7e0c176310beb4ed494a68202396621d3bf67001f65187e866d5143` |
