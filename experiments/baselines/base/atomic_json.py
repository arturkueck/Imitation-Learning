"""Atomic status writes resilient to short Windows sharing violations."""
import json
import os
from pathlib import Path
import tempfile
import time


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name+'.',suffix='.tmp',dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as stream:
            json.dump(value,stream,indent=2)
        for attempt in range(10):
            try:
                os.replace(temporary,path)
                break
            except PermissionError:
                if attempt==9: raise
                time.sleep(min(.05*2**attempt,.5))
    finally:
        if os.path.exists(temporary): os.unlink(temporary)
