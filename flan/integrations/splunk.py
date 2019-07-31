
import splunklib.client as client
from flan.flan import istruthy, error, info, __VERSION__
import socket


class Splunk:

    class Writer:

        def __init__(self, producer):
            self.producer = producer
            return

        def write(self, data):
            try:
                self.producer.socket.send(data)
                if self.producer.config["loglevel"] == "info":
                    info('Flan->Splunk {} [{}]'.format("%s:%s" % (self.producer.config["host"], self.producer.config["port"]),
                                                       self.producer.config["index"]))
            except Exception as e:
                if self.producer.config["loglevel"] == "error":
                    error('Flan->Splunk delivery failed: {}'.format(str(e)))
                if self.producer.haltonerror:
                    exit(1)
            return

    def __init__(self, config):
        self.config = config
        self.loglevel = "info" if istruthy(config["loginfo"]) else "errors" if istruthy(config["logerrors"]) else "none"
        self.haltonerror = istruthy(config["haltonerror"])
        try:
            self.service = client.connect(
                    host=config["host"],
                    port=int(config["port"]),
                    username=config["username"],
                    password=config["password"])
            self.index = self.service.indexes[config["index"]]
            self.socket = self.index.attach(
                    sourcetype='Flan/%s' % __VERSION__,
                    host=socket.getfqdn())
        except Exception as e:
            error('Flan->Splunk connection to %s:%s as user %s failed: %s' % (config["host"], config["port"], config["username"], str(e)))
            exit(1)
        self.writer = self.Writer(self)

    @property
    def target(self):
        return self.writer

    @property
    def closed(self):
        if self.socket.closed:
            return False
        else:
            return True

    def close(self):
        try:
            self.socket.close()
        except:
            pass
        return
