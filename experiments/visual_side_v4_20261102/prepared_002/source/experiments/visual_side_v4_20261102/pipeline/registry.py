"""Local monitor registration; public config excludes the private replay index."""
from .common import ROOT,read,save
def register(run):
    cfg=read(run/'config.json');summary=read(run/'history.json')
    public={k:cfg[k] for k in ['status','task','paired_seeds','variants','parameters','optimization','selection','geometry_holdout','camera_holdout','geometry_plots','history','downstream_heads']}
    public.update(loss='BCE + 5×position + size + 0.5×symmetry rotation + 0.25×visibility; paired contexts',
        data_counts={k:v['count'] for k,v in cfg['splits'].items()},replay=dict(count=cfg['replay']['count'],role='historical perception training only'),
        lineage=dict(unique_historical_families=summary['unique_families'],reserved_namespaces=summary['reserved_seed_namespaces'],history_sha256=cfg['historical_registry_sha256']))
    if (run/'budget.json').exists():public['deadline_unix']=read(run/'budget.json')['deadline_unix']
    save(run/'public_config.json',public)
    path=ROOT/'monitor/training-runs.json';data=read(path);id='vision-side-v4-'+run.name.replace('_','-')
    entry=dict(id=id,category='vision',method='supervised',kind='design',title='Vision V4 · A/B-Seitenansichten · vorbereitet',directory=run.relative_to(ROOT).as_posix(),config='public_config.json',
        parameters=904112,geometryIndex='geometry/index.json',description='Vorbereitete Pipeline, noch kein V4-Training. A/B mit je drei Seeds. Neue Familien strikt getrennt; 25% Replay ausschließlich aus historischem V3-Trainingssplit. V3-Startgewichte, Simulatorreferenz für Kamerafahrten.',
        architecture=[['Parameter','904.112'],['Eingabe','2 feste + bis zu 3 Handbilder, RGB 160×160 und kalibrierte Strahlen'],['CNN','6 Conv-Lagen, Kanäle 32/64/128, ReLU'],['Decoder','3 Transformer-Lagen, Breite 128, 4 Heads, GELU'],['Ausgabe','5 Objekt-Slots, 16 Werte je Slot'],['Start','V3-M2, Hashs eingefroren']],
        artifacts=[dict(name='pipeline-lineage.json',file='history.json',kind='document',label='Historische Familien und Split-Herkunft'),dict(name='pipeline-config.json',file='public_config.json',kind='document',label='V4-Protokoll (öffentliche Zusammenfassung)'),
            dict(name='loss.png',file='loss.png',kind='plot',label='Train / Validation / feste Train-Probe'),dict(name='view-metrics.png',file='view_metrics.png',kind='plot',label='A/B-Fehler auf gleichen Blickkontexten'),dict(name='pipeline-results.json',file='results.json',kind='document',label='Tatsächliche V4-Ergebnisse'),dict(name='pipeline-data-audit.json',file='dataset_freeze.json',kind='document',label='Prüfung gegen historische und neue Datensplits')])
    prior=next((r for r in data['runs'] if r['id']==id),None)
    if prior and (run/'budget.json').exists():entry.update(kind='training',title='Vision V4 · A/B-Seitenansichten',description='A/B mit je drei Seeds; tatsächlicher Laufstatus und Messwerte. Historische Trainingsdaten nur als festes Replay, alle Validierungs-/Testfamilien gesperrt.')
    data['runs']=[entry]+[r for r in data['runs'] if r['id']!=id];save(path,data)
    return id
