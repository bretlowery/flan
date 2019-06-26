from __future__ import print_function
import os
import sys
import glob
from optparse import OptionParser
import datetime
from datetime import timezone
from dateutil import parser as dtparser
import re
import json
import user_agents
import random
import ipaddress
import string
import numpy as np


__version__ = "0.0.1"

MONTHS = {
    'Jan': 1,
    'Feb': 2,
    'Mar': 3,
    'Apr': 4,
    'May': 5,
    'Jun': 6,
    'Jul': 7,
    'Aug': 8,
    'Sep': 9,
    'Oct': 10,
    'Nov': 11,
    'Dec': 12
}

supported_nginx_fields = '[' \
         '{' \
         '  "name": "$remote_addr",' \
         '  "regex": "(\\\\d+.\\\\d+.\\\\d+.\\\\d+)"' \
         '},' \
         '{' \
         '  "name": "$remote_user",' \
         '  "regex": "(.+)"' \
         '},' \
         '{' \
         '  "name": "$time_local",' \
         '  "regex": "(.+)"' \
         '},' \
         '{' \
         '  "name": "$request",' \
         '  "regex": "(.+)"' \
         '},' \
         '{' \
         '  "name": "$status",' \
         '  "regex": "(\\\\d+)"' \
         '},' \
         '{' \
         '  "name": "$body_bytes_sent",' \
         '  "regex": "(\\\\d+)"' \
         '},' \
         '{' \
         '  "name": "$http_referer",' \
         '  "regex": "(.+)"' \
         '},' \
         '{' \
         '  "name": "$http_user_agent",' \
         '  "regex": "(.*)"' \
         '},' \
         '{' \
         '  "name": "-",' \
         '  "regex": "-"' \
         '}' \
         ']'

# from https://techblog.willshouse.com/2012/01/03/most-common-user-agents/
# Last Updated: Tue, 18 Jun 2019 13:07:06 +0000
uafreqlist = \
    '[{"percent":"21.9%","useragent":"replace-with-bot"},' \
    '{"percent":"14.1%","useragent":"Mozilla//5.0 (Windows NT 10.0; Win64; x64) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//74.0.3729.169 Safari//537.36","system":"Chrome Generic Win10"},' \
    '{"percent":"4.7%","useragent":"Mozilla//5.0 (Windows NT 10.0; Win64; x64; rv:67.0) Gecko//20100101 Firefox//67.0","system":"Firefox 67.0 Win10"},' \
    '{"percent":"3.9%","useragent":"Mozilla//5.0 (Windows NT 10.0; Win64; x64) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//74.0.3729.157 Safari//537.36","system":"Chrome Generic Win10"},' \
    '{"percent":"3.3%","useragent":"Mozilla//5.0 (Macintosh; Intel Mac OS X 10_14_5) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//74.0.3729.169 Safari//537.36","system":"Chrome Generic macOS"},' \
    '{"percent":"2.9%","useragent":"Mozilla//5.0 (Windows NT 6.1; Win64; x64) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//74.0.3729.169 Safari//537.36","system":"Chrome Generic Win7"},' \
    '{"percent":"2.7%","useragent":"Mozilla//5.0 (Macintosh; Intel Mac OS X 10_14_5) AppleWebKit//605.1.15 (KHTML, like Gecko) Version//12.1.1 Safari//605.1.15","system":"Safari Generic macOS"},' \
    '{"percent":"1.9%","useragent":"Mozilla//5.0 (Windows NT 10.0; Win64; x64) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//75.0.3770.80 Safari//537.36","system":"Chrome Generic Win10"},' \
    '{"percent":"1.8%","useragent":"Mozilla//5.0 (X11; Ubuntu; Linux x86_64; rv:67.0) Gecko//20100101 Firefox//67.0","system":"Firefox 67.0 Linux"},' \
    '{"percent":"1.8%","useragent":"Mozilla//5.0 (Windows NT 10.0; Win64; x64; rv:66.0) Gecko//20100101 Firefox//66.0","system":"Firefox 66.0 Win10"},' \
    '{"percent":"1.7%","useragent":"Mozilla//5.0 (Windows NT 10.0; WOW64) AppleWebKit//537.36 (KHTML, like Gecko) HeadlessChrome//60.0.3112.78 Safari//537.36","system":"Headless Chrome 60.0 Win10"},' \
    '{"percent":"1.6%","useragent":"Mozilla//5.0 (Windows NT 10.0; Win64; x64) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//74.0.3729.131 Safari//537.36","system":"Chrome Generic Win10"},' \
    '{"percent":"1.5%","useragent":"Mozilla//5.0 (Windows NT 6.1; rv:60.0) Gecko//20100101 Firefox//60.0","system":"Firefox 60.0 Win7"},' \
    '{"percent":"1.3%","useragent":"Mozilla//5.0 (Macintosh; Intel Mac OS X 10_14_4) AppleWebKit//605.1.15 (KHTML, like Gecko) Version//12.1 Safari//605.1.15","system":"Safari Generic macOS"},' \
    '{"percent":"1.2%","useragent":"Mozilla//5.0 (Macintosh; Intel Mac OS X 10.14; rv:67.0) Gecko//20100101 Firefox//67.0","system":"Firefox 67.0 macOS"},' \
    '{"percent":"1.2%","useragent":"Mozilla//5.0 (Macintosh; Intel Mac OS X 10_14_4) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//74.0.3729.169 Safari//537.36","system":"Chrome Generic macOS"},' \
    '{"percent":"1.1%","useragent":"Mozilla//5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//74.0.3729.169 Safari//537.36","system":"Chrome Generic macOS"},' \
    '{"percent":"1.1%","useragent":"Mozilla//5.0 (Windows NT 10.0; Win64; x64) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//64.0.3282.140 Safari//537.36 Edge//17.17134","system":"Edge 17.0 Win10"},' \
    '{"percent":"1.1%","useragent":"Mozilla//5.0 (Windows NT 6.1; Win64; x64; rv:67.0) Gecko//20100101 Firefox//67.0","system":"Firefox 67.0 Win7"},' \
    '{"percent":"1.0%","useragent":"Mozilla//5.0 (Windows NT 10.0; Win64; x64) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//64.0.3282.140 Safari//537.36 Edge//18.17763","system":"Edge 18.0 Win10"},' \
    '{"percent":"0.9%","useragent":"Mozilla//5.0 (Windows NT 10.0; Win64; x64) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//73.0.3683.103 Safari//537.36","system":"Chrome 73.0 Win10"},' \
    '{"percent":"0.9%","useragent":"Mozilla//5.0 (X11; Linux x86_64; rv:67.0) Gecko//20100101 Firefox//67.0","system":"Firefox 67.0 Linux"},' \
    '{"percent":"0.8%","useragent":"Mozilla//5.0 (Windows NT 10.0; Win64; x64) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//75.0.3770.90 Safari//537.36","system":"Chrome Generic Win10"},' \
    '{"percent":"0.8%","useragent":"Mozilla//5.0 (Windows NT 6.1; Win64; x64) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//74.0.3729.157 Safari//537.36","system":"Chrome Generic Win7"},' \
    '{"percent":"0.8%","useragent":"Mozilla//5.0 (X11; Linux x86_64) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//74.0.3729.169 Safari//537.36","system":"Chrome Generic Linux"},' \
    '{"percent":"0.7%","useragent":"Mozilla//5.0 (Windows NT 10.0; WOW64) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//74.0.3729.169 Safari//537.36","system":"Chrome Generic Win10"},' \
    '{"percent":"0.7%","useragent":"Mozilla//5.0 (Windows NT 10.0; WOW64; Trident//7.0; rv:11.0) like Gecko","system":"IE 11.0 for Desktop Win10"},' \
    '{"percent":"0.6%","useragent":"Mozilla//5.0 (Macintosh; Intel Mac OS X 10_14_5) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//74.0.3729.157 Safari//537.36","system":"Chrome Generic macOS"},' \
    '{"percent":"0.6%","useragent":"Mozilla//5.0 (Windows NT 10.0; Win64; x64) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//73.0.3683.103 Safari//537.36 OPR//60.0.3255.109","system":"Opera 60.0 Win10"},' \
    '{"percent":"0.6%","useragent":"Mozilla//5.0 (X11; Linux x86_64; rv:60.0) Gecko//20100101 Firefox//60.0","system":"Firefox 60.0 Linux"},' \
    '{"percent":"0.6%","useragent":"Mozilla//5.0 (Windows NT 6.3; Win64; x64) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//74.0.3729.169 Safari//537.36","system":"Chrome Generic Win8.1"},' \
    '{"percent":"0.6%","useragent":"Mozilla//5.0 (Macintosh; Intel Mac OS X 10.14; rv:66.0) Gecko//20100101 Firefox//66.0","system":"Firefox 66.0 macOS"},' \
    '{"percent":"0.5%","useragent":"Mozilla//5.0 (Macintosh; Intel Mac OS X 10_14_4) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//74.0.3729.157 Safari//537.36","system":"Chrome Generic macOS"},' \
    '{"percent":"0.5%","useragent":"Mozilla//5.0 (Windows NT 6.1; Win64; x64; rv:66.0) Gecko//20100101 Firefox//66.0","system":"Firefox 66.0 Win7"},' \
    '{"percent":"0.5%","useragent":"Mozilla//5.0 (Windows NT 6.1; WOW64; Trident//7.0; rv:11.0) like Gecko","system":"IE 11.0 for Desktop Win7"},' \
    '{"percent":"0.5%","useragent":"Mozilla//5.0 (X11; Ubuntu; Linux x86_64; rv:66.0) Gecko//20100101 Firefox//66.0","system":"Firefox 66.0 Linux"},' \
    '{"percent":"0.5%","useragent":"Mozilla//5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//74.0.3729.157 Safari//537.36","system":"Chrome Generic macOS"},' \
    '{"percent":"0.5%","useragent":"Mozilla//5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit//605.1.15 (KHTML, like Gecko) Version//12.1.1 Safari//605.1.15","system":"Safari Generic macOS"},' \
    '{"percent":"0.5%","useragent":"Mozilla//5.0 (X11; Linux x86_64) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//72.0.3626.109 Safari//537.36","system":"Chrome 72.0 Linux"},' \
    '{"percent":"0.5%","useragent":"Mozilla//5.0 (X11; Linux x86_64) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//74.0.3729.131 Safari//537.36","system":"Chrome Generic Linux"},' \
    '{"percent":"0.5%","useragent":"Mozilla//5.0 (Windows NT 10.0; Win64; x64) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//73.0.3683.103 Safari//537.36 OPR//60.0.3255.151","system":"Opera 60.0 Win10"},' \
    '{"percent":"0.4%","useragent":"Mozilla//5.0 (X11; Linux x86_64) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//74.0.3729.157 Safari//537.36","system":"Chrome Generic Linux"},' \
    '{"percent":"0.4%","useragent":"Mozilla//5.0 (Windows NT 10.0; WOW64) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//73.0.3683.103 YaBrowser//19.4.2.702 Yowser//2.5 Safari//537.36","system":"Yandex Browser Generic Win10"},' \
    '{"percent":"0.4%","useragent":"Mozilla//5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//74.0.3729.169 Safari//537.36","system":"Chrome Generic macOS"},' \
    '{"percent":"0.4%","useragent":"Mozilla//5.0 (Windows NT 10.0; Win64; x64) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//73.0.3683.103 Safari//537.36 OPR//60.0.3255.95","system":"Opera 60.0 Win10"},' \
    '{"percent":"0.4%","useragent":"Mozilla//5.0 (Macintosh; Intel Mac OS X 10_14_4) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//74.0.3729.131 Safari//537.36","system":"Chrome Generic macOS"},' \
    '{"percent":"0.4%","useragent":"Mozilla//5.0 (Windows NT 6.3; Win64; x64; rv:67.0) Gecko//20100101 Firefox//67.0","system":"Firefox 67.0 Win8.1"},' \
    '{"percent":"0.4%","useragent":"Mozilla//5.0 (Macintosh; Intel Mac OS X 10_14_3) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//74.0.3729.169 Safari//537.36","system":"Chrome Generic macOS"},' \
    '{"percent":"0.4%","useragent":"Mozilla//5.0 (Windows NT 6.1; WOW64) AppleWebKit//537.36 (KHTML, like Gecko) HeadlessChrome//60.0.3112.78 Safari//537.36","system":"Headless Chrome 60.0 Win7"},' \
    '{"percent":"0.4%","useragent":"Mozilla//5.0 (X11; Linux x86_64) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//75.0.3770.80 Safari//537.36","system":"Chrome Generic Linux"},' \
    '{"percent":"0.4%","useragent":"Mozilla//5.0 (X11; Linux x86_64; rv:66.0) Gecko//20100101 Firefox//66.0","system":"Firefox 66.0 Linux"},' \
    '{"percent":"0.4%","useragent":"Mozilla//5.0 (Windows NT 6.1; Win64; x64) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//75.0.3770.80 Safari//537.36","system":"Chrome Generic Win7"},' \
    '{"percent":"0.3%","useragent":"Mozilla//5.0 (Macintosh; Intel Mac OS X 10_14_5) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//75.0.3770.80 Safari//537.36","system":"Chrome Generic macOS"},' \
    '{"percent":"0.3%","useragent":"Mozilla//5.0 (Windows NT 10.0; WOW64) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//73.0.3683.103 YaBrowser//19.4.3.370 Yowser//2.5 Safari//537.36","system":"Yandex Browser Generic Win10"},' \
    '{"percent":"0.3%","useragent":"Mozilla//5.0 (Windows NT 6.1; Win64; x64) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//74.0.3729.131 Safari//537.36","system":"Chrome Generic Win7"},' \
    '{"percent":"0.3%","useragent":"Mozilla//5.0 (Windows NT 10.0; Win64; x64) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//62.0.3202.94 Safari//537.36","system":"Chrome 62.0 Win10"},' \
    '{"percent":"0.3%","useragent":"Mozilla//5.0 (Windows NT 6.1) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//74.0.3729.169 Safari//537.36","system":"Chrome Generic Win7"},' \
    '{"percent":"0.3%","useragent":"Mozilla//5.0 (Macintosh; Intel Mac OS X 10_14_3) AppleWebKit//605.1.15 (KHTML, like Gecko) Version//12.0.3 Safari//605.1.15","system":"Safari 12.0 macOS"},' \
    '{"percent":"0.3%","useragent":"Mozilla//5.0 (X11; Linux x86_64) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//73.0.3683.86 Safari//537.36","system":"Chrome 73.0 Linux"},' \
    '{"percent":"0.3%","useragent":"Mozilla//5.0 (X11; Linux x86_64) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//70.0.3538.77 Safari//537.36","system":"Chrome 70.0 Linux"},' \
    '{"percent":"0.3%","useragent":"Mozilla//5.0 (Macintosh; Intel Mac OS X 10_14_0) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//74.0.3729.169 Safari//537.36","system":"Chrome Generic macOS"},' \
    '{"percent":"0.3%","useragent":"Mozilla//5.0 (Windows NT 10.0; Win64; x64; rv:68.0) Gecko//20100101 Firefox//68.0","system":"Firefox Generic Win10"},' \
    '{"percent":"0.3%","useragent":"Mozilla//5.0 (Linux; U; Android 4.3; en-us; SM-N900T Build//JSS15J) AppleWebKit//534.30 (KHTML, like Gecko) Version//4.0 Mobile Safari//534.30","system":"Android Browser 4.0 Android"},' \
    '{"percent":"0.3%","useragent":"Mozilla//5.0 (Windows NT 10.0; Win64; x64) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//72.0.3626.121 Safari//537.36","system":"Chrome 72.0 Win10"},' \
    '{"percent":"0.3%","useragent":"Mozilla//5.0 (Windows NT 6.3; Win64; x64) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//74.0.3729.157 Safari//537.36","system":"Chrome Generic Win8.1"},' \
    '{"percent":"0.3%","useragent":"Mozilla//5.0 (Windows NT 10.0; Win64; x64) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//71.0.3578.98 Safari//537.36","system":"Chrome 71.0 Win10"},' \
    '{"percent":"0.3%","useragent":"Mozilla//5.0 (Windows NT 10.0; Win64; x64) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//73.0.3683.86 Safari//537.36","system":"Chrome 73.0 Win10"},' \
    '{"percent":"0.2%","useragent":"Mozilla//5.0 (X11; Linux x86_64) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//73.0.3683.103 Safari//537.36","system":"Chrome 73.0 Linux"},' \
    '{"percent":"0.2%","useragent":"Mozilla//5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit//605.1.15 (KHTML, like Gecko) Version//12.1 Mobile//15E148 Safari//604.1","system":"Mobile Safari Generic iOS"},' \
    '{"percent":"0.2%","useragent":"Mozilla//5.0 (Macintosh; Intel Mac OS X 10.13; rv:67.0) Gecko//20100101 Firefox//67.0","system":"Firefox 67.0 macOS"},' \
    '{"percent":"0.2%","useragent":"Mozilla//5.0 (Macintosh; Intel Mac OS X 10_14) AppleWebKit//605.1.15 (KHTML, like Gecko) Version//12.0 Safari//605.1.15","system":"Safari 12.0 macOS"},' \
    '{"percent":"0.2%","useragent":"Mozilla//5.0 (Windows NT 10.0; Win64; x64; rv:60.0) Gecko//20100101 Firefox//60.0","system":"Firefox 60.0 Win10"},' \
    '{"percent":"0.2%","useragent":"Mozilla//5.0 (Windows NT 10.0; WOW64) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//74.0.3729.169 YaBrowser//19.6.0.1574 Yowser//2.5 Safari//537.36","system":"Yandex Browser Generic Win10"},' \
    '{"percent":"0.2%","useragent":"Mozilla//5.0 (Windows NT 10.0; WOW64; rv:67.0) Gecko//20100101 Firefox//67.0","system":"Firefox 67.0 Win10"},' \
    '{"percent":"0.2%","useragent":"Mozilla//5.0 (Windows NT 6.1; Win64; x64) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//72.0.3626.121 Safari//537.36","system":"Chrome 72.0 Win7"},' \
    '{"percent":"0.2%","useragent":"Mozilla//5.0 (X11; Linux x86_64) AppleWebKit//537.36 (KHTML, like Gecko) Ubuntu Chromium//74.0.3729.169 Chrome//74.0.3729.169 Safari//537.36","system":"Chromium Generic Linux"},' \
    '{"percent":"0.2%","useragent":"Mozilla//5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//74.0.3729.169 Safari//537.36","system":"Chrome Generic MacOSX"},' \
    '{"percent":"0.2%","useragent":"Mozilla//5.0 (X11; Linux x86_64) AppleWebKit//537.36 (KHTML, like Gecko) Ubuntu Chromium//73.0.3683.86 Chrome//73.0.3683.86 Safari//537.36","system":"Chromium 73.0 Linux"},' \
    '{"percent":"0.2%","useragent":"Mozilla//5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit//605.1.15 (KHTML, like Gecko) Version//11.1.2 Safari//605.1.15","system":"Safari 11.1 MacOSX"},' \
    '{"percent":"0.2%","useragent":"Mozilla//5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit//605.1.15 (KHTML, like Gecko) Version//11.1.2 Safari//605.1.15","system":"Safari 11.1 macOS"},' \
    '{"percent":"0.2%","useragent":"Mozilla//5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit//605.1.15 (KHTML, like Gecko) Version//12.0.2 Safari//605.1.15","system":"Safari 12.0 macOS"},' \
    '{"percent":"0.2%","useragent":"Mozilla//5.0 (Macintosh; Intel Mac OS X 10_14_3) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//74.0.3729.157 Safari//537.36","system":"Chrome Generic macOS"},' \
    '{"percent":"0.2%","useragent":"Mozilla//5.0 (Windows NT 10.0; Win64; x64) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//74.0.3729.108 Safari//537.36","system":"Chrome Generic Win10"},' \
    '{"percent":"0.2%","useragent":"Mozilla//5.0 (Windows NT 6.1; Win64; x64) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//73.0.3683.103 Safari//537.36","system":"Chrome 73.0 Win7"},' \
    '{"percent":"0.2%","useragent":"Mozilla//5.0 (Windows NT 10.0; WOW64; rv:45.0) Gecko//20100101 Firefox//45.0","system":"Firefox 45.0 Win10"},' \
    '{"percent":"0.2%","useragent":"Mozilla//5.0 (Windows NT 6.1; WOW64; rv:67.0) Gecko//20100101 Firefox//67.0","system":"Firefox 67.0 Win7"},' \
    '{"percent":"0.2%","useragent":"Mozilla//5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit//605.1.15 (KHTML, like Gecko) Version//12.1 Safari//605.1.15","system":"Safari Generic macOS"},' \
    '{"percent":"0.2%","useragent":"Mozilla//5.0 (Macintosh; Intel Mac OS X 10_14_3) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//74.0.3729.131 Safari//537.36","system":"Chrome Generic macOS"},' \
    '{"percent":"0.2%","useragent":"Mozilla//5.0 (iPad; CPU OS 12_3_1 like Mac OS X) AppleWebKit//605.1.15 (KHTML, like Gecko) Version//12.1.1 Mobile//15E148 Safari//604.1","system":"Mobile Safari Generic iOS"},' \
    '{"percent":"0.2%","useragent":"Mozilla//5.0 (Macintosh; Intel Mac OS X 10.13; rv:66.0) Gecko//20100101 Firefox//66.0","system":"Firefox 66.0 macOS"},' \
    '{"percent":"0.2%","useragent":"Mozilla//5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//74.0.3729.157 Safari//537.36","system":"Chrome Generic macOS"},' \
    '{"percent":"0.2%","useragent":"Mozilla//5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//74.0.3729.131 Safari//537.36","system":"Chrome Generic macOS"},' \
    '{"percent":"0.2%","useragent":"Mozilla//5.0 (Macintosh; Intel Mac OS X 10_14_4) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//73.0.3683.103 Safari//537.36","system":"Chrome 73.0 macOS"},' \
    '{"percent":"0.2%","useragent":"Mozilla//5.0 (Windows NT 10.0; WOW64; Trident//7.0; Touch; rv:11.0) like Gecko","system":"IE 11.0 for Tablet Win10"},' \
    '{"percent":"0.2%","useragent":"Mozilla//5.0 (X11; Fedora; Linux x86_64; rv:67.0) Gecko//20100101 Firefox//67.0","system":"Firefox 67.0 Linux"},' \
    '{"percent":"0.2%","useragent":"Mozilla//5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//74.0.3729.169 Safari//537.36","system":"Chrome Generic macOS"},' \
    '{"percent":"0.2%","useragent":"Mozilla//5.0 (Windows NT 10.0; Win64; x64) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//70.0.3538.102 Safari//537.36 Edge//18.18362","system":"Edge 18.0 Win10"},' \
    '{"percent":"0.2%","useragent":"Mozilla//5.0 (Windows NT 10.0; Win64; x64) AppleWebKit//537.36 (KHTML, like Gecko) Chrome//70.0.3538.102 Safari//537.36 Edge//18.18362","system":"Edge 18.0 Win10"}]'


def get_input(templatelogfile, cmdline):
    contents = None
    try:
        templatelogfile = templatelogfile.strip()
        for file in glob.glob(templatelogfile):
            with open(file, "r") as fp:
                contents = fp.readlines()
                fp.close()
        # do something with file
    except IOError as e:
        cmdline.error("ERROR trying to read the example log file: %s", str(e))
        exit(1)
    if not contents:
        cmdline.error("ERROR, the example access log provided is empty.")
        exit(1)
    return contents


def verify_input(options, cmdline):
    f = 0
    if options.files.isdigit():
        f = int(options.files)
        f = 0 if f < 1 or f > 1000 else f
    if f == 0:
        cmdline.error("ERROR, the number of files to generate must be between 1 and 1000.")
        exit(1)
    r = 0
    if options.records.isdigit():
        r = int(options.records)
        r = 0 if r < 1 or r > 1000000 else r
    if r == 0:
        cmdline.error("ERROR, the number of records to generate per file must be between 1 and 1000000.")
        exit(1)

    chk = datetime.datetime.now()
    try:
        x = chk.strftime(options.timeformat)
    except:
        cmdline.error("ERROR, the --timestamp format must be a valid Python strftime format. See http://strftime.com.")
        exit(1)

    start_dt = None
    try:
        start_dt = dtparser.parse(options.start_dt)
    except:
        pass
    if not start_dt:
        start_dt = datetime.datetime.combine(datetime.date.today(), datetime.datetime.min.time())
    end_dt = None
    try:
        end_dt = dtparser.parse(options.end_dt)
    except:
        pass
    if not end_dt:
        end_dt = datetime.datetime.combine(datetime.date.today() + datetime.timedelta(days=1), datetime.datetime.min.time())

    bots = options.bots.strip().upper()
    if bots:
        if bots in 'INCLUDE,I,TRUE,T,YES,Y,1':
            bots = "Y"
        elif bots in 'EXCLUDE,E,X,FALSE,F,NO,N,0':
            bots = "N"
        elif bots in 'ONLY,O':
            bots = "O"
        else:
            cmdline.error("ERROR, the --bots/-b value if specified should be one of: include,i,true,t,yes,y,1,0,exclude,e,x,false,f,no,n,0,only, or o.")
            exit(1)
    else:
        bots = "Y"

    # 1 = random
    # 2 = normal
    if options.distribution.strip().lower() == "normal":
        disttype = 2
    else:
        disttype = 1

    fmt = options.format
    assert (len(fmt) > 0)

    delim = options.delimiter.strip().lower()
    if delim in ['none', 'no', 'n', 'false', 'f', 0]:
        delim = "n"
    elif delim in ['tab', 't']:
        delim = "t"
    elif delim in ['comma', 'c']:
        delim = "c"
    elif delim not in ['cr', 'lf', 'crlf']:
        cmdline.error("ERROR, the --linedelimiter/-l value if specified should be one of: none, no, n, false, f, tab, t, comma, c, cr, lf, or crlf.")
        exit(1)

    if not options.quiet:
        if options.abort:
            print("-a specified; will halt on the first unparseable log entry found, if any.")
        else:
            print("-a not specified; unparseable log entries will be skipped.")

    return f, r, start_dt, end_dt, bots, disttype, delim


def get_outputfile(i, outputdir):
    return os.path.join(outputdir, "access.log.%d" % i if i != 0 else "access.log")


def new_outputfile(i, outputdir):
    return open(get_outputfile(i, outputdir), "w+")


def output_exists(f, outputdir):
    for i in range(0, f-1):
        fn = get_outputfile(i, outputdir)
        if os.path.exists(fn):
            return True
    return False


def verify_output(output, cmdline):
    pdir = None
    try:
        output = output.strip()
        if os.path.exists(output):
            if os.path.isfile(output):
                cmdline.error("ERROR, the output location must be a directory, not a file.")
                exit(1)
            pdir = os.path.dirname(output)
            pdir = '.' if not pdir else pdir
            if not os.access(pdir, os.W_OK):
                cmdline.error("ERROR, no write access to target directory. Check your permissions.")
                exit(1)
    except IOError as e:
        cmdline.error("ERROR checking output directory access/permissions: %s", str(e))
        exit(1)
    return pdir


def ua2struct(uastring):
    return user_agents.parse(uastring.lstrip('\"').rstrip('\"'))


def ua2structstr(uastring):
    uap = ua2struct(uastring)
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


def explode_uas():
    ualist = json.loads(uafreqlist)
    explodeduas = []
    for ua in ualist:
        n = int(float(ua['percent'].strip("%"))*10.0)
        if ua['useragent'] == "replace-with-bot":
            uad = ua['useragent']
        else:
            uad = ua2structstr(ua['useragent'])
        for i in range(n):
            explodeduas.append(uad)
    return explodeduas


def assign_ua(explodeduas):
    return explodeduas[random.randint(0, len(explodeduas)-1)]


def parse_log(contents, options, cmdline):

    def _get_loglineregex(fmt):
        patterns = {}
        fields = json.loads(supported_nginx_fields)
        for field in fields:
            patterns[str(field["name"]).lstrip("$")] = str(field["regex"])
        try:
            reexpr = ''.join(
                    '(?P<%s>%s)' % (g, patterns.get(g, '.*?')) if g else re.escape(c)
                    for g, c in re.findall(r'\$(\w+)|(.)', fmt))
            return re.compile(reexpr)
        except:
            cmdline.error("ERROR, incorrect, incomplete, or unsupported Format (-f) value provided.")
            exit(1)

    def _parse_logline(line, lineno, rgxpat, strict):

        def _ts_to_dts(ts):
            try:
                dts = str(datetime.datetime(int(ts[7:11]), MONTHS[ts[3:6]], int(ts[0:2]), int(ts[12:14]), int(ts[15:17]), int(ts[18:20])))
            except:
                dts = None
            return dts

        m = None
        line = line.rstrip()
        try:
            m = rgxpat.match(line)
        except Exception as e:
            if strict:
                cmdline.error("Halting on line %d (--strict specified): %s." % (lineno, str(e)))
                exit(1)
            print("Skipping unparseable line %d: %s..." % (lineno, str(e)))
            pass
        if m:
            dikt = m.groupdict()
            if "time_local" in dikt.keys():
                dikt["_ts"] = _ts_to_dts(dikt["time_local"])
            return dikt
        else:
            return None

    totread = 0
    totok = 0
    parsed = []
    earliest_ts = None
    latest_ts = None
    botlist = []
    lineregex = _get_loglineregex(options.format)

    for entry in contents:

        totread += 1
        parsed_line = _parse_logline(entry, totread, lineregex, options.abort)
        if not parsed_line:
            continue
        totok += 1

        keys = parsed_line.keys()

        if "_ts" in keys:
            if earliest_ts:
                if parsed_line["_ts"] < earliest_ts:
                    earliest_ts = parsed_line["_ts"]
            else:
                earliest_ts = parsed_line["_ts"]
            if latest_ts:
                if parsed_line["_ts"] > latest_ts:
                    latest_ts = parsed_line["_ts"]
            else:
                latest_ts = parsed_line["_ts"]

        if 'http_user_agent' in keys:
            parsed_line["_ua"] = ua2struct(parsed_line["http_user_agent"])
            if parsed_line["_ua"].is_bot:
                botlist.append(parsed_line["http_user_agent"])
                parsed_line["_isbot"] = True
            else:
                parsed_line["_isbot"] = False

        if 'remote_addr' in keys:
            parsed_line["_ip"] = ipaddress.ip_address(parsed_line["remote_addr"])

        parsed.append(parsed_line)

        if not options.quiet:
            if totread % 100 == 0:
                print('Parsed %d entries...' % totread)

    if not earliest_ts and not latest_ts:
        cmdline.error("ERROR, no timestamps found in the provided log file. Timestamps are required.")
        exit(0)

    return parsed, totread, totok, earliest_ts, latest_ts, botlist


def make_distribution(disttype, f, r, start_dt, end_dt):
    seconds = int((end_dt - start_dt).total_seconds())
    midpoint = round(seconds / 2.0) if disttype == 2 else None
    totwrite = f * r
    aps = totwrite / seconds
    if disttype == 2:
        # normal distribution with a bit of randomization
        normal_distribution = np.random.normal(midpoint, 0.1666 * seconds, totwrite)
        time_distribution = [start_dt + datetime.timedelta(seconds=int(val))
                             if 0.00 <= val <= seconds
                             else start_dt + datetime.timedelta(seconds=random.randint(0, seconds))
                             for val in normal_distribution]
    else:
        # random dist
        time_distribution = [start_dt + datetime.timedelta(seconds=int(val)) for val in np.random.randint(seconds, size=totwrite)]
    time_distribution.sort()  # chronological order
    return totwrite, time_distribution, aps


def make_uas(botlist):
    d = {}
    uas = explode_uas()
    bs = len(botlist) - 1
    if bs >= 0:
        for i in range(0, len(uas) - 1):
            if uas[i] == "replace-with-bot":
                d[i] = ua2struct(botlist[random.randint(0, bs)])
            else:
                d[i] = ua2struct(uas[i])
    return d


def obsfucate_ip(entry):
    ipvXaddress = entry["_ip"]
    isbot = entry["_isbot"]
    # we don't obfuscate any of these
    if ipvXaddress.is_link_local \
            or ipvXaddress.is_loopback \
            or ipvXaddress.is_multicast \
            or ipvXaddress.is_private \
            or ipvXaddress.is_reserved \
            or isbot:
        newip = ipvXaddress
    else:
        # minimal obfuscation to maximally preserve general geolocation, residential vs commercial, etc.
        # no guarantees here; may improve on this or rethink it in a future version
        newip = None
        while not newip:
            if ipvXaddress.version == 4:
                newip = "%s.%s" % (str(ipvXaddress).rsplit(".", 1)[0], str(random.randint(1, 255)))
            else:
                newip = "%s:%s" % (str(ipvXaddress).rsplit(":", 1)[0], ''.join(random.choice(string.digits+"abcdef") for i in range(4)))
            # is it a valid global ip?
            try:
                chk = ipaddress.ip_address(newip)
                if chk.is_link_local \
                        or chk.is_multicast \
                        or chk.is_loopback \
                        or chk.is_private \
                        or chk.is_reserved :
                    newip = None
            except:
                newip = None
                pass
    return str(newip)


def obfuscate_ua(entry, uas):
    entry_browser = entry["_ua"].browser.family
    entry_device = entry["_ua"].device.family
    entry_os = entry["_ua"].os.family
    entry_is_bot = entry["_isbot"]
    hits = [uas[x] for x in uas
            if uas[x].browser.family == entry_browser
            and uas[x].device.family == entry_device
            and uas[x].os.family == entry_os
            and uas[x].is_bot == entry_is_bot]
    h = len(hits)
    return str(hits[random.randint(0, h - 1)] if h > 0 else entry["_ua"])


def generate_entry(timestamp, parsed, uas, options):
    # pick a random parsed entry from the previously generated distribution
    random_entry = parsed[random.randint(0, len(parsed)-1)]
    # ip obsfucation
    ip = obsfucate_ip(random_entry)
    # ua obfuscation
    ua = obfuscate_ua(random_entry, uas)
    # format the timestamp back to desired nginx $time_local format
    ts = options.timeformat+" "+options.timezone
    ts = timestamp.strftime(ts.rstrip())
    # return the log string
    return options.format.\
        replace("$time_local", ts).\
        replace("$remote_addr", ip).\
        replace("$http_user_agent", ua).\
        replace("$remote_user", random_entry["remote_user"]).\
        replace("$request", random_entry["request"]).\
        replace("$status", random_entry["status"]).\
        replace("$body_bytes_sent", random_entry["body_bytes_sent"]).\
        replace("$http_referer", random_entry["http_referer"])


def main():
    # command-line parsing
    cmdline = OptionParser(usage="usage: %prog [options] examplelogfile outputdirectory",
                           description="Create one or more Nginx access.log(.#) file(s) from a single real-world example access.log file.")
    cmdline.add_option("-a",
                       action="store_true",
                       dest="abort",
                       help="If specified, abort on the first (meaning, 'any and every') non-parsable log line found. "
                            "If not specified (the default), skip all non-parsable log lines but process the rest of the entries.")
    cmdline.add_option("-b", "--bots",
                       action="store",
                       dest="bots",
                       default="include",
                       help="include,i,true,t,yes,y,1=include bot useragents; exclude,e,x,false,f,no,n,0=exclude bot user agents; only,o=ONLY include bot user agents. Default=include.")
    cmdline.add_option("-d", "--distribution",
                       action="store",
                       dest="distribution",
                       default="normal",
                       help="Specifies the distribution of the generated fake log data between the start and end dates, one of: random (distribute log entries randomly between start and end dates), normal (distribute using a normal distribution with the peak in the middle of the start/end range). Default=normal.")
    cmdline.add_option("-e", "--end",
                      action="store",
                      dest="end_dt",
                      help='Latest datetime YYYY-MM-DD HH24:MI:SS to provide in the generated log files. Defaults to midnight tomorrow.' )
    cmdline.add_option("-f", "--format",
                      action="store",
                      dest="format",
                      default='$remote_addr - $remote_user [$time_local] \"$request\" $status $body_bytes_sent \"$http_referer\" \"$http_user_agent\"',
                      help='Format of the long entry line. Default is: \'$remote_addr - $remote_user [$time_local] \"$request\" $status $body_bytes_sent \"$http_referer\" \"$http_user_agent\"\'', )
    cmdline.add_option("-k",
                      action="store_true",
                      dest="quote",
                      help="If specified, add single quotes to the beginning and end of every generated log entry line. Default=no quotes added.", )
    cmdline.add_option("-l", "--linedelimiter",
                      action="store",
                      dest="delimiter",
                      default='crlf',
                      help="Line delimiter to append to all generated log entries, one of: [none, no, false, n, f], [comma, c], [tab, t], cr, lf, or crlf. Default=crlf.", )
    cmdline.add_option("-n", "--numfiles",
                      action="store",
                      dest="files",
                      default="1",
                      help="Number of access.log(.#) file(s) to output. Default=1, min=1, max=1000. Example: '-n 4' creates access.log, access.log.1, access.log.2, and access.log.3 in the output directory.", )
    cmdline.add_option("-o",
                       action="store_true",
                       dest="overwrite",
                       help="If specified, delete any generated log files if they already exist. "
                            "If not specified (the default), exit with an error if any log file to be generated already exists.")
    cmdline.add_option("-q",
                       action="store_true",
                       dest="quiet",
                       help="Basho-like stdout. Default=Proust-like stdout.")
    cmdline.add_option("-r", "--records",
                      action="store",
                      dest="records",
                      default="10000",
                      help="Number of records (entries) to create per generated access.log(.#) file. Default=10000, min=1, max=1000000.", )
    cmdline.add_option("-s", "--start",
                      action="store",
                      dest="start_dt",
                      help='Earliest datetime YYYY-MM-DD HH24:MI:SS to provide in the generated log files. Defaults to midnight today.' )
    cmdline.add_option("-t", "--timeformat",
                      action="store",
                      dest="timeformat",
                      default="%-d/%b/%Y:%H:%M:%S",
                      help="Timestamp format to use in the generated log file(s), EXCLUDING TIMEZONE (see -z parameter), in Python strftime format (see http://strftime.org/). Default='%-d/%b/%Y:%H:%M:%S'", )
    cmdline.add_option("-v",
                       action="store_true",
                       dest="version",
                       help="Print version and exit.")
    tz = datetime.datetime.now(timezone.utc).astimezone().strftime('%z')
    cmdline.add_option("-z", "--timezone",
                      action="store",
                      dest="timezone",
                      default=tz,
                      help="Timezone offset in (+/-)HHMM format to append to timestamps in the generated log file(s), or pass '' to specify no timezone. Default=your current timezone (%s)." % tz, )


    options, args = cmdline.parse_args()

    print("FLAN v", __version__)
    if options.version:
        sys.exit(0)

    try:
        assert (args[0] and args[1])
        assert (len(args[0]) > 0 and len(args[1]) > 0)
    except:
        cmdline.error("ERROR, please provide an example logfile to read, and a destination output directory to write access logs to.")
        exit(1)

    #
    # check provided options and arguments and perform quality/sanity checks
    #

    contents = get_input(args[0], cmdline)
    outputdir = verify_output(args[1], cmdline)
    totfiles, totperfile, start_dt, end_dt, bots, disttype, delim = verify_input(options, cmdline)
    if not options.overwrite:
        if output_exists(totfiles, outputdir):
            cmdline.error("ERROR, --overwrite was not specified, and one or more target file(s) exist. Halting.")
            exit(1)
    if not options.quiet:
        print("%d lines read from %s." % (len(contents), args[0].strip()))

    #
    # Parse-and-store
    #

    parsed, totread, totok, earliest_ts, latest_ts, botlist = parse_log(contents, options, cmdline)

    #
    # Build the time slice distribution to attribute fake log entries to
    #

    tot2write, time_distribution, aps = make_distribution(disttype, totfiles, totperfile, start_dt, end_dt)

    #
    # Populate ua list with frequency-appropriate selection of bots actually seen in the example log file provided
    #

    uas = make_uas(botlist)

    if not options.quiet:
        print('Parsed and prepped a total of %d entries (%d successfully, %d skipped).' % (totread, totok, totread - totok))

    #
    # Generate the requested fake logs from what we have
    #

    delim = '' if delim == 'n' \
        else '\t' if delim == 't' \
        else ',' if delim == 'c' \
        else '\r' if delim == 'cr' \
        else '\n' if delim == 'lf' \
        else '\r\n'
    totfiles = totfiles - 1
    totthisfile = 0
    totwritten = 0
    i = 0
    log = None
    timespan = []
    while totwritten < tot2write:
        if not log:
            log = new_outputfile(totfiles, outputdir)
            if not options.quiet:
                print('Beginning write of fake entries to log %s.' % log.name)
            # pop the last r timestamps from the timestamp distribution and use them on the current log file
            timespan = time_distribution[-totperfile:]
            time_distribution = time_distribution[:-totperfile]
            i = 0
        if options.quote:
            log.write("'%s'%s" % (generate_entry(timespan[i], parsed, uas, options), delim))
        else:
            log.write("%s%s" % (generate_entry(timespan[i], parsed, uas, options), delim))
        totthisfile += 1
        totwritten += 1
        i += 1
        if not options.quiet:
            if totthisfile % 100 == 0:
                print('Wrote %d entries...' % totthisfile)
        if totthisfile > totperfile:
            if not options.quiet:
                print('Log %s completed.' % log.name)
            log.close()
            log = None
            totfiles -= 1
            totthisfile = 0

    if log:
        if not log.closed:
            log.close()
        if not options.quiet:
            print('Log %s completed.' % log.name)

    if not options.quiet:
        print('Log generation completed.')
        print('Total of %d record(s) parsed successfully.' % totok)
        print('Total of %d record(s) written successfully.' % totwritten)

    exit(0)


if __name__ == "__main__":
    main()

