from abc import ABCMeta, abstractmethod
from flan.flan import istruthy, error, info
import settings

class FlanIntegration:
    __metaclass__ = ABCMeta

    class FlanIntegrationWriter:

        def __init__(self, publisher):
            self.publisher = publisher

        def _xform(self, data):
            return data

        def write(self, data):
            data = self._xform(data)
            self.publisher.send(data)

    def __init__(self, name, meta, config):
        self.name = name
        self.meta = meta
        self.config = config["producer"]
        self.loglevel = "info" if istruthy(self.config["loginfo"]) \
            else "errors" if istruthy(self.config["logerrors"]) \
            else "none"
        self.haltonerror = istruthy(self.config["haltonerror"])
        self.version = settings.__VERSION__
        self.prepare()
        self.writer = self.FlanIntegrationWriter(self)

    @abstractmethod
    def prepare(self):
        return

    @abstractmethod
    def send(self, data):
        return

    @property
    def target(self):
        return self.writer

    @property
    @abstractmethod
    def closed(self):
        return False

    @abstractmethod
    def close(self):
        return

    def logerr(self, err):
        return error('Flan->%s integration failed: %s' % (self.name, err))

    def loginfo(self, msg):
        return info(msg)

