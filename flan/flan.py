import os
import sys
import glob
import argparse
import datetime
from datetime import timezone, timedelta
from dateutil import parser as dtparser
import re
import json
import user_agents
import random
import ipaddress
import string
import numpy as np
import pickle
import gzip
from math import ceil
from time import sleep
import collections
import operator
import itertools
from service import Service, find_syslog
import resource
import logging
from logging.handlers import SysLogHandler
import logging.config
import yaml
from urllib import request

from settings import __VERSION__, \
    DEFAULT_FORMAT, \
    EXPORTS, \
    EXPORT_CONFIG_FILE, \
    IMPORTS, \
    IPMAP, \
    IPMAP2, \
    JSON_FORMAT, \
    LOGGER, \
    MAX_RSS_MEMORY_USED, \
    MONTHS, \
    R_DEFAULT_NOSTREAMING, \
    R_DEFAULT_STREAMING, \
    R_MAX, \
    REPLAY_LOG_FILE, \
    RSS_MEMORY_BASE, \
    SERVICE_CONFIG_FILE, \
    SUPPORTED_FIELDS, \
    UA_FREQUENCIES


def info(msg):
    msg = msg.strip()
    if LOGGER:
        LOGGER.info(msg)
    else:
        print(msg, file=sys.stdout)


def error(msg):
    msg = "ERROR: %s" % msg.strip()
    if LOGGER:
        LOGGER.error(msg)
    else:
        print(msg, file=sys.stderr)
        sys.stderr.flush()
    os._exit(1)


def profile_memory(meta):
    global MAX_RSS_MEMORY_USED
    if meta.profile:
        curr_mem_used = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss - RSS_MEMORY_BASE
        if curr_mem_used > MAX_RSS_MEMORY_USED:
            MAX_RSS_MEMORY_USED = curr_mem_used


def uatostruct(uastring):
    return user_agents.parse(uastring.lstrip('\"').rstrip('\"'))


def uatostructstr(uastring):
    uap = uatostruct(uastring)
    return '{ "ua_string": "%s", ' \
           '"device": { "brand": "%s", "family": "%s", "model": "%s" }, ' \
           '"os": { "family": "%s", "version" : "%s", "version_string": "%s" }, ' \
           '"is_bot": "%s", ' \
           '"is_email_client": "%s", ' \
           '"is_mobile": "%s", ' \
           '"is_pc": "%s", ' \
           '"is_tablet": "%s", ' \
           '"is_touch_capable": "%s" }' \
           % (
               uap.ua_string,
               uap.device.brand, uap.device.family, uap.device.model,
               uap.os.family, uap.os.version, uap.os.version_string,
               str(uap.is_bot), str(uap.is_email_client), str(uap.is_mobile),
               str(uap.is_pc), str(uap.is_tablet), str(uap.is_touch_capable)
           )


def istruthy(val):
    return {
        't': True,
        'true': True,
        'y': True,
        'yes': True,
        '1': True
    }.get(str(val).strip().lower(), False)


def getconfig(yamlfile, root):
    yamlfile = yamlfile.strip()
    configdict = {}
    try:
        with open(yamlfile) as config_file:
            configyaml = yaml.safe_load(config_file)
    except:
        error('%s was not found, is not readable, has insufficient read permissions, or is not a valid YAML file' % yamlfile)
        os._exit(1)
    try:
        configdict = configyaml[root] if root else configyaml
    except:
        error('%s not found within %s' % (root, yamlfile))
        os._exit(1)
    return configdict


def importer(meta):
    source = meta.inputsource
    importconfig = getconfig(IMPORT_CONFIG_FILE, source)
    try:
        enabled = istruthy(importconfig["import"]["enabled"])
    except Exception as e:
        enabled = False
        pass
    if not enabled:
        error('%s imports are not enabled in %s' % (source, IMPORT_CONFIG_FILE))
        os._exit(1)
    import importlib
    # Load "flan.imports.kafka.Kafka", "flan.imports.pulsar.Pulsar", etc.
    ImportClass = getattr(importlib.import_module("imports.%s" % source), source.capitalize())
    # Instantiate the class. This connects, authenticates, etc to the source, and performs the actual template data import.
    proxy = ImportClass(meta, importconfig)
    return proxy


def exporter(meta):
    target = meta.streamtarget
    exportconfig = None
    if target != "stdout":
        exportconfig = getconfig(EXPORT_CONFIG_FILE, target)
        try:
            enabled = istruthy(exportconfig["export"]["enabled"])
        except Exception as e:
            enabled = False
            pass
        if not enabled:
            error('%s exports are not enabled in %s' % (target, EXPORT_CONFIG_FILE))
            os._exit(1)
    import importlib
    # Load "flan.exports.kafka.Kafka", "flan.exports.pulsar.Pulsar", etc.
    ExportClass = getattr(importlib.import_module("exports.%s" % target), target.capitalize())
    # Instantiate the class. This connects, authenticates, etc to the target sink & handles all prep up to the actual write.
    proxy = ExportClass(meta, exportconfig)
    return proxy


class MetaManager:

    def _verify_outputdir(self, options):
        output = None
        if self.streamtarget == "none":
            if not options.outputdir:
                error("no output directory was specified.")
            try:
                output = (options.outputdir.strip() + "/").replace("//", "/")
                if os.path.exists(output):
                    if os.path.isfile(output):
                        error("the output location must be a directory, not a file.")
                    output = os.path.dirname(output)
                    output = '.' if not output else output
                    if not os.access(output, os.W_OK):
                        error("no write access to target directory. Check your permissions.")
                else:
                    error("the output location does not exist or is not accessible by the current user context.")
            except IOError as e:
                error("when checking output directory access/permissions: %s" % str(e))
        self.outputdir = output

    def get_outputfile(self, i, g):
        if self.outputdir:
            return os.path.join(self.outputdir,
                            "access.log.%d.gz" % i if i != 0 and g > 0
                            else "access.log.gz" if i == 0 and g > 0
                            else "access.log.%d" % i if i != 0
                            else "access.log")
        else:
            return None

    def new_outputfile(self, currentfile):
        out = self.get_outputfile(currentfile, self.gzipindex)
        if self.gzipindex > 0:
            return gzip.open(out, "w+")
        else:
            return open(out, "w+")

    def output_exists(self):
        g = self.gzipindex
        for i in range(self.files - 1, 0):
            fn = self.get_outputfile(i, g)
            if os.path.exists(fn):
                return True
            g -= 1 if g > 0 else 0
        return False

    @staticmethod
    def _onein(choice, choicelist, default=None):
        if not choice:
            return default
        choice = choice.strip().lower()
        if choice in choicelist:
            return choice
        else:
            return default

    @staticmethod
    def _oneof(choice, choicedict, default=None):
        return choicedict.get(choice.strip().lower(), default)

    def emitmeta(self):
        if self.meta:
            if self.streamtarget != "none":
                import socket
                hn = socket.gethostname()
                fqdn = socket.getfqdn()
                locips = str(socket.gethostbyname_ex(socket.gethostname())[-1])
                j = ""
                for d in range(1, self.period_days + 1):
                    for h in range(0, 24):
                        j = j + '\r\n        {"day": %d, "hour": %d, "count": %d},' % (d, h, self.meta[d][h])
                j = '[\r\n  {"flan": "%s",' \
                    '\r\n  "rundate": "%s", ' \
                    '\r\n  "hostname": "%s", ' \
                    '\r\n  "hostfqdn": "%s", ' \
                    '\r\n  "hostips": "%s", ' \
                    '%s\r\n  }\r\n]' % \
                    (__VERSION__,
                     datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
                     hn,
                     fqdn,
                     locips,
                     '\r\n  "stats": [' + j[:-1] + '\r\n    ]')
                print(j)
            else:
                print('Distribution Stats')
                for d in range(1, self.delta + 1):
                    print('  Day %d' % d)
                    for h in range(0, 24):
                        print('      Hour %d:\t%d' % (h, self.meta[d][h]))
        return

    def __init__(self, options, servicemode=False):
        global IMPORT_CONFIG_FILE, EXPORT_CONFIG_FILE

        if options.streamtarget not in ["none", "stdout"]:
            options.quiet = True

        if not options.quiet:
            print("FLAN v", __VERSION__)

        #
        # verify inputs
        #

        # servicemode
        self.servicemode = servicemode
        # --profile
        self.profile = options.profile
        # -q
        self.quiet = options.quiet
        # -a
        self.abort = options.abort
        # -c
        self.streaming = options.streaming
        # -p
        self.preserve_sessions = options.preserve_sessions
        # -z
        self.timezone = options.timezone
        # --nouatag
        self.excludeuatag = options.excludeuatag
        # -i
        self.inputsource = self._onein(options.inputsource, IMPORTS, "files")
        IMPORT_CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config/flan.%s.yaml' % self.inputsource)
        # -o
        self.streamtarget = self._onein(options.streamtarget, EXPORTS, "none")
        if self.streaming and self.streamtarget == "none":
            error("-o must specify a valid supported streaming target choice (for example, 'stdout') if -c is also specified.")
        if self.servicemode and self.streaming and self.streamtarget == "stdout":
            error("stdout streaming is not supported in service mode.")
        if self.streamtarget not in ["none", "stdout"]:
            self.quiet = True
            EXPORT_CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config/flan.%s.yaml' % self.streamtarget)

        if self.inputsource == "files":
            try:
                assert (options.templatelogfiles and (options.outputdir or options.streamtarget))
            except:
                error("please provide a/an example logfile(s) to read, and either a destination output directory to write access logs to OR specify stream output with -o/-c.")
            self.templatelogfiles = options.templatelogfiles.strip()
        else:
            try:
                assert (options.outputdir or options.streamtarget)
            except:
                error("please provide either a destination output directory to write access logs to OR specify stream output with -o/-c.")
            self.templatelogfiles = None

        # -y
        self.replay = options.replay
        # -k
        self.quotechar = "'" if options.quote else ""
        # --pace
        self.pace = options.pace  # if not self.streaming else True

        # -n
        f = 0
        if options.files:
            f = options.files
            f = 0 if f < 1 or f > 1000 else f
        if f == 0 and self.streamtarget == "none":
            error("the number of files to generate (-n) must be between 1 and 1000.")
        self.files = f

        # -g
        g = 0
        if options.gzipindex:
            g = options.gzipindex
            if g > self.files or g < 0:
                error("the gzip index must be between 0 and %d." % self.files)
            if g > 0 and self.streamtarget != 'none':
                error("-g cannot be specified if using stream output or non-file input. Check your -i, -o and/or -c settings.")
        self.gzipindex = g

        # -r
        r = 0
        if options.records:
            r = options.records
            r = R_DEFAULT_NOSTREAMING if r == -1 and not options.streaming else R_DEFAULT_STREAMING if r == -1 and options.streaming else r
            r = 0 if r < 1 or r > R_MAX else r
        if r == 0:
            error("the total number of records to generate per period (-r) must be between 1 and %d." % R_MAX)
        self.records = r

        # -t
        chk = datetime.datetime.now()
        try:
            x = chk.strftime(options.timeformat)
        except:
            error("the -t/--timeformat format must be a valid Python strftime format. See http://strftime.com.")
        self.timeformat = options.timeformat

        # -s
        try:
            start_dt = dtparser.parse(options.start_dt)
        except:
            if options.start_dt:
                error('the start date (-s) specified is not a valid datetime.')
            start_dt = datetime.datetime.combine(datetime.date.today(), datetime.datetime.min.time())
            pass
        self.start_dt = start_dt

        # -e and -j
        end_dt = None
        self.end_dt = None
        self.period = None
        if options.period < 0:
            error('when specifying a distribution period (-j), the period must be greater than zero.')
        if not options.end_dt:
            end_dt = datetime.datetime.combine(datetime.date.today() + datetime.timedelta(days=1), datetime.datetime.min.time())
        if options.end_dt:
            try:
                end_dt = dtparser.parse(options.end_dt)
            except:
                error('the end date (-e) specified is not a valid datetime.')
        if end_dt <= self.start_dt:
            error('the end date (-e) must be after the start date (-s).')
        self.end_dt = end_dt
        self.delta = (self.end_dt - self.start_dt).total_seconds()
        if options.period == 0:
            self.period = self.delta if self.delta <= 86400 else 86400
        elif self.delta < options.period:
            error('if a start date (-s), end date (-e) and period (-j) are all specified, '
                  'the period must be less than the number of seconds between the start and end dates.')
        else:
            self.period = options.period
        self.period_days = ceil(self.delta / 86400)
        self.period_start_dt = None
        self.period_end_dt = None

        # --rps
        # self.rps = 0
        # if options.rps:
        #     if options.rps > 0:
        #         if self.pace:
        #             error('throttling (--rps) and pacing (--pace) are mutually exclusive. Choose one or the other.')
        #         self.rps = options.rps
        #         self.records = int(self.rps * self.period)
        #         if options.records > 0 and not options.quiet:
        #                 print("NOTE: --rps specified; specified -r value of %d replaced with calculated -r value of %d."
        #                       % (options.records, self.records))

        # -b
        self.botfilter = self._onein(options.botfilter, ["all", "seen", "unseen"], "seen")
        if not self.botfilter:
            error("the -b/--botfilter value if specified should be one of: 'all', 'seen', or 'unseen'.")

        # -u
        self.uafilter = self._onein(options.uafilter, ["all", "bots", "nobots"], "all")
        if not self.uafilter:
            error("the -u/--uafilter value if specified should be one of: 'all', 'bots', or 'nobots'.")

        # -d
        # 1 = random
        # 2 = normal
        self.disttype = self._oneof(options.distribution, {"normal": 2, "random": 1}, 1)

        # -l
        self.delimiter = self._oneof(options.delimiter,
                                     {
                                         "none": "",
                                         "no": "",
                                         "n": "",
                                         "false": "",
                                         "f": "",
                                         "0": "",
                                         "tab": "\t",
                                         "t": "\t",
                                         "comma": ",",
                                         "c": "\r",
                                         "cr": "\r",
                                         "lf": "\n",
                                         "crlf": "\r\n"
                                     },
                                     "\r\n")

        # --inputformat, --outputformat
        self.inputformat = options.inputformat.lower()
        if options.outputformat:
            o = options.outputformat.strip()
            if o in ("json", "avro"):
                self.outputstyle = o
                self.outputformat = JSON_FORMAT
                self.delimiter = ",\r\n"
            else:
                self.outputstyle = "text"
                self.outputformat = o

        # -m
        if self.preserve_sessions:
            self.ipmapping = self._onein(options.ipmapping, ["none", "oto24", "oto16"], "oto24")
        else:
            self.ipmapping = self._onein(options.ipmapping, ["none", "oto24", "oto16", "otm24", "otm16" ], "otm24")

        # -p
        if options.preserve_sessions:
            if self.ipmapping not in ["oto24", "oto16"]:
                error("-p (session preservation) requires that -m be specified as either 'oto24' or 'oto16'.")

        # -x
        regx = None
        if options.regex:
            chk = options.regex.strip()
            try:
                regx = re.compile(chk)
            except:
                error("the regex string provided (-x '%s') is not a valid regex. See https://www.google.com/search?q=python+regex+cheat+sheet for help." % chk)
        self.customregex = regx

        # -f
        ipmatches = []
        if options.ipfilter:
            ipmatch = None
            lst = options.ipfilter.strip().split(",")
            for chk in lst:
                try:
                    ipmatch = ipaddress.ip_network(chk) if "/" in chk else ipaddress.ip_address(chk)
                except:
                    error("one or more values in the -f parameter value provided ('%s') is neither a valid IP address or network (CIDR)." % chk)
                ipmatches.append(ipmatch)
        self.ipfilter = ipmatches

        # --stats
        if options.meta and not self.streaming:
            # initialize the stats counters with zeros
            self.meta = {}
            for d in range(1, self.period_days + 1):
                self.meta[d] = {}
                for h in range(0, 24):
                    self.meta[d][h] = 0
        else:
            self.meta = None

        # -q
        if not options.quiet:
            if options.abort:
                info("NOTE: -a specified; will halt on the first unparseable log entry found, if any.")
            else:
                info("NOTE: -a not specified; unparseable log entries will be skipped.")

        if not options.overwrite and not options.streamtarget != "none":
            if self.output_exists():
                error("one or more target file(s) exist, and --overwrite was not specified.")

        # --squeeze
        self.squeeze = options.squeeze

        #
        # handle arg 0: load either the template log file(s), the replay log, the Splunk source, etc
        #

        self.importer = importer(self)
        if not options.quiet:
            if options.replay:
                info("%d lines read from replay log." % (len(self.importer.contents)))
            else:
                info("%d lines read from %s." % (len(self.importer.contents), self.importer.name))

        #
        # handle arg 1: verify output location
        #

        self._verify_outputdir(options)

        return


class UAFactory:

    @staticmethod
    def _explode_uas():
        ualist = json.loads(UA_FREQUENCIES)
        explodeduas = []
        for ua in ualist:
            n = int(float(ua['percent'].strip("%")) * 10.0)
            if ua['useragent'] == "replace-with-bot":
                uad = ua['useragent']
            else:
                uad = uatostructstr(ua['useragent'])
            for i in range(n):
                explodeduas.append(uad)
        return explodeduas

    def __init__(self, meta, template):
        d = {}
        uas = self._explode_uas()
        bs = len(template.botlist) - 1
        if bs >= 0:
            for i in range(0, len(uas) - 1):
                if uas[i] == "replace-with-bot":
                    d[i] = uatostruct(template.botlist[random.randint(0, bs)])
                else:
                    d[i] = uatostruct(uas[i])
        self.uas = d
        return

    def assign_ua(self):
        return self.uas[random.randint(0, len(self.uas) - 1)]


class DataManager:

    @staticmethod
    def _str_to_dt(strdt, fmt="%Y-%m-%d %H:%M:%S"):
        return datetime.datetime.strptime(strdt, fmt)

    @staticmethod
    def _dt_to_str(dt):
        return str(dt)

    @staticmethod
    def _tl_to_ymdhms(tl):
        try:
            tl = tl[:-6] if tl[-6:][:1] == " " else tl
            tl = tl.replace(":", " ", 1) if tl.count(":") == 3 else tl
            dts = dtparser.parse(tl)
            rtn = datetime.datetime.strftime(dts, "%Y-%m-%d %H:%M:%S")
        except Exception as e:
            rtn = None
            pass
        return rtn

    @staticmethod
    def _dt_to_tl(ymdhms, meta):
        try:
            rtn = datetime.datetime.strftime(ymdhms, meta.timeformat) + " " + meta.timezone
        except Exception as e:
            rtn = None
        return rtn

    @staticmethod
    def _load_bot_json():
        blist = []
        try:
            loc = 'https://raw.githubusercontent.com/monperrus/crawler-user-agents/master/crawler-user-agents.json'
            url = request.urlopen(loc)
            raw = url.read()
            uajson = json.loads(raw)
        except:
            uajson = None
            pass
        if not uajson:
            try:
                jf = os.path.join(os.path.dirname(__file__), 'user-agents.json')
                with open(jf) as json_file:
                    uajson = json.load(json_file)
            except:
                uajson = None
                pass
        try:
            for ua in uajson:
                if "instances" in ua:
                    if len(ua["instances"]) > 0:
                        blist = blist + ua["instances"]
        except:
            blist = None
            pass
        return blist

    @staticmethod
    def _load_replay_log():
        replaydata = []
        try:
            for file in glob.glob(REPLAY_LOG_FILE):
                with open(file, "rb") as rl:
                    replaydata = pickle.load(rl)
                    rl.close()
        except:
            replaydata = []
            pass
        return replaydata

    @staticmethod
    def _save_replay_log(replaydata, meta):
        try:
            with open(REPLAY_LOG_FILE, "wb+") as rl:
                pickle.dump(replaydata, rl)
                rl.close()
        except Exception as e:
            error("unable to save %s: %s" % (REPLAY_LOG_FILE, str(e)))
        return

    @staticmethod
    def _get_loglineregex(meta):
        patterns = {}
        fields = json.loads(SUPPORTED_FIELDS)
        for field in fields:
            patterns[str(field["name"]).lstrip("$")] = str(field["regex"])
        try:
            reexpr = ''.join(
                    '(?P<%s>%s)' % (g, patterns.get(g, '.*?')) if g else re.escape(c)
                    for g, c in re.findall(r'\$(\w+)|(.)', meta.inputformat))
            return re.compile(reexpr)
        except:
            error("incorrect, incomplete, or unsupported input format (--inputformat) value provided.")

    def _parse_logline(self, line, meta):
        m = None
        line = line.rstrip()
        try:
            m = self.lineregex.match(line)
        except Exception as e:
            m = None
            pass

        if not m:
            if meta.abort:
                error("Line %d is incorrectly formatted." % self.totread)
            if not meta.quiet:
                info("Skipping unparseable line %d..." % self.totread)

        if meta.customregex:
            m = None
            try:
                m = meta.customregex.match(line)
            except Exception as e:
                pass

        if m:
            dikt = m.groupdict()
            if "time_local" in dikt.keys():
                dikt["_ts"] = self._tl_to_ymdhms(dikt["time_local"])
            return dikt
        else:
            return None

    @staticmethod
    def _obsfucate_ip(entry, meta):
        ipvXaddress = entry["_ip"]
        isbot = entry["_isbot"]
        # we don't obfuscate any of these
        if ipvXaddress.is_link_local \
                or ipvXaddress.is_loopback \
                or ipvXaddress.is_multicast \
                or ipvXaddress.is_private \
                or ipvXaddress.is_reserved \
                or isbot \
                or meta.ipmapping is None:
            newip = str(ipvXaddress)
        else:
            # obfuscate but try to preserve general geolocation, residential vs commercial, etc.
            ipkey = str(ipvXaddress)
            # generate a new ip if using o2m or if o2o found nothing in the map
            # o2m may generate multiple obfuscated IPs from the same IP during the same run
            # o2o always generates/returns the same obfuscated IP from a given input IP during the same run
            tries = 0
            newip = IPMAP[ipkey] if meta.ipmapping in ["oto24", "oto16"] and ipkey in IPMAP.keys() else None
            while not newip:
                if ipvXaddress.version == 4:
                    if meta.ipmapping[-2:] == "24":
                        newip = "%s.%s" % (ipkey.rsplit(".", 1)[0], str(random.randint(0, 255)))
                    elif meta.ipmapping[-2:] == "16":
                        newip = "%s.%s.%s" % (ipkey.rsplit(".", 2)[0], str(random.randint(0, 255)), str(random.randint(0, 255)))
                else:
                    newip = "%s:%s" % (ipkey.rsplit(":", 1)[0], ''.join(random.choice(string.digits + "abcdef") for i in range(4)))
                # ensure obfuscation
                if newip == ipkey:
                    newip = None
                    continue
                # is it a valid global ip? if not, regenerate it
                try:
                    chk = ipaddress.ip_address(newip)
                    if not chk.is_global:
                        newip = None
                except:
                    newip = None
                    pass
                if newip:
                    if meta.ipmapping[:3] == "oto":
                        if newip in IPMAP2.keys():
                            newip = None
                            tries += 1
                            if tries == 1024:
                                error("excessive number of retries during attempt to obfuscate ip %s using one-to-one method." % ipkey)
                        else:
                            IPMAP[ipkey] = newip
                            IPMAP2[newip] = True
        return newip

    @staticmethod
    def _obfuscate_ua(entry, meta, uas):
        if meta.excludeuatag:
            flantag = ""
        else:
            flantag = " Flan/%s (https://bret.guru/flan)" % __VERSION__
        if meta.preserve_sessions:
            return entry["_ua"].ua_string + flantag
        # pick a ua from the same family of uas
        # if there isn't one, use the one provided
        entry_browser = entry["_ua"].browser.family
        entry_device = entry["_ua"].device.family
        entry_os = entry["_ua"].os.family
        entry_is_bot = entry["_isbot"]
        hits = [uas[x].ua_string for x in uas
                if uas[x].browser.family == entry_browser
                and uas[x].device.family == entry_device
                and uas[x].os.family == entry_os
                and uas[x].is_bot == entry_is_bot]
        h = len(hits)
        newua = str(hits[random.randint(0, h - 1)] if h > 0 else entry["_ua"].ua_string) + flantag
        return newua

    def __init__(self, meta):

        self.totread = 0
        self.totok = 0
        self.parsed = []
        self.botlist = []
        if meta.uafilter != "nobots" and meta.botfilter != "seen":
            self.botlist = self._load_bot_json()
        earliest_ts = None
        latest_ts = None

        replaying = False

        if meta.replay:

            self.parsed = self._load_replay_log()
            if self.parsed:
                replaying = True
                self.totok = len(self.parsed)
                self.totread = self.totok
                if not meta.quiet:
                    info('%d preparsed entries loaded from replay log.' % self.totread)

        if not replaying:

            self.lineregex = self._get_loglineregex(meta)

            for entry in meta.importer.contents:

                self.totread += 1

                parsed_line = self._parse_logline(entry, meta)
                if not parsed_line:
                    continue

                keys = parsed_line.keys()

                if 'http_user_agent' in keys:
                    parsed_line["_ua"] = uatostruct(parsed_line["http_user_agent"])
                    if parsed_line["_ua"].is_bot:
                        if meta.botfilter != "unseen" and meta.uafilter != "nobots":
                            self.botlist.append(parsed_line["http_user_agent"])
                            parsed_line["_isbot"] = True
                        else:
                            if not meta.quiet:
                                info('Skipping bot [excluded by -b/-u settings] found on line %d...' % self.totread)
                            continue
                    elif meta.uafilter == "bots":
                        if not meta.quiet:
                            info('Skipping non-bot [excluded by -u setting] found on line %d...' % self.totread)
                        continue
                    else:
                        parsed_line["_isbot"] = False

                t = self._str_to_dt(parsed_line["_ts"])
                if earliest_ts:
                    if t < earliest_ts:
                        earliest_ts = t
                else:
                    earliest_ts = t

                if 'remote_addr' in keys:
                    ip = parsed_line["remote_addr"]
                    if meta.ipfilter:
                        chk = ipaddress.ip_address(ip)
                        found = False
                        for ipmatch in meta.ipfilter:
                            # == for an address match if ipmatch is an address, in for a network match if ipmatch is a CIDR
                            if "/" in str(ipmatch):
                                if chk in ipmatch:
                                    found = True
                                    break
                            elif chk == ipmatch:
                                found = True
                                break
                        if not found:
                            continue

                    parsed_line["_ip"] = ipaddress.ip_address(ip)

                self.totok += 1

                if meta.squeeze:
                    if latest_ts:
                        t = earliest_ts + datetime.timedelta(seconds=self.totok-1)
                        parsed_line["_ts"] = self._dt_to_str(t)
                        if "time_local" in keys:
                            parsed_line["time_local"] = self._dt_to_tl(t, meta)
                    elif earliest_ts and "time_local" in keys:
                        parsed_line["time_local"] = self._dt_to_tl(earliest_ts, meta)

                if latest_ts:
                    if t > latest_ts:
                        latest_ts = t
                else:
                    latest_ts = t

                self.parsed.append(parsed_line)

                if not meta.quiet:
                    if self.totread % 100 == 0:
                        info('Parsed %d entries...' % self.totread)

                profile_memory(meta)

        if self.totok == 0:
            error("no usable entries found in the log file provided based on passed parameter filters.")

        if not replaying:
            if not earliest_ts or not latest_ts:
                error("no timestamps found in the log file provided. Timestamps are required.")
            self.record_density = self.totok * 1.0 / (latest_ts - earliest_ts).total_seconds()
            if meta.replay:
                self._save_replay_log(self.parsed, meta)
        else:
            self.record_density = 1

        if self.botlist:
            self.botlist = list(dict.fromkeys(self.botlist))  # remove dupes

        return

    def generate_entry(self, timestamp, logindex, meta, uas):
        if meta.preserve_sessions:
            # pick the next parsed entry in order, since we are preserving sessions and need to keep it in order
            entry = self.parsed[logindex]
        else:
            # pick a random parsed entry from the previously generated distribution
            entry = self.parsed[random.randint(0, len(self.parsed) - 1)]
        # ip obsfucation
        ip = self._obsfucate_ip(entry, meta)
        # ua obfuscation
        ua = self._obfuscate_ua(entry, meta, uas)
        # format the timestamp back to desired nginx $time_local format
        ts = meta.timeformat + " " + meta.timezone
        ts = timestamp.strftime(ts.rstrip())
        # update stats
        if meta.meta:
            delta = timestamp - meta.start_dt
            meta.meta[delta.days + 1][timestamp.hour] += 1
        # return the log entry
        return meta.outputformat. \
            replace("$time_local", ts). \
            replace("$remote_addr", ip). \
            replace("$http_user_agent", ua). \
            replace("$remote_user", entry["remote_user"]). \
            replace("$request", entry["request"]). \
            replace("$status", entry["status"]). \
            replace("$body_bytes_sent", entry["body_bytes_sent"]). \
            replace("$http_referer", entry["http_referer"])


def make_distribution(meta, data):

    def _addtopsdt(offset):
        # round down microseconds then add seconds offset
        return meta.period_start_dt - datetime.timedelta(microseconds=meta.period_start_dt.microsecond) + \
               datetime.timedelta(seconds=offset, microseconds=0)

    if meta.disttype == 1:
        midpoint = None
        meta.period_end_dt = meta.end_dt
        tot2write = (meta.files * meta.records) if meta.files > 0 else meta.records
    else:
        midpoint = round(meta.period / 2.0)
        meta.period_end_dt = _addtopsdt(meta.period)
        period_length = (meta.period_end_dt - meta.period_start_dt).total_seconds()
        period_ratio = period_length * 1.0 / meta.delta
        tot2write = int(data.record_density * period_length) if meta.streaming \
            else int(meta.files * meta.records * period_ratio) if meta.files > 0 \
            else int(meta.records * period_ratio)
    d = {}
    if meta.disttype == 2:
        # create a set of normally-distributed time slots with a sprinkle of random points between the start and end datetimes
        normal_distribution = np.random.normal(midpoint, 0.1866 * meta.period, tot2write)
        # uniqueify the generated distribution at the per-second level
        # if I generated the same datetime X times, add a counter = X
        for val in normal_distribution:
            key = _addtopsdt(int(val)) \
                if 0.00 <= val <= meta.period \
                else _addtopsdt(random.randint(0, meta.period))
            d[key] = d[key] + 1 \
                if key in d.keys() \
                else 1
            profile_memory(meta)
    else:
        # create a set of randomly-distributed time slots between the start and end datetimes
        # uniqueify the generated distribution at the per-second level
        # if I generated the same datetime X times, add a counter = X
        random_distribution = np.random.randint(meta.period, size=tot2write)
        for val in random_distribution:
            key = _addtopsdt(int(val))
            d[key] = d[key] + 1 \
                if key in d.keys() \
                else 1
            profile_memory(meta)
    # sort the generated time distribution in chronological order ascending using fast itemgetter-based sort
    td = collections.OrderedDict(sorted(d.items(), key=operator.itemgetter(0)))
    return tot2write, td


def make_flan(options, servicemode=False):

    def _next(td):
        try:
            _nxt = next(itertools.islice(td.items(), 1))
        except StopIteration:
            _nxt = None
            pass
        return _nxt

    # verify parameters, and load the template log file or replay log
    meta = MetaManager(options, servicemode)

    # parse and store the template log file data line by line
    data = DataManager(meta)

    # populate ua list with frequency-appropriate selection of UAs actually seen in the template log
    uas = UAFactory(meta, data)

    meta.files = 1 if meta.files < 1 else meta.files
    currentfile = meta.files
    log = None
    time_distribution = None
    timeslot = None
    targetproxy = None
    totthisfile = 0
    totwritten = 0
    logindex = 0
    current_delimiter = ""
    meta.period_start_dt = meta.start_dt
    meta.period_end_dt = None
    last_logindex = len(data.parsed) - 1

    while True:
        if not time_distribution:
            #
            # Build a new time slice distribution to attribute fake log entries to
            #
            tot2write, time_distribution = make_distribution(meta, data)
            # get 1st entry in the time distribution
            timeslot = _next(time_distribution)
            if timeslot is None:
                break
            time_base = timeslot[0]
        #
        # if not meta.quiet and not meta.streaming:
        #    info('Parsed and prepped a total of %d entries (%d successfully, %d skipped).' % (data.totread, data.totok, data.totread - data.totok))
        #
        # Generate the requested fake logs for the current periodicity
        #
        if not log:
            #
            # start a new output log
            #
            if meta.streamtarget == "none":
                currentfile -= 1
                log = meta.new_outputfile(currentfile)
                if not meta.quiet:
                    info('Beginning write of fake entries to log %s.' % log.name)
                totthisfile = 0
            else:
                targetproxy = exporter(meta)
                log = targetproxy.target
            # beginning of template log
            logindex = 0
            # if json output, start a json array
            if options.outputformat == "json":
                log.write('[\r\n')
            current_delimiter = ""
            # pacing base
            pace_base = datetime.datetime.now() if meta.pace else None
        #
        # get timestamp of the log entry to write
        # is that timestamp after the -e date? we're done!
        #
        timestamp = timeslot[0]
        if timestamp > meta.end_dt and not meta.streaming:
            break
        #
        # pacing
        #
        if meta.pace:
            clock_offset = (datetime.datetime.now() - pace_base).total_seconds()
            log_offset = (timestamp - time_base).total_seconds()
            while log_offset > clock_offset:
                #  I'm ahead of myself, hold yer horses hoss
                sleep(0.05)
                clock_offset = (datetime.datetime.now() - pace_base).total_seconds()
                log_offset = (timestamp - time_base).total_seconds()
        #
        # emit one entry
        #
        if meta.gzipindex > 0:
            log.write(str.encode("%s%s%s%s" % (current_delimiter, meta.quotechar, data.generate_entry(timestamp, logindex, meta, uas.uas), meta.quotechar)))
        else:
            log.write("%s%s%s%s" % (current_delimiter, meta.quotechar, data.generate_entry(timestamp, logindex, meta, uas.uas), meta.quotechar))
        #
        # increment counters and available timeslot if needed
        #
        totthisfile += 1
        totwritten += 1
        spots = timeslot[1]
        if spots == 1:
            # no spots left, we're done with this time slot
            # get next available time slot, freeing up memory in the process
            del time_distribution[timestamp]
            timeslot = _next(time_distribution)
            if timeslot is None:
                # The current time distribution is filled! Get a new time distribution if we go around again
                meta.period_start_dt = meta.period_end_dt + timedelta(seconds=1)
                meta.period_end_dt = meta.period_end_dt + timedelta(seconds=meta.period)
                time_distribution = None
        else:
            # one spot filled; decrement the number of available spots we have with this timestamp
            timeslot = (timestamp, spots - 1)
        current_delimiter = meta.delimiter
        #
        # move the template log pointer forward; if at the end, wrap around back to its beginning
        #
        if last_logindex == logindex:
            logindex = 0
        else:
            logindex += 1
        #
        # check status
        #
        if totthisfile % 100 == 0:
            profile_memory(meta)
            if not meta.quiet:
                info('Wrote %d entries...' % totthisfile)
        #
        # is the current output log file full? then start a new one
        #
        if meta.streamtarget == "none" and not meta.streaming:
            if totthisfile >= meta.records:
                if options.outputformat == "json":
                    log.write('\r\n]')
                if not meta.quiet:
                    info('Log %s completed.' % log.name)
                if targetproxy:
                    targetproxy.close()
                log = None
                if currentfile == 0:
                    break
                else:
                    meta.gzipindex -= 1 if meta.gzipindex > 0 else 0
        #
        # go back for more
        #
        continue

    # finally
    if log:
        if options.outputformat == "json":
            log.write('\r\n]')
        if targetproxy:
            if not targetproxy.closed:
                targetproxy.close()
        if meta.streamtarget == "none":
            if not meta.quiet:
                info('Log %s completed.' % log.name)

    if not meta.quiet:
        info('Total of %d record(s) written successfully from %d parsed template entries.' % (totwritten, data.totok))
        info('Log generation completed.')

    profile_memory(meta)
    meta.emitmeta()

    return


def interactiveMode():
    # command-line parsing
    argz = argparse.ArgumentParser(usage="flan [options] [templatelogfiles] [outputdir]",
                                   description="Create one or more 'fake' Apache or Nginx access.log(.#) file(s) from a single real-world example access.log file.")
    argz.add_argument("templatelogfiles",
                      nargs='?',
                      default=None)
    argz.add_argument("outputdir",
                      nargs='?',
                      default=None)
    argz.add_argument("-a",
                      action="store_true",
                      dest="abort",
                      help="If specified, abort on the first (meaning, 'any and every') non-parsable log line found. "
                           "If not specified (the default), skip all non-parsable log lines but process the rest of the entries.")
    argz.add_argument("-b", "--botfilter",
                      action="store",
                      dest="botfilter",
                      default="seen",
                      help="Specifies which bots if any to include in the generated log files (iff -u is set to 'all' or 'bots'), "
                           "one of: all=include all bots from both the template log and user-agents.json in the fake log entries, "
                           "seen=ONLY include bots found in the template log file in the fake log entries, "
                           "unseen=ONLY include bots found in the user-agents.json in the fake log entries. Default=seen.")
    argz.add_argument("-c", "--continuous",
                      action="store_true",
                      dest="streaming",
                      help="Continuous streaming mode. If enabled, ignores the -e setting, and streams entries continuously until "
                           "settings.R_MAX is reached. -o must be specified. Not available for file output.	"
                      )
    argz.add_argument("-d", "--distribution",
                      action="store",
                      dest="distribution",
                      default="normal",
                      help="Specifies the distribution of the generated fake log data between the start and end dates, "
                           "one of: random (distribute log entries randomly between start and end dates), "
                           "normal (distribute using a normal distribution with the peak in the middle of the start/end range). Default=normal.")
    argz.add_argument("-e", "--end",
                      action="store",
                      dest="end_dt",
                      help='Latest datetime to provide in the generated log files. Defaults to midnight tomorrow.')
    argz.add_argument("-f", "--ipfilter",
                      action="store",
                      dest="ipfilter",
                      default="",
                      help="If provided, this should specify one or more optional IP(s) and/or CIDR range(s) in quotes that all entries in the template log file must "
                           "match in order to be used for output log generation. Only lines containing an IP that matches one or more of these will "
                           "be used. Separate one or more IPs or CIDRs here by commas; for example, '-f \"123.4.5.6,145.0.0.0/16,2001:db8::/48\"'. "
                           "If not provided, use all otherwise valid template log lines in generating the output logs.")
    argz.add_argument("-g", "--gzip",
                      action="store",
                      dest="gzipindex",
                      type=int,
                      default=0,
                      help='Used in conjunction with the passed -n value, this specifies a file index number at which to begin gzipping generated '
                           'log files. It must be between 0 and the -n value provided. For example, "-n 5 -g 3" generates log files called '
                           '"access.log", "access.log.1", "access.log.2.gz", "access.log.3.gz", "access.log.4.gz": 5 files, the last 3 of '
                           'which are gzipped. Default=0, no gzipping occurs.')
    argz.add_argument("-i", "--inputsource",
                      action="store",
                      dest="inputsource",
                      default="files",
                      help='Source of input template logs/data, one of:<br><br>'
                           'files=one or more template log files<br><br>'
                           'splunk=a Splunk Enterprise source and query as defined in the flan.splunk.yaml file. '
                           'Default=files.')
    argz.add_argument("--inputformat",
                      action="store",
                      dest="inputformat",
                      default=DEFAULT_FORMAT,
                      help='Format of individual lines in the template log file(s) provided. Default=\'%s\'' % DEFAULT_FORMAT)
    argz.add_argument("--nouatag",
                      action="store_true",
                      dest="excludeuatag",
                      help="If specified, does not append the custom 'Flan/%s' tag to all of the user agents in the generated file(s). Default=append "
                           "the tag to all UAFactory." % __VERSION__)
    argz.add_argument("-j",
                      action="store",
                      dest="period",
                      type=int,
                      default=0,
                      help="Defines the length of a single time distribution period in seconds (1d=exactly 24h; no leaps taken into account). "
                           "If using normal distribution, the distribution will be this long, with the peak in the middle of it. This must be "
                           "equal to or less than the number of seconds between the -s and -e values. Default=0; the period is set to the time "
                           "between the -s and -e values, or 86400 seconds (1 day), whichever is less." )
    argz.add_argument("-k",
                      action="store_true",
                      dest="quote",
                      help="If specified, adds single quotes around each generated log line. Useful for some downstream consumers. Default=no quotes added.")
    argz.add_argument("-l", "--linedelimiter",
                      action="store",
                      dest="delimiter",
                      default='crlf',
                      help="Line delimiter to append to all generated log entries, one of: [none, no, false, n, f], [comma, c], [tab, t], cr, lf, or crlf. "
                           "Default=crlf.")
    argz.add_argument("-m", "--ipmapping",
                      action="store",
                      dest="ipmapping",
                      default='onetomany',
                      help='Obfuscation rule to use for IPs, one of: otm24=map one IPv4 to up to 255 IPv4 /24 addresses or '
                           'one IPv6 to up to 65536 IPv6 /116 addresses, otm16=map one IPv4 to up to 65535 IPv4 /16 addresses or '
                           'one IPv6 to up to 65536 IPv6 /116 addresses, oto24=map one IPv4/IPv6 address to one IPv4/IPv6 address '
                           'within the same /24 or /116 block, oto16=map one IPv4/IPv6 address to one IPv4/IPv6 address '
                           'within the same /16 or /116 block, off=do not obfuscate IPs. Default=otm24.' )
    argz.add_argument("--meta",
                      action="store_true",
                      dest="meta",
                      help='Collect and emit (at the end) execution metadata and per-hour cumulative counts on all the log entries generated. '
                           'Use this to identify the source of your generated data and verify '
                           'the spread across your chosen distribution. If -o is specified, this is in JSON format, otherwise it is a human-readable print format. '
                           'Default=no metadata emitted.')
    argz.add_argument("-n", "--numfiles",
                      action="store",
                      dest="files",
                      type=int,
                      default=0,
                      help="Number of access.log(.#) file(s) to output. Default=1, min=1, max=1000. Example: '-n 4' creates access.log, "
                           "access.log.1, access.log.2, and access.log.3 in the output directory." )
    argz.add_argument("-o",
                      action="store",
                      dest="streamtarget",
                      default="none",
                      help="If specified, ignores the output directory and -n flag values, enables quiet mode (-q), and streams all output "
                           "to the target, one of : 'stdout' (other options tbd). If not specified (the default), output is written to file(s) in the output directory provided.")
    argz.add_argument("--outputformat",
                      action="store",
                      dest="outputformat",
                      default=DEFAULT_FORMAT,
                      help='Format of individual emitted entries in the generated logs. If provided, overrides the combined format (-f) '
                           'setting. Special values: avro=emits JSON-encoded entries in binary Avro format, json=emits entries in textual JSON format. Default=\'%s\'' % DEFAULT_FORMAT)
    argz.add_argument("-p",
                      action="store_true",
                      dest="preserve_sessions",
                      help="If specified, preserve sessions (specifically, pathing order for a given IP/UA/user combo). "
                           "'-m oto24' must also be specified for this to work."
                           "If not specified (the default), do not preserve sessions.")
    argz.add_argument("--pace",
                      action="store_true",
                      dest="pace",
                      help="If specified, syncs the timestamps in the generated log records with the current clock time at generation, "
                           "so that log entry . Default=no pacing (write/stream as fast as possible).", )
    argz.add_argument("--profile",
                      action="store_true",
                      dest="profile",
                      help="If specified, prints speed profile information for flan.py execution to stdout. Default=do not profile.")
    argz.add_argument("-q",
                      action="store_true",
                      dest="quiet",
                      help="Basho-like stdout. Default=Proust-like stdout.")
    argz.add_argument("-r", "--records",
                      action="store",
                      type=int,
                      dest="records",
                      default=-1,
                      help="Number of records (entries) to create per generated access.log(.#) file. "
                           "Default=%d (nonstreaming) or %d (streaming), min=1, max=%d."
                           % (R_DEFAULT_NOSTREAMING, R_DEFAULT_STREAMING, R_MAX)
                      )
    # argz.add_argument("--rps",
    #                   action="store",
    #                   type=int,
    #                   dest="rps",
    #                   default=0,
    #                   help="If specified, defines a maximum records-per-second pace with which to write "
    #                        "or stream records to either file or streaming output, and computes the -r value from this, "
    #                        "ignoring any explicitly specified -r value. "
    #                        "The actual pace may be less than this value in practice. "
    #                        "Default=no pacing (write/stream as fast as possible)." )
    argz.add_argument("--squeeze",
                      action="store_true",
                      dest="squeeze",
                      help="If specified, compresses the timestamps on the template log file so that at least one entry will be generated "
                           "every second regardless of the actual records-per-second density in the template log. Meant specifically for "
                           "testing Flan results."
                      )
    argz.add_argument("-s", "--start",
                      action="store",
                      dest="start_dt",
                      help='Earliest datetime to provide in the generated log files. Defaults to midnight today.')
    argz.add_argument("-t", "--timeformat",
                      action="store",
                      dest="timeformat",
                      default="%-d/%b/%Y:%H:%M:%S",
                      help="Timestamp format to use in both the template log and the generated log file(s), EXCLUDING TIMEZONE (see -z parameter), "
                           "in Python strftime format (see http://strftime.org/). Default='%%-d/%%b/%%Y:%%H:%%M:%%S'")
    argz.add_argument("-u", "--uafilter",
                      action="store",
                      dest="uafilter",
                      default="all",
                      help="Filter generate log entries by UA, one of: all=use BOTH bot and non-bot UAFactory and template "
                           "log entries with bot/non-bot UAFactory when creating the generated log entries, "
                           "bots=use ONLY bot UAFactory and template log entries with bot UAFactory when creating the generated log entries, "
                           "nobots=use ONLY non-bot UAFactory and template log entries with non-bot UAFactory when creating the generated "
                           "log entries. "
                           "Default=all.")
    argz.add_argument("-v",
                      action="version",
                      version="Flan/%s" % __VERSION__,
                      help="Print version and exit.")
    argz.add_argument("-w",
                      action="store_true",
                      dest="overwrite",
                      help="If specified, delete any generated log files if they already exist. "
                           "If not specified (the default), exit with an error if any log file to be generated already exists.")
    argz.add_argument("-x", "--regex",
                      action="store",
                      dest="regex",
                      default="",
                      help="Specifies an optional (Python) regex that all template log file lines must match to be used in generating "
                           "the log files. DataManager log entries that do not match this regex are ignored. "
                           "If not specified, use all otherwise valid template log lines in generating the output logs.")
    argz.add_argument("-y",
                      action="store_true",
                      dest="replay",
                      help="If specified, saves the parsed log file in a replay log (called 'flan.replay' in the current directory) "
                           "for faster subsequent reload and execution on the same data.")
    tz = datetime.datetime.now(timezone.utc).astimezone().strftime('%z')
    argz.add_argument("-z", "--timezone",
                      action="store",
                      dest="timezone",
                      default=tz,
                      help="Timezone offset in (+/-)HHMM format to append to timestamps in the generated log file(s), "
                           "or pass '' to specify no timezone. Default=your current timezone (%s)." % tz)

    options = argz.parse_args()

    make_flan(options)
    if options.profile:
        x = 1024.0 if sys.platform == "darwin" else 1.0 if sys.platform == "linux" else 1.0
        info("\n\r%s MB maximum (peak) memory used" % str(round(MAX_RSS_MEMORY_USED / 1024.0 / x, 3)))


class FlanService(Service):

    def __init__(self, *args, **kwargs):
        global LOGGER
        super(FlanService, self).__init__(*args, **kwargs)
        self.logger.addHandler(SysLogHandler(address=find_syslog(),
                               facility=SysLogHandler.LOG_DAEMON))
        self.logger.setLevel(logging.INFO)
        LOGGER = self.logger

    def run(self):
        # wait 30s when running in a Mac dev env to allow opportunity to attach to the debugger and debug the service
        sleep(30) if sys.platform == "darwin" else sleep(0)
        info("Starting Flan/%s" % __VERSION__)
        # set up defaults when running as a service
        from argparse import Namespace
        options = Namespace(
                abort=False,
                botfilter='seen',
                delimiter='crlf',
                distribution='normal',
                emitjson=False,
                end_dt=None,
                excludeuatag=False,
                files=10,
                inputformat=DEFAULT_FORMAT,
                gzipindex=0,
                ipfilter='',
                ipmapping='otm24',
                meta=False,
                outputdir='',
                outputformat=DEFAULT_FORMAT,
                overwrite=True,
                pace=False,
                period=0,
                preserve_sessions=False,
                profile=False,
                quiet=True,
                quote=False,
                records=10000,
                regex='',
                replay=False,
                start_dt=None,
                streaming=False,
                streamtarget='none',
                templatelogfiles='',
                timeformat='%-d/%b/%Y:%H:%M:%S',
                timezone='-0400',
                uafilter='all')
        immutable_service_settings = ["meta", "overwrite", "profile", "quiet"]
        # look for flan.config.yaml
        # update default service settings with the entries in the flan.config.yaml
        settings = getconfig(SERVICE_CONFIG_FILE, "settings")
        for setting in settings:
            setting = setting.strip().lower()
            if setting not in immutable_service_settings:
                try:
                    options.vars()[setting] = settings[setting]
                except:
                    error('unrecognized setting "%s" in %s' % (setting, SERVICE_CONFIG_FILE))
                    os._exit(1)
        info("%s loaded successfully" % SERVICE_CONFIG_FILE)
        # make flan
        make_flan(options, servicemode=True)
        info("Flan/%s finished" % __VERSION__)

    def show_status(self):
        return


def main():
    try:
        cmd = sys.argv[1].strip().lower()
    except IndexError:
        cmd = None
        pass
    if cmd in ['start', 'stop', 'status']:
        service_name = 'Flan v%s Service' % __VERSION__
        service = FlanService(service_name, pid_dir='/tmp')
        if cmd == "start":
            service.start()
            sleep(2)
            if service.is_running():
                print("%s is running." % service_name)
            else:
                print("WARNING, %s is NOT running." % service_name)
        elif cmd == "stop":
            service.stop()
            sleep(2)
            if service.is_running():
                print("WARNING, %s is STILL running." % service_name)
            else:
                print("%s is not running." % service_name)
        elif cmd == "status":
            if service.is_running():
                print("%s is running." % service_name)
            else:
                print("%s is not running." % service_name)
            service.show_status()
    else:
        interactiveMode()
    os._exit(0)


if __name__ == "__main__":
    main()

