"""Measured results and explicitly assumed planning scenarios, no training."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).resolve().parent
def main():
    fig,axes=plt.subplots(2,2,figsize=(13,9))
    ax=axes[0,0];x=np.arange(3)
    ax.bar(x-.18,[55,51,49],.36,color='#888888',label='A: nur Originaldaten')
    ax.bar(x+.18,[62,58,49],.36,color='#007a8a',label='C: eigene Dreierdaten')
    ax.axhline(90,color='red',ls='--');ax.set(xticks=x,xticklabels=[1,2,3],ylim=(0,105),xlabel='Parent-/Trainingsseed',ylabel='Stabile Dreiertuerme [%]',title='GEMESSEN: gleiche30.000 Zusatzupdates');ax.legend(fontsize=8)
    ax=axes[0,1];p=np.linspace(.5,1,200)
    ax.plot(p*100,p**4*100,color='#007a8a',label='Vier bedingte Platzierungen mit gleicher Rate')
    ax.axhline(90,color='red',ls='--');ax.axvline(.9**.25*100,color='red',ls=':');ax.scatter([60,.6**.5*100],[.6**4*100,36],color='#b47b22')
    ax.set(xlabel='Angenommene Rate jeder Platzierung [%]',ylabel='Fuenferturm-Erfolg [%]',ylim=(0,105),title='RECHENMODELL: p(Turm) = p(Platzierung)^4');ax.legend(fontsize=7)
    ax.text(52,82,'Fuer90% Gesamtziel: ca.97,4% je Schritt\nNur Modellrechnung; gleiche bedingte Raten angenommen.',fontsize=8)
    ax=axes[1,0];updates=np.array([30000,30000,120000]);equiv=updates*64/27322
    bars=ax.bar(['3er-Stufe','4er-Stufe','5er-Stufe'],equiv,color=['#8fc5cc','#4b9ca8','#007a8a'])
    for b,u in zip(bars,updates):ax.text(b.get_x()+b.get_width()/2,b.get_height()+4,f'{u/1000:.0f}k Updates',ha='center',fontsize=9)
    ax.set(ylabel='Originaldatenpass-Aequivalente',ylim=(0,365),title='PLANBEISPIEL je Seed: kein Epochen-Erfolgsversprechen')
    ax.text(.02,.89,'30k /30k /120k sind vorab gewaehlte Oberbudgets.\nNicht gemessene notwendige Epochen bis60% oder90%.\nRL ohneIL: unbekannt; RL-Epochen nicht direkt vergleichbar.',transform=ax.transAxes,fontsize=8)
    ax=axes[1,1];rl=np.linspace(0,5,200);ax.plot(rl,rl,color='#777777',label='RL: angenommener, bisher unbekannter Bedarf')
    for p5,color in [(.6,'#007a8a'),(.2,'#c59436'),(.1,'#b75050')]:
        cost=(100/.6*(1000+1500)+100/p5*2000)/1e6
        ax.axhline(cost,color=color,label=f'Sammel-Szenario IL: p5={p5:.0%}, ca.{cost:.2f}M Schritte')
    ax.set(xlabel='Angenommener RL-Umweltschrittbedarf [Mio.]',ylabel='Umweltschritte [Mio.]',ylim=(0,5),title='BREAK-EVEN-SZENARIO: kein gemessener RL-Speedup')
    ax.legend(fontsize=7,loc='upper left');ax.text(.03,.04,'IL-Linien: je100 Erfolge bei3/4/5; p3=p4=60%.\nJe Versuch max.1000/1500/2000 Schritte angenommen.\nOptimierung, Evaluation und historische Kosten fehlen hier!',transform=ax.transAxes,fontsize=8)
    for ax in axes.flat:ax.grid(axis='y',alpha=.15)
    fig.suptitle('Fuenferturm-Curriculum: Evidenz, Fehlerkette und offene Trainingskosten',fontsize=14)
    fig.tight_layout(rect=(0,0,1,.96));fig.savefig(P/'hypothesis.png',dpi=160);plt.close(fig)
    (P/'scenario_assumptions.json').write_text(json.dumps(dict(measured_A=[55,51,49],measured_C=[62,58,49],illustrative_update_caps=[30000,30000,120000],batch=64,reference_frames=27322,rl_observations=None,collection_successes_per_stage=100,assumed_p3=.6,assumed_p4=.6,assumed_p5=[.6,.2,.1],assumed_horizons=[1000,1500,2000],warning='All future costs are illustrative budgets/scenarios, not fitted predictions or confidence bands.'),indent=2))
if __name__=='__main__':main()
