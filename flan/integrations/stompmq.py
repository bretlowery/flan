
from flanintegration import FlanIntegration, timeout_after
import os

try:
    import stomp
except:
    pass

class MQCallback(stomp.ConnectionListener):

    def __init__(self, *args, **kwargs):
        self.producer = kwargs.pop("flanproducer")
        super().__init__(args, kwargs)

    @timeout_after(10)
    def on_error(self, headers, msg):
        if msg is not None and self.producer.loglevel == "errors":
            self.producer.logerr(msg)

    @timeout_after(10)
    def on_message(self, headers, msg):
        if msg is not None and self.producer.loglevel == "info":
            self.producer.loginfo('Flan->%s: %s' % (self.producer.name, msg))


# for ActiveMQ, Amazon MQ, Apollo, stompserver, RabbitMQ, or any other STOMP-1.x compliant MQ system
class StompMQ(FlanIntegration):

    def __init__(self, meta, config):
        self.name = self.__class__.__name__
        super().__init__(self.name, meta, config)

    @timeout_after(10)
    def prepare(self):
        try:
            self.mq = stomp.Connection(host_and_ports='tcp://%s:%d' % (self.config['host'], self.config['port']),
                                    ssl_ca_certs=self.config['ssl_ca_certs'],
                                    ssl_cert_file=self.config['ssl_cert_file'],
                                    ssl_cert_validator=self.config['ssl_cert_validator'],
                                    ssl_key_file=self.config['ssl_key_file'],
                                    ssl_version=self.config['ssl_version'])
            self.mq.set_listener('flan_%s_mqlistener' % self.version, MQCallback(flanproducer=self))
            self.mq.start()
            self.mq.connect(self.config['username'],self.config['password'], wait=True)
            self.mq.subscribe(destination=self.config['destination'], id=str(self.config['id']), ack='auto')
        except Exception as e:
            self.logerr(str(e))
            os._exit(1)

    @timeout_after(10)
    def send(self, data):
        try:
            self.producer.mq.send(destination=self.config['destination'], body=data.encode('utf-8'), headers={'persistent': 'false'})
        except Exception as e:
            self.logerr(str(e))
            pass
        return

    @property
    def closed(self):
        if self.producer:
            if self.producer.mq:
                return self.producer.mq.is_connected()
        return True

    @timeout_after(10)
    def close(self):
        if not self.closed:
            self.producer.mq.disconnect(receipt='bye')
            self.producer = None
        return
