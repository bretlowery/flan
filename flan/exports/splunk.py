from flanexport import FlanExport, timeout_after
import splunklib.client as client
import socket
import os


class Splunk(FlanExport):

    def __init__(self, meta, config):
        name = self.__class__.__name__
        super().__init__(name, meta, config)

    @timeout_after(10)
    def prepare(self):
        try:
            self.service = client.connect(
                    scheme=self._getsetting("scheme"),
                    host=self._getsetting("host"),
                    port=self._getsetting("port"),
                    username=self._getsetting("username"),
                    password=self._getsetting("password"))
            self.index = self.service.indexes[self._getsetting("index")]
            self.socket = self.index.attach(
                    sourcetype='Flan/%s' % self.version,
                    host=socket.getfqdn())
        except Exception as e:
            self.logerr('Flan->%s connection to %s:%s as user %s failed: %s' %
                          (self.name, self._getsetting("host"), self._getsetting("port"), self._getsetting("username"), str(e)))
            os._exit(1)

    @timeout_after(10)
    def send(self, data):
        try:
            self.socket.send(data.encode('utf-8'))
            self.loginfo('Flan->%s %s [%s]' % (self.name, "%s:%s" % (self._getsetting("host"), self._getsetting("port")), self._getsetting("index")))
        except Exception as e:
            self.logerr('Flan->%s delivery failed: %s' % (self.name, str(e)))
            pass
        return

    @property
    def closed(self):
        return False

    @timeout_after(10)
    def close(self):
        try:
            self.socket.close()
        except:
            pass
        return
