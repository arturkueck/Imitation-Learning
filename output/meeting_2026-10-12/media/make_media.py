"""Reproducible meeting illustrations. No training or simulation is performed."""
from pathlib import Path
import json
import math
import hashlib

from PIL import Image, ImageDraw, ImageFont
import imageio.v2 as imageio
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DATA = ROOT / "praxis/reports/lift_ph_full_100ep_summary.json"
BG = "#F5F3EF"
INK = "#182B3A"
MUTED = "#5A6872"
TEAL = "#147D71"
PURPLE = "#7953AE"
ORANGE = "#CE6B24"
GRID = "#DCE2E3"
WHITE = "#FFFFFF"
FONT = Path("C:/Windows/Fonts/segoeui.ttf")
BOLD = Path("C:/Windows/Fonts/segoeuib.ttf")

def font(size, bold=False):
    return ImageFont.truetype(str(BOLD if bold else FONT), size)

def text(d, xy, s, size=28, fill=INK, bold=False, anchor=None):
    d.text(xy, s, font=font(size,bold), fill=fill, anchor=anchor)

def arrow(d, p, q, color, width=7, head=17):
    d.line([p,q], fill=color, width=width)
    a = math.atan2(q[1]-p[1], q[0]-p[0])
    pts = [q, (q[0]-head*math.cos(a-.48),q[1]-head*math.sin(a-.48)),
           (q[0]-head*math.cos(a+.48),q[1]-head*math.sin(a+.48))]
    d.polygon(pts, fill=color)

def dashed(d, p, q, fill=GRID, width=3, dash=12, gap=8):
    length=math.dist(p,q)
    if length == 0:
        return
    n=0
    while n < length:
        a=n/length; b=min(length,n+dash)/length
        d.line([(p[0]+(q[0]-p[0])*a,p[1]+(q[1]-p[1])*a),
                (p[0]+(q[0]-p[0])*b,p[1]+(q[1]-p[1])*b)],fill=fill,width=width)
        n += dash+gap

def grip(d, x, y, color=INK, ghost=False, scale=1):
    # A schematic top-down gripper, with its two fingers facing the target.
    points=[(x-29*scale,y+20*scale),(x-29*scale,y-12*scale),
            (x+29*scale,y-12*scale),(x+29*scale,y+20*scale)]
    for p,q in zip(points,points[1:]):
        if ghost:
            dashed(d,p,q,color,width=max(2,int(5*scale)),dash=9*scale,gap=6*scale)
        else:
            d.line([p,q],fill=color,width=max(2,int(8*scale)))
    if not ghost:
        d.ellipse([x-6*scale,y-6*scale,x+6*scale,y+6*scale],fill=color)

def cube(d, x, y, size=42):
    d.rounded_rectangle([x-size/2,y-size/2,x+size/2,y+size/2],radius=6,
                        fill="#D6E8E1",outline=TEAL,width=3)

def card(d,box):
    d.rounded_rectangle(box, radius=24,fill=WHITE,outline=GRID,width=2)

def concept():
    im=Image.new("RGB",(1800,1120),BG); d=ImageDraw.Draw(im)
    text(d,(70,38),"FORSCHUNGSIDEE · ROBUSTES IMITATION LEARNING",24,TEAL,True)
    text(d,(70,82),"Zwei Störungen – zwei Lernziele",62,bold=True)
    text(d,(70,165),"Was die Policy ignorieren sollte und worauf sie reagieren muss.",31,MUTED)
    panels=[(70,242,865,850),(935,242,1730,850)]
    for b in panels: card(d,b)
    for i,(left,top,right,bottom) in enumerate(panels):
        color=PURPLE if i==0 else ORANGE
        text(d,(left+32,top+27),f"0{i+1}",24,color,True)
        text(d,(left+92,top+19),"Sensorfehler" if i==0 else "Physische Zustandsabweichung",36,bold=True)
        text(d,(left+32,top+81),"Nur die Messung ist verändert." if i==0 else "Der reale Zustand ist verändert.",27,MUTED)
        x=left+300; y=top+220
        cube(d,x,top+430,48)
        text(d,(x,top+478),"Zielobjekt",25,MUTED,anchor="mm")
        dashed(d,(x,y+30),(x,top+390),GRID,3)
        if i==0:
            grip(d,x,y,scale=1.3)
            grip(d,x+230,y,PURPLE,True,1.3)
            dashed(d,(x+48,y),(x+176,y),PURPLE,4)
            text(d,(x-58,y-73),"real",27,INK,True)
            text(d,(x+156,y-73),"gemessen",27,PURPLE,True)
            arrow(d,(x,y+45),(x,top+373),TEAL,9,23)
            text(d,(x+44,top+328),"gleiche",26,TEAL,True)
            text(d,(x+44,top+362),"Aufgabenaktion",26,TEAL,True)
        else:
            grip(d,x,y,"#BBC5CB",True,1.3)
            grip(d,x+230,y,INK,False,1.3)
            arrow(d,(x+48,y),(x+170,y),ORANGE,7,21)
            text(d,(x-83,y-77),"Referenz",25,MUTED)
            text(d,(x+150,y-95),"real +",26,INK,True)
            text(d,(x+150,y-62),"gemessen",26,INK,True)
            arrow(d,(x+208,y+43),(x+35,top+381),TEAL,9,23)
            text(d,(x+183,top+348),"korrigierte",26,TEAL,True)
            text(d,(x+183,top+381),"Aktion",26,TEAL,True)
        d.line([left+32,top+519,right-32,top+519],fill=GRID,width=2)
        text(d,(left+32,top+540),"Lernziel: möglichst messfehler-invariant" if i==0 else "Lernziel: Abweichung aktiv verkleinern",28,color,True)
    d.rounded_rectangle([70,895,1730,1025],radius=20,fill="#E4ECE7")
    text(d,(98,915),"Prüfbare Frage",25,TEAL,True)
    text(d,(98,955),"Hilft ein Dynamikmodell bei realen Abweichungen über reine Sensoraugmentation hinaus?",31,bold=True)
    text(d,(70,1060),"Schematische Illustration – keine Versuchsdaten. Aktionen sind idealisierte Lernziele, keine Modellvorhersagen.",24,MUTED)
    im.save(HERE/"01_sensor_vs_state.png")

def ease(z):
    z=max(0,min(1,z)); return z*z*(3-2*z)

def animation_frame(t):
    im=Image.new("RGB",(1440,900),BG); d=ImageDraw.Draw(im)
    text(d,(50,28),"Sensorfehler oder echte Zustandsabweichung?",43,bold=True)
    d.rounded_rectangle([50,92,1390,144],radius=12,fill="#E8DED1")
    text(d,(720,116),"Schematische Illustration – keine Versuchsdaten",27,INK,True,"mm")
    phase="1  Ausgangslage: gleicher Zustand, gleiche Aufgabe" if t<2 else ("2  Störung: Messung fehlerhaft oder Zustand verschoben" if t<4 else "3  Lernziel: Messfehler ignorieren, Zustandsfehler korrigieren")
    text(d,(50,170),phase,28,MUTED)
    sensor_active=t>=2
    displacement=200*ease((t-2)/.8)*(1-ease((t-4)/3.8))
    for i,left in enumerate([50,750]):
        card(d,[left,225,left+640,705])
        text(d,(left+28,246),"SENSORFEHLER" if i==0 else "PHYSISCHE ABWEICHUNG",26,PURPLE if i==0 else ORANGE,True)
        text(d,(left+28,286),"Realer Zustand bleibt gleich" if i==0 else "Realer Zustand verändert sich",25,MUTED)
        x=left+228; y=426
        cube(d,x,601,44)
        dashed(d,(x,y+30),(x,565),GRID,3)
        text(d,(x,651),"Zielobjekt",23,MUTED,anchor="mm")
        if i==0:
            grip(d,x,y,scale=1.3)
            if sensor_active:
                dx=145+24*math.sin(t*7)
                dy=17*math.sin(t*5)
                grip(d,x+dx,y+dy,PURPLE,True,1.3)
                text(d,(left+411,493),"Messung",22,PURPLE,True)
                dashed(d,(x+40,y),(x+dx-43,y+dy),PURPLE,3)
            else:
                d.ellipse([x-48,y-37,x+48,y+36],outline=PURPLE,width=3)
            text(d,(x-42,367),"real",24,INK,True)
            arrow(d,(x,y+45),(x,560),TEAL,8,21)
        else:
            grip(d,x,y,"#BBC5CB",True,1.3)
            grip(d,x+displacement,y,scale=1.3)
            text(d,(left+377,330),"real + Messung",23,INK,True)
            if 2<=t<4 and displacement>60:
                arrow(d,(x+45,y-58),(x+displacement-26,y-58),ORANGE,6,17)
            arrow(d,(x+displacement,y+45),(x+3,560),TEAL,8,21)
            if t>=4 and displacement>10:
                text(d,(left+384,535),"Korrektur",24,TEAL,True)
    d.rounded_rectangle([50,738,1390,820],radius=15,fill="#E4ECE7")
    text(d,(75,755),"GLEICHE AKTION",24,TEAL,True)
    text(d,(775,755),"PASSENDE KORREKTUR",24,TEAL,True)
    text(d,(75,787),"bei irrelevanter Messabweichung",22,MUTED)
    text(d,(775,787),"bei realer Abweichung von der Referenz",22,MUTED)
    text(d,(50,846),"Idealisierte Lernziele. Die gezeigte Rückkehr ist keine gemessene Policy-Leistung.",23,MUTED)
    d.rounded_rectangle([50,886,1390,891],radius=2,fill=GRID)
    d.rounded_rectangle([50,886,50+1340*min(1,t/9.9),891],radius=2,fill=TEAL)
    return im

def animate():
    frames=[]
    writer=imageio.get_writer(HERE/"02_sensor_vs_state.mp4",fps=10,codec="libx264",quality=8,macro_block_size=2)
    for i in range(100):
        fr=animation_frame(i/10)
        writer.append_data(np.asarray(fr))
        frames.append(fr.convert("P",palette=Image.Palette.ADAPTIVE,colors=128))
    writer.close()
    frames[0].save(HERE/"02_sensor_vs_state.gif",save_all=True,append_images=frames[1:],duration=100,loop=0,optimize=False,disposal=2)
    # Three actual animation frames for inspection and handout use.
    selected=[animation_frame(t).resize((720,450),Image.Resampling.LANCZOS) for t in [0,3,5.5]]
    sheet=Image.new("RGB",(2160,450),BG)
    for i,fr in enumerate(selected):sheet.paste(fr,(i*720,0))
    sheet.save(HERE/"02_animation_storyboard.png")

def historical():
    report=json.loads(DATA.read_text(encoding="utf-8"))
    rows=[r for r in report["rows"] if r["condition"]=="nominal"]
    assert [r["training_seed"] for r in rows] == [1,2,3]
    assert sum(r["bc_successes"] for r in rows)==44
    assert sum(r["extension_successes"] for r in rows)==56
    im=Image.new("RGB",(1800,1120),BG); d=ImageDraw.Draw(im)
    text(d,(70,38),"HISTORISCH · EXPLORATIV · LOKALE VORARBEIT",25,ORANGE,True)
    text(d,(70,82),"Lift: ein Ausgangspunkt, noch kein Nachweis",56,bold=True)
    text(d,(70,165),"Nominal · 10.000 Updates je Modell · Lift PH / Low-Dimensional · 20 Rollouts je Trainingsseed",28,MUTED)
    x0,x1=295,1570; y0,y1=345,768
    for tick in range(0,101,20):
        x=x0+(x1-x0)*tick/100
        d.line([(x,y0-18),(x,y1)],fill=GRID,width=2)
        text(d,(x,y1+28),f"{tick} %",24,MUTED,anchor="mm")
    text(d,((x0+x1)/2,y1+77),"Erfolgsrate in den nominalen Test-Rollouts",27,MUTED,anchor="mm")
    d.ellipse([73,246,93,266],fill=INK)
    text(d,(110,236),"Behavioral Cloning (BC)",27,INK,True)
    d.ellipse([624,246,644,266],fill=TEAL)
    text(d,(661,236),"Frühere lokale Erweiterung",27,TEAL,True)
    for row,y in zip(rows,[392,545,698]):
        text(d,(70,y),f"Trainingsseed {row['training_seed']}",25,bold=True,anchor="lm")
        bc=row["bc_successes"] / row["episodes"]*100
        ext=row["extension_successes"] / row["episodes"]*100
        a=x0+(x1-x0)*bc/100; b=x0+(x1-x0)*ext/100
        d.line([(a,y),(b,y)],fill="#A5BAB3",width=6)
        d.ellipse([a-12,y-12,a+12,y+12],fill=INK)
        d.ellipse([b-12,y-12,b+12,y+12],fill=TEAL)
        text(d,(a,y+38),f"{row['bc_successes']}/20",27,INK,True,"mm")
        text(d,(b,y-40),f"{row['extension_successes']}/20",27,TEAL,True,"mm")
    d.rounded_rectangle([70,900,1730,1013],radius=18,fill="#E7ECE8")
    text(d,(100,919),"Gepoolt: BC 44/60 (73,3 %) · frühere Erweiterung 56/60 (93,3 %)",32,bold=True)
    text(d,(100,963),"Drei Trainingsseeds sind die unabhängigen Trainingswiederholungen; 60 Rollouts sind keine 60 Seeds.",25,MUTED)
    text(d,(70,1043),"Keine Signifikanzbehauptung und kein Stabilitätsnachweis. Die vorgeschlagene neue Methode ist damit nicht validiert.",24,MUTED)
    text(d,(70,1080),"Quelle: praxis/reports/lift_ph_full_100ep_summary.json · Darstellung: nominal, alle drei vorhandenen Trainingsseeds",21,MUTED)
    im.save(HERE/"03_historical_lift_seeds.png")

def readme():
    digest=hashlib.sha256(DATA.read_bytes()).hexdigest()
    body=f'''# Medien für die erste Rücksprache

Erstellt am 12. Oktober 2026. Alle Dateien sind lokal erzeugt; es wurde kein Modell trainiert und keine neue Simulation ausgeführt.

## Dateien und Verwendung

- `01_sensor_vs_state.png`: Konzeptgrafik (1800 × 1120 Pixel). Links ändert sich nur die gemessene Greiferposition, rechts der reale Zustand. Die grünen Pfeile zeigen idealisierte gewünschte Aktionen. Sie sind keine gemessenen Modellausgaben. Die eingezeichnete Invarianz ist das Lernziel bei irrelevanten Messfehlern, keine Aussage über beliebige Sensorfehler.
- `02_sensor_vs_state.mp4`: 10 Sekunden, 10 Bilder/s, 1440 × 900 Pixel, H.264; dieselbe Unterscheidung als schematische Animation. Sichtbar beschriftet mit „Schematische Illustration – keine Versuchsdaten“. Die eingezeichnete Rückkehr zur Referenz demonstriert das Lernziel und keine Leistungsfähigkeit eines trainierten Modells.
- `02_sensor_vs_state.gif`: Endlosschleife derselben 10-Sekunden-Animation, 100 Bilder/s **nicht** erforderlich: die Datei verwendet 100 ms pro Bild (= 10 Bilder/s).
- `02_animation_storyboard.png`: Tatsächliche Frames aus der Animation zu t = 0, 3 und 5,5 Sekunden, zur visuellen Prüfung und als statische Alternative.
- `03_historical_lift_seeds.png`: Historische lokale nominale Lift-Ergebnisse für alle drei Trainingsseeds, mit identischem Achsenmaßstab von 0 bis 100 %. Es werden absolute Erfolge pro 20 Rollouts ausgewiesen. Drei Linien verbinden die beiden Methoden desselben Trainingsseeds. Gepoolte Zahlen dienen nur der Beschreibung.
- `make_media.py`: Reproduzierbarer Erstellungscode. Benötigt Pillow, NumPy, imageio und imageio-ffmpeg; ausführbar mit der vorhandenen `praxis/.venv/Scripts/python.exe`.

## Daten und Grenzen der Interpretation

Die historischen Ergebnisse stammen ausschließlich aus `praxis/reports/lift_ph_full_100ep_summary.json` (SHA-256: `{digest}`). Nominale Werte: Seed 1 BC 16/20, frühere Erweiterung 18/20; Seed 2 15/20 und 20/20; Seed 3 13/20 und 18/20. Summe: 44/60 und 56/60. Die Trainingskonfiguration `praxis/configs/lift_ph_bc_contraction_w1e100_seed1.json` enthält 100 Epochen mit 100 Updates pro Epoche. Die Verfahrensbeschreibung steht in `praxis/README.md`.

Diese Abbildung zeigt die **frühere lokale Erweiterung**, nicht die noch untrainierte neue Loss-Variante. Ein Ergebnisunterschied beweist weder einen kausalen Dynamikmechanismus noch Stabilität. Die drei Trainingsseeds werden einzeln gezeigt; die 60 Test-Rollouts sind keine 60 unabhängigen Trainingswiederholungen. Es wird keine Signifikanz behauptet. Die Vorarbeit motiviert eine kontrollierte Untersuchung; sie ist nicht deren Ergebnis.

Die Konzeptgrafik und Animation sind eigene schematische Zeichnungen ohne externe Bildvorlagen. Die Datenabbildung verwendet lokale Vorarbeiten. Die wissenschaftliche Literaturzuordnung gehört in das zugehörige Gesprächsdokument; die Medien treffen keine Neuheitsbehauptung.
'''
    body=body.replace('Endlosschleife derselben 10-Sekunden-Animation, 100 Bilder/s **nicht** erforderlich: die Datei verwendet 100 ms pro Bild (= 10 Bilder/s).','Endlosschleife derselben 10-Sekunden-Animation, 100 ms pro Bild (= 10 Bilder/s).')
    (HERE/"README.md").write_text(body,encoding="utf-8")

if __name__ == "__main__":
    HERE.mkdir(parents=True,exist_ok=True)
    concept()
    animate()
    historical()
    readme()
    print(json.dumps({p.name:p.stat().st_size for p in HERE.iterdir() if p.is_file()},indent=2))
