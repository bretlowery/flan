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
from flan.flan import istruthy, error, info

class Kafka:

    class Writer:

        def __init__(self, producer):
            self.producer = producer

        def _callback(self, err, msg):
            if err is not None:
                if self.producer.loglevel == "error":
                    error('Message delivery failed: {}'.format(err))
            elif self.producer.loglevel == "info":
                info('Message delivered to {} [{}]'.format(msg.topic(), msg.partition()))

        def write(self, data):
            self.producer.poll(0)
            self.producer.produce(self.producer.config['topic'], data.encode('utf-8'), callback=self._callback)
            return

    def __init__(self, config):
        self.config = config
        self.producer = Producer(config["producer"])
        self.writer = self.Writer(self.producer)
        self.loglevel = "info" if istruthy(config["loginfo"]) else "errors" if istruthy(config["logerrors"]) else "none"

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

