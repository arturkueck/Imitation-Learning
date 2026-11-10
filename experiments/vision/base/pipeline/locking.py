"""OS-held nonblocking run lock, independent of sandbox PID visibility."""
import os
from contextlib import contextmanager
from pathlib import Path

@contextmanager
def exclusive(run):
    run=Path(run);run.mkdir(parents=True,exist_ok=True);fd=os.open(run/'.pipeline.lock',os.O_CREAT|os.O_RDWR)
    acquired=False
    try:
        if os.fstat(fd).st_size==0:os.write(fd,b'0')
        os.lseek(fd,0,os.SEEK_SET)
        try:
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(fd,msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            acquired=True
        except OSError as e:raise RuntimeError('This run is already locked by another process; no parallel writer started') from e
        yield
    finally:
        if acquired:
            os.lseek(fd,0,os.SEEK_SET)
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(fd,msvcrt.LK_UNLCK,1)
            else:
                import fcntl
                fcntl.flock(fd,fcntl.LOCK_UN)
        os.close(fd)
