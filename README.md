# sd-py
Schedules Direct JSON and XMLTV Python API

Call [Schedules Direct](https://schedulesdirect.org/) JSON [API](../../../../SchedulesDirect/JSON-Service/wiki/API-20141201) 
and convert the retrieved schedules and programs to an [XMLTV](../../../../XMLTV/xmltv/blob/master/xmltv.dtd) EPG file.

See the code and the Schedules Direct API [documentation](../../../../SchedulesDirect/JSON-Service/wiki/API-20141201) for a 
list of API calls.

There is a launchd.plist that creates a new XMLTV EPG file every week, and loads it into [EyeTV](../../../etv-comskip).

## Usage

Command line:
```
./sd_json.py -u USERNAME -p PASSWORD_SHA1 -l LINEUP
```

The creates the file `xmltv.xml`.

Python API:
```python
from sd_json import SD_JSON

sd = SD_JSON(api_call="xmltv")
```

Help string:
```
sd_json.py --help
```

```
usage: sd_json.py [-h] [-U SD_URL] [-u USERNAME] [-p PASSWORD_SHA1]
                  [-c COUNTRY] [-z POSTALCODE] [-l LINEUP] [-H HEADERS] [-M]
                  [-T TIMEDELTA_DAYS] [-q] [-v] [-g] [-A API_CALL]
                  [-S SERVICE] [-X XMLTV_FILE]

optional arguments:
  -h, --help            show this help message and exit
  -U SD_URL, --sd-url SD_URL
                        Schedules Direct URL (no trailing '/')
  -u USERNAME, --username USERNAME
                        Schedules Direct username
  -p PASSWORD_SHA1, --password-sha1 PASSWORD_SHA1
                        Schedules Direct SHA1-hashed password
  -c COUNTRY, --country COUNTRY
                        3-character country code
  -z POSTALCODE, --postalcode POSTALCODE
                        Postal Code
  -l LINEUP, --lineup LINEUP
                        Lineup Code
  -H HEADERS, --headers HEADERS
                        HTTP Headers
  -M, --verboseMap      verboseMap off
  -T TIMEDELTA_DAYS, --timedelta-days TIMEDELTA_DAYS
                        Number of days retrieved
  -q, --quiet           Quiet on
  -v, --verbose         Verbose on
  -g, --debug           Debug on
  -A API_CALL, --api-call API_CALL
                        Schedules Direct API Call
  -S SERVICE, --service SERVICE
                        Schedules Direct Service name
  -X XMLTV_FILE, --xmltv-file XMLTV_FILE
                        XMLtv file name
```

## Dependencies / Configuration / Install ([MacPorts](https://www.macports.org))

Dependencies:
```
sudo port install python37 py37-pip
sudo port select --set python3 python37
sudo port select --set pip pip37
sudo -EH pip install tzlocal
```

Configuration:

Create an account at [Schedules Direct](https://schedulesdirect.org/).

```
echo "PASSWORD" | openssl sha1
sd_json.py -u USERNAME -p PASSWORD_SHA1 -c USA -z 02138 -A headends -v | less
nano com.github.essandess.sd-py.plist
```

Edit in your username, the SHA1 hash of your Schedules Direct password, and your lineup to this launch daemon.

Install:
```
mkdir ~/bin
install -m 755 sd_json.py ~/bin
install -m 600 com.github.essandess.sd-py.plist ~/Library/LaunchAgents
launchctl load -w ~/Library/LaunchAgents/com.github.essandess.sd-py.plist
launchctl start com.github.essandess.sd-py
```
