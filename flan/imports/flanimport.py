from abc import ABCMeta, abstractmethod

try:
    from flan import istruthy, error, info
    from settings import REPLAY_LOG_FILE
except:
    from flan.flan import istruthy, error, info
    from flan.settings import REPLAY_LOG_FILE
    pass

import os
import threading
import _thread as thread


def _timeout(exportname):
    error('Flan->%s import timed out' % exportname)
    thread.interrupt_main()  # raises KeyboardInterrupt


def timeout_after(s):
    """
    Use as decorator to exit process if function takes longer than s seconds
    """
    def outer(fn):
        def inner(*args, **kwargs):
            x = fn
            timer = threading.Timer(s, _timeout, args=[fn.__module__])
            timer.start()
            try:
                result = fn(*args, **kwargs)
            finally:
                timer.cancel()
            return result
        return inner
    return outer


class FlanImport:
    __metaclass__ = ABCMeta

    def __init__(self, name, meta, config):
        self.name = name
        self.config = config["import"]
        self.contents = []
        self.templatelogfiles = None
        self.usereplaylog = True if meta.replay and self.replaylogfile_exists else False
        if not self.usereplaylog:
            self._load(meta)
            if not self.contents:
                error("the template log data could not be read or imported from %s." % meta.inputsource)
                os._exit(1)
        return

    @abstractmethod
    def _load(self, meta):
        return

    @property
    def replaylogfile_exists(self):
        return os.path.exists(REPLAY_LOG_FILE)
