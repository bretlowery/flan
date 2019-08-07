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
            cmd = ['flan'] + parameters
        else:
            cmd = ['flan'] + shlex.split(parameters)  # preserves quoted strings post-split, in this case -s and -e parameter values
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
    def _getsetyaml(integrationname, settingname, newvalue=None):
        integrationname = integrationname.strip().lower()
        settingname = settingname.strip().lower()
        icf = os.path.join(os.path.dirname(__file__), '../config/flan.%s.yaml' % integrationname)
        with open(icf, "r") as f:
            ic = yaml.safe_load(f)
        if settingname in ic[integrationname]["producer"]:
            if newvalue is not None:
                if isinstance(newvalue, str):
                    ic[integrationname]["producer"][settingname] = newvalue.strip()
                else:
                    ic[integrationname]["producer"][settingname] = newvalue
                with open(icf, "w") as f:
                    yaml.safe_dump(ic, f, default_flow_style=False)
                with open(icf, "r") as f:
                    ic = yaml.safe_load(f)
            return ic[integrationname]["producer"][settingname]
        elif settingname in ic[integrationname]:
            if newvalue is not None:
                if isinstance(newvalue, str):
                    ic[integrationname][settingname] = newvalue.strip()
                else:
                    ic[integrationname][settingname] = newvalue
                with open(icf, "w") as f:
                    yaml.safe_dump(ic, f, default_flow_style=False)
                with open(icf, "r") as f:
                    ic = yaml.safe_load(f)
            return ic[integrationname][settingname]

    def getyaml(self, integrationname, settingname):
        return self._getsetyaml(integrationname, settingname, None)

    def setyaml(self, integrationname, settingname, newvalue):
        return self._getsetyaml(integrationname, settingname, newvalue)
