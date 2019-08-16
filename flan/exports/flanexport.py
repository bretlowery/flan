from abc import ABCMeta, abstractmethod
try:
    from flan import istruthy
    from flanintegration import FlanIntegration, _timeoput, timeout_after
except:
    from flan.flan import istruthy
    from flan.flanintegration import FlanIntegration, _timeoput, timeout_after
    pass
import socket
import string


class FlanExport(FlanIntegration):
    __metaclass__ = ABCMeta

    class FlanExportWriter:

        def __init__(self, publisher):
            self.publisher = publisher

        def _xform(self, data):
            return data

        def write(self, data):
            data = self._xform(data)
            self.publisher.send(data)

    def __init__(self, name, meta, config):
        super().__init__(name, meta, config)
        self.config = config["export"]
        if "topic_must_exist" in self.config:
            self.topic_must_exist = istruthy(self.config["topic_must_exist"])
        else:
            self.topic_must_exist = None
        self.prepare()
        self.writer = self.FlanExportWriter(self)

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

    @property
    def defaulttopic(self):
        topic = 'Flan_%s-%s' % (self.version, socket.getfqdn().translate(str.maketrans(string.punctuation, '_' * len(string.punctuation))))
        if 'topic' in self.config:
            if self.config['topic']:
                topic = self.config['topic'].strip().translate(str.maketrans(string.punctuation, '_' * len(string.punctuation)))
        return topic[:255]

