import subprocess
import re
import json
from settings import SUPPORTED_FIELDS, DEFAULT_FORMAT
import shlex
from dateutil import parser as dtparser
import os
import shutil
import hashlib
import yaml

__FLAN__ = os.path.join(os.path.dirname(__file__), "../flan.py")

class Utils:

    @staticmethod
    def _ts_to_yyyymmddhhmiss(ts):
        try:
            d = ts[:ts.find(":")]
            t = ts[ts.find(":")+1:ts.find(" ")]
            dts = dtparser.parse("%s %s" % (d, t))
        except:
            dts = None
        return dts.strftime('%Y/%m/%d %H:%M:%S')

    @staticmethod
    def _get_loglineregex():
        patterns = {}
        fields = json.loads(SUPPORTED_FIELDS)
        for field in fields:
            patterns[str(field["name"]).lstrip("$")] = str(field["regex"])
        try:
            reexpr = ''.join(
                    '(?P<%s>%s)' % (g, patterns.get(g, '.*?')) if g else re.escape(c)
                    for g, c in re.findall(r'\$(\w+)|(.)', DEFAULT_FORMAT))
            return re.compile(reexpr)
        except:
            pass
        return None

    def parse_logline(self, line):
        if not hasattr(self, 'lineregex'):
            self.lineregex = self._get_loglineregex()
        m = None
        line = line.rstrip()
        try:
            m = self.lineregex.match(line)
        except:
            pass
        if m:
            dikt = m.groupdict()
            if "time_local" in dikt.keys():
                dikt["_ts"] = self._ts_to_yyyymmddhhmiss(dikt["time_local"])
            return dikt
        else:
            return None

    @staticmethod
    def newtest(fn):
        print("\r\nRunning %s..." % fn.upper())

    @staticmethod
    def execmd(parameters, returnstdout=False, returnstderr=False, linedelimiter="\r\n"):
        if parameters is list:
            cmd = ["python3", __FLAN__] + parameters
        else:
            cmd = ["python3", __FLAN__] + shlex.split(parameters)  # preserves quoted strings post-split, in this case -s and -e parameter values
        results = subprocess.run(cmd, capture_output=True)
        out = results.stdout.decode('utf-8')
        errs = results.stderr.decode('utf-8')
        if results.stderr or not results.stdout:
            print("rtncode > %d (%s)" % (results.returncode, "SUCCESS" if results.returncode == 0 else "FAILURE/OTHER"))
            print("stdout >> %s" % out)
            print("stderr >> %s" % errs)
        resultslist = []
        if returnstdout:
            try:
                resultslist = [r for r in out.split(linedelimiter) if r]
            except:
                resultslist = None
                pass
        if returnstderr:
            error = errs
        else:
            error = None
        if returnstdout:
            if returnstderr:
                return results, resultslist, error
            else:
                return results, resultslist
        elif returnstderr:
            return results, error
        else:
            return results

    @staticmethod
    def wipe(folder):
        for file in os.listdir(folder):
            file_path = os.path.join(folder, file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(str(e))
        try:
            shutil.rmtree(folder)
        except Exception as e:
            print(str(e))

    @staticmethod
    def checksum(item):
        hash_md5 = hashlib.md5()
        if os.path.isfile(item):
            with open(item, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        elif isinstance(item, str):
            return hash_md5(item.encode())
        return hash_md5(str(item).encode())

    @staticmethod
    def _getsetyaml(exportname, importorexport, settingname, newvalue=None):

        def _reloadyaml(_icf, _ic=None):
            if _ic is not None:
                with open(_icf, "w") as _f:
                    yaml.safe_dump(_ic, _f, default_flow_style=False)
            with open(_icf, "r") as _f:
                _ic = yaml.safe_load(_f)
            return _ic

        exportname = exportname.strip().lower()
        settingname = settingname.strip().lower()
        icf = os.path.join(os.path.dirname(__file__), '../config/flan.%s.yaml' % exportname)
        ic = _reloadyaml(icf)
        if importorexport == "export" and settingname in ic[exportname]["export"]:
            if newvalue is not None:
                if isinstance(newvalue, str):
                    ic[exportname]["export"][settingname] = newvalue.strip()
                else:
                    ic[exportname]["export"][settingname] = newvalue
                ic = _reloadyaml(icf, ic)
            return ic[exportname]["export"][settingname]
        elif importorexport == "import" and settingname in ic[exportname]["import"]:
            if newvalue is not None:
                if isinstance(newvalue, str):
                    ic[exportname]["import"][settingname] = newvalue.strip()
                else:
                    ic[exportname]["import"][settingname] = newvalue
                ic = _reloadyaml(icf, ic)
            return ic[exportname]["import"][settingname]

    def getyaml(self, exportname, importorexport, settingname):
        return self._getsetyaml(exportname, importorexport, settingname, None)

    def setyaml(self, exportname, importorexport, settingname, newvalue):
        return self._getsetyaml(exportname, importorexport, settingname, newvalue)
