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

from confluent_kafka import Producer, KafkaException
from flan import istruthy, error, info, __VERSION__
import socket
import string


class Kafka:

    class Writer:

        def __init__(self, publisher):
            self.publisher = publisher

        def _callback(self, err, msg):
            if err is not None:
                self.publisher.err(err)
            elif self.publisher.loglevel == "info":
                info('Flan->Kafka {} [{}]'.format(msg.topic(), msg.partition()))

        def write(self, data):
            try:
                self.publisher.producer.poll(0)
                self.publisher.producer.produce(self.publisher.topic, data.encode('utf-8'), callback=self._callback)
            except KafkaException as e:
                self.publisher.err(str(e))
            return

    def __init__(self, config):
        self.config = config["producer"]
        self.loglevel = "info" if istruthy(self.config["loginfo"]) \
            else "errors" if istruthy(self.config["logerrors"]) \
            else "none"
        self.haltonerror = istruthy(self.config["haltonerror"])
        servers = {'bootstrap.servers': self.config["bootstrap.servers"]}
        try:
            self.producer = Producer(servers)
        except KafkaException as e:
            self.err(str(e))
            exit(1)
        # Kafka topic cleaning
        topic = 'Flan_%s-%s' % (__VERSION__, socket.getfqdn().translate(str.maketrans(string.punctuation, '_' * len(string.punctuation))))
        if 'topic' in self.config:
            if self.config['topic']:
                topic = self.config['topic'].strip().translate(str.maketrans(string.punctuation, '_'*len(string.punctuation)))
        self.topic = topic[:255]
        self.writer = self.Writer(self)

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

    def err(self, err):
        if self.loglevel == "error":
            error('Flan->Kafka failed: {}'.format(err))
        if self.haltonerror:
            exit(1)
