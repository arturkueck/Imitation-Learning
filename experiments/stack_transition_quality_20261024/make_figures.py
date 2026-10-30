"""Static explanatory figures. All quality examples are synthetic, not run results."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle, Circle

OUT = Path(__file__).resolve().parent
FIG = OUT / 'figures'
FIG.mkdir(exist_ok=True)
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11,
                     'svg.fonttype': 'none'})
INK = '#243443'
BLUE = '#226b94'
TEAL = '#287c72'
PURPLE = '#81549c'
ORANGE = '#bd7424'
GRAY = '#657785'


def box(ax, x, y, w, h, title, detail, color=BLUE):
    ax.add_patch(FancyBboxPatch((x-w/2, y-h/2), w, h,
                 boxstyle='round,pad=0.06,rounding_size=0.12',
                 linewidth=1.4, edgecolor=color, facecolor='#f6f9fb'))
    ax.text(x, y+.21, title, ha='center', va='center', color=color,
            fontsize=12, weight='bold')
    ax.text(x, y-.24, detail, ha='center', va='center', color=INK,
            fontsize=10.5, linespacing=1.4)


def arrow(ax, start, end, color=GRAY, dashed=False):
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle='-|>',
                 mutation_scale=16, linewidth=1.8, color=color,
                 linestyle='--' if dashed else '-'))


def save(fig, name):
    fig.savefig(FIG / (name+'.png'), dpi=180, bbox_inches='tight', facecolor='white')
    fig.savefig(FIG / (name+'.svg'), bbox_inches='tight', facecolor='white')
    plt.close(fig)


def information_flow():
    fig, ax = plt.subplots(figsize=(13.4, 8.5))
    ax.set(xlim=(0, 14), ylim=(-.2, 9)); ax.axis('off')
    fig.suptitle('Informationsübertrag: sichere Handlungen lernen, Zukunftswissen trennen',
                 fontsize=16, weight='bold', y=.97, color=INK)
    ax.text(7, 8.5, 'Geplanter Datenfluss · jeder Datensatz behält seine Teacher- und Episodenherkunft',
            ha='center', color=GRAY, fontsize=11)
    box(ax, 7, 7.25, 6.3, 1.05, 'Geloggter Teacher-Rollout',
        'Vor jeder Aktion beobachten → Aktion ausführen\n→ vollständigen Verlauf speichern')
    cols = [2.4, 7, 11.6]
    for x in cols:
        arrow(ax, (7, 6.65), (x, 5.95))
    box(ax, cols[0], 5.25, 3.75, 1.25, 'Zustand vor der Aktion',
        'Greifer, Quelle, Phase\nArm C zusätzlich: unterer Turm', BLUE)
    box(ax, cols[1], 5.25, 3.75, 1.25, 'Ausgeführte Aktion',
        'Tatsächliche Teacherbewegung\nund Greiferaktion', TEAL)
    box(ax, cols[2], 5.25, 3.75, 1.25, 'Späterer Übergangsverlauf',
        'Turmerhalt, Verschiebung,\nKontakte, nächste Aufnahme', PURPLE)
    for x, col in zip(cols, [BLUE, TEAL, PURPLE]):
        arrow(ax, (x, 4.55), (x, 3.9), col)
    box(ax, cols[0], 3.2, 3.75, 1.25, 'Student bekommt s(t)',
        'Nur jetzt beobachtbare Größen\n→ eigene Aktionsvorhersage', BLUE)
    box(ax, cols[1], 3.2, 3.75, 1.25, 'Imitationsziel a(t)',
        'Aktion wird nicht durch den\nQualitätsscore umgeschrieben', TEAL)
    box(ax, cols[2], 3.2, 3.75, 1.25, 'Gültigkeit + Gewicht g',
        'Rückblickende Bewertung\nändert den Lernbeitrag', PURPLE)
    arrow(ax, (2.4, 2.5), (5.1, 1.65), BLUE)
    arrow(ax, (7, 2.5), (7, 1.8), TEAL)
    arrow(ax, (11.6, 2.5), (8.9, 1.65), PURPLE)
    box(ax, 7, 1.1, 7.8, 1.2, 'Gewichtetes Behavior Cloning → neues Modell',
        'Lernt, ausgewählte Teacheraktionen aus aktuellen Zuständen vorherzusagen', TEAL)
    ax.text(7, -.02, 'Kein Informationspfad von späterer Stabilität zum Policyinput.\n'
            'Ein gutes Gewicht ist keine neue oder korrigierte Expertenaktion.',
            ha='center', va='top', fontsize=11, color=PURPLE, linespacing=1.5)
    save(fig, '01_information_flow')


def tower(ax, source=True):
    ax.plot([.15, 3.7], [.45, .45], color=GRAY, lw=2)
    for i in range(2):
        ax.add_patch(Rectangle((.8, .45+i*.5), .5, .5,
                     edgecolor=TEAL, facecolor='#c1ded6', lw=1.5))
    if source:
        ax.add_patch(Rectangle((2.8, .45), .5, .5, edgecolor=ORANGE,
                             facecolor='#f0d3aa', lw=1.5))


def gripper(ax, x, y):
    ax.plot([x-.16, x+.16], [y, y], color=INK, lw=3)
    ax.plot([x-.16, x-.16], [y, y-.22], color=INK, lw=3)
    ax.plot([x+.16, x+.16], [y, y-.22], color=INK, lw=3)


def transition_window():
    fig = plt.figure(figsize=(13, 7.2))
    grid = fig.add_gridspec(2, 3, height_ratios=[3.1, 1], hspace=.18,
                           left=.045, right=.98, top=.79, bottom=.12, wspace=.12)
    titles = ['1 · Freigegebenes Präfix', '2 · Rückzug und Anflug', '3 · Nächste Aufnahme']
    for i in range(3):
        ax = fig.add_subplot(grid[0, i]); ax.set(xlim=(0, 4), ylim=(0, 3)); ax.axis('off')
        tower(ax, source=(i != 2)); ax.set_title(titles[i], fontsize=13, color=INK, pad=15)
        if i == 0:
            gripper(ax, 1.05, 1.85)
            ax.text(1.05, .17, 'Unterer Turm', ha='center', color=TEAL, fontsize=11)
            ax.text(3.05, .17, 'Nächste Quelle', ha='center', color=ORANGE, fontsize=10)
            arrow(ax, (1.05, 2), (1.05, 2.65), TEAL)
            ax.text(2.45, 2.6, 'Referenzpositionen\nfesthalten', ha='center', color=INK, fontsize=11)
        elif i == 1:
            gripper(ax, 2.05, 2.65)
            arrow(ax, (1.05, 1.9), (1.05, 2.6), TEAL)
            arrow(ax, (1.22, 2.6), (3.05, 2.6), TEAL)
            arrow(ax, (3.05, 2.48), (3.05, 1.2), TEAL)
            arrow(ax, (1.22, 1.65), (2.8, 1.1), '#b44d4d', dashed=True)
            ax.text(1.9, .11, 'Turm schützen, Abstand gewinnen', ha='center', color=TEAL, fontsize=10.5)
        else:
            gripper(ax, 3.05, 1.85)
            # The next source has been lifted; keep lower tower unchanged.
            ax.add_patch(Rectangle((2.8, 1.12), .5, .5, edgecolor=ORANGE,
                                 facecolor='#f0d3aa', lw=1.5))
            arrow(ax, (3.6, 1.15), (3.6, 2.1), ORANGE)
            ax.text(1.12, 2.4, 'Unterer Turm\nweiter gültig?', ha='center', color=TEAL, fontsize=11)
            ax.text(1.9, .11, 'Aufnahme + Stabilitätsnachlauf', ha='center', color=INK, fontsize=10.5)
    ax = fig.add_subplot(grid[1, :]); ax.set(xlim=(0, 12), ylim=(0, 1)); ax.axis('off')
    arrow(ax, (.4, .72), (11.6, .72), PURPLE)
    ax.text(6, .87, 'Qualität wird über den vollständigen Übergang bewertet',
            ha='center', color=PURPLE, fontsize=12)
    ax.text(6, .19, 'Turmerhalt · maximale Einzelwürfelverschiebung · erneute Kontakte · Freiraum',
            ha='center', color=INK, fontsize=11)
    fig.suptitle('Was vom Übergang in den Datensatz übernommen wird', fontsize=16,
                 weight='bold', y=.96, color=INK)
    fig.text(.5, .86, 'Schematische Bewegungswege, keine Simulationsmessung oder fest programmierte Teacherbahn',
             ha='center', color=GRAY, fontsize=11)
    fig.text(.5, .035, 'Grün: zu prüfende sichere Variante   ·   Rot gestrichelt: mögliche Gefährdung   ·   '
             'Orange: neuer Quellwürfel', ha='center', color=GRAY, fontsize=10.5)
    save(fig, '02_transition_window')


def weighted_transfer():
    q = [.2, .5, .9]; g = [.5+1.5*v for v in q]; shares = [v/sum(g) for v in g]
    (OUT/'illustration.json').write_text(json.dumps(dict(synthetic=True,
        quality=q, raw_weights=g, relative_new_pool_shares=shares,
        replay_fractions=dict(original=.5, previous=.25, new=.25)), indent=2))
    fig, axes = plt.subplots(1, 2, figsize=(12, 6.1), gridspec_kw={'width_ratios':[1,1.25]})
    fig.subplots_adjust(left=.08, right=.97, top=.76, bottom=.32, wspace=.35)
    ax = axes[0]; labels=['Abschnitt A', 'Abschnitt B', 'Abschnitt C']
    ax.barh(labels, g, color=[BLUE, TEAL, PURPLE], height=.5)
    ax.invert_yaxis(); ax.set(xlim=(0, 2.3), xlabel='Rohgewicht g = 0,5 + 1,5 × Q')
    ax.set_title('Gültige Beispiele bleiben enthalten', fontsize=12, pad=20)
    for i, (qq, gg) in enumerate(zip(q,g)):
        ax.text(gg+.05, i, f'Q={qq:.1f}\ng={gg:.2f}', va='center', fontsize=10.5, color=INK)
    ax.spines[['top','right']].set_visible(False)
    ax = axes[1]; start=0
    for width, label, color in [(.5,'50%\nOriginal',BLUE),(.25,'25%\nReplay',TEAL),(.25,'25%\nNeu',PURPLE)]:
        ax.barh(.7,width,left=start,height=.28,color=color)
        ax.text(start+width/2,.7,label,ha='center',va='center',color='white',fontsize=11)
        start+=width
    ax.text(.5,.98,'Gesamter Actor-Loss: feste Anteile',ha='center',fontsize=12,color=INK)
    start=0
    for width,color in zip(shares,[BLUE,TEAL,PURPLE]):
        ax.barh(.15,width,left=start,height=.22,color=color)
        ax.text(start+width/2,.15,f'{100*width:.1f}%',ha='center',va='center',color='white',fontsize=10)
        start+=width
    ax.text(.5,.41,'Nur innerhalb des neuen Viertels normalisieren',ha='center',fontsize=11,color=PURPLE)
    ax.set(xlim=(0,1),ylim=(-.14,1.12));ax.axis('off')
    fig.suptitle('Qualität verändert den Lernbeitrag, nicht die ausgeführte Zielaktion',
                 y=.96,fontsize=15,weight='bold',color=INK)
    fig.text(.5,.86,'Illustrative Werte bei gleicher Basis-Samplinghäufigkeit · keine gemessenen Qualitätswerte',
             ha='center',fontsize=11,color=GRAY)
    fig.text(.5,.07,'Gewichte im Loss anwenden; nicht zusätzlich nochmals qualitätsabhängig oversamplen.\n'
             'Die Normalisierung erhält den neuen Replayanteil bei 25%.',ha='center',fontsize=11,color=INK,linespacing=1.5)
    save(fig, '03_weighted_transfer')


if __name__ == '__main__':
    information_flow(); transition_window(); weighted_transfer()
    print('Created three explanatory figures in PNG and SVG.')
