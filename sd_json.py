#!/usr/bin/env python3
# coding: utf-8

__author__ = 'stsmith'

# sd_json.py: Python wrapper and xmltv generator for Schedules Direct JSON API

# Copyright © 2019 Steven T. Smith <steve dot t dot smith at gmail dot com>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# Schedules Direct API documentation:
# https://github.com/SchedulesDirect/JSON-Service/wiki/API-20141201

# XMLTV documentation:
# https://github.com/XMLTV/xmltv/blob/master/xmltv.dtd

__version__ = '1.0'

__all__ = ['SD_JSON']

import argparse as ap, copy, datetime as dt, hashlib as hl, json, lxml.etree as et, \
    math, os, re, requests, string, sys, tzlocal, urllib.parse as uprs, warnings as warn

# defaults
sd_url = "https://json.schedulesdirect.org/20141201"  # no trailing '/'
username = "username"
password_sha1 =  "x"*40
country = "USA"
postalcode = "02138"
lineup = "USA-MA02317-X"
headers = {"Content-type": "application/json", "Accept": "text/plain,deflate,gzip"}
api_call = "xmltv"
verboseMap = True
timedelta_days = 15
xmltv_file = "xmltv.xml"
quiet = True
verbose = True
debug = False

sha1_regex = re.compile(r'\b[0-9a-f]{40}\b',flags=re.IGNORECASE)
def issha1(s):
    try:
        res = bool(sha1_regex.match(s))
    except:
        return False
    return res

def json_prettyprint(j,*args,**kwargs):
    print(json.dumps(j,indent=4,sort_keys=True),*args,**kwargs)

# cache programme's using a keyword with this hash name prefix
sd_md5_prefix = 'sd-md5-'
sd_md5_re = re.compile(f'^{sd_md5_prefix}')

class SD_JSON:
    """
    Schedules Direct JASON API for http://schedulesdirect.org.

    Reference: https://github.com/SchedulesDirect/JSON-Service/wiki/API-20141201
    """

    def __init__(self,
                 sd_url=sd_url,
                 username=username,
                 password_sha1=password_sha1,
                 country=country,
                 postalcode=postalcode,
                 lineup=lineup,
                 headers=headers,
                 api_call=api_call,
                 verboseMap=verboseMap,
                 timedelta_days=timedelta_days,
                 parseArgs_flag=False,
                 xmltv_file=xmltv_file,
                 quiet=quiet,
                 verbose=verbose,
                 debug=debug):
        self.sd_url = sd_url
        self.username = username
        self.password_sha1 = password_sha1
        self.country = country
        self.postalcode = postalcode
        self.lineup = lineup
        self.headers = headers
        self.api_call = api_call
        self.verboseMap = verboseMap
        self.timedelta_days = timedelta_days
        self.parseArgs_flag = parseArgs_flag
        self.xmltv_file = xmltv_file
        self.quiet = quiet
        self.verbose = verbose
        self.debug = debug
        self.return_value = 0
        self.args = self.parseArgs(parseArgs_flag)  # possibly override input arguments
        self.hash_password()
        self.resp_json = self.call_api()

    def parseArgs(self,parseArgs_flag):
        parser = ap.ArgumentParser()
        parser.add_argument('-U', '--sd-url', help="Schedules Direct URL (no trailing '/')", type=str, default=None)
        parser.add_argument('-u', '--username', help="Schedules Direct username", type=str, default=None)
        parser.add_argument('-p', '--password-sha1', help="Schedules Direct SHA1-hashed password", type=str, default=None)
        parser.add_argument('-c', '--country', help="3-character country code", type=str, default=None)
        parser.add_argument('-z', '--postalcode', help="Postal Code", type=str, default=None)
        parser.add_argument('-l', '--lineup', help="Lineup Code", type=str, default=None)
        parser.add_argument('-H', '--headers', help="HTTP Headers", type=str, default=None)
        parser.add_argument('-M', '--verboseMap', help="verboseMap off", action='store_false')
        parser.add_argument('-T', '--timedelta-days', help="Number of days retrieved", type=int, default=self.timedelta_days)
        parser.add_argument('-q', '--quiet', help="Quiet on", action='store_true')
        parser.add_argument('-v', '--verbose', help="Verbose on", action='store_true')
        parser.add_argument('-g', '--debug', help="Debug on", action='store_true')
        parser.add_argument('-A', '--api-call', help="Schedules Direct API Call", type=str, default=None)
        parser.add_argument('-S', '--service', help="Schedules Direct Service name", type=str, default=None)
        parser.add_argument('-X', '--xmltv-file', help="XMLtv file name", type=str, default=None)
        args = []
        if parseArgs_flag:
            args = parser.parse_args()
            for k in args.__dict__:
                if getattr(args, k) is not None: setattr(self, k, getattr(args, k))
            if "headers" in args.__dict__:  # load the headers string as json
                if getattr(args, "headers") is not None: setattr(self, "headers", json.loads(getattr(args, "headers")))
        return args

    def hash_password(self):
        if not issha1(self.password_sha1):
            warn.warn('Password converted to SHA1 hash. Please pass SHA1-hashed passwords.')
            self.password_sha1 = hl.sha1(self.password_sha1.encode()).hexdigest()

    def call_api(self):
        api_call_name = f'api_{self.api_call}'
        if not hasattr(self,api_call_name):
            if self.debug: print(f"No API call named '{self.api_call}'.")
            self.return_value = 1
            return
        return (getattr(self, api_call_name))()

    def api_token(self):
        sd_token_request = {"username": self.username, "password": self.password_sha1}
        if False and self.debug: json_prettyprint(sd_token_request,end='\n\n',flush=True)
        resp = requests.post(f"{self.sd_url}/token", data=json.dumps(sd_token_request))
        resp_json = None
        try:
            resp.raise_for_status()
            # assert resp.status_code < 400, f'API token response status code {resp.status_code}.'
            resp_json = resp.json()
        except Exception as e:
            print(e)
            self.return_value = 1
            return
        try:
            token = resp_json["token"]
        except Exception as e:
            warn.warn(f"Token doesn't exist. Error message:\n{e}\nScheduled Direct API JSON return:")
            json_prettyprint(uprs.urlencode(sd_token_request), end='\n\n', flush=True)
            self.return_value = 1
            return
        self.token = token
        self.api_token_data = sd_token_request
        self.api_token_json = resp_json
        return resp_json

    def api_status(self):
        @self.sd_api_token_required
        def sd_api_status():
            return requests.get(f"{self.sd_url}/status", headers=self.headers)
        resp_json = sd_api_status()
        if self.verbose: json_prettyprint(resp_json)
        self.api_status_json = resp_json
        return resp_json

    def api_available(self):
        if not hasattr(self,"service") or len(self.service) == 0:
            @self.sd_api_no_token
            def sd_api_available():
                return requests.get(f"{sd_url}/available", headers=self.headers)
        else:
            @self.sd_api_no_token
            def sd_api_available():
                return requests.get(f"{sd_url}/available/{self.service}", headers=self.headers)
        resp_json = sd_api_available()
        if self.verbose: json_prettyprint(resp_json)
        self.api_available_json = resp_json
        return resp_json

    def api_service_country(self):
        @self.sd_api_no_token
        def sd_api_service_country():
            return requests.get(f"{sd_url}/{self.service}/{self.country}", headers=self.headers)
        resp_json = sd_api_service_country()
        if self.verbose: json_prettyprint(resp_json)
        self.api_service_country_json = resp_json
        return resp_json

    def api_headends(self):
        @self.sd_api_token_required
        def sd_api_headends():
            headends_query = uprs.urlencode({"country": country, "postalcode": postalcode})
            return requests.get(f'{sd_url}/headends?{headends_query}', headers=self.headers)
        resp_json = sd_api_headends()
        if self.verbose: json_prettyprint(resp_json)
        self.api_headends_json = resp_json
        return resp_json

    def api_lineups(self):
        @self.sd_api_token_required
        def sd_api_lineups():
            return requests.get(f'{sd_url}/lineups', headers=self.headers)
        resp_json = sd_api_lineups()
        if self.verbose: json_prettyprint(resp_json)
        self.api_lineups_json = resp_json
        return resp_json

    def api_channel_mapping(self):
        @self.sd_verbose_map
        @self.sd_api_token_required
        def sd_api_channel_mapping():
            return requests.get(f'{sd_url}/lineups/{self.lineup}', headers=self.headers)
        resp_json = sd_api_channel_mapping()
        if not self.quiet or self.verbose:
            print(f'Lineup: {self.lineup}')
            print(f'\tchannels retrieved: {len(resp_json["map"])}',flush=True)
        self.api_channel_mapping_json = resp_json
        return resp_json

    def api_schedules(self,timedelta_days=timedelta_days,max_stationIDs=5000):
        """Schedules API takes a POST of:
            [ {"stationID": "20454", "date": [ "2015-03-13", "2015-03-17" ]}, …]

        The schedules for the current date to `timedelta_days` is retrieved.
        """
        @self.sd_api_token_required
        def sd_api_schedules():
            return requests.post(f'{sd_url}/schedules', data=json.dumps(sd_schedule_query), headers=self.headers)
        now = dt.datetime.now()
        dates = {"date": [ (now+dt.timedelta(days=k)).strftime("%Y-%m-%d")
            for k in range(timedelta_days) ]}
        resp_cm = self.api_channel_mapping()
        idx = 0  # block indexing through stationID's
        sd_schedule_data = [dict(stationID=sid["stationID"], **dates)
            for sid in resp_cm["map"]]
        resp_json = []
        while True:
            sd_schedule_query = sd_schedule_data[idx:idx+max_stationIDs]
            if len(sd_schedule_query) == 0: break  # no more stations
            resp_json += sd_api_schedules()  # API returns a list of dicts
            idx += max_stationIDs
        if not self.quiet or self.verbose:
            print(f'\tschedules retrieved: {len(resp_json)}',flush=True)
        self.api_schedules_data = sd_schedule_data
        self.api_schedules_json = resp_json
        return resp_json

    def api_programs(self,max_programIDs=500):
        """Programs API takes a POST of: ["EP000000060003", "EP000000510142"]"""
        @self.sd_api_token_required
        def sd_api_programs():
            return requests.post(f'{sd_url}/programs', data=json.dumps(sd_pgm_query), headers=self.headers)
        resp_sched = self.api_schedules()
        xmltv_cache = self.load_xmltv_cache()
        sd_programs_data = list(set([p["programID"] for s in resp_sched for p in s["programs"] if p["md5"] not in xmltv_cache]))
        if not self.quiet or self.verbose:
            print(f'\tprograms requested: {len(sd_programs_data)}… ',end="",flush=True)
        idx = 0  # block indexing through programID's
        resp_json = []
        while True:
            sd_pgm_query = sd_programs_data[idx:idx+max_programIDs]
            if len(sd_pgm_query) == 0: break  # no more programs
            resp_json += sd_api_programs()  # API returns a list of dicts
            idx += max_programIDs
            if not self.quiet or self.verbose:
                print('.',end="",flush=True)
        if not self.quiet or self.verbose:
            print(f'\n\tprograms retrieved: {len(resp_json)}',flush=True)
        self.api_programs_data = sd_programs_data
        self.api_programs_json = resp_json
        return resp_json

    def load_xmltv_cache(self):
        xmltv_cache = dict()
        if not os.path.isfile(self.xmltv_file): return xmltv_cache
        doc = et.parse(os.path.expanduser(self.xmltv_file))
        for child1 in [child1 for child1 in doc.getroot().iterchildren() if child1.tag == "programme"]:
            for child2 in [child2 for child2 in child1.iterchildren() if
                    child2.tag == "keyword" and bool(sd_md5_re.match(child2.text))]:
                sd_md5 = sd_md5_re.sub("", child2.text)
                if sd_md5 not in xmltv_cache:  # deepcopy the first instance
                    xmltv_cache[sd_md5] = copy.deepcopy(child1)
        self.xmltv_cache = xmltv_cache
        return xmltv_cache

    def api_xmltv(self):
        """
        Write the xmltv.xml EPG file.

        References:
            https://github.com/XMLTV/xmltv/blob/master/xmltv.dtd
            https://github.com/kgroeneveld/tv_grab_sd_json/blob/master/tv_grab_sd_json
        """
        root = et.Element("tv",
            attrib={"source-info-name": "Schedules Direct", "generator-info-name": "sd_json.py", "generator-info-url": "https://github.com/essandess/sd-py"})

        # get channel mapping, schedule, and programs
        self.api_programs()

        # channels
        stationID_map_dict = { sid["stationID"]: {"id": f'I{k}.{sid["stationID"]}.schedulesdirect.org', "channel": str(int(sid["channel"]))}
            for k, sid in enumerate(self.api_channel_mapping_json["map"]) }
        for k, stn in enumerate(self.api_channel_mapping_json["stations"]):
            channel = et.SubElement(root, "channel", attrib={"id": stationID_map_dict[stn["stationID"]]["id"]})
            # "mythtv seems to assume that the first three display-name elements are
            # name, callsign and channel number. We follow that scheme here."
            et.SubElement(channel, "display-name").text = f'{stationID_map_dict[stn["stationID"]]["channel"]} {stn["name"]}'
            et.SubElement(channel, "display-name").text = stn["callsign"]
            et.SubElement(channel, "display-name").text = stationID_map_dict[stn["stationID"]]["channel"]
            if "logo" in stn:
                icon = et.SubElement(channel, "icon",
                    attrib={"src": stn["logo"]["URL"], "width": str(stn["logo"]["width"]), "height": str(stn["logo"]["height"])})

        # programs
        if not hasattr(self,"xmltv_cache"): self.load_xmltv_cache()
        stationID_stn_dict = { stn["stationID"]: stn
            for k, stn in enumerate(self.api_channel_mapping_json["stations"]) }
        programID_dict = { pid["programID"]: k
            for k, pid in enumerate(self.api_programs_json) }
        local_timezone = tzlocal.get_localzone()
        pgmid_counts = {k: 0 for k in programID_dict}
        pgm_prec = math.ceil(math.log10(max(1,len(self.api_programs_json))))
        for sid in self.api_schedules_json:
            for sid_pgm in sid["programs"]:
                if sid_pgm["md5"] not in self.xmltv_cache \
                        and sid_pgm["programID"] not in programID_dict:
                    warn.warn("No program data for hash '{}' or program id '{}'.".format(sid_pgm["md5"],sid_pgm["programID"]))
                    continue
                attrib_lang = {"lang": stationID_stn_dict[sid["stationID"]]["broadcastLanguage"][0]} \
                    if "broadcastLanguage" in stationID_stn_dict[sid["stationID"]] \
                    else None
                # programme
                start = dt.datetime.strptime(sid_pgm["airDateTime"],"%Y-%m-%dT%H:%M:%S%z")
                stop = start + dt.timedelta(seconds=sid_pgm["duration"])
                programme_attrib = dict(
                    start=start.astimezone(local_timezone).strftime("%Y%m%d%H%M%S %z"),
                    stop=stop.astimezone(local_timezone).strftime("%Y%m%d%H%M%S %z"),
                    channel=stationID_map_dict[sid["stationID"]]["id"] )
                # grab the program from cache if it exists
                if sid_pgm["md5"] in self.xmltv_cache:
                    programme = self.xmltv_cache[sid_pgm["md5"]]
                    for ky in programme_attrib: programme.set(ky,programme_attrib[ky])
                    root.append(copy.deepcopy(programme))
                    continue
                pgm = self.api_programs_json[programID_dict[sid_pgm["programID"]]]
                programme = et.SubElement(root, "programme", attrib=programme_attrib)
                # Schedules Direct program md5 hash as keyword "sd-md5-<hash>"
                if "md5" in sid_pgm:
                    et.SubElement(programme,"keyword").text = f'{sd_md5_prefix}{sid_pgm["md5"]}'
                # title
                if "titles" in pgm:
                    for ttl in pgm["titles"]:
                        if "title120" in ttl:
                            et.SubElement(programme,"title",attrib=attrib_lang).text = ttl["title120"]
                # sub-title
                if "episodeTitle150" in pgm:
                    et.SubElement(programme, "sub-title", attrib=attrib_lang).text = pgm["episodeTitle150"]
                # desc
                if "descriptions" in pgm:
                    attrib_desc_lang = attrib_lang
                    if "description1000" in pgm["descriptions"]:
                        if "descriptionLanguage" in pgm["descriptions"]["description1000"][0]:
                            attrib_desc_lang = {"lang": pgm["descriptions"]["description1000"][0]["descriptionLanguage"]}
                        et.SubElement(programme,"desc",attrib=attrib_desc_lang).text = pgm["descriptions"]["description1000"][0]["description"]
                    elif "description100" in pgm["descriptions"]:
                        if "descriptionLanguage" in pgm["descriptions"]["description100"][0]:
                            attrib_desc_lang = {"lang": pgm["descriptions"]["description100"][0]["descriptionLanguage"]}
                        et.SubElement(programme,"desc",attrib=attrib_desc_lang).text = pgm["descriptions"]["description100"][0]["description"]
                # date
                if "movie" in pgm and "year" in pgm["movie"]:
                    et.SubElement(programme, "date").text = pgm["movie"]["year"]
                elif "originalAirDate" in pgm:
                    et.SubElement(programme, "date").text = dt.datetime.strptime(pgm["originalAirDate"],"%Y-%m-%d").strftime("%Y%m%d")
                # length
                if "duration" in pgm:
                    et.SubElement(programme,"length",attrib={"units": "seconds"}).text = str(pgm["duration"])
                elif "movie" in pgm and "duration" in pgm["movie"]:
                    et.SubElement(programme,"length",attrib={"units": "seconds"}).text = str(pgm["movie"]["duration"])
                # category
                if "genres" in pgm:
                    for gnr in pgm["genres"]:
                        et.SubElement(programme,"category",attrib=attrib_lang).text = gnr
                # episode-num
                if "metadata" in pgm and "Gracenote" in pgm["metadata"][0]:
                    et.SubElement(programme,"episode-num",attrib={"system": "xmltv_ns"}).text = self.create_episode_num(pgm["metadata"][0]["Gracenote"])
                et.SubElement(programme, "episode-num", attrib={"system": "dd_progid"}).text = f'{pgm["programID"]}.{pgmid_counts[pgm["programID"]]:0{pgm_prec}d}'
                pgmid_counts[pgm["programID"]] += 1
                # previously-shown
                if "originalAirDate" in pgm:
                    et.SubElement(programme,"previously-shown",attrib={"start": dt.datetime.strptime(pgm["originalAirDate"],"%Y-%m-%d").strftime("%Y%m%d%H%M%S")})
                # rating
                if "contentRating" in pgm:
                    for rtn in pgm["contentRating"]:
                        rating = et.SubElement(programme,"rating",attrib={"system": rtn["body"]})
                        et.SubElement(rating,"value").text = rtn["code"]
                # credits
                xmltv_roles = ["director", "actor", "writer", "adapter", "producer", "composer", "editor", "presenter", "commentator", "guest"]
                def role_to_xml(role):
                    role_normalized = re.sub(r" ","-",role.lower().translate(str.maketrans('','',string.punctuation)))
                    role_xml = None
                    for x in xmltv_roles:
                        if bool(re.match(x,role_normalized,re.IGNORECASE)):
                            role_xml = x
                            break
                    return role_xml
                credits = None
                if "cast" in pgm:
                    if credits is None: credits = et.SubElement(programme,"credits")
                    for cst in pgm["cast"]:
                        role_xml = role_to_xml(cst["role"])
                        if role_xml is not None:
                            attrib_role = None
                            if role_xml == "actor" and "characterName" in cst:
                                attrib_role = {"role": cst["characterName"]}
                            et.SubElement(credits,role_xml,attrib=attrib_role).text = cst["name"]
                if "crew" in pgm:
                    if credits is None: credits = et.SubElement(programme,"credits")
                    for crw in pgm["crew"]:
                        role_xml = role_to_xml(crw["role"])
                        if role_xml is not None:
                            et.SubElement(credits,role_xml).text = crw["name"]
                # video
                def re_any(pattern,list_of_str,*args,**kwargs):
                    return any([bool(re.match(pattern,x,*args,**kwargs)) for x in list_of_str])
                if "videoProperties" in pgm and re_any("HDTV",pgm["videoProperties"],re.IGNORECASE):
                    video = et.SubElement(programme, "video")
                    et.SubElement(video, "quality").text = "HDTV"
                # audio
                if "audioProperties" in pgm:
                    if re_any("mono",pgm["audioProperties"],re.IGNORECASE):
                        audio = et.SubElement(programme, "audio")
                        et.SubElement(audio, "stereo").text = "mono"
                    elif re_any("stereo",pgm["audioProperties"],re.IGNORECASE):
                        audio = et.SubElement(programme, "audio")
                        et.SubElement(audio, "stereo").text = "stereo"
                    elif re_any("DD",pgm["audioProperties"],re.IGNORECASE):
                        audio = et.SubElement(programme, "audio")
                        et.SubElement(audio, "stereo").text = "dolby digital"
                # subtitles
                if "audioProperties" in pgm and re_any("cc",pgm["audioProperties"],re.IGNORECASE):
                    et.SubElement(programme, "subtitles", attrib={"type": "teletext"})
                # url
                if "officialURL" in pgm:
                    et.SubElement(programme, "url").text = pgm["officialURL"]
                # premiere
                if "isPremiereOrFinale" in pgm and bool(re.match("premiere",pgm["isPremiereOrFinale"],re.IGNORECASE)):
                    et.SubElement(programme, "premiere").text = pgm["isPremiereOrFinale"]
                # new
                if "new" in pgm:
                    et.SubElement(programme, "new")
                # star-rating
                if "movie" in pgm and "qualityRating" in pgm["movie"]:
                    for qrt in pgm["movie"]["qualityRating"]:
                        star_rating = et.SubElement(programme, "star-rating")
                        et.SubElement(star_rating, "value").text = f'{qrt["rating"]}/{qrt["maxRating"]}'

        # write the XML file
        with et.xmlfile(self.xmltv_file, encoding="ISO-8859-1") as xf:
            xf.write_declaration()
            xf.write_doctype('<!DOCTYPE tv SYSTEM "xmltv.dtd">')
            xf.write(root, pretty_print=True)

        # print(et.tostring(root, pretty_print=True, xml_declaration=True, encoding="ISO-8859-1", doctype='<!DOCTYPE tv SYSTEM "xmltv.dtd">').decode())

    def create_episode_num(self,gracenote):
        """Reference: https://github.com/XMLTV/xmltv/blob/master/xmltv.dtd"""
        episode_num = ""
        if "season" in gracenote: episode_num += str(gracenote["season"]-1)
        if "totalSeasons" in gracenote: episode_num += "/" + str(gracenote["totalSeasons"])
        episode_num += "."
        if "episode" in gracenote: episode_num += str(gracenote["episode"]-1)
        if "totalEpisodes" in gracenote: episode_num += "/" + str(gracenote["totalEpisodes"])
        episode_num += "."
        if "part" in gracenote: episode_num += str(gracenote["part"]-1)
        if "totalParts" in gracenote: episode_num += "/" + str(gracenote["totalParts"])
        return episode_num

    # handle Schedules Direct API calls and HTTP-Headers with decorators
    # Example syntax:
    # @sd_api_token_required
    # def sd_api_block():
    #     return requests.get(<The API call>, headers=headers)
    # sd_api_block()

    def sd_api_no_token(self,func):
        """API call with error handling. Note that the JSON is returned, not the response."""
        def call_func(*args, **kwargs):
            resp = None
            try:
                resp = func(*args, **kwargs)
            except Exception as e:
                if self.debug: print(f'{func.__name__} exception:\n{e}')
                self.return_value = 1
                return
            resp_json = None
            try:
                resp.raise_for_status()
                # assert resp.status_code < 400, f'API response status code {resp.status_code}.'
                resp_json = resp.json()
            except Exception as e:
                print(e)
                self.return_value = 1
                return
            if self.debug and resp_json is not None:
                json_prettyprint(resp_json, end='\n\n', flush=True)
            return resp_json
        return call_func

    def sd_api_token_required(self,func):
        """Set the HTTP Header "token" to the API token, call the API, then remove the header."""
        def call_func(*args, **kwargs):
            if not hasattr(self, "token"): self.api_token()
            try:
                self.headers["token"] = self.token
            except Exception as e:
                print(e)
                self.return_value = 1
                return
            @self.sd_api_no_token
            def sd_api_call():
                return func(*args, **kwargs)
            resp_json = sd_api_call()
            del self.headers["token"]
            return resp_json
        return call_func

    def sd_verbose_map(self, func):
        """Set the HTTP Header "verboseMap" to "true", per API documentation."""
        def call_func(*args, **kwargs):
            if self.verboseMap: self.headers["verboseMap"] = "true"
            resp_json = func(*args, **kwargs)
            self.headers.pop("verboseMap",None)  # silently delete "verboseMap"
            return resp_json
        return call_func

if __name__ == "__main__":
    parseArgs_flag = True  # set False for debugging within IDE
    sd = SD_JSON(parseArgs_flag=parseArgs_flag)
    sys.exit(sd.return_value)