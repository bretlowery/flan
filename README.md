# FLAN: Fake (Access) Logs for Apache or NGINX

FLAN is a Python 3.x utility that creates one or more fake Apache or NGINX access.log files with fake entries based on the entries from a real-world access.log file that you provide it. The name itself is actually fake: it can generate logs for anything that consumes NCSA Combined Log Format, but FLNCSACLF seems like the name of a Wonka-brand prescription nasal spray rather than a properly ascetic Github project acronym, so.

----------------------
### Feature Highlights
1. It's fast, with speed enhancements like replay ability;
2. It's real, generating its data in part from one or more example "template" log file(s) you provide and using valid IPs and user agent combos that make sense;
3. You can optionally preserve sessions and session semantics while obfuscating their original source;
4. Use different traffic distributions in your generated files: normal (bell curve), even (random), etc. between start and end dates you specify;
5. You can include bot traffic, or not;
6. You can include only bots that actually appear in your provided template log file, bots that occur in the wild (in the proportions they actually occur in), both, or no bots at all;
7. You can include only user agents found in your template file, user agents that are common in the wild (in the proportions they actually occur in), or both;
8. Supports and obfuscates both IPv4 and IPv6, using intelligent rules that guarantee valid global IPs while maintaining non-global IPs like loopback and private networks as-is without obfuscation;
9. Write to files, or stream results to stdout;
10. Optionally gzip any or all generated log files.
11. Run interactively, or as a service/daemon.
12. Completed integrations: write/stream to stdout, uncompressed files, gzip files, Splunk (text or JSON), Kafka (text, JSON or Avro). More to come...

--------------
### Background
I needed a way to test some systems that consume access.log entries in an environment where:

1. Volume/scale was  high (millions of users/sessions);
2. Production access.logs were protected with limited access for obvious reasons;
3. Logs were hard to acquire (multiple approvals required every time; long turnaround times; no direct, easy paths between production and dev/test environments, etc);
4. Logs had to be scrubbed once acquired, for (debateably) PII in the form of global IP addresses, and global IP address + HTTP user-agent combinations;
5. Some specific use cases needed to be tested in the test environment: partner, SEO, etc. traffic with certain IPs, CIDRs, and/or user-agents;
6. Some private network access on 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16 needed to be tested as-is without being changed.

and some other considerations.

I looked for solutions but they lacked. 90% generated random data, including invalid IP addresses, or user agents that didn't match a real-world distribution of user-agents, which was important for my immediate needs (fraud research). The other 10% couldn't handle my special use cases, like preservation of partner/SEO bots and private network IPs. So, I created FLAN.

FLAN generates up to 1K test access.log files of up to 1M records each, per run. On my Mac, it can generate 200K records in about 30 seconds in verbose mode with basic settings so it's way way fast on any ol' EC2 or GCE server including the free tier stuff.

---------------------------------------------------------------
### Flan generates log files semantically similar to production
To ensure your fake logs look as semantically real as your production ones, it reads one or more "template" access.logs from a real production system that you provide (hereinafter referred to as the "template logs"). It doesn't matter how many records the template logs contain, but the longer it/they are, the more realistic your generated fake logs will be. If you do NOT specify session preservation with the -p flag (described below), you can specify the number of files and records to generate, and your template log(s) can be bigger or smaller than your generated log file(s). If you specify session preservation, your generated log files will contain the same number of records as the total number of records contained in your template log file(s).

To provide more than one template log file, use wildcards; for example, "/var/logs/access.log*". Your template logs may be gzipped; if they have a ".gz" extension, FLAN will unzip them when it reads them. You can mix both non-zipped and gzipped files in your wildcard spec.

You can specify the number of access.log file(s) you want to generate, and the entries per file. Access logs are created using the standard suffixes access.log, access.log.1, access.log.2, etc. 

You can specify start and end datetimea for your generated log entries that can, but don't have to, match the dates in the template logs. There is no guarantee that entries *exactly* matching your start and end dates will be generated, however. They are just guaranteed to be between your selected dates. 

_IP addresses_<br><br>Global addresses in the template log are obfuscated: the last three digits (/24) of an IPv4 or the last four digits (/116) of an IPv6 are randomized. This provides minimal IP obfuscation while maximizing retention of other interesting properties in your IP addresses, like the geolocation of your users, commercial vs residential, etc. 

Non-global IPs (private, loopback, etc) are kept as-is. All generated IPs are guaranteed valid: for example, 192.168.0.0 is a network identifier and is never assigned to an interface, and 169.254.0.0/16 link-locals aren't routable, so it won't use any of those. 

The -m parameter allows you to obfuscate IPs using either a one-to-many or one-to-one mapping. One-to-many will obfuscate the same IP to one or multiple random IPs in the resulting log files. One-to-one will ensure that IP "X" is obfuscated to the same IP "Y" every time during any given run. One-to-one mappings are not preserved between runs.

_User Agents_<br><br>A basic bot-or-not check is made on all user agents in the template log. All user agents identified as bots are extracted and optionally replayed as-is into your generated fake logs, with their real originating IPs. 

Real-device agents are generated from a list of the top real-world user agents in the wild, weighted by frequency of occurrence, and matching the distribution of browser, os, and desktop/mobile possibilities that are found in your template log. If your template log contains only mobile Safari UAs, all you will see in your generated logs is mobile Safari UAs. If you have 70% mobile Chrome and 30% desktop all others in your template log, you will get that. 

You have the ability to control what percentage of bots vs non-bot UAs you get (currently, this is hard-coded to what I use, 21.9% bots and 78.1% everything else, but that's easy to change). You can optionally include bots from a list of common bots found in the supplied user-agents.json file, an d/or optionally include only those bots that are found in your template file, or you can choose to include no bots at all. The -u and -b commandline parameters control what bots if any appear. See the commandline parameter descriptions for details. 

--------------------------
### IP/User Agent Examples
1. One template log entry with IP 123.4.5.6, Chromebook Mac UA is expanded to one or more generated entries with IPs in the range 123.4.5.0/24 (bc it's global) + Chromebook Mac UA

2. One template log entry with IP 10.1.2.3, Linux, curl UA is expanded to one or more generated entries with IP 10.1.2.3 (bc it's private) + the same Linux curl UA

3. Googlebot stays Googlebot: same UA, IPs

----------------------
### Time Distributions 
You can specify the overall time distribution you want to appear in the logs, one of:

*Normal*<br>Specifies that a normal distribution of entries should be generated, centered around the midpoint time-wise between your start and end datetimes. This is the default as most real-world web access follows natural wake/sleep cycles.

*Even*<br>Specifies a random (even) distribution be used instead. You may want to use this if you are an international company and no one time zone wake/sleep cycle dominates your site/app usage patterns.

----------------------
### How many records does it generate?
> If you are NOT using session preservation (-p), the total number of entries generated is equal to the -n parameter value TIMES the -r parameter value, spread in the selected distribution across the timeframe specified between the -s and -e parameter start and end datetimes.

> If you ARE using session preservation (-p), the total number of entries generated is equal to the total number in your provided template log file.

----------------------
### What does it cost, resource-wise?
Memory is the main resource used by Flan. Memory consumption is primarily influenced by two factors:

1. The size of the template log file used and in particular the number of unique user agent strings within it, and;

2. The need to cache an entire time distribution period in memory to "keep the shape" of the distribution as we go. The number of seconds between -s and -e determines how much memory is used by this.

A 500K-record template log file with -n 10 -r 100000 uses less than 1GB memory on my Mac. Your results may vary. Use Flan's --profile switch to see memory consumed.

Disk usage (if you're using file mode) is highly dependent on the length of the user agents and request paths. With my test file, using -n 10 -r 1000000 I get roughly 250MB of storage per file for a total of 2.5GB total disk.

CPU cycles are mostly taken up by the hidden Bitcoin miner I've added (just kidding... Flan is not particularly CPU intensive). 

Overall runtime is dependent on the time range between your start and end dates, the size of your template log, and the total number of records you are generating. Larger template logs create more accurate output data, but take longer to parse and in particular to go through and obfuscate all of the user agents, given that they are pretty-free-form, often-lengthy strings. Use replay mode to minimize template log parse time. Quiet mode will also reduce runtime.

I'm not currently supporting preservation of sessions across a time distribution period boundary. That would mean I'd have to keep multiple time distribution periods cached simultaneously, and that just eats memory alive. So for example, a 3-day range starting at midnight between start and end dates, using a normal distribution and session preservation, creates a "3-humped" pattern with saddles at midnight, peaks at noon, and sessions preserved within each day/hump but not spanning days/humps.

## Instructions

Flan is developed and tested on Python 3.7 (as of July 2019). It's untested on other versions. 

### Dependencies
>  numpy <br>
   python-dateutil <br>
   pyYAML <br>
   service <br>
   ua-parser <br>
   user-agents<br>
   confluent_kafka (only if using Kafka integration)<br>
   splunk-sdk (only if using Splunk integration)<br>
   

### Installation

1. Download and extract all *.py files, *requirements.txt files, and (optionally) user-agents.json to a installation directory of your choice. You don't need the tests folder or its contents if you are not running unit tests. This exercise is left to the reader.

2. (Optional) Set up a Python 3.7 virtualenv and activate it. This exercise is left to the reader.

3. Install dependency requirements. You may optionally first comment out any integration dependencies you don't need:

   `pip install -r requirements.txt`
   
4. Run setup.py:

   `python setup.py install`
   
   OPTION: if you (might) want to uninstall later, record the files created locally during install by using this command instead:
   
   `python setup.py install --record flaninstalledfiles.txt`

5. Run it:

   `flan [arguments] template.log outputdir`
   
### Uninstall

   `xargs rm -rf < flaninstalledfiles.txt`
   
### Update

Uninstall, then reinstall using the same installation instructions listed above.

-------------------------
## Syntax and Parameters

##### INTERACTIVE MODE (uses commandline arguments)

File output:

```
flan -n <number of files to write> -r <number of records per file> [arguments] templatelogspec outputdir
```
Streaming output:

```
flan -c [-o outputtarget] [--pace] [arguments] templatelogspec
```

##### SERVICE/DAEMON MODE (uses flan.config.yaml)

```
flan [ start | stop | status ]
```

##### CONTROLLING FLAN VIA ARGUMENTS AND CONFIGS

For service mode, use flan.config.yaml instead of commandline arguments. Each of its entries map one-to-one to one of the arguments below. Quiet (-q), stats (--stats), profile (--profile), and overwrite (-w) are set to fixed defaults in service mode and if set in flan.config.yaml are ignored. flan.config.yaml is ignored in interactive mode.


| Commandline Argument            | Definition                             | Default       |
| ------------------- |:---------------------------------------| ------------- |
|<span style="white-space: pre;">-a</span>| If specified, halt on any (i.e. the first) unparseable entries in your template log. | Skip any&all unparseable entries |
|<span style="white-space: pre;">-b,<br>--botfilter</span>| Iff -u is set to 'all' or 'bots', defines which bots appear in the generated log files, one of:<br><br>seen=only use bots that appear in the template log file and are identifiable as robotic;<br><br>unseen=only use bots found in the user-agents.json file (if used, this should be located in the same directory as flan.py);<br><br>all=use bots from both the template log and the user-agents.json file. | seen |
|<span style="white-space: pre;">-c</span>| ALPHA FEATURE! Continuous streaming mode. If specified, enables continuous streaming. More info here to follow on next release. | No continuous streaming |
|<span style="white-space: pre;">-d,<br>--distribution</span>| One of:<br><br>normal=use a normal distribution centered midway between start and end datetimes for the time dimension;<br><br>random=use a random ("shotgun blast") distribution. | normal |
|<span style="white-space: pre;">-e,<br>--end</span>| Specifies the end datetime to use for the generated log entries. All log entries will have a timestamp on or before this date. | Midnight tomorrow local/server time |
|<span style="white-space: pre;">-g,<br>--gzip</span>| Gzip support. Used in conjunction with the passed -n value, this specifies a file index number at which to begin gzipping generated log files. It must be between 0 and the -n value provided. For example, "-n 5 -g 3" generates log files called "access.log", "access.log.1", "access.log.2.gz", "access.log.3.gz", and "access.log.4.gz": 5 total files, the last 3 of which are gzipped. | 0; no gzipping occurs. |
|<span style="white-space: pre;">-h</span>| Print out these options on the commandline. | |
|<span style="white-space: pre;">-i,<br>--ipfilter</span>| If provided, this should specify one or more optional IP(s) and/or CIDR range(s) in quotes that all entries in the template log file must match in order to be used for output log generation. Only lines containing an IP that matches one or more of these will be used. Separate one or more IPs or CIDRs here by commas; for example, '--ipfilter \"123.4.5.6,145.0.0.0/16,2001:db8::/48\"'. | Use all otherwise eligible template log lines and their IPs in generating the output logs. |
|<span style="white-space: pre;">--inputformat</span>| The format of each line in the the template log file (a valid NCSA Combined Log Format string). | '$remote_addr - $remote_user [$time_local] \"$request\" $status $body_bytes_sent \"$http_referer\" \"$http_user_agent\"' |
|<span style="white-space: pre;">-j</span>| Continuous streaming periodicity. UNSUPPORTED AS OF v0.0.15. TBD. | N/A |
|<span style="white-space: pre;">-k</span>| If specified, add single quotes to the beginning and end of every generated log entry line. | Do not add quotes. |
|<span style="white-space: pre;">-l,<br>--linedelimiter</span>| Line delimiter to append to all generated log entries, one of:<br><br>[None, No, False, N, F];<br>[Comma, C];<br>[Tab, T];<br>CR;<br>LF;<br>CRLF.| CRLF |
|<span style="white-space: pre;">-m,<br>--ipmapping</span>| Defines how IPs are obfuscated, one of:<br><br>onetomany=one template log IP is mapped to one or more obfuscated IPs in the generated logs. This provides better obfuscation but destroys sessions;<br><br>onetoone=maps every template log IP to a single obfuscated IP in the generated logs, preserving sessions but providing minimal obfuscation;<br><br>none=no IP obfuscation, IPs are left as-is.<br><br>If -p (preserve sessions) is specified, this must be either "none" or "onetoone". | If -p is specified, "onetoone". If -p is not specified, "onetomany". |
|<span style="white-space: pre;">--meta</span>| Replaces the old --stats parameter. Collect and emit (at the end) meta data and per-hour cumulative counts on all the log entries generated. Use this to identify the source of the log files and verify the spread across your chosen distribution. | No meta is emitted. | 
|<span style="white-space: pre;">-n,<br>--numfiles</span>| The total number of access.log files to generate. Min=1, Max=1000. Example: '-n 4' creates access.log, access.log.1, access.log.2, and access.log.3 in the output directory. | 1 |
|<span style="white-space: pre;">--nouatag</span>| If specified, excludes the "Flan/<version#> (https://bret.guru/flan)" from the user agent values in the generated log files. | Append the Flan UA tag to all generated UAs. |
|<span style="white-space: pre;">-o</span>| Stream mode output target. If specified, ignores the output directory and -n flag values, enables quiet mode (-q), and streams all output to the designated target. Only stdout is currently supported. | Output is written to file(s) in the output directory provided. |
|<span style="white-space: pre;">--outputformat</span>| Format of individual emitted entries in the generated logs. A valid NCSA Combined Log Format string, or one of two special values: json=emits entries in JSON format, avro=emits JSON-encoded entries in Avro binary format. | '$remote_addr - $remote_user [$time_local] \"$request\" $status $body_bytes_sent \"$http_referer\" \"$http_user_agent\"' |
|<span style="white-space: pre;">-p</span>| Session preservation. If specified, preserves sessions as follows:<br><br>1. Ignores the -r setting and generates as many records as exist in the template log file;<br><br>2. Maintains the time index order of the request paths in the template log in the generated logs; <br><br>3. Maintains the UA for each IP found in the template log.<br><br>The -m ipmapping setting must be set to either "onetoone" or "none". | No session preservation. Request paths are randomly assigned throughout the generated time distribution, destroying sessions. |
|<span style="white-space: pre;">--pace</span>| Pacing. If specified, syncs the timestamps in the generated log records with the current clock time as log entries are generated such that log entries are emitted in apparent 'real time'. Each second in the log timestamps corresponds to a second of emission time in real time. | Default=no pacing; emit entries as fast as possible. |
|<span style="white-space: pre;">-q</span>| Basho-like stdout. | Proust-like stdout. |
|<span style="white-space: pre;">-r,<br>--records</span>| The number of entries to write per generated log file. Min=1, Max=1M. | 10,000 |
|<span style="white-space: pre;">-s,<br>--start</span>| Specifies the start datetime to use for the generated log entries. All log entries will have a timestamp on or after this date. | Midnight today local/server time |
|<span style="white-space: pre;">-t,<br>--timeformat</span>| Timestamp format to use in the generated log file(s), EXCLUDING TIMEZONE (see -z parameter), in Python strftime format (see http://strftime.org/). | '%-d/%b/%Y:%H:%M:%S' |
|<span style="white-space: pre;">-u,<br>--uafilter</span>| Defines the kinds of user agents that will appear in the generated log files, one of: <br><br>bots=bot UAs only;<br><br> nonbots=non-bot UAs only;<br><br>all=both bot and non-bot UAs. | all |
|<span style="white-space: pre;">-v</span>| Print version number and immediately exit. | |
|<span style="white-space: pre;">-w</span>| If specified, overwrites any generated log file(s) that already exist. This check is made before writing anything. | Error if any already exist, leaving any & all of them unchanged. |
|<span style="white-space: pre;">-x,<br>--regex</span>| Custom regex matching. Specifies a custom regex to use as a line-by-line filter for entries in the template log. Only lines that match the regex are included in log generation; lines that do not match are excluded. | All otherwise eligible lines in the template log file are used to generate logs. |
|<span style="white-space: pre;">-y</span>| Replay logging. If specified, enables the replay log. Replay logging parses the template log file on first execution and stores the parsed results in a binary 'flan.replay' file located in the same directory as flan.py. On subsequent execution, Flan will load the already-parsed replay log rather than reparse the template log file, saving lots of time when reusing the same large template log repeatedly. Once created, the replay log is never overwritten or deleted; delete it manually first to recreate it on the next Flan run, if needed. If a replay log exists but -y is not specified, the replay log is ignored (neither read nor overwritten).| Do not use replay logs; parse the template log every time and ignore any existing replay log. |
|<span style="white-space: pre;">-z,<br>--timezone</span>| Timezone offset in (+/-)HHMM format to append to timestamps in the generated log file(s), or pass '' to specify no timezone. | Your current local/server timezone. |

--------------------------------------------------
### Where can I get access.log files to test with?
Test log files are available in the tests folder.

Here's another resource:

https://gist.github.com/rm-hull/bd60aed44024e9986e3c

Or, just Google "example access.log files".

-----------------------
### Future Enhancements
Definitely:

1. Integrations: ActiveMQ/Amazon MQ, other AWS services (one or more of SQS, EventBridge, IoT Events), Redis Pub/Sub, FluentD, Apache Flume, RabbitMQ, Apache Pulsar, Apache Nifi are a few off the top of my head and in no particular order. I've removed some things I had on this list: Graylog, ELK, etc. as I'm not sure those are the right sinks solving the right use cases for this. If you want an integration, ask, or submit a PR.

2. Could always use tuning/refactoring. Ongoing effort. Warning: I tend to refactor every couple of releases.

Possibly:

1. Ability to specify the generation of specific CIDRs, ASNUM blocks, IP ranges, etc.;

2. Ability to inject custom data into the user-agent field for downstream flagging/detection;

3. Support additional (and, for some use cases, better) ways to obfuscate IPs that make sense and are relatively fast;

4. Support other time distributions for specific use cases. Examples: heavy-tailed Poisson to model unlikely events/DDoS, discrete/degenerate distributions to emulate API/RESTful activity, etc. For considerations, see: 
<br/>https://en.wikipedia.org/wiki/Web_traffic 
<br/>https://www.nngroup.com/articles/traffic-log-patterns
<br/>https://en.wikipedia.org/wiki/Traffic_generation_model
<br>https://en.wikipedia.org/wiki/List_of_probability_distributions

-------------
### Citations
crawler-user-agents.json Copyright (c) 2019 Martin Monperrus <br>
https://github.com/monperrus/crawler-user-agents/blob/master/crawler-user-agents.json

## PRs welcome!