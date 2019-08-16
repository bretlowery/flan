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
from flanexport import FlanExport, timeout_after
from confluent_kafka import Producer, KafkaException
import socket
import string
import json
import os

try:
    from confluent_kafka import avro
    from confluent_kafka.avro import AvroProducer
    from settings import AVRO_KEY_SCHEMA, AVRO_VALUE_SCHEMA
except:
    pass


class Kafka(FlanExport):

    def __init__(self, meta, config):
        self.name = self.__class__.__name__
        super().__init__(self.name, meta, config)

    @timeout_after(30)
    def prepare(self):
        self.topic = self.defaulttopic
        try:
            if self.meta.outputstyle == "avro":
                servers = {
                    'bootstrap.servers': self._getsetting("bootstrap.servers"),
                    'schema.registry.url': self._getsetting("avro.schema.registry.url"),
                }
                self.producer = AvroProducer(servers, default_key_schema=AVRO_KEY_SCHEMA, default_value_schema=AVRO_VALUE_SCHEMA)
            else:
                servers = {'bootstrap.servers': self._getsetting("bootstrap.servers")}
                self.producer = Producer(servers)
        except Exception as e:
            self.logerr(str(e))
            os._exit(1)
        if self.topic_must_exist:
            topic = self.producer.list_topics(self.topic)
            if not topic:
                self.logerr('Flan->%s exports error: %s is not an existing topic in the bootstrap servers provided' % (self.name, self.topic))
                os._exit(1)

    @timeout_after(10)
    def send(self, data):
        try:
            self.producer.poll(0)
            if self.meta.outputstyle == "avro":
                jsondata = json.loads(data)
                self.producer.produce(self.topic, value=jsondata, key=jsondata, callback=self.kafkacallback)
            else:
                self.producer.produce(self.topic, data.encode('utf-8'), callback=self.kafkacallback)
        except Exception as e:
            self.logerr(str(e))
            pass
        return

    @timeout_after(10)
    def kafkacallback(self, err, msg):
        if err is not None and self.loglevel == "errors":
            self.logerr(err)
        elif msg is not None and self.loglevel == "info":
            self.loginfo('Flan->%s: sent on topic "%s" [%s]' % (self.name, msg.topic(), msg.partition()))

    @property
    def closed(self):
        if self.producer:
            return False
        else:
            return True

    @timeout_after(10)
    def close(self):
        if self.producer:
            self.producer.flush()
            self.producer = None
        return
