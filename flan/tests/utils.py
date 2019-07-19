
import subprocess
import re
import json
from flan.flan import supported_nginx_fields, MONTHS, default_format
import shlex
from dateutil import parser as dtparser
import os
import shutil

linedelimiter = "\r\n"

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
        fields = json.loads(supported_nginx_fields)
        for field in fields:
            patterns[str(field["name"]).lstrip("$")] = str(field["regex"])
        try:
            reexpr = ''.join(
                    '(?P<%s>%s)' % (g, patterns.get(g, '.*?')) if g else re.escape(c)
                    for g, c in re.findall(r'\$(\w+)|(.)', default_format))
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
    def execmd(parameters, returnstdout=False, returnstderr=False):
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

