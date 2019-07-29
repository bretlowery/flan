# CHANGELOG

## v0.0.20 "Beyond The Missouri Sky"
Stable release


## v0.0.19 "The Sign Of 4"
Div by zero bug fix when using -p


## v0.0.18 "Passaggio Para Il Paradiso"
Service/daemon mode available


## v0.0.17 "The Man From Ipanema"
Performance and memory usage enhancements to streaming, time distribution and log file generation


## v0.0.16 "Blues For Pat: Live in SF"
Pacing (clock synchronization) 


## v0.0.15 "I Can See Your House From Here"
Initial continuous streaming release w/out throttling or pacing


## v0.0.14 "Zero Tolerance For Silence"
Renamed --stats to --meta; added meta info; emit meta in JSON format if both -o and --meta specified; additional unit tests


## v0.0.13 "Secret Story"
More unit tests


## v0.0.12 "Flower Hour (BOOTLEG!)"
Bug fixes and initial unit tests


## v0.0.11 "Question And Answer"
Replace deprecated OptionParser with argparse


## v0.0.10 "Works II"
Allow multiple, chronologically-sequential template logs as input, for long-range session preservation.


## v0.0.9 "Song X"
setup.py install supported.


## v0.0.8 "Rejoicing"
--stats flag added.


## v0.0.7 "Works"
Added gzip support.


## v0.0.6 "As Falls Wichita, So Falls Wichita Falls"
Refactored into classes; added "none" option to -m flag (IP obfuscation) to allow non-obfuscated IPs.


## v0.0.5 "80/81"
Option to stream log generation to stdout.


## v0.0.4 "New Chautauqua"
Replay logs.


## v0.0.3 "Watercolors"
Full session preservation support via the -p and -m parameters (see below).


## v0.0.2 "Bright Size Life"
Partial preservation and/or generation of user "sessions" (in the context of an access.log, really just the clustering of repeated, order-significant IP/UA combos following a semantically sound series of request paths) in the generated logs via the -m onetoone setting.


## v0.0.1 "Jaco (BOOTLEG!)"
Including bots not in the template log from a list of bots commonly seen in the wild by frequency commonly seen via the user-agent.json file and appropriate -b and -u parameter settings.

