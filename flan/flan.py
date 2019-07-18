import os
import sys
import glob
import argparse
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
import pickle
import gzip
import collections

__version__ = "0.0.11"

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

default_format = '$remote_addr - $remote_user [$time_local] \"$request\" $status $body_bytes_sent \"$http_referer\" \"$http_user_agent\"'

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

ipmap = {}
ipmap2 = {}
replaylogfile = os.path.join(os.path.dirname(__file__), 'flan.replay')


def error(msg):
    msg = "ERROR: %s" % msg.strip()
    print(msg, file=sys.stderr)
    exit(1)

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


class DataLoader:

    def _load_templates(self, options):
        self.contents = []
        self.templatelogfiles = None
        if not options.replay or not self.replaylogfile_exists():
            try:
                # get spec of template log file(s)
                self.templatelogfiles = options.templatelogfiles.strip()
                # get each template log file's file creation date
                fd = {}
                for file in glob.glob(self.templatelogfiles):
                    cd = os.path.getctime(file)
                    fd[cd] = file
                # order the list of template log files by creation date asc (oldest first)
                fod = collections.OrderedDict(sorted(fd.items()))
                for cd, file in fod.items():
                    if file[3:].lower() == ".gz" or file[5:].lower() == ".gzip":
                        with gzip.open(file, "rb") as fp:
                            currentfile = fp.readlines()
                            fp.close()
                    else:
                        with open(file, "r") as fp:
                            currentfile = fp.readlines()
                            fp.close()
                    self.contents = self.contents + [x.strip() for x in currentfile]
                # do something with file
            except IOError as e:
                error("ERROR trying to read the template log file: %s", str(e))
            if not self.contents:
                error("the template access log provided is empty.")

    def _verify_outputdir(self, options):
        output = None
        if not options.streamout:
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
        return os.path.join(self.outputdir,
                            "access.log.%d.gz" % i if i != 0 and g > 0
                            else "access.log.gz" if i == 0 and g > 0
                            else "access.log.%d" % i if i != 0
                            else "access.log")

    def new_outputfile(self):
        out = self.get_outputfile(self.files, self.gzipindex)
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

    @staticmethod
    def replaylogfile_exists():
        return os.path.exists(replaylogfile)

    def print_stats(self):
        if self.stats and not self.streamout:
            print('Distribution Stats')
            for d in range(1, self.delta + 1):
                print('  Day %d' % d)
                for h in range(0, 24):
                    print('      Hour %d:\t%d' % (h, self.stats[d][h]))
        return

    def __init__(self, options):

        if options.streamout:
            options.quiet = True

#       if options.version or not options.quiet:
        if not options.quiet:
            print("FLAN v", __version__)
#        if options.version:
#            sys.exit(0)

        try:
            assert (options.templatelogfiles and (options.outputdir or options.streamout))
            assert (len(options.templatelogfiles) > 0 and (options.outputdir or options.streamout))
        except:
            error("please provide a/an example logfile(s) to read, and either a destination output directory to write access logs to OR specify stream output with -o.")

        #
        # handle arg 0: load either the template log file(s) or the replay log
        #

        self._load_templates(options)

        #
        # handle arg 1: verify output location
        #

        self._verify_outputdir(options)

        #
        # verify inputs
        #

        # -q
        self.quiet = options.quiet
        # -a
        self.abort = options.abort
        # -p
        self.preserve_sessions = options.preserve_sessions
        # -z
        self.timezone = options.timezone
        # -j
        self.excludeuatag = options.excludeuatag
        # -o
        self.streamout = options.streamout
        # -y
        self.replay = options.replay
        # -k
        self.quote = options.quote

        # -n
        f = 0
        if options.files:
            f = options.files
            f = 0 if f < 1 or f > 1000 else f
        if f == 0:
            error("the number of files to generate must be between 1 and 1000.")
        self.files = f

        # -g
        g = 0
        if options.gzipindex:
            g = options.gzipindex
            if g > self.files or g < 0:
                error("the gzip index must be between 0 and %d." % self.files)
            if g > 0 and options.streamout:
                error("gzip is not supported for stream output.")
        self.gzipindex = g

        # -r
        r = 0
        if options.records:
            r = options.records
            r = 0 if r < 1 or r > 1000000 else r
        if r == 0:
            error("the number of records to generate per file must be between 1 and 1000000.")
        self.records = r

        # -t
        chk = datetime.datetime.now()
        try:
            x = chk.strftime(options.timeformat)
        except:
            error("the -t/--timeformat format must be a valid Python strftime format. See http://strftime.com.")
        self.timeformat = options.timeformat

        # -s
        start_dt = None
        try:
            start_dt = dtparser.parse(options.start_dt)
        except:
            pass
        if not start_dt:
            start_dt = datetime.datetime.combine(datetime.date.today(), datetime.datetime.min.time())
        self.start_dt = start_dt

        # -e
        end_dt = None
        try:
            end_dt = dtparser.parse(options.end_dt)
        except:
            pass
        if not end_dt:
            end_dt = datetime.datetime.combine(datetime.date.today() + datetime.timedelta(days=1), datetime.datetime.min.time())
        self.end_dt = end_dt

        delta = end_dt - start_dt
        self.delta = delta.days

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

        # -f
        assert (len(options.format) > 0)
        self.format = options.format

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

        # -m
        if self.preserve_sessions:
            self.ipmapping = self._onein(options.ipmapping, ["none", "onetoone"], "onetoone")
        else:
            self.ipmapping = self._onein(options.ipmapping, ["none", "onetoone", "onetomany"], "onetomany")

        # -p
        if options.preserve_sessions:
            if self.ipmapping != "onetoone":
                error("-p (session preservation) requires that '-m onetoone' be specified as well.")

        # -x
        regx = None
        if options.regex:
            chk = options.regex.strip()
            try:
                regx = re.compile(chk)
            except:
                error("the regex string provided (-x '%s') is not a valid regex. See https://www.google.com/search?q=python+regex+cheat+sheet for help." % chk)
        self.customregex = regx

        # -i
        ipmatches = []
        if options.ipfilter:
            lst = options.ipfilter.strip().split(",")
            for chk in lst:
                try:
                    ipmatch = ipaddress.ip_network(chk) if "/" in chk else ipaddress.ip_address(chk)
                except:
                    error("one or more values in the -i parameter value provided ('%s') is neither a valid IP address or network (CIDR)." % chk)
                ipmatches.append(ipmatch)
        self.ipfilter = ipmatches

        # --stats
        if options.stats:
            # initialize the stats counters with zeros
            self.stats = {}
            for d in range(1, self.delta + 1):
                self.stats[d] = {}
                for h in range(0, 24):
                    self.stats[d][h] = 0
        else:
            self.stats = None

        # -q
        if not options.quiet:
            if options.abort:
                print("NOTE: -a specified; will halt on the first unparseable log entry found, if any.")
            else:
                print("NOTE: -a not specified; unparseable log entries will be skipped.")

        if not options.overwrite and not options.streamout:
            if self.output_exists():
                error("one or more target file(s) exist, and --overwrite was not specified.")
        if not options.quiet and not options.replay:
            print("%d lines read from %s." % (len(self.contents), options.templatelogfiles.strip()))

        return


class UAFactory:

    @staticmethod
    def _explode_uas():
        ualist = json.loads(uafreqlist)
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

    def __init__(self, data, template):
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


class TemplateManager:

    @staticmethod
    def _ts_to_dts(ts):
        try:
            dts = str(datetime.datetime(int(ts[7:11]), MONTHS[ts[3:6]], int(ts[0:2]), int(ts[12:14]), int(ts[15:17]), int(ts[18:20])))
        except:
            dts = None
        return dts

    @staticmethod
    def _load_bot_json():
        blist = []
        try:
            jf = os.path.join(os.path.dirname(__file__), 'user-agents.json')
            with open(jf) as json_file:
                uajson = json.load(json_file)
            for ua in uajson:
                if "instances" in ua:
                    if len(ua["instances"]) > 0:
                        blist = blist + ua["instances"]
        except:
            blist = None
            pass
        return blist

    def _load_replay_log(self):
        replaydata = []
        try:
            for file in glob.glob(replaylogfile):
                with open(file, "rb") as rl:
                    replaydata = pickle.load(rl)
                    rl.close()
        except:
            replaydata = []
            pass
        return replaydata

    def _save_replay_log(self, replaydata, data):
        try:
            with open(replaylogfile, "wb+") as rl:
                pickle.dump(replaydata, rl)
                rl.close()
        except Exception as e:
            error("unable to save %s: %s" % (replaylogfile, str(e)))
        return

    def _get_loglineregex(self, data):
        patterns = {}
        fields = json.loads(supported_nginx_fields)
        for field in fields:
            patterns[str(field["name"]).lstrip("$")] = str(field["regex"])
        try:
            reexpr = ''.join(
                    '(?P<%s>%s)' % (g, patterns.get(g, '.*?')) if g else re.escape(c)
                    for g, c in re.findall(r'\$(\w+)|(.)', data.format))
            return re.compile(reexpr)
        except:
            error("incorrect, incomplete, or unsupported Format (-f) value provided.")

    def _parse_logline(self, line, data):

        m = None
        line = line.rstrip()
        try:
            m = self.lineregex.match(line)
        except Exception as e:
            m = None
            pass

        if not m:
            if data.abort:
                error("Line %d is incorrectly formatted." % self.totread)
            if not data.quiet:
                print("Skipping unparseable line %d..." % self.totread)

        if data.customregex:
            m = None
            try:
                m = data.customregex.match(line)
            except Exception as e:
                pass

        if m:
            dikt = m.groupdict()
            if "time_local" in dikt.keys():
                dikt["_ts"] = self._ts_to_dts(dikt["time_local"])
            return dikt
        else:
            return None

    @staticmethod
    def _obsfucate_ip(entry, data):
        global ipmap, ipmap2
        ipvXaddress = entry["_ip"]
        isbot = entry["_isbot"]
        # we don't obfuscate any of these
        if ipvXaddress.is_link_local \
                or ipvXaddress.is_loopback \
                or ipvXaddress.is_multicast \
                or ipvXaddress.is_private \
                or ipvXaddress.is_reserved \
                or isbot \
                or data.ipmapping == "none":
            newip = str(ipvXaddress)
        else:
            # obfuscate but try to preserve general geolocation, residential vs commercial, etc.
            ipkey = str(ipvXaddress)
            # generate a new ip if using o2m or if o2o found nothing in the map
            # o2m may generate multiple obfuscated IPs from the same IP during the same run
            # o2o always generates/returns the same obfuscated IP from a given input IP during the same run
            tries = 0
            newip = ipmap[ipkey] if data.ipmapping == "onetoone" and ipkey in ipmap.keys() else None
            while not newip:
                if ipvXaddress.version == 4:
                    newip = "%s.%s" % (ipkey.rsplit(".", 1)[0], str(random.randint(0, 255)))
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
                    if data.ipmapping == "onetoone":
                        if newip in ipmap2.keys():
                            newip = None
                            tries += 1
                            if tries == 1024:
                                error("excessive number of retries during attempt to obfuscate ip %s using one-to-one method." % ipkey)
                        else:
                            ipmap[ipkey] = newip
                            ipmap2[newip] = True
        return newip

    @staticmethod
    def _obfuscate_ua(entry, data, uas):
        if data.excludeuatag:
            flantag = ""
        else:
            flantag = " Flan/%s (https://bret.guru/flan)" % __version__
        if data.preserve_sessions:
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

    def __init__(self, data):

        self.totread = 0
        self.totok = 0
        self.parsed = []
        self.botlist = []
        if data.uafilter != "nobots" and data.botfilter != "seen":
            self.botlist = self._load_bot_json()
        earliest_ts = None
        latest_ts = None

        replaying = False

        if data.replay:

            self.parsed = self._load_replay_log()
            if self.parsed:
                replaying = True
                self.totok = len(self.parsed)
                self.totread = self.totok
                if not data.quiet:
                    print('%d preparsed entries loaded from replay log.' % self.totread)

        if not replaying:

            self.lineregex = self._get_loglineregex(data)

            for entry in data.contents:

                self.totread += 1
                parsed_line = self._parse_logline(entry, data)
                if not parsed_line:
                    continue

                keys = parsed_line.keys()

                if 'http_user_agent' in keys:
                    parsed_line["_ua"] = uatostruct(parsed_line["http_user_agent"])
                    if parsed_line["_ua"].is_bot:
                        if data.botfilter != "unseen" and data.uafilter != "nobots":
                            self.botlist.append(parsed_line["http_user_agent"])
                            parsed_line["_isbot"] = True
                        else:
                            if not data.quiet:
                                print('Skipping bot [excluded by -b/-u settings] found on line %d...' % self.totread)
                            continue
                    elif data.uafilter == "bots":
                        if not data.quiet:
                            print('Skipping non-bot [excluded by -u setting] found on line %d...' % self.totread)
                        continue
                    else:
                        parsed_line["_isbot"] = False

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

                if 'remote_addr' in keys:
                    ip = parsed_line["remote_addr"]
                    if data.ipfilter:
                        chk = ipaddress.ip_address(ip)
                        found = False
                        for ipmatch in data.ipfilter:
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

                self.parsed.append(parsed_line)
                self.totok += 1

                if not data.quiet:
                    if self.totread % 100 == 0:
                        print('Parsed %d entries...' % self.totread)

        if self.totok == 0:
            error("no usable entries found in the log file provided based on passed parameter filters.")

        if not replaying and (not earliest_ts or not latest_ts):
            error("no timestamps found in the log file provided. Timestamps are required.")

        if data.replay and not replaying:
            self._save_replay_log(self.parsed, data)

        if self.botlist:
            self.botlist = list(dict.fromkeys(self.botlist))  # remove dupes
        self.parsed = self.parsed

        return

    def generate_entry(self, timedist, timeindex, data, uas):
        timestamp = timedist[timeindex]
        if data.preserve_sessions:
            # pick the next parsed entry in order, since we are preserving sessions and need to keep it in order
            entry = self.parsed[timeindex]
        else:
            # pick a random parsed entry from the previously generated distribution
            entry = self.parsed[random.randint(0, len(self.parsed) - 1)]
        # ip obsfucation
        ip = self._obsfucate_ip(entry, data)
        # ua obfuscation
        ua = self._obfuscate_ua(entry, data, uas)
        # format the timestamp back to desired nginx $time_local format
        ts = data.timeformat + " " + data.timezone
        ts = timestamp.strftime(ts.rstrip())
        # update stats
        if data.stats:
            delta = timestamp - data.start_dt
            data.stats[delta.days + 1][timestamp.hour] += 1
        # return the log string
        return data.format. \
            replace("$time_local", ts). \
            replace("$remote_addr", ip). \
            replace("$http_user_agent", ua). \
            replace("$remote_user", entry["remote_user"]). \
            replace("$request", entry["request"]). \
            replace("$status", entry["status"]). \
            replace("$body_bytes_sent", entry["body_bytes_sent"]). \
            replace("$http_referer", entry["http_referer"])


def make_distribution(data):
    seconds = int((data.end_dt - data.start_dt).total_seconds())
    midpoint = round(seconds / 2.0) if data.disttype == 2 else None
    tot2write = data.files * data.records
    aps = tot2write / seconds
    if data.disttype == 2:
        # normal distribution with a bit of randomization
        normal_distribution = np.random.normal(midpoint, 0.1866 * seconds, tot2write)
        time_distribution = [data.start_dt + datetime.timedelta(seconds=int(val))
                             if 0.00 <= val <= seconds
                             else data.start_dt + datetime.timedelta(seconds=random.randint(0, seconds))
                             for val in normal_distribution]
    else:
        # random dist
        time_distribution = [data.start_dt + datetime.timedelta(seconds=int(val)) for val in np.random.randint(seconds, size=tot2write)]
    time_distribution.sort()  # chronological order
    return tot2write, time_distribution, aps


def make_flan(options):
    # verify parameters, and load the template log file or replay log
    data = DataLoader(options)
    # parse and store the template log file data line by line
    manager = TemplateManager(data)
    # if preserving sessions, the number of generated entries must = the number in the template log
    if data.preserve_sessions:
        data.records = int(manager.totok * 1.0 / data.files)
        if not data.quiet:
            print("NOTE: -p (preserve sessions) specified. Matching template log, setting -r (the number of records per file) = %d * %d files = "
                  "%d total records will be generated." % (data.records, data.files, data.records * data.files))
    #
    # Build the time slice distribution to attribute fake log entries to
    #
    tot2write, time_distribution, aps = make_distribution(data)
    #
    # Populate ua list with frequency-appropriate selection of bots actually seen in the template log
    #
    uas = UAFactory(data, manager)
    #
    if not data.quiet:
        print('Parsed and prepped a total of %d entries (%d successfully, %d skipped).' % (manager.totread, manager.totok, manager.totread - manager.totok))
    #
    # Generate the requested fake logs!
    #
    data.files = data.files - 1
    totthisfile = 0
    totwritten = 0
    log = None
    while totwritten < tot2write:
        #
        # prewrite
        #
        if not log:
            if data.streamout:
                log = sys.stdout
                timespan = time_distribution
            else:
                log = data.new_outputfile()
                if not data.quiet:
                    print('Beginning write of fake entries to log %s.' % log.name)
                # pop the oldest r timestamps from the timestamp distribution and use them on the current log file
                timespan = time_distribution[:data.records]
                time_distribution = time_distribution[data.records:]
            i = 0
        #
        # write one entry
        #
        if data.gzipindex > 0:
            if data.quote:
                log.write(str.encode("'%s'%s" % (manager.generate_entry(timespan, i, data, uas.uas), data.delimiter)))
            else:
                log.write(str.encode("%s%s" % (manager.generate_entry(timespan, i, data, uas.uas), data.delimiter)))
        elif data.quote:
            log.write("'%s'%s" % (manager.generate_entry(timespan, i, data, uas.uas), data.delimiter))
        else:
            log.write("%s%s" % (manager.generate_entry(timespan, i, data, uas.uas), data.delimiter))
        #
        # postwrite
        #
        totthisfile += 1
        totwritten += 1
        i += 1
        if not data.quiet:
            if totthisfile % 100 == 0:
                print('Wrote %d entries...' % totthisfile)
        if not data.streamout:
            if totthisfile == data.records:
                if not data.quiet:
                    print('Log %s completed.' % log.name)
                log.close()
                log = None
                data.files -= 1
                data.gzipindex -= 1 if data.gzipindex > 0 else 0
                totthisfile = 0

    if log and not data.streamout:
        if not log.closed:
            log.close()
        if not data.quiet:
            print('Log %s completed.' % log.name)

    if not data.quiet:
        print('Total of %d record(s) written successfully from %d parsed template entries.' % (totwritten, manager.totok))
        print('Log generation completed.')
    data.print_stats()

    return


def main():
    # command-line parsing
    argz = argparse.ArgumentParser(usage="usage: %prog [options] templatelogfiles outputdirectory",
                                   description="Create one or more 'fake' Apache or Nginx access.log(.#) file(s) from a single real-world example access.log file.")
    argz.add_argument("templatelogfiles")
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
                      help='Latest datetime YYYY-MM-DD HH24:MI:SS to provide in the generated log files. Defaults to midnight tomorrow.')
    argz.add_argument("-f", "--format",
                      action="store",
                      dest="format",
                      default=default_format,
                      help='Format of the long entry line. Default is: \'$remote_addr - $remote_user [$time_local] \"$request\" '
                           '$status $body_bytes_sent \"$http_referer\" \"$http_user_agent\"\'', )
    argz.add_argument("-g", "--gzip",
                      action="store",
                      dest="gzipindex",
                      type=int,
                      default=0,
                      help='Used in conjunction with the passed -n value, this specifies a file index number at which to begin gzipping generated '
                           'log files. It must be between 0 and the -n value provided. For example, "-n 5 -g 3" generates log files called '
                           '"access.log", "access.log.1", "access.log.2.gz", "access.log.3.gz", "access.log.4.gz": 5 files, the last 3 of '
                           'which are gzipped. Default=0, no gzipping occurs.')
    argz.add_argument("-i", "--ipfilter",
                      action="store",
                      dest="ipfilter",
                      default="",
                      help="If provided, this should specify one or more optional IP(s) and/or CIDR range(s) in quotes that all entries in the template log file must "
                           "match in order to be used for output log generation. Only lines containing an IP that matches one or more of these will "
                           "be used. Separate one or more IPs or CIDRs here by commas; for example, '--ipfilter \"123.4.5.6,145.0.0.0/16,2001:db8::/48\"'. "
                           "If not provided, use all otherwise valid template log lines in generating the output logs.")
    argz.add_argument("--nouatag",
                      action="store_true",
                      dest="excludeuatag",
                      help="If specified, does not append the custom 'Flan/%s' tag to all of the user agents in the generated file(s). Default=append the tag to all UAFactory." % __version__)
    argz.add_argument("-k",
                      action="store_true",
                      dest="quote",
                      help="If specified, add single quotes to the beginning and end of every generated log entry line. Default=no quotes added.", )
    argz.add_argument("-l", "--linedelimiter",
                      action="store",
                      dest="delimiter",
                      default='crlf',
                      help="Line delimiter to append to all generated log entries, one of: [none, no, false, n, f], [comma, c], [tab, t], cr, lf, or crlf. Default=crlf.", )
    argz.add_argument("-m", "--ipmapping",
                      action="store",
                      dest="ipmapping",
                      default='onetomany',
                      help='Obfuscation rule to use for IPs, one of: onetomany=map one IPv4 to up to 255 IPv4 /24 addresses or '
                           'one IPv6 to up to 65536 IPv6 /116 addresses, onetoone=map one IPv4/IPv6 address to one IPv4/IPv6 address '
                           'within the same /24 or /116 block, off=do not obfuscate IPs. Default=onetomany.', )
    argz.add_argument("-n", "--numfiles",
                      action="store",
                      dest="files",
                      type=int,
                      default=1,
                      help="Number of access.log(.#) file(s) to output. Default=1, min=1, max=1000. Example: '-n 4' creates access.log, "
                           "access.log.1, access.log.2, and access.log.3 in the output directory.", )
    argz.add_argument("-o",
                      action="store_true",
                      dest="streamout",
                      help="If specified, ignores the output directory and -n flag values, enables quiet mode (-q), and streams all output to stdout. "
                           "If not specified (the default), output is written to file(s) in the output directory provided.")
    argz.add_argument("-p",
                      action="store_true",
                      dest="preserve_sessions",
                      help="If specified, preserve sessions (specifically, pathing order for a given IP/UA/user combo). "
                           "'-m onetoone' must also be specified for this to work."
                           "If not specified (the default), do not preserve sessions.")
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
                      default=10000,
                      help="Number of records (entries) to create per generated access.log(.#) file. Default=10000, min=1, max=1000000.", )
    argz.add_argument("-s", "--start",
                      action="store",
                      dest="start_dt",
                      help='Earliest datetime YYYY-MM-DD HH24:MI:SS to provide in the generated log files. Defaults to midnight today.')
    argz.add_argument("--stats",
                      action="store_true",
                      dest="stats",
                      help='Collect and report (at the end) per-hour cumulative counts on all the log entries generated. Use this to verify '
                           'the spread across your chosen distribution. Default=no stats generated or shown.')
    argz.add_argument("-t", "--timeformat",
                      action="store",
                      dest="timeformat",
                      default="%-d/%b/%Y:%H:%M:%S",
                      help="Timestamp format to use in the generated log file(s), EXCLUDING TIMEZONE (see -z parameter), "
                           "in Python strftime format (see http://strftime.org/). Default='%-d/%b/%Y:%H:%M:%S'", )
    argz.add_argument("-u", "--uafilter",
                      action="store",
                      dest="uafilter",
                      default="all",
                      help="Filter generate log entries by UA, one of: all=use BOTH bot and non-bot UAFactory and template "
                           "log entries with bot/non-bot UAFactory when creating the generated log entries, "
                           "bots=use ONLY bot UAFactory and template log entries with bot UAFactory when creating the generated log entries, "
                           "nobots=use ONLY non-bot UAFactory and template log entries with non-bot UAFactory when creating the generated log entries. "
                           "Default=all.")
    argz.add_argument("-v",
                      action="version",
                      version="Flan/%s" % __version__,
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
                           "the log files. TemplateManager log entries that do not match this regex are ignored. "
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
    if options.profile:
        import cProfile
        cProfile.runctx('make_flan(options)', globals(), locals())
    else:
        make_flan(options)
    exit(0)


if __name__ == "__main__":
    main()
