## FLAN: Fake (Access) Logs for Apache or NGINX

FLAN is a Python 3.x utility that creates one or more fake Apache or NGINX log files with fake entries based on a real-world "template" access.log file that you provide it.


### Feature Highlights

1. It's fast, with speed enhancements like replay ability;
2. It's real, generating its data in part from an example "template" log file you provide and using valid IPs and user agent combos that make sense;
3. You can optionally preserve sessions and session semantics while obfuscating their original source;
4. Use different traffic distributions in your generated files: normal (bell curve), even (random), etc. between start and end dates you specify;
5. You can include bot traffic, or not;
6. You can include only bots that actually appear in your provided template log file, bots that occur in the wild (in the proportions they actually occur in), both, or no bots at all;
7. You can include only user agents found in your template file, user agents that are common in the wild (in the proportions they actually occur in), or both;
8. Supports and obfuscates both IPv4 and IPv6, using intelligent rules that guarantee valid global IPs while maintaining non-global IPs like loopback and private networks as-is without obfuscation;
9. Write to files, or stream results to stdout;
10. Optionally gzip any or all generated log files.

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

FLAN generates up to 1K test access.log files of up to 1M records each, per run. On my Mac, it can generate 200K records in about 30 seconds in verbose mode with basic settings (enabling session preservation with -p adds about 5x to the runtime) so it's way way fast on any ol' EC2 or GCE server including the free tier stuff.

### Generating log files semantically similar to production

To ensure your fake logs look as semantically real as your production ones, it reads a "template" access.log from a real production system that you provide (hereinafter referred to as the "template log"). It doesn't matter how many records the template log contains, but the longer it is the more realistic your generated fake logs will be. If you do NOT specify session preservation with the -p flag (described below), you can specify the number of files and records to generate, and your template log can be bigger or smaller than your generated log file(s). If you specify session preservation, your generated log files will be the same total record size as your template log file.

You can specify the number of access.log file(s) you want to generate, and the entries per file. Access logs are created using the standard suffixes access.log, access.log.1, access.log.2, etc. You can specify a start and end datetime for your log entries.

_IP addresses_<br>Global addresses in the template log are obfuscated: the last three digits (/24) of an IPv4 or the last four digits (/116) of an IPv6 are randomized. This provides minimal IP obfuscation while maximizing retention of other interesting properties in your IP addresses, like the geolocation of your users, commercial vs residential, etc. 

Non-global IPs (private, loopback, etc) are kept as-is. All generated IPs are guaranteed valid: for example, 192.168.0.0 is a network identifier and is never assigned to an interface, and 169.254.0.0/16 link-locals aren't routable, so it won't use any of those. 

The -m parameter allows you to obfuscate IPs using either a one-to-many or one-to-one mapping. One-to-many will obfuscate the same IP to one or multiple random IPs in the resulting log files. One-to-one will ensure that IP "X" is obfuscated to the same IP "Y" every time during any given run. One-to-one mappings are not preserved between runs.

_User Agents_<br>A basic bot-or-not check is made on all user agents in the template log. All user agents identified as bots are extracted and optionally replayed as-is into your generated fake logs, with their real originating IPs. 

Real-device agents are generated from a list of the top real-world user agents in the wild, weighted by frequency of occurrence, and matching the distribution of browser, os, and desktop/mobile possibilities that are found in your template log. If your template log contains only mobile Safari UAFactory, all you will see in your generated logs is mobile Safari UAFactory. If you have 70% mobile Chrome and 30% desktop all others in your template log, you will get that. 

You have the ability to control what percentage of bots vs non-bot UAFactory you get (currently, this is hard-coded to what I use, 21.9% bots and 78.1% everything else, but that's easy to change). You can optionally include bots from a list of common bots found in the supplied user-agents.json file, an d/or optionally include only those bots that are found in your template file, or you can choose to include no bots at all. The -u and -b commandline parameters control what bots if any appear. See the commandline parameter descriptions for details. 

### IP/User Agent Examples:

1. One template log entry with IP 123.4.5.6, Chromebook Mac UA is expanded to one or more generated entries with IPs in the range 123.4.5.0/24 (bc it's global) + Chromebook Mac UAFactory

2. One template log entry with IP 10.1.2.3, Linux, curl UA is expanded to one or more generated entries with IP 10.1.2.3 (bc it's private) + the same Linux curl UA

3. Googlebot stays Googlebot: same UA, IPs

### Time Distribution

You can specify the overall time distribution you want to appear in the logs, one of:

*Normal*<br>Specifies that a normal distribution of entries should be generated, centered around the midpoint time-wise between your start and end datetimes. This is the default as most real-world web access follows natural wake/sleep cycles.

*Even*<br>Specifies a random (even) distribution be used instead. You may want to use this if you are an international company and no one time zone wake/sleep cycle dominates your site/app usage patterns.

### How many records does it generate?
> If you are NOT using session preservation (-p), the total number of entries generated is equal to the -n parameter value TIMES the -r parameter value, spread in the selected distribution across the timeframe specified between the -s and -e parameter start and end datetimes.

> If you ARE using session preservation (-p), the total number of entries generated is equal to the total number in your provided template log file.

### Released Enhancements

v0.0.1<br>
Including bots not in the template log from a list of bots commonly seen in the wild by frequency commonly seen via the user-agent.json file and appropriate -b and -u parameter settings.

v0.0.2<br>
Partial preservation and/or generation of user "sessions" (in the context of an access.log, really just the clustering of repeated, order-significant IP/UA combos following a semantically sound series of request paths) in the generated logs via the -m onetoone setting.

v0.0.3<br>
Full session preservation support via the -p and -m parameters (see below).

v0.0.4<br>
Replay logs.

v0.0.5<br>
Option to stream log generation to stdout.

v0.0.6<br>
Refactored into classes; added "none" option to -m flag (IP obfuscation) to allow non-obfuscated IPs

v0.0.7<br>
Added gzip support

### Future Enhancements

Log files have complex semantics and multiple consumption possibilities. Possible future enhancements:

1. Ability to specify the generation of specific CIDRs, ASNUM blocks, IP ranges, etc.;

2. Ability to inject custom data into the user-agent field for downstream flagging/detection;

3. Support additional (and, for some use cases, better) ways to obfuscate IPs that make sense and are relatively fast;

4. Support other time distributions for specific use cases. Examples: heavy-tailed Poisson to model unlikely events/DDoS, discrete/degenerate distributions to emulate API/RESTful activity, etc. For considerations, see: 
<br/>https://en.wikipedia.org/wiki/Web_traffic 
<br/>https://www.nngroup.com/articles/traffic-log-patterns
<br/>https://en.wikipedia.org/wiki/Traffic_generation_model
<br>https://en.wikipedia.org/wiki/List_of_probability_distributions

5. Tighter integrations: Splunk, QRadar, LogRhythm, SolarWinds, LogStash/ELK, Graylog, LOGalyze, ManageEngine, FluentD, Apache Flume are a few off the top of my head.


### PRs welcome!

### Syntax and Parameters

```
flan.py [arguments] template.log outputdir
```

| Commandline Argument            | Definition                             | Default       |
| ------------------- |:---------------------------------------| ------------- |
| -a    | If specified, halt on any (i.e. the first) unparseable entries in your template log. | Skip any&all unparseable entries |
| -b,<br>--botfilter     | Iff -u is set to 'all' or 'bots', defines which bots appear in the generated log files, one of:<br><br>seen=only use bots that appear in the template log file and are identifiable as robotic;<br><br>unseen=only use bots found in the user-agents.json file (if used, this should be located in the same directory as flan.py);<br><br>all=use bots from both the template log and the user-agents.json file. | seen |
| -d,<br>--distribution | One of:<br><br>normal=use a normal distribution centered midway between start and end datetimes for the time dimension;<br><br>random=use a random ("shotgun blast") distribution. | normal |
| -e,<br>--end | Specifies the end datetime to use for the generated log entries. All log entries will have a timestamp on or before this date. | Midnight tomorrow local/server time |
| -f,<br>--format | Your Apache/NGINX log entry format string. | '$remote_addr - $remote_user [$time_local] \"$request\" $status $body_bytes_sent \"$http_referer\" \"$http_user_agent\"' |
| -g,<br>--gzip | Gzip support. Used in conjunction with the passed -n value, this specifies a file index number at which to begin gzipping generated log files. It must be between 0 and the -n value provided. For example, "-n 5 -g 3" generates log files called "access.log", "access.log.1", "access.log.2.gz", "access.log.3.gz", and "access.log.4.gz": 5 total files, the last 3 of which are gzipped. | 0; no gzipping occurs. |
| -h | Print out these options on the commandline. | |
| -i,<br>--ipfilter | If provided, this should specify one or more optional IP(s) and/or CIDR range(s) in quotes that all entries in the template log file must match in order to be used for output log generation. Only lines containing an IP that matches one or more of these will be used. Separate one or more IPs or CIDRs here by commas; for example, '--ipfilter \"123.4.5.6,145.0.0.0/16,2001:db8::/48\"'. | Use all otherwise eligible template log lines and their IPs in generating the output logs. |
| -k | If specified, add single quotes to the beginning and end of every generated log entry line. | Do not add quotes. |
| -l,<br>--linedelimiter | Line delimiter to append to all generated log entries, one of:<br><br>[None, No, False, N, F];<br>[Comma, C];<br>[Tab, T];<br>CR;<br>LF;<br>CRLF.| CRLF |
| -m,<br>--ipmapping | Defines how IPs are obfuscated, one of:<br><br>onetomany=one template log IP is mapped to one or more obfuscated IPs in the generated logs. This provides better obfuscation but destroys sessions;<br><br>onetoone=maps every template log IP to a single obfuscated IP in the generated logs, preserving sessions but providing minimal obfuscation;<br><br>none=no IP obfuscation, IPs are left as-is.<br><br>If -p (preserve sessions) is specified, this must be either "none" or "onetoone". | If -p is specified, "onetoone". If -p is not specified, "onetomany". |
| -n,<br>--numfiles | The total number of access.log files to generate. Min=1, Max=1000. Example: '-n 4' creates access.log, access.log.1, access.log.2, and access.log.3 in the output directory. | 1 |
| --nouatag | If specified, excludes the "Flan/<version#> (https://bret.guru/flan)" from the user agent values in the generated log files. | Append the Flan UA tag to all generated UAs. |
| -o | Stream mode. If specified, ignores the output directory and -n flag values, enables quiet mode (-q), and streams all output to stdout. | Output is written to file(s) in the output directory provided. |
| -p | Session preservation. If specified, preserves sessions as follows:<br><br>1. Ignores the -r setting and generates as many records as exist in the template log file;<br><br>2. Maintains the time index order of the request paths in the template log in the generated logs; <br><br>3. Maintains the UA for each IP found in the template log.<br><br>The -m ipmapping setting must be set to either "onetoone" or "none". | No session preservation. Request paths are randomly assigned throughout the generated time distribution, destroying sessions. |
| -q | Basho-like stdout. | Proust-like stdout. |
| -r,<br>--records | The number of entries to write per generated log file. Min=1, Max=1M. | 10,000 |
| -s,<br>--start | Specifies the start datetime to use for the generated log entries. All log entries will have a timestamp on or after this date. | Midnight today local/server time |
| -t,<br>--timeformat | Timestamp format to use in the generated log file(s), EXCLUDING TIMEZONE (see -z parameter), in Python strftime format (see http://strftime.org/). | '%-d/%b/%Y:%H:%M:%S' |
| -u,<br>--uafilter | Defines the kinds of user agents that will appear in the generated log files, one of: <br><br>bots=bot UAs only;<br><br> nonbots=non-bot UAs only;<br><br>all=both bot and non-bot UAs. | all |
| -v | Print version number and immediately exit. | |
| -w | If specified, overwrites any generated log file(s) that already exist. This check is made before writing anything. | Error if any already exist, leaving any & all of them unchanged. |
| -x,<br>--regex | Custom regex matching. Specifies a custom regex to use as a line-by-line filter for entries in the template log. Only lines that match the regex are included in log generation; lines that do not match are excluded. | All otherwise eligible lines in the template log file are used to generate logs. |
| -y | Replay logging. If specified, enables the replay log. Replay logging parses the template log file on first execution and stores the parsed results in a binary 'flan.replay' file located in the same directory as flan.py. On subsequent execution, Flan will load the already-parsed replay log rather than reparse the template log file, saving lots of time when reusing the same large template log repeatedly. Once created, the replay log is never overwritten or deleted; delete it manually first to recreate it on the next Flan run, if needed. If a replay log exists but -y is not specified, the replay log is ignored (neither read nor overwritten).| Do not use replay logs; parse the template log every time and ignore any existing replay log. |
| -z,<br>--timezone | Timezone offset in (+/-)HHMM format to append to timestamps in the generated log file(s), or pass '' to specify no timezone. | Your current local/server timezone. |




