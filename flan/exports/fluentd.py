from flanexport import FlanExport, timeout_after
import os
import time
import ast
import json

try:
    from fluent import sender
except:
    pass


class FluentD(FlanExport):

    def __init__(self, meta, config):
        name = self.__class__.__name__
        super().__init__(name, meta, config)

    @timeout_after(10)
    def prepare(self):
        try:
            if "topic" in self.config:
                self.topic = self._getsetting("topic")
            else:
                self.topic = self.defaulttopic
            self.sender = sender.FluentSender(self._getsetting("app"), host=self._getsetting("host"), port=self._getsetting("port"))
        except Exception as e:
            self.logerr('Flan->%s connection to %s:%s failed: %s' %
                          (self.name, self._getsetting("host"), self._getsetting("port"), str(e)))
            os._exit(1)

    @timeout_after(10)
    def send(self, data):
        try:
            dict = ast.literal_eval(data) # data must be a json-formatted string
            if json.load(dict):
                cur_time = int(time.time())
                self.sender.emit_with_time(self.topic, cur_time, dict)
                self.loginfo('Flan->%s %s [%s]' % (self.name, "%s:%s" % (self._getsetting("host"), self._getsetting("port")), self._getsetting("topic")))
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
            self.sender.close()
        except:
            pass
        return
