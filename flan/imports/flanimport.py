from abc import ABCMeta, abstractmethod
import os
import io

try:
    from settings import REPLAY_LOG_FILE
    from flanintegration import FlanIntegration
except:
    from flan.settings import REPLAY_LOG_FILE
    from flan.flanintegration import FlanIntegration
    pass


class FlanStreamBuffer(io.RawIOBase):

    def __init__(self, responsereader):
        self.responseReader = responsereader

    def readable(self):
        return True

    def close(self):
        self.responseReader.close()

    def read(self, n):
        return self.responseReader.read(n)

    def readinto(self, b):
        sz = len(b)
        data = self.responseReader.read(sz)
        for idx, ch in enumerate(data):
            b[idx] = ch

        return len(data)


class FlanImport(FlanIntegration):
    __metaclass__ = ABCMeta

    @property
    def replaylogfile_exists(self):
        if os.path.exists(REPLAY_LOG_FILE):
            return os.path.isfile(REPLAY_LOG_FILE)
        else:
            return False

    def __init__(self, name, meta, config):
        super().__init__(name, meta, config)
        self.config = config["import"]
        self.loglevel = "info" if self.istruthy(self.config["loginfo"]) \
            else "errors" if self.istruthy(self.config["logerrors"]) \
            else "none"
        self.haltonerror = self.istruthy(self.config["haltonerror"])
        self.contents = []
        self.templatelogfiles = None
        self.usereplaylog = True if meta.replay and self.replaylogfile_exists else False
        if not self.usereplaylog:
            self._load(meta)
            if not self.contents:
                self.logerr("the template log data could not be read or imported from %s." % meta.inputsource)
                os._exit(1)

    @abstractmethod
    def _load(self, meta):
        return

