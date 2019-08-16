from abc import ABCMeta, abstractmethod
try:
    from flan import istruthy, error, info
except:
    from flan.flan import istruthy, error, info
    pass
import settings
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


class FlanIntegration:
    __metaclass__ = ABCMeta

    def __init__(self, name, meta, config):
        self.name = name
        self.meta = meta
        self.config = None
        self.loglevel = None
        self.haltonerror = None
        self.version = settings.__VERSION__

    def logerr(self, err):
        if self.loglevel == "errors" or self.haltonerror:
            error('Flan->%s exports failed: %s' % (self.name, err))
        if self.haltonerror:
            os._exit(1)
        return

    def loginfo(self, msg):
        if self.loglevel == "info":
            info(msg)
        return

    @staticmethod
    def istruthy(val):
        return istruthy(val)

    def _getsetting(self, name, erroronnone=True, checkenv=False, defaultvalue=None):
        val = defaultvalue
        try:
            if checkenv:
                val = os.environ[name.upper()]
        except KeyError:
            pass
        if not val:
            ln = name.lower()
            if ln in self.config:
                val = self.config[ln]
        if not val and erroronnone:
            self.logerr('Flan->%s config failed: no %s defined in the environment or passed to Flan.' % (self.name, name))
        return val
