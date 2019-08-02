#
# Broker Compatibility
# The Python client (as well as the underlying C library librdkafka) supports all broker versions >= 0.8.
# But due to the nature of the Kafka protocol in broker versions 0.8 and 0.9 it is not safe for a client
# to assume what protocol version is actually supported by the broker, thus you will need to hint the Python
# client what protocol version it may use. This is done through two Kafka configuration settings:
#
# broker.version.fallback=YOUR_BROKER_VERSION (default 0.9.0.1)
# api.version.request=true|false (default true)
#
# When using a Kafka 0.10 broker or later you don't need to do anything (api.version.request=true is the default).
# If you use Kafka broker 0.9 or 0.8 you must set api.version.request=false and set broker.version.fallback to your
# broker version, e.g broker.version.fallback=0.9.0.1.
#
# More info here: https://github.com/edenhill/librdkafka/wiki/Broker-version-compatibility
#

from confluent_kafka import Producer
from flan.flan import istruthy, error, info, __VERSION__
import socket


class Kafka:

    class Writer:

        def __init__(self, producer):
            self.producer = producer

        def _callback(self, err, msg):
            if err is not None:
                if self.producer.loglevel == "error":
                    error('Flan-Kafka delivery failed: {}'.format(err))
                if self.producer.haltonerror:
                    exit(1)
            elif self.producer.loglevel == "info":
                info('Flan->Kafka {} [{}]'.format(msg.topic(), msg.partition()))

        def write(self, data):
            self.producer.poll(0)
            self.producer.produce(self.producer.topic, data.encode('utf-8'), callback=self._callback)
            return

    def __init__(self, config):
        self.config = config
        self.loglevel = "info" if istruthy(config["loginfo"]) else "errors" if istruthy(config["logerrors"]) else "none"
        self.haltonerror = istruthy(config["haltonerror"])
        self.producer = Producer(config["producer"])
        self.topic = self.config['topic'] if self.config['topic'] else 'Flan/%s:%s' % (__VERSION__, socket.getfqdn())
        self.writer = self.Writer(self.producer)

    @property
    def target(self):
        return self.writer

    @property
    def closed(self):
        if self.producer:
            return False
        else:
            return True

    def close(self):
        if self.producer:
            self.producer.flush()
            self.producer = None
        return

