from flanintegration import FlanIntegration
import splunklib.client as client
import socket
import os


class Splunk(FlanIntegration):

    def __init__(self, meta, config):
        name = self.__class__.__name__
        super().__init__(name, meta, config)

    def prepare(self):
        try:
            self.service = client.connect(
                    host=self.config["host"],
                    port=int(self.config["port"]),
                    username=self.config["username"],
                    password=self.config["password"])
            self.index = self.service.indexes[self.config["index"]]
            self.socket = self.index.attach(
                    sourcetype='Flan/%s' % self.version,
                    host=socket.getfqdn())
        except Exception as e:
            self.logerr('Flan->%s connection to %s:%s as user %s failed: %s' %
                          (self.name, self.config["host"], self.config["port"], self.config["username"], str(e)))
            os._exit(1)

    def send(self, data):
        try:
            self.socket.send(data)
            if self.config["loglevel"] == "info":
                self.loginfo('Flan->%s %s [%s]' % (self.name, "%s:%s" % (self.config["host"], self.config["port"]), self.config["index"]))
        except Exception as e:
            if self.config["loglevel"] == "error":
                self.logerr('Flan->%s delivery failed: %s' % (self.name, str(e)))
            if self.haltonerror:
                os._exit(1)
        return

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
