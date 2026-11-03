"""Historical family/seed and content registry. No weights/data mutation."""
import ast,hashlib,json,sqlite3,subprocess
from pathlib import Path
import numpy as np
from .common import ROOT,sha,save

def role(path):
    parts=Path(path).parts
    if any(p.startswith(('smoke','preflight','pilot','data_pilot','guidance')) for p in parts):return 'development'
    if 'request_calibration' in parts or 'calibration' in parts:return 'calibration'
    if 'request_validation' in parts:return 'request_validation'
    if 'request_train' in parts:return 'request_train'
    if any(p.startswith(('reserved','test_')) or p=='test' for p in parts):return 'test'
    if 'validation' in parts:return 'model_validation'
    if 'train' in parts:return 'perception_train'
    return 'development'

def geometry_digest(row):
    active=np.asarray(row['active']).astype(bool)
    if not active.any():return None # Empty object sets are not unique scenes.
    signs=np.array([[a,b,c] for a in [-1,1] for b in [-1,1] for c in [-1,1]])
    objects=[]
    for i in np.flatnonzero(active):
        corners=(signs*np.asarray(row['sizes'][i])/2)@np.asarray(row['rotations'][i]).T+row['positions'][i]
        corners=np.round(corners/1e-5).astype(np.int64)
        objects.append(sorted(map(tuple,corners.tolist())))
    return hashlib.sha256(json.dumps(sorted(objects),separators=(',',':')).encode()).hexdigest()
def image_digest(images):
    a=np.ascontiguousarray(images)
    return hashlib.sha256(str(a.shape).encode()+a.tobytes()).hexdigest()

def connect(path,readonly=False):
    db=sqlite3.connect('file:'+Path(path).resolve().as_posix()+'?mode=ro',uri=True) if readonly else sqlite3.connect(path)
    if not readonly:db.executescript('''
        CREATE TABLE families(seed INTEGER, idx INTEGER, role TEXT, origin TEXT, PRIMARY KEY(seed,idx,role,origin));
        CREATE INDEX family_lookup ON families(seed,idx);
        CREATE TABLE fingerprints(kind TEXT,digest TEXT,seed INTEGER,idx INTEGER,role TEXT,origin TEXT);
        CREATE INDEX fingerprint_lookup ON fingerprints(kind,digest);
        CREATE TABLE seeds(seed INTEGER,role TEXT,origin TEXT,PRIMARY KEY(seed,role,origin));
        CREATE TABLE sources(path TEXT PRIMARY KEY,sha256 TEXT,kind TEXT);
    ''')
    return db

def add(db,family,usage,origin,row=None):
    seed,index=map(int,family)
    db.execute('INSERT OR IGNORE INTO families VALUES(?,?,?,?)',(seed,index,usage,origin))
    db.execute('INSERT OR IGNORE INTO seeds VALUES(?,?,?)',(seed,usage,origin))
    if row is not None:
        values=[]
        if all(k in row for k in ['positions','sizes','rotations','active']):
            digest=geometry_digest(row)
            if digest:values.append(('geometry',digest))
        if 'images' in row:
            images=row['images'];initial=images[0] if images.ndim==5 else images
            values.append(('initial_rgb',image_digest(initial)))
        db.executemany('INSERT INTO fingerprints VALUES(?,?,?,?,?,?)',[(kind,digest,seed,index,usage,origin) for kind,digest in values])

def inventory(destination):
    destination=Path(destination)
    if destination.exists():raise FileExistsError(destination)
    db=connect(destination);counts={};scanned=0
    # rg only enumerates relevant artifact/source names, not logs or checkpoints.
    result=subprocess.run(['rg','--files','--hidden','--no-ignore','experiments','-g','family.npy','-g','*.npz','-g','data_manifest.jsonl','-g','config.json','-g','protocol.json','-g','*.py'],cwd=ROOT,text=True,capture_output=True,check=True)
    files=[ROOT/p for p in result.stdout.splitlines() if Path(p).parts[1].startswith(('visual_','active_view_'))]
    for path in sorted(files):
        rel=path.relative_to(ROOT).as_posix()
        if '/pipeline/' in rel or path.name=='pipeline.py' or path.is_relative_to(destination.parent):continue
        if '/source' in rel:continue
        if path.name in ['config.json','protocol.json']:
            def reserve(v,in_seed=False):
                if isinstance(v,dict):
                    for k,x in v.items():reserve(x,in_seed or 'seed' in k.lower())
                elif isinstance(v,list):
                    for x in v:reserve(x,in_seed)
                elif in_seed and isinstance(v,int) and v>=1_000_000:
                    db.execute('INSERT OR IGNORE INTO seeds VALUES(?,?,?)',(v,'reserved_metadata',rel))
            reserve(json.loads(path.read_text(encoding='utf-8')));continue
        if path.suffix=='.py':
            # Conservatively reserve literal historical generator namespaces too.
            try:tree=ast.parse(path.read_text(encoding='utf-8-sig'))
            except (SyntaxError,UnicodeError):continue
            seeds={n.value for n in ast.walk(tree) if isinstance(n,ast.Constant) and isinstance(n.value,int) and 1_000_000<=n.value<100_000_000}
            db.executemany('INSERT OR IGNORE INTO seeds VALUES(?,?,?)',[(s,'development_literal',rel) for s in seeds]);continue
        if path.name=='data_manifest.jsonl':
            for line in path.read_text().splitlines():
                v=json.loads(line)
                if 'seed' not in v:continue
                usage='perception_train' if v.get('split','').startswith('train') else 'model_validation' if 'val' in v.get('split','') else 'test'
                db.execute('INSERT OR IGNORE INTO seeds VALUES(?,?,?)',(int(v['seed']),usage,rel))
                for i in range(int(v.get('count',0))):add(db,[v['seed'],i],usage,rel)
            db.execute('INSERT OR REPLACE INTO sources VALUES(?,?,?)',(rel,sha(path),'legacy_seed_index_only'));continue
        if path.name=='family.npy':
            family=np.load(path,mmap_mode='r',allow_pickle=False)
            if family.ndim!=2 or family.shape[1]!=2:raise ValueError('Unknown historical family schema: '+rel)
            folder=path.parent;usage=role(path);arrays={}
            for key in ['positions','sizes','rotations','active','images']:
                p=folder/(key+'.npy')
                if p.exists():arrays[key]=np.load(p,mmap_mode='r',allow_pickle=False)
            for i,f in enumerate(family):add(db,f,usage,rel,{k:a[i] for k,a in arrays.items()})
            db.execute('INSERT OR REPLACE INTO sources VALUES(?,?,?)',(rel,sha(path),'family_array'))
            counts[usage]=counts.get(usage,0)+len(family);scanned+=1
        elif path.suffix=='.npz':
            with np.load(path,allow_pickle=False) as z:
                if 'family' not in z.files:continue
                family=z['family'];usage=role(path)
                if family.shape==(2,):
                    keys=[k for k in ['positions','sizes','rotations','active','images'] if k in z.files]
                    add(db,family,usage,rel,{k:z[k] for k in keys});size=1
                elif family.ndim==2 and family.shape[1]==2:
                    arrays={k:z[k] for k in ['positions','sizes','rotations','active','images'] if k in z.files}
                    for i,f in enumerate(family):add(db,f,usage,rel,{k:a[i] for k,a in arrays.items()})
                    size=len(family)
                else:raise ValueError('Unknown historical NPZ family schema: '+rel)
                db.execute('INSERT OR REPLACE INTO sources VALUES(?,?,?)',(rel,sha(path),'npz_families'));counts[usage]=counts.get(usage,0)+size;scanned+=1
        if scanned and scanned%10==0:db.commit()
    db.commit()
    summary=dict(family_artifacts=scanned,role_observations=counts,unique_families=db.execute('SELECT COUNT(*) FROM (SELECT DISTINCT seed,idx FROM families)').fetchone()[0],
        reserved_seed_namespaces=db.execute('SELECT COUNT(DISTINCT seed) FROM seeds').fetchone()[0],
        ambiguous_historical_families=db.execute('SELECT COUNT(*) FROM (SELECT seed,idx FROM families GROUP BY seed,idx HAVING COUNT(DISTINCT role)>1)').fetchone()[0],
        legacy_scope='V1 image-only logs reserve seed/index namespaces; content fingerprints cover family-bearing V2/V3/pilot datasets. V2 starts from random initialization, V3 is the actual warm-start chain.')
    db.close();summary['registry_sha256']=sha(destination);save(destination.with_suffix('.json'),summary);return summary

def family_roles(db,family):return {r[0] for r in db.execute('SELECT DISTINCT role FROM families WHERE seed=? AND idx=?',tuple(map(int,family)))}
def assert_fresh_seed(db,seed):
    if db.execute('SELECT 1 FROM seeds WHERE seed=? LIMIT 1',(int(seed),)).fetchone():raise ValueError('Historical seed namespace reused: '+str(seed))
def assert_new_family(db,family):
    if family_roles(db,family):raise ValueError('Historical family cannot enter a new split: '+str(family))
def assert_replay(db,family):
    if family_roles(db,family)!={'perception_train'}:raise ValueError('Replay is not exclusively historical training: '+str(family))
def historical_duplicate(db,row):
    values=[('initial_rgb',image_digest(row['images'][0]))]
    geom=geometry_digest(row)
    if geom:values.append(('geometry',geom))
    for kind,digest in values:
        match=db.execute('SELECT seed,idx,role,origin FROM fingerprints WHERE kind=? AND digest=? LIMIT 1',(kind,digest)).fetchone()
        if match:return dict(kind=kind,source=list(match))
    return None
