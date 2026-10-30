# Öffentliche Daten und Entscheidung für diesen Versuch

Recherche und lokale Dateiprüfung:24.10.2026. Es wurden passende **thematische** Daten gefunden; die Aussage „es gibt keine Stapeldaten“ wäre falsch.

## Geprüfter Hauptkandidat: offizielles MimicGen Stack Three

- [Offizieller Code und Datenverweise](https://github.com/NVlabs/mimicgen)
- [Offizielle Dataset Card](https://huggingface.co/datasets/amandlek/mimicgen_datasets)
- [Originale StackThree-Umgebung](https://github.com/NVlabs/mimicgen/blob/main/mimicgen/envs/robosuite/stack.py)
- [Geprüfte Quelldatei](https://huggingface.co/datasets/amandlek/mimicgen_datasets/resolve/main/source/stack_three.hdf5)

Die Quelldatei wurde tatsächlich heruntergeladen, nicht nur anhand einer Suchbeschreibung bewertet. Lokale Kopie:`web_dataset_audit/mimicgen_stack_three_source.hdf5`,24.904.535Bytes,SHA256`68b9033fefe904a5575e79bdf5040c2d2d207c1bfcc939bbaec5b438a9d7fcfe`. Der Hash stimmt mit dem offiziellen LFS-Objekthash überein. Inhalt:zehn menschliche Demonstrationen,2333 Aktionsframes, gespeicherte Simulatorzustände, Aktionen und Beobachtungen einschließlich Bildern. Die offizielle Datenlizenz istCC-BY-4.0; Zuordnung:Mandlekar et al.,MimicGen,CoRL2023. Die Lizenz des Codes ist separat und wird nicht als Lizenz der Daten ausgegeben.

## Warum wir diese Datei nicht ungeprüft in B0/B mischen

| Eigenschaft | Öffentliche Quelldatei, lokal geprüft | Aktueller eigener Versuch |
|---|---|---|
| Umgebungsversion | Robosuite1.4.1,StackThree_D0 | lokal verwendete aktuelle Custom-Umgebung |
| Würfelgeometrie | A/C40mm,B50mm Kantenlänge | alle40mm |
| Reihenfolge | B unten,A mittig,C oben | A unten,B mittig,C oben |
| Aktionen |7D mit in jedem Frame nicht exakt null gesetzten Rotationskomponenten | gelernteXYZ/Greiferkomponenten; Rotation fest null |
| Phasenlabels | keine Labels für unsere sieben BC-Phasen | phasengetrennte Actor-/Completionköpfe |
| Stabilität | Originaltask-Erfolgskriterium | unser korrigiertes, strengeres kontaktfreies Präfixkriterium |

Die vorhandenen Positionen/Aktionen lassen sich daher nicht verlustfrei durch bloßes Umbenennen übernehmen. Rotationen auf null zu setzen oder eigene Phasenlabels ungeprüft zu erfinden würde korrekte menschliche Aktionsziele verändern. Ein seriöser Import braucht Retargeting, kompatible Aktions-/Geometriedefinition, eine separat validierte Segmentierung und einen eigenen Vergleichsarm. Dasselbe DatenformatHDF5 genügt nicht als Kompatibilitätsbeweis.

## Konkrete Entscheidung

Die öffentliche Datei bleibt eine **separate, hashgeprüfte Kompatibilitätsprobe**. Sie wird in diesem B0/B-Vergleich weder trainiert noch zur Qualitätsnormalisierung benutzt. Damit ändert nur die Qualitätsgewichtung den Unterschied zwischen B0 undB. Beide erhalten denselben neuen nativen Datensatz aus unserer eigenen korrigierten Umgebung.

Die überarbeitete eigene Datenerhebung speichert echte Griff-/Kontaktmessungen, synchronisierte Zustände und vollständige Controllerzustände für vorbereitete Übergangsprüfungen. Eine feste, laufzeitbedingt vor Fortsetzung dokumentierte Kohorte enthält200 Episoden:je60 Trainings- und40 Validierungsversuche auf drei bzw.vier Würfeln. Alle Fehlschläge bleiben erhalten; nur gültige lokale Übergänge werden zu Actorzielen. Die unveränderten Qualitätsgates müssen bestehen, sonst gibt es keine Trainingsfreigabe.

Für einen späteren separaten Experten-/Retargetingarm ist MimicGen ein sinnvoller Ausgangspunkt. Dieser wäre jedoch ein anderes Experiment als die isolierte Frage, ob Qualität **derselben eigenen Übergangsdaten** besser als Einheitsgewichtung wirkt. Das aktuelle Experiment ist ohnehin keine reine Zweier-Zero-shot-Untersuchung mehr.

Maschinell prüfbare Recherche-/Dateibefunde:`web_dataset_audit/mimicgen_source_listing.json` und `web_dataset_audit/mimicgen_inspection.json`. Die öffentlichen Dateien werden nicht als lokal reproduzierte Erfolgsquote oder als bereits kompatibler zusätzlicher Expertendatensatz dargestellt.
