
from flanintegration import FlanIntegration, timeout_after
import os

try:
    from stompest.config import StompConfig
    from stompest.async import Stomp
except:
    pass


class ActiveMQ(FlanIntegration):

    def __init__(self, meta, config):
        self.name = self.__class__.__name__
        super().__init__(self.name, meta, config)

    @timeout_after(10)
    def prepare(self):
        try:
            config = StompConfig('tcp://%s:%d' % (self.config['host'], self.config['port']),
                                 login=self.config['username'],
                                 passcode=self.config['password'],
                                 version=str(self.config['version']))
            self.producer = Stomp(config)
            yield self.producer.connect(host=self.config['broker'])
        except Exception as e:
            self.logerr(str(e))
            os._exit(1)

    @timeout_after(10)
    def send(self, data):
        try:
            self.producer.send(destination=self.config['destination'], body=data.encode('utf-8'), headers={'persistent': 'false'})
        except Exception as e:
            self.logerr(str(e))
            pass
        return

    @property
    def closed(self):
        if self.producer:
            return False
        else:
            return True

    @timeout_after(10)
    def close(self):
        if self.producer:
            yield self.producer.disconnect(receipt='bye')
            self.producer = None
        return
