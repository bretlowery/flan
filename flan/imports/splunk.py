from flanimport import FlanImport, timeout_after
from datetime import datetime
from time import sleep
try:
    from flan import error
except:
    from flan.flan import error
    pass

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
        splunkresults = None
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
            splunkresults = self.service.jobs.oneshot(splunkquery, timeout=timeout)
        except Exception as e:
            error("Flan import error when trying to read from Splunk: %s" % str(e))
            pass
        if not splunkresults:
            error("Flan import timed out before receiving a response from Splunk.")
        http_status_code = 0
        http_reason = "none"
        try:
            http_status_code = splunkresults._response.status
            http_reason = splunkresults._response.reason
        except Exception as e:
            error("Flan received an invalid response from Splunk: %s" % str(e))
        if http_status_code != 200:
            error("Flan received a %d response from Splunk: %s" % (http_status_code, http_reason))
        for result in results.ResultsReader(splunkresults):
            self.contents.append(result["_raw"])
        return self.contents
