"""Seal all artifacts after the pipeline and final editorial review have finished."""
from common import *

def main():
    assert read(OUT/'complete.json')['verified']
    assert read(OUT/'verification.json')['passed']
    manifest=read(OUT/'hashes.json')
    files={}
    for path in OUT.rglob('*'):
        if path.is_file() and path.name!='hashes.json' and path.suffix not in ('.pyc','.tmp'):
            files[str(path.relative_to(OUT))]=dict(sha256=digest(path),bytes=path.stat().st_size)
    manifest['files']=files
    manifest['scope']='Final completed artifacts, including complete.json and closed logs; excludes this manifest and Python bytecode.'
    write(OUT/'hashes.json',manifest)
    print(json.dumps(dict(sealed_files=len(files),complete_json_included='complete.json' in files)))

if __name__=='__main__':main()
