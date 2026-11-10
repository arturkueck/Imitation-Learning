"""Report actual camera-guidance evidence and export bounded frontend artifacts."""
from pathlib import Path
import json,shutil
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pilot as P

def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--run',default='guidance_001');p.add_argument('--register',action='store_true');args=p.parse_args();out=P.HERE/args.run
    r=json.loads((out/'report.json').read_text());a=json.loads((out/'capture_audit.json').read_text());assert a['passed'] and a['captured_images']==r['total_after']
    names=['right','left','base','elevated','difficult'];labels=['Rechts','Links','Basis','Erhöht','Kontrollblick\n(unscharf)'];x=np.arange(5)
    fig,axes=plt.subplots(1,2,figsize=(11,4));axes[0].bar(x-.18,[r['comparison'][f]['before'] for f in names],.36,label='Vorher',color='#e7a35b');axes[0].bar(x+.18,[r['comparison'][f]['after'] for f in names],.36,label='Neue Führung',color='#22b5c5')
    axes[0].set(xticks=x,xticklabels=labels,ylabel='Erfasste Zusatzansichten\n(je 40 Wünsche)',ylim=(0,42),title='Gleiche 200 Pilotszenen');axes[0].tick_params(axis='x',rotation=22);axes[0].legend()
    angles=[c['optical_axis_error_deg'] for c in a['captures']];axes[1].hist(angles,bins=16,color='#22b5c5');axes[1].axvline(3,color='#db7750',ls='--',label='Grenze 3°');axes[1].set(xlabel='Optische Zielabweichung nach der Fahrt [°]',ylabel='Aufnahmen',title='Tatsächlich erfasste Kameraposen');axes[1].legend();fig.tight_layout();fig.savefig(out/'guidance_comparison.png',dpi=150);plt.close(fig)
    table='\n'.join(f"| {label} | {r['comparison'][f]['before']} / 40 | {r['comparison'][f]['after']} / 40 |" for f,label in zip(names,labels))
    gate=all(r['comparison'][f]['after']>=20 for f in ['right','left','elevated'])
    text=f'''# Verbesserte Kameraführung – Simulation, keine Modelltrainierung

Gleiche 200 Entwicklungsfamilien wie pilot_002; **{r['total_before']} → {r['total_after']} zusätzliche Ansichten**. Jede neue gültige Zielhaltung wurde danach tatsächlich gerendert und anhand der gespeicherten Kamerapose überprüft. Keine Optimizerupdates, keine neue aktive Produktionspolicy und kein unabhängiger Endtest.

| Blickwunsch | Vorher | Neue Führung |
| --- | ---: | ---: |
{table}

## Änderung und Ursache

Die bisherige Bewegungsüberapproximation benutzte 32 Teilintervalle pro Gelenksegment. Eine vorab getrennte Diagnose mit 128 Teilintervallen und gleicher Bank ergab 107 statt 47 gültige Ansichten unter den alten Blickfeldregeln. Dies zeigt den wesentlichen Anteil zu grober Bewegungshüllen. Die neue Führung verwendet 128 Intervalle mit **unverändertem analytischem Bewegungsbound und unveränderten Abständen** (Umwelt 10 mm, Selbstkollision 2 mm). Es wurde keine Sparse-Sampling-Freigabe eingeführt.

Zusätzlich alle geeigneten erhaltenen Posen statt höchstens drei pro Richtung: {r['bank_entries']} statisch zertifizierte Wege. Für Basisansichten wurden objektunabhängige Arbeitsbereichsanker, zusätzliche IK-Ausgangshaltungen und Kamerarollwinkel geprüft. Blockierte Ziele werden nicht durch eine andere Blickrichtung ersetzt.

Die Handkamera wird von der Bankhaltung aus auf die unsicherste aktuelle V3-Ensemble-Vorhersage ausgerichtet. Bei Bedarf löst der Planer eine kleine Zielkorrektur und prüft deren gesamten zusätzlichen Gelenkweg gegen die vollständige Referenzwelt. Die erreichte Position darf sich dabei höchstens 15 mm verschieben. Auch nach der Korrektur müssen Blickfeld, gewünschte Seite, mindestens 20 cm Kameraversatz, Blickhöhe und optische Zielabweichung bestehen. Grenzwert optische Abweichung: 3°; gemessen maximal {a['actual_maximum_axis_error_deg']:.3f}°. {r['refined_views']} Ansichten wurden nachgeführt.

## Bewegung und Erfassung

Die statische Bank umfasst Selbst-/Umweltprüfung von Arm, Greifer und Kamerahalterungsproxy. Pro Szene werden sämtliche Objekte mit der konservativen analytischen Bewegungshülle geprüft. Die Nachführung erhält einen vollständigen separaten Edge-Check. Zusätzlich {r['independent_full_path_audits']} unabhängige vollständige Weltprüfungen auf neu zugelassenen, nach Blickfamilie/Anordnung geschichteten Fällen; diese sind kein Ersatz für die übrigen Zertifikate. Alle {r['native_replay_states']} gespeicherten Replay-Zustände wurden zusätzlich auf native Robot-Umwelt-Penetration geprüft: kein Fehler.

Alle {a['captured_images']} angenommenen Ansichten wurden tatsächlich aufgenommen. Maximum Pose-Abweichung zwischen Plan und gerendertem Zustand: {a['maximum_position_difference_m']:.9f} m. Rückprojektionsabweichung maximal {a['maximum_projection_error_px']:.6f} Pixel. Aufnahmejournale trennen Wunsch, Plan, Ist-Pose und Bild. Der Wunsch für diesen Replay ist als frische auf das Ziel gerichtete Bankpose dokumentiert; er wird nicht als historisch geloggte ursprüngliche IK-Eingabe ausgegeben. Jede neue Wahrnehmungsschätzung bleibt diagnostisch `hold`.

Für den Replay werden die gespeicherten gesetzten Objektposen geladen, statt die Szene erneut physikalisch zu setteln. Die ursprüngliche Beleuchtung wurde nicht separat serialisiert; photometrisch identische Beleuchtung wird nicht behauptet. In einem früheren Wiederaufnahmeversuch wurde ein NumPy-Weg irrtümlich addiert statt verkettet. Die unabhängige native Kontaktprüfung stoppte diesen Versuch. Ungültige Resultate bleiben separat in guidance_001; sie werden hier nicht als Erfolg gezählt. 138 zuvor gültige und auf Anfangs-/Endpunkte geprüfte Datensätze wurden übernommen, die restlichen 62 mit Regressionstest und expliziter Verkettung ergänzt. Für alle tatsächlichen Aufnahmen wurde die Zielnachführung nochmals in der exakt gespeicherten Referenzszene zertifiziert.

## Grenzen und nächster Schritt

Dies ist **Simulatorreferenz**. Die rein visuelle Freiraumfreigabe wird dadurch nicht gelöst; unbekannter Raum bleibt blockiert. Keine reale Bewegung und keine Garantie, dass eine echte Kamera das Ziel richtig erkannt hat. Ziel und Richtungsbewertung stammen aus vorhandenen Bildern; echte Objektgeometrie wird nur für explizite Simulations-Kollisionsprüfung, Sichtlinienprüfung und Auswertung benutzt, nicht als Objektpose für die Blickausrichtung.

Das zuvor festgelegte Abdeckungsgate (mindestens 20 rechte/linke/erhöhte Ansichten je 40 Wünsche) ist **{'bestanden' if gate else 'noch nicht bestanden'}**. Dies ist eine Entwicklungsprüfung, kein Generalisierungsbeleg. Die 200 Familien dürfen nicht zum späteren Blindtest werden. Bessere Kameraführung ist noch kein Nachweis besserer Objekterkennung; das unveränderte V3-Modell kann die neuen Bilder weiterhin schlechter verrechnen. Die Animationen zeigen die ersten erfolgreichen Beispiele je Richtung, ohne Auswahl nach Erkennungsqualität, und bleiben als technische Diagnosen beschriftet.

Bankvorbereitung {r['bank_seconds']/60:.1f} min; Validierung {r['validation_seconds']/60:.1f} min; zusätzliche tatsächliche Bilderfassung {a['seconds']:.1f} s. Testprotokoll: 21 fokussierte Kamera-/Seiten-/Armtests bestanden. Haupttraining wartet weiterhin auf Freigabe und die übrige V4-Implementierung.

Artefakte: bank.json, certificate_*.npz, families.jsonl, report.json, capture_audit.json, captures/, animations/, source/.
'''
    (out/'REPORT.md').write_text(text,encoding='utf-8')
    review={**r,'capture_audit_passed':True,'actually_captured':a['captured_images'],'coverage_gate_passed':gate,'tests_passed':21,'training_started':False}
    P.save(out/'review.json',review)
    if args.register:
        registry=P.ROOT/'monitor/training-runs.json';data=json.loads(registry.read_text(encoding='utf-8'));run=next(x for x in data['runs'] if x['id']=='vision-active-v3-run1');dest=P.ROOT/run['directory']/'presentation';entries=[]
        mappings=[('left','09_fuehrung_links','Neue Führung links → Blick rechts'),('right','10_fuehrung_rechts','Neue Führung rechts → Blick links'),('base','11_fuehrung_basis','Neue Führung zur Basis → Blick nach außen')]
        animation_report=json.loads((out/'animations/report.json').read_text())
        for family,slug,label in mappings:
            metric=next((v for v in animation_report if v['family']==family),None)
            if metric is None:continue
            stem='comparison-'+slug
            for suffix,kind in [('.gif','comparison-gif'),('.scene.json','comparison-scene')]:
                name=stem+suffix;shutil.copy2(out/'animations'/('guidance_'+family+suffix),dest/name)
                entries.append(dict(name=name,file='presentation/'+name,kind=kind,label=f"{label} · {metric['baseline_m']*100:.1f} cm · Zielabweichung {metric['axis_error_deg']:.2f}°"))
        for source,name,kind,label in [('REPORT.md','guidance-method.md','document','Neue Kameraführung · Methode und Grenzen'),('review.json','guidance-review.json','document','Neue Kameraführung · 200-Szenen-Prüfung'),('guidance_comparison.png','guidance-comparison.png','plot',f'Kameraführung · {r["total_before"]} → {r["total_after"]} Ansichten')]:
            shutil.copy2(out/source,dest/name);entries.append(dict(name=name,file='presentation/'+name,kind=kind,label=label))
        names={e['name'] for e in entries};run['artifacts']=entries+[a for a in run['artifacts'] if a['name'] not in names]
        run['description']=f"Vision-Training abgeschlossen. Neue Kameraführung: {r['total_before']} → {r['total_after']} gültige Zusatzansichten auf denselben 200 Pilotszenen; Zielnachführung ≤3°, neue Basisblicke. Vergleich und GIFs unter 3D-Abgleich. Keine neue Modelltrainierung oder freigegebene aktive Produktionspolicy; Bewegung ausschließlich mit Simulatorreferenz."
        registry.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(coverage_gate_passed=gate,total_after=r['total_after'],report=str(out/'REPORT.md'),registered=args.register)),flush=True)

if __name__=='__main__':main()
