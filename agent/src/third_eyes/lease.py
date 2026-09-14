"""An OS-backed single-monitor lease; releases automatically after a crash."""
import os


class MonitorLease:
    def __init__(self, path):
        self.path, self.handle = path, None

    def acquire(self):
        self.handle = self.path.open("a+b")
        self.handle.seek(0, 2)
        if self.handle.tell() == 0:
            self.handle.write(b"0")
            self.handle.flush()
        self.handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.handle.close()
            self.handle = None
            raise RuntimeError("Another Third Eyes monitor owns this state directory") from None

    def release(self):
        if self.handle is not None:
            self.handle.close()
            self.handle = None
