"""Atomic cross-run family/content claims, including concurrently collected data."""
import json,sqlite3
from .common import ROOT,sha
from .lineage import geometry_digest,image_digest

def path():return ROOT/'monitor/vision-data-claims.sqlite'
def claim(row,split,owner,destination=None,verify_only=False):
    destination=destination or path();destination.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(destination,timeout=30)
    db.executescript('''CREATE TABLE IF NOT EXISTS families(seed INTEGER,idx INTEGER,split TEXT,owner TEXT,digests TEXT,PRIMARY KEY(seed,idx));
    CREATE TABLE IF NOT EXISTS fingerprints(kind TEXT,digest TEXT,seed INTEGER,idx INTEGER,split TEXT,owner TEXT,PRIMARY KEY(kind,digest));''')
    seed,index=map(int,row['family']);digests=dict(initial_rgb=image_digest(row['images'][0]));geometry=geometry_digest(row)
    if geometry:digests['geometry']=geometry
    serialized=json.dumps(digests,sort_keys=True)
    try:
        db.execute('BEGIN IMMEDIATE')
        old=db.execute('SELECT split,owner,digests FROM families WHERE seed=? AND idx=?',(seed,index)).fetchone()
        if old and old!=(split,owner,serialized):raise ValueError('Cross-run family role/owner/content conflict')
        for kind,digest in digests.items():
            prior=db.execute('SELECT seed,idx,split,owner FROM fingerprints WHERE kind=? AND digest=?',(kind,digest)).fetchone()
            if prior and prior!=(seed,index,split,owner):raise ValueError('Cross-run content duplicate: '+str(prior))
        if verify_only:
            if old is None:raise ValueError('Missing cross-run family claim')
        else:
            db.execute('INSERT OR IGNORE INTO families VALUES(?,?,?,?,?)',(seed,index,split,owner,serialized))
            db.executemany('INSERT OR IGNORE INTO fingerprints VALUES(?,?,?,?,?,?)',[(kind,digest,seed,index,split,owner) for kind,digest in digests.items()])
        db.commit()
    except Exception:db.rollback();raise
    finally:db.close()
