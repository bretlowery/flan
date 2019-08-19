from flanimport import FlanImport, FlanStreamBuffer
from datetime import datetime
import io

from settings import T_MAX, R_MAX

try:
    import splunklib.client as client
    import splunklib.results as results
except:
    pass


class Splunk(FlanImport):

    def __init__(self, meta, config):
        self.name = self.__class__.__name__
        super().__init__(self.name, meta, config)

    @staticmethod
    def _dt_to_ymdhms(dt):
        try:
            rtn = datetime.strftime(dt, "%Y/%b/%d %H:%M:%S")
        except Exception as e:
            rtn = None
            pass
        return rtn

    def _load(self, meta):
        try:
            self.service = client.connect(
                    scheme=self.config["scheme"],
                    host=self.config["host"],
                    port=self.config["port"],
                    username=self.config["username"],
                    password=self.config["password"])
            self.index = self.service.indexes[self.config["index"]]
            fn = self.config["time_local_splunk_field_name"]
            sdt = self._dt_to_ymdhms(meta.start_dt)
            edt = self._dt_to_ymdhms(meta.end_dt)
            splunkquery = 'search index="%s"' % self.config["index"]
            splunkquery = "%s | where(strptime(%s, \"%%d/%%b/%%Y:%%H:%%M:%%S %%z\") >= strptime(\"%s\", \"%%Y/%%b/%%d %%H:%%M:%%S\") " \
                          "AND strptime(%s, \"%%d/%%b/%%Y:%%H:%%M:%%S %%z\") <= strptime(\"%s\", \"%%Y/%%b/%%d %%H:%%M:%%S\"))" \
                          % (splunkquery, fn, sdt, fn, edt)
            if "querycondition" in self.config:
                qc = self.config["querycondition"].strip()
                if qc not in ["none", ""]:
                    qc = self.config["querycondition"].strip()
                    splunkquery = "%s %s" % (splunkquery, qc)
            splunkquery = "%s | head %d" % (splunkquery, meta.records)
            if "querytimeout" in self.config:
                timeout = self.config["querytimeout"]
                timeout = 60 if timeout < 60 else timeout
            else:
                timeout = 60
            if not meta.quiet:
                self.loginfo('Issuing import query to Splunk instance at %s://%s:%d as user %s (timeout=%d secs)...' %
                     (self.config["scheme"], self.config["host"], self.config["port"], self.config["username"], timeout))
            kwargs_export = {"count": 0, "maxEvents": R_MAX}
            splunkreader = self.service.jobs.export(splunkquery, **kwargs_export)
            totread = 0
            for logentry in results.ResultsReader(io.BufferedReader(FlanStreamBuffer(splunkreader))):
                if isinstance(logentry, dict):
                    self.contents.append(logentry["_raw"])
                    totread += 1
                    if not meta.quiet:
                        if totread % 100 == 0:
                            self.loginfo("Imported %d Splunk log entries..." % totread)
                    if totread > T_MAX:
                        break
        except Exception as e:
            self.logerr("Flan import error when trying to import from Splunk: %s" % str(e))
        if not meta.quiet:
            self.loginfo("Import complete; %d entries imported" % len(self.contents))
        return self.contents

