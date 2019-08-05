from abc import ABCMeta, abstractmethod
from flan import istruthy, error, info, __VERSION__
#from fastavro import writer, reader, schema
from rec_avro import to_rec_avro_destructive, rec_avro_schema


class FlanIntegration:
    __metaclass__ = ABCMeta

    class FlanIntegrationWriter:

        def __init__(self, publisher):
            self.publisher = publisher

        def _xform(self, data):
            # if self.meta.outputstyle == "avro":
            # https://github.com/bmizhen/rec-avro
            #   data = to_rec_avro_destructive(data)
            return data

        def write(self, data):
            data = self._xform(data)
            self.publisher.customwrite(data)

    def __init__(self, name, meta, config):
        self.name = name
        self.meta = meta
        self.config = config["producer"]
        self.loglevel = "info" if istruthy(self.config["loginfo"]) \
            else "errors" if istruthy(self.config["logerrors"]) \
            else "none"
        self.haltonerror = istruthy(self.config["haltonerror"])
        self.version = __VERSION__
        self.custominit()
        self.writer = self.FlanIntegrationWriter(self)

    @abstractmethod
    def custominit(self):
        return

    @abstractmethod
    def customwrite(self, data):
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
        if self.loglevel == "error":
            error('Flan->%s integration failed: %s' % (self.name, err))
        if self.haltonerror:
            exit(1)

    def loginfo(self, msg):
        return info(msg)

