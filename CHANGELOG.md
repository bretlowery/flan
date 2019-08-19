### CHANGELOG

#### v0.0.37 "What's It All About"
Added additional IP obfuscation options to -m parameter<br>
Better memory utilization on template import


#### v0.0.36 "Orchestrion"
Export to AWS SQS


#### v0.0.35 no name!
Deleted version


#### v0.0.34 "Tokyo Day Trip"
Updated readme for pip distro


#### v0.0.33 "Day Trip"
100X+ speed improvement when importing from Splunk


#### v0.0.32 ".../Mehldau Quartet"
Support Splunk as an alternative input source to files


#### v0.0.31 ".../Mehldau"
Performance enhancements and bug fixes


#### v0.0.30 "Selected Recordings :rarum IX"
Refactored "Integrations" into separate Import and Export code and configs
Changed -i parameter to -f to repurpose -i for something else in a later version


#### v0.0.29 "One Quiet Night"
FluentD integration


#### v0.0.28 "Upojenie"
Support SSL connections for Stomp-compliant MQs 


#### v0.0.27 "Trio->Live"
ActiveMQ, Amazon MQ, other STOMP-compliant queue integration


#### v0.0.26 "Trio 99->00"
Stable Splunk and Kafka integrations


#### v0.0.25 "A Map Of The World"
Improved timeout and exception handling when pub/sub integration sinks are not responsive


#### v0.0.24 "Jim Hall & ..."
Refactored settings and integrations; Avro output support


#### v0.0.23 "Like Minds"
YAML-based configs


#### v0.0.22 "Blue Break Beats Vol. 4"
Splunk and Kafka integrations


#### v0.0.21 "Quartet"
Kafka integration ALPHA
Support JSON output
Replace -f with --inputformat & --outputformat


#### v0.0.20 "Beyond The Missouri Sky"
Stable release


#### v0.0.19 "The Sign Of 4"
Div by zero bug fix when using -p


#### v0.0.18 "Passaggio Per Il Paradiso"
Service/daemon mode available


#### v0.0.17 "The Man From Ipanema"
Performance and memory usage enhancements to streaming, time distribution and log file generation


#### v0.0.16 "Blues For Pat: Live in SF"
Pacing (clock synchronization) 


#### v0.0.15 "I Can See Your House From Here"
Initial continuous streaming release w/out throttling or pacing


#### v0.0.14 "Zero Tolerance For Silence"
Renamed --stats to --meta; added meta info; emit meta in JSON format if both -o and --meta specified; additional unit tests


#### v0.0.13 "Secret Story"
More unit tests


#### v0.0.12 "Flower Hour (BOOTLEG!)"
Bug fixes and initial unit tests


#### v0.0.11 "Question And Answer"
Replace deprecated OptionParser with argparse


#### v0.0.10 "Works II"
Allow multiple, chronologically-sequential template logs as input, for long-range session preservation.


#### v0.0.9 "Song X"
setup.py install supported.


#### v0.0.8 "Rejoicing"
--stats flag added.


#### v0.0.7 "Works"
Added gzip support.


#### v0.0.6 "As Falls Wichita, So Falls Wichita Falls"
Refactored into classes; added "none" option to -m flag (IP obfuscation) to allow non-obfuscated IPs.


#### v0.0.5 "80/81"
Option to stream log generation to stdout.


#### v0.0.4 "New Chautauqua"
Replay logs.


#### v0.0.3 "Watercolors"
Full session preservation support via the -p and -m parameters (see below).


#### v0.0.2 "Bright Size Life"
Partial preservation and/or generation of user "sessions" (in the context of an access.log, really just the clustering of repeated, order-significant IP/UA combos following a semantically sound series of request paths) in the generated logs via the -m onetoone setting.


#### v0.0.1 "Jaco (BOOTLEG!)"
Including bots not in the template log from a list of bots commonly seen in the wild by frequency commonly seen via the user-agent.json file and appropriate -b and -u parameter settings.

