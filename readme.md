## FLAN: Fake (Access) Logs for Apache or NGINX

FLAN is a Python 3.x utility that creates one or more fake Apache or NGINX log files with fake entries based on a real-world "template" access.log file that you provide it.

I needed a way to test some systems that cosume access.log entries in an environment where:

1. Volume/scale was  high (millions of users/sessions);
2. Production access.logs were protected with limited access for obvious reasons;
3. Logs were hard to acquire (multiple approvals required every time; long turnaround times; no direct, easy paths between production and dev/test environments, etc);
4. Logs had to be scrubbed once acquired, for (debateably) PII in the form of global IP addresses, and global IP address + HTTP user-agent combinations;
5. Some specific use cases needed to be tested in the test environment: partner, SEO, etc. traffic with certain IPs, CIDRs, and/or user-agents;
6. Some private network access on 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16 needed to be tested as-is without being changed.

and some other considerations.

I looked for solutions but they lacked. 90% generated random data, including invalid IP addresses, or user agents that didn't match a real-world distribution of user-agents, which was important for my immediate needs (fraud research). The other 10% couldn't handle my special use cases, like preservation of partner/SEO bots and private network IPs. So, I created FLAN.

### Features

FLAN generates up to 1K test access.log files of up to 1M records each, per run. On my Mac, it can generate 200K records in about 30 seconds in verbose mode, so it's way way fast on any ol' EC2 or GCE server including the free tier stuff.

To ensure your fake logs look as semantically real as your production ones, it reads a "template" access.log from a real production system that you provide (hereinafter referred to as the "template log"). It doesn't matter how many records the template log contains, but the longer it is the more realistic your generated fake logs will be. You template log can be bigger than your generated log file(s), or vice versa.

You can specify the number of access.log file(s) you want to generate, and the entries per file. Access logs are created using the standard suffixes access.log, access.log.1, access.log.2, etc. You can specify a start and end datetime for your log entries.

_IP addresses_<br>Global addresses in the template log are obfuscated: the last three digits (/24) of an IPv4 or the last four digits (/116) of an IPv6 are randomized. This provides minimal IP obfuscation while maximizing retention of other interesting properties in your IP addresses, like the geolocation of your users, commercial vs residential, etc. 

Non-global IPs (private, loopback, etc) are kept as-is. All generated IPs are guaranteed valid: for example, 192.168.0.0 is a network identifier and is never assigned to an interface, and 169.254.0.0/16 link-locals aren't routable, so it won't use any of those. 

The -i parameter allows you to obfuscate IPs using either a one-to-many or one-to-one mapping. One-to-many will obfuscate the same IP to one or multiple random IPs in the resulting log files. One-to-one will ensure that IP "X" is obfuscated to the same IP "Y" every time during any given run. One-to-one mappings are not preserved between runs.

_User Agents_<br>A basic bot-or-not check is made on all user agents in the template log. All user agents identified as bots are extracted and optionally replayed as-is into your generated fake logs, with their real originating IPs. 

Real-device agents are generated from a list of the top real-world user agents in the wild, weighted by frequency of occurrence, and matching the distribution of browser, os, and desktop/mobile possibilities that are found in your template log. If your template log contains only mobile Safari UAs, all you will see in your generated logs is mobile Safari UAs. If you have 70% mobile Chrome and 30% desktop all others in your template log, you will get that. 

You have the ability to control what percentage of bots vs non-bot UAs you get (currently, this is hard-coded to what I use, 21.9% bots and 78.1% everything else, but that's easy to change). You can optionally include bots from a list of common bots found in the supplied user-agents.json file, an d/or optionally include only those bots that are found in your template file, or you can choose to include no bots at all. The -u and -b commandline parameters control what bots if any appear. See the commandline parameter descriptions for details. 

### IP/User Agent Examples:

1. One template log entry with IP 123.4.5.6, Chromebook Mac UA is expanded to one or more generated entries with IPs in the range 123.4.5.0/24 (bc it's global) + Chromebook Mac UAs

2. One template log entry with IP 10.1.2.3, Linux, curl UA is expanded to one or more generated entries with IP 10.1.2.3 (bc it's private) + the same Linux curl UA

3. Googlebot stays Googlebot: same UA, IPs

### Time Distribution

You can specify the overall time distribution you want to appear in the logs, one of:

*Normal*<br>Specifies that a normal distribution of entries should be generated, centered around the midpoint time-wise between your start and end datetimes. This is the default as most real-world web access follows natural wake/sleep cycles.

*Even*<br>Specifies a random (even) distribution be used instead. You may want to use this if you are an international company and no one time zone wake/sleep cycle dominates your site/app usage patterns.

### THEREFORE...
> The total number of entries generated is equal to the -n parameter value TIMES the -r parameter value, spread in the selected distribution across the timeframe specified between the -s and -e parameter start and end datetimes.

### Released Enhancements

v0.0.1
Including bots not in the template log from a list of bots commonly seen in the wild by frequency commonly seen via the user-agent.json file and appropriate -b and -u parameter settings.

v0.0.2 
Preservation and/or generation of user "sessions" (in the context of an access.log, really just the clustering of repeated, order-significant IP/UA combos following a semantically sound series of request paths) in the generated logs via the -i onetoone setting.


### Future Enhancements

Log files have complex semantics and multiple consumption possibilities. Possible future enhancements:

1. Ability to specify the generation of specific CIDRs, ASNUM blocks, IP ranges, etc.;

2. Ability to inject custom data into the user-agent field for downstream flagging/detection;

3. Support additional (and better for some use cases) ways to obfuscate IPs that make sense and are relatively fast;

4. Support other time distributions for specific use cases. Examples: heavy-tailed Poisson to model unlikely events/DDoS, discrete/degenerate distributions to emulate API/RESTful activity, etc. For considerations, see: 
<br/>https://en.wikipedia.org/wiki/Web_traffic 
<br/>https://www.nngroup.com/articles/traffic-log-patterns
<br/>https://en.wikipedia.org/wiki/Traffic_generation_model
<br>https://en.wikipedia.org/wiki/List_of_probability_distributions

### PRs welcome!

### Syntax and Parameters

```
flan.py [arguments] template.log outputdir
```

| Commandline Argument            | Definition                             | Default       |
| ------------------- |:---------------------------------------| ------------- |
| -a    | If specified, halt on any (i.e. the first) unparseable entries in your template log. | Skip any&all unparseable entries |
| -b,<br>--botfilter     | Iff -u is set to 'all' or 'bot', defines which bots appear in the generated log files, one of: seen=only use bots that appear in the template log file and are identifiable as robotic, unseen=only use bots found in the user-agents.json file (if used, this should be located in the same directory as flan.py), all=use bots from both the template log and the user-agents.json file. | seen |
| -d,<br>--distribution | Normal=use a normal distribution centered midway between start and end datetimes for the time dimension. Random=use a random ("shotgun blast") distribution. | Normal |
| -e,<br>--end | Specifies the end datetime to use for the generated log entries. All log entries will have a timestamp on or before this date. | Midnight tomorrow local/server time |
| -f,<br>--format | Your Apache/NGINX log entry format string. | '$remote_addr - $remote_user [$time_local] \"$request\" $status $body_bytes_sent \"$http_referer\" \"$http_user_agent\"' |
| -h | Print out these options on the commandline. | |
| -i,<br>--ipmapping | Defines how IPs are obfuscated, one of: onetomany=one template log IP is mapped to one or more obfuscated IPs in the generated logs; this is the most random obfuscation but destroys sessions. onetoone=maps every template log IP to a single obfuscated IP in the generated logs, preserving sessions. | onetomany |
| -k | If specified, add single quotes to the beginning and end of every generated log entry line. | Do not add quotes. |
| -l,<br>--linedelimiter | Line delimiter to append to all generated log entries, one of: [None, No, False, N, F], [Comma, C], [Tab, T], CR, LF, or CRLF.| CRLF |
| -n,<br>--numfiles | The total number of access.log files to generate. Min=1, Max=1000. Example: '-n 4' creates access.log, access.log.1, access.log.2, and access.log.3 in the output directory. | 1 |
| -o | Overwrite any generated log file(s) that already exist. This check is made before writing anything. | Error if any already exist, leaving any & all of them unchanged. |
| -q | Basho-like stdout. | Proust-like stdout. |
| -r,<br>--records | The number of entries to write per generated log file. Min=1, Max=1M. | 10,000 |
| -s,<br>--start | Specifies the start datetime to use for the generated log entries. All log entries will have a timestamp on or after this date. | Midnight today local/server time |
| -t,<br>--timeformat | Timestamp format to use in the generated log file(s), EXCLUDING TIMEZONE (see -z parameter), in Python strftime format (see http://strftime.org/). | '%-d/%b/%Y:%H:%M:%S' |
| -u,<br>--uafilter | Defines the kinds of user agents to generate in the log files, one of: bots=use bot UAs only, nonbots=use non-bot UAs only, all=use both bot and non-bot UAs. | all |
| -v | Print version number and immediately exit. | |
| -z,<br>--timezone | Timezone offset in (+/-)HHMM format to append to timestamps in the generated log file(s), or pass '' to specify no timezone. | Your current local/server timezone. |




