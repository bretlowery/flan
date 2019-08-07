from abc import ABCMeta, abstractmethod
from flan import istruthy, error, info
import settings
import threading
import _thread as thread
import os
import socket
import string

def _timeout(integrationname):
    error('Flan->%s integration timed out' % integrationname)
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
        if self.loglevel == "errors" or self.haltonerror:
            error('Flan->%s integration failed: %s' % (self.name, err))
        if self.haltonerror:
            os._exit(1)
        return

    def loginfo(self, msg):
        if self.loglevel == "info":
            info(msg)
        return

    @property
    def defaulttopic(self):
        topic = 'Flan_%s-%s' % (self.version, socket.getfqdn().translate(str.maketrans(string.punctuation, '_' * len(string.punctuation))))
        if 'topic' in self.config:
            if self.config['topic']:
                topic = self.config['topic'].strip().translate(str.maketrans(string.punctuation, '_' * len(string.punctuation)))
        return topic[:255]
