### UCSC Grade Notifier
A simple Python 3 script to login to MyUCSC student portal and check if new grades are posted or old grades are updated. SMS notifications delievered through the Twilio SMS API. Input your own Twilio API keys in the twilio.yaml file. 

# Usage:
```$ python3 grades.py CruzID GoldPass PhoneNum TermID [--no-texts]```

## Required:
CruzID    = UCSC Cruz ID for Ecommons <br/>
GoldPass  = UCSC Gold Password for Ecommons <br/>
PhoneNum  = Mobile phone number to receive texts <br/>
TermID    = Term ID to check grades for (2152, 2154, 2156, ...) <br/>

## Optional: 
--no-texts: Turn off text message notifications 

## Run checker on an interval
- Create linux virtual machine (such as Ubuntu 16.04LTS on DigitalOcean)
- Install requirements for the Python script
- Create bash script (in same directory) to run script and then wait an interval (30 mins)
- Install supervisord
- Create new supervisor watcher

## Bash script (commands.sh):
```
#!/bin/bash
python3.5 grades.py 'CruzId' 'Password' '+15555555555' 2170;
sleep 30m;
```

## Supervisor config (/etc/supervisor/conf.d/utility.conf):
```
[program:utility]
directory = /root/Python
command = bash commands.sh
stdout_logfile = /var/log/grades-stdout.log
stdout_logfile_maxbytes = 1GB
stdout_logfile_backups = 1
stderr_logfile = /var/log/grades-stderr.log
stderr_logfile_maxbytes = 1GB
stderr_logfile_backups = 1
autostart = true
autorestart = true
```
