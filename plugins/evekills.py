from datetime import datetime
#from lxml import etree
from xml import etree
import evelink.api
import evelink.eve

import ago
import json
import humanize

import traceback
import sys
import time
import stomp
import logging

logging.basicConfig() 
logging.getLogger("stomp.py").setLevel(logging.WARNING)

from errbot import botcmd, BotPlugin, PY2
from errbot.templating import tenv

if PY2:
    from urllib2 import urlopen, quote, Request
else:
    from urllib.request import urlopen, quote, Request

DEBUG = False

POLL_SECONDS = 300

class EveKills(BotPlugin):
    #min_err_version = '1.6.0' # Optional, but recommended
    #max_err_version = '2.0.0' # Optional, but recommended

    def activate(self):
        super(EveKills, self).activate()

        self.resetStomp()
        self.seen = []
        if not "users" in self:
            self["users"] = {}
        if not "stats" in self:
            self["stats"] = {"checks": 0, "lost": 0, "killed": 0, "errors": 0}

    def resetStomp(self):
        if "conn" in self:
            self.conn.disconnect()
        self.conn = stomp.Connection(host_and_ports=(("eve-kill.net", 61613),))
        self.conn.set_listener('', self)          
        self.conn.start()
        self.conn.connect(username="guest", passcode="guest")
        #self.conn.subscribe(destination="/topic/kills", id=1, ack='auto')
        # I get errors after the 15th subscribe, I think the stomp server limits us
        # so I'll listen to all kills instead.
        if 'users' in self:
            for userid in self["users"].keys():
                self.conn.subscribe(destination="/topic/involved.alliance.%d" % userid, id=userid, ack='auto')

    def on_error(self, headers, message):
        # STOMP error
        print('received an error %s' % message)

    def _our_guys(self, kill):
        """ Returns the guy if one of our guys is on the mail"""
        userids = self["users"].keys()
        #if kill["victim"]["characterID"] in userids:
        #    return self["users"][kill["victim"]["characterID"]]
        #for attacker in kill["attackers"]:
        #    if attacker["characterID"] in userids:
        #        return self["users"][attacker["characterID"]]
        #return None

        if kill['victim']['allianceID'] in userids:
            return self['users'][kill['victim']['allianceID']]
        for attacker in kill['attackers']:
            if attacker['allianceID'] in userids:
                return self['users'][attacker['allianceID']]
        return None


    def on_message(self, headers, message):
        # STOMP message                      
        kills = []
        stats = self["stats"]  #{"checks":0, "lost":0, "killed":0, "errors":0}
        stats["checks"] += 1

        kill = json.loads(message)

        killId = int(kill["killID"])
        if killId in self.seen:
            return  # we've already seen this killmail, ignore it.
        self.seen.append(killId)

        #no need to check, we are subscribed to alliance events
        #guy = self._our_guys(kill)
        #if guy is None:
        #    self["stats"] = stats
        #    return  # Killmail didn't have anyone we care about on it

        victimId = int(kill["victim"]["allianceID"])
        loss = victimId in self["users"].keys()
        if loss:  # For the !kill stats command...
            stats["lost"] += 1
        else:
            stats["killed"] += 1

        formattedKill = self._format_kill(kill, loss)

        #self.send(self["channel"], formattedKill, message_type="groupchat") # Announce it!
        self.send(self['channel'], formattedKill, message_type='groupchat')
        self["stats"] = stats  # Save our new stats to the shelf


    def _get_characer_id(self, name):
        # url = "http://api.eve-online.com/eve/CharacterID.xml.aspx?names=%s" % quote(name)
        # response = urlopen(url)
        # xml = etree.parse(response)
        # nodes = xml.xpath('/eveapi/result/rowset/row')
        # if len(nodes) == 0:
        #     raise Exception("Character not found")
        # node = nodes[0]
        # id = int(node.attrib["characterID"])
        # if id == 0:
        #     raise Exception("Character not found")
        # return id
        api = evelink.eve.EVE()
        try:
            id = api.character_id_from_name(name=name)[0]
        except Exception:
            raise Exception("Alliance not found")
        return id

    @staticmethod
    def _ship_name(itemId):
        if itemId in shipTypes:
            return shipTypes[itemId]
        return "???"

    @staticmethod
    def _value(kill):
        try:
            # print kill
            strValue = kill["zkb"]["totalValue"]
            value = round(float(strValue))
            return humanize.intword(value)
        except:
            print(traceback.format_exc())
            return "???"

    def _format_kill(self, kill, loss):
        """ Format the kill JSON into a nice string we can output"""        
        verb = "LOSS" if loss else "KILL"
        ship = self._ship_name(int(kill["victim"]["shipTypeID"]))
        url = "https://zkillboard.com/kill/%s/" % kill["killID"]
        value = self._value(kill)        
        #return "%s | %s (%s) | %s | %s isk | %s" % \
        #    (verb,
        #     kill["victim"]["characterName"],
        #     kill["victim"]["allianceName"],
        #     ship,
        #     value,
        #     url
        #    )
        response = tenv().get_template('killmail.html').render(loss=loss, name=kill['victim']['characterName'],
                                                               alliance=kill['victim']['allianceName'], ship=ship,
                                                               value=value, link=url)
        return response
    
    @botcmd(template="stats")
    def kill_stats(self, mess, args):
        return self["stats"]

    @botcmd(split_args_with=None)
    def kill_reset(self, mess, args):
        """Reset the connection"""
        self.resetStomp()
        self.seen = []
        self["stats"] = {"checks": 0, "lost": 0, "killed": 0, "errors": 0}
        return "Reset"

    @botcmd(split_args_with=None)
    def kill_announce(self, mess, args):
        """Set the bot to announce kills to this channel."""
        self["channel"] = mess.getFrom()
        return "I'll announce to this channel (%s) for now on." % self["channel"]

    @botcmd(split_args_with=None)
    def kill_watch(self, mess, args):
        """Start watching an eve guy for kills/losses.  Specify a character name."""        
        try:
            characterName = " ".join(args)
            characterId = self._get_characer_id(characterName)
            
            args = {'character_name': characterName, 'time': datetime.utcnow()}
            users = self["users"]
            users[characterId] = args
            self["users"] = users
            if "conn" in self:
                self.conn.subscribe(destination="/topic/involved.alliance.%d" % characterId, id=characterId, ack='auto')
            return "Added %s/%d" % (characterName, characterId)

        except Exception as e:
            return "Couldn't add you to the kill watchlist - %s" % e.message

    @botcmd(template="char_list")
    def kill_list(self, mess, args):
        """Show everyone who is on the watch list."""
        now = datetime.utcnow()
        members = self["users"].values()
        members = sorted(members, key=lambda member: member['character_name'])
        for member in members:            
            member['time_ago'] = ago.human(now - member['time'])

        return {'members': members}

    @botcmd(split_args_with=None)
    def kill_unwatch(self, mess, args):
        """Remove a character from the watch list"""
        
        characterName = " ".join(args)

        try:
            characterId = self._get_characer_id(characterName)
        except Exception as e:
            return "Something went wrong - %s" % e.message

        if characterId in self["users"]:
            del self["users"][characterId]
            self.resetStomp()
            return "Done."
        else:
            return "Couldn't find that person."



# yeah, I know... it's stupid to have this in here, but I was having 
# a hell of a time getting local imports working with the whole
# python 3.0/2.7 py2to3 thing
shipTypes = {
    23:"Cargo Container",
    2263:"Planetary Launch Container",
    3293:"Medium Standard Container",
    3296:"Large Standard Container",
    3297:"Small Standard Container",
    582:"Bantam",
    583:"Condor",
    584:"Griffin",
    585:"Slasher",
    586:"Probe",
    587:"Rifter",
    589:"Executioner",
    590:"Inquisitor",
    591:"Tormentor",
    592:"Navitas",
    593:"Tristan",
    594:"Incursus",
    595:"Gallente Police Ship",
    597:"Punisher",
    598:"Breacher",
    599:"Burst",
    600:"Minmatar Peacekeeper Ship",
    602:"Kestrel",
    603:"Merlin",
    605:"Heron",
    607:"Imicus",
    608:"Atron",
    609:"Maulus",
    613:"Devourer",
    614:"Fury",
    616:"Medusa",
    618:"Lynx",
    619:"Swordspine",
    1896:"Concord Police Frigate",
    1898:"Concord SWAT Frigate",
    1900:"Concord Army Frigate",
    1902:"Concord Special Ops Frigate",
    2161:"Crucifier",
    3532:"Echelon",
    3751:"SOCT 1",
    3753:"SOCT 2",
    3766:"Vigil",
    3768:"Amarr Police Frigate",
    11019:"Cockroach",
    11940:"Gold Magnate",
    11942:"Silver Magnate",
    17360:"Immovable Enigma",
    17619:"Caldari Navy Hookbill",
    17703:"Imperial Navy Slicer",
    17705:"Khanid Navy Frigate",
    17707:"Mordus Frigate",
    17812:"Republic Fleet Firetail",
    17841:"Federation Navy Comet",
    17924:"Succubus",
    17926:"Cruor",
    17928:"Daredevil",
    17930:"Worm",
    17932:"Dramiel",
    29248:"Magnate",
    32880:"Venture",
    32983:"Sukuuvestaa Heron",
    32985:"Inner Zone Shipping Imicus",
    32987:"Sarum Magnate",
    32989:"Vherokior Probe",
    33190:"Tash-Murkon Magnate",
    33468:"Astero",
    33655:"Punisher Kador Edition",
    33657:"Punisher Tash-Murkon Edition",
    33659:"Merlin Nugoeihuvi Edition",
    33661:"Merlin Wiyrkomi Edition",
    33663:"Rifter Nefantar Edition",
    33665:"Rifter Krusual Edition",
    33667:"Incursus Aliastra Edition",
    33669:"Incursus Innerzone Shipping Edition",
    33677:"Police Pursuit Comet",
    33816:"Garmur",
    620:"Osprey",
    621:"Caracal",
    622:"Stabber",
    623:"Moa",
    624:"Maller",
    625:"Augoror",
    626:"Vexor",
    627:"Thorax",
    628:"Arbitrator",
    629:"Rupture",
    630:"Bellicose",
    631:"Scythe",
    632:"Blackbird",
    633:"Celestis",
    634:"Exequror",
    635:"Opux Luxury Yacht",
    1904:"Concord Police Cruiser",
    2006:"Omen",
    11011:"Guardian-Vexor",
    17634:"Caracal Navy Issue",
    17709:"Omen Navy Issue",
    17713:"Stabber Fleet Issue",
    17715:"Gila",
    17718:"Phantasm",
    17720:"Cynabal",
    17722:"Vigilant",
    17843:"Vexor Navy Issue",
    17922:"Ashimmu",
    25560:"Opux Dragoon Yacht",
    29336:"Scythe Fleet Issue",
    29337:"Augoror Navy Issue",
    29340:"Osprey Navy Issue",
    29344:"Exequror Navy Issue",
    33470:"Stratios",
    33553:"Stratios Emergency Responder",
    33639:"Omen Kador Edition",
    33641:"Omen Tash-Murkon Edition",
    33643:"Caracal Nugoeihuvi Edition",
    33645:"Caracal Wiyrkomi Edition",
    33647:"Stabber Nefantar Edition",
    33649:"Stabber Krusual Edition",
    33651:"Thorax Aliastra Edition",
    33653:"Thorax Innerzone Shipping Edition",
    33818:"Orthrus",
    638:"Raven",
    639:"Tempest",
    640:"Scorpion",
    641:"Megathron",
    642:"Apocalypse",
    643:"Armageddon",
    644:"Typhoon",
    645:"Dominix",
    1912:"Concord Police Battleship",
    1914:"Concord Special Ops Battleship",
    1916:"Concord SWAT Battleship",
    1918:"Concord Army Battleship",
    4005:"Scorpion Ishukone Watch",
    11936:"Apocalypse Imperial Issue",
    11938:"Armageddon Imperial Issue",
    13202:"Megathron Federate Issue",
    17636:"Raven Navy Issue",
    17726:"Apocalypse Navy Issue",
    17728:"Megathron Navy Issue",
    17732:"Tempest Fleet Issue",
    17736:"Nightmare",
    17738:"Machariel",
    17740:"Vindicator",
    17918:"Rattlesnake",
    17920:"Bhaalgorn",
    24688:"Rokh",
    24690:"Hyperion",
    24692:"Abaddon",
    24694:"Maelstrom",
    26840:"Raven State Issue",
    26842:"Tempest Tribal Issue",
    32305:"Armageddon Navy Issue",
    32307:"Dominix Navy Issue",
    32309:"Scorpion Navy Issue",
    32311:"Typhoon Fleet Issue",
    33472:"Nestor",
    33623:"Abaddon Tash-Murkon Edition",
    33625:"Abaddon Kador Edition",
    33627:"Rokh Nugoeihuvi Edition",
    33629:"Rokh Wiyrkomi Edition",
    33631:"Maelstrom Nefantar Edition",
    33633:"Maelstrom Krusual Edition",
    33635:"Hyperion Aliastra Edition",
    33637:"Hyperion Innerzone Shipping Edition",
    33820:"Barghest",
    648:"Badger",
    649:"Tayra",
    650:"Nereus",
    651:"Hoarder",
    652:"Mammoth",
    653:"Wreathe",
    654:"Kryos",
    655:"Epithal",
    656:"Miasmos",
    657:"Iteron Mark V",
    1944:"Bestower",
    2863:"Primae",
    2998:"Noctis",
    4363:"Miasmos Quafe Ultra Edition",
    4388:"Miasmos Quafe Ultramarine Edition",
    19744:"Sigil",
    32811:"Miasmos Amastris Edition",
    33689:"Iteron Inner Zone Shipping Edition",
    33691:"Tayra Wiyrkomi Edition",
    33693:"Mammoth Nefantar Edition",
    33695:"Bestower Tash-Murkon Edition",
    670:"Capsule",
    33328:"Capsule - Genolution 'Auroral' 197-variant",
    671:"Erebus",
    3764:"Leviathan",
    11567:"Avatar",
    23773:"Ragnarok",
    672:"Caldari Shuttle",
    11129:"Gallente Shuttle",
    11132:"Minmatar Shuttle",
    11134:"Amarr Shuttle",
    21097:"Goru's Shuttle",
    21628:"Guristas Shuttle",
    27299:"Civilian Amarr Shuttle",
    27301:"Civilian Caldari Shuttle",
    27303:"Civilian Gallente Shuttle",
    27305:"Civilian Minmatar Shuttle",
    29266:"Apotheosis",
    29328:"Amarr Media Shuttle",
    29330:"Caldari Media Shuttle",
    29332:"Gallente Media Shuttle",
    29334:"Minmatar Media Shuttle",
    30842:"Interbus Shuttle",
    33513:"Leopard",
    588:"Reaper",
    596:"Impairor",
    601:"Ibis",
    606:"Velator",
    615:"Immolator",
    617:"Echo",
    1233:"Polaris Enigma Frigate",
    9854:"Polaris Inspector Frigate",
    9858:"Polaris Centurion TEST",
    9860:"Polaris Legatus Frigate",
    9862:"Polaris Centurion Frigate",
    33079:"Hematos",
    33081:"Taipan",
    33083:"Violator",
    2834:"Utu",
    3516:"Malice",
    11365:"Vengeance",
    11371:"Wolf",
    11373:"Blade",
    11375:"Erinye",
    11379:"Hawk",
    11381:"Harpy",
    11383:"Gatherer",
    11389:"Kishar",
    11393:"Retribution",
    11400:"Jaguar",
    12036:"Dagger",
    12042:"Ishkur",
    12044:"Enyo",
    32207:"Freki",
    32788:"Cambion",
    3465:"Large Secure Container",
    3466:"Medium Secure Container",
    3467:"Small Secure Container",
    11488:"Huge Secure Container",
    11489:"Giant Secure Container",
    11490:"Colossal Secure Container",
    2836:"Adrestia",
    3518:"Vangel",
    11993:"Cerberus",
    11999:"Vagabond",
    12003:"Zealot",
    12005:"Ishtar",
    12011:"Eagle",
    12015:"Muninn",
    12019:"Sacrilege",
    12023:"Deimos",
    32209:"Mimir",
    12731:"Bustard",
    12745:"Occator",
    12747:"Mastodon",
    12753:"Impel",
    3756:"Gnosis",
    16227:"Ferox",
    16229:"Brutix",
    16231:"Cyclone",
    16233:"Prophecy",
    24696:"Harbinger",
    24698:"Drake",
    24700:"Myrmidon",
    24702:"Hurricane",
    33151:"Brutix Navy Issue",
    33153:"Drake Navy Issue",
    33155:"Harbinger Navy Issue",
    33157:"Hurricane Fleet Issue",
    33869:"Brutix Serpentis Edition",
    33871:"Cyclone Thukker Tribe Edition",
    33873:"Ferox Guristas Edition",
    33875:"Prophecy Blood Raiders Edition",
    16236:"Coercer",
    16238:"Cormorant",
    16240:"Catalyst",
    16242:"Thrasher",
    32840:"InterBus Catalyst",
    32842:"Intaki Syndicate Catalyst",
    32844:"Inner Zone Shipping Catalyst",
    32846:"Quafe Catalyst",
    32848:"Aliastra Catalyst",
    32872:"Algos",
    32874:"Dragoon",
    32876:"Corax",
    32878:"Talwar",
    33099:"Nefantar Thrasher",
    33877:"Catalyst Serpentis Edition",
    33879:"Coercer Blood Raiders Edition",
    33881:"Cormorant Guristas Edition",
    33883:"Thrasher Thukker Tribe Edition",
    17363:"Small Audit Log Secure Container",
    17364:"Medium Audit Log Secure Container",
    17365:"Large Audit Log Secure Container",
    17366:"Station Container",
    17367:"Station Vault Container",
    17368:"Station Warehouse Container",
    17476:"Covetor",
    17478:"Retriever",
    17480:"Procurer",
    19720:"Revelation",
    19722:"Naglfar",
    19724:"Moros",
    19726:"Phoenix",
    20183:"Providence",
    20185:"Charon",
    20187:"Obelisk",
    20189:"Fenrir",
    22442:"Eos",
    22444:"Sleipnir",
    22446:"Vulture",
    22448:"Absolution",
    22466:"Astarte",
    22468:"Claymore",
    22470:"Nighthawk",
    22474:"Damnation",
    22452:"Heretic",
    22456:"Sabre",
    22460:"Eris",
    22464:"Flycatcher",
    22544:"Hulk",
    22546:"Skiff",
    22548:"Mackinaw",
    33683:"Mackinaw ORE Development Edition",
    23757:"Archon",
    23911:"Thanatos",
    23915:"Chimera",
    24483:"Nidhoggur",
    3468:"Plastic Wrap",
    24445:"Giant Freight Container",
    33003:"Enormous Freight Container",
    33005:"Huge Freight Container",
    33007:"Large Freight Container",
    33009:"Medium Freight Container",
    33011:"Small Freight Container",
    3514:"Revenant",
    3628:"Nation",
    22852:"Hel",
    23913:"Nyx",
    23917:"Wyvern",
    23919:"Aeon",
    11172:"Helios",
    11182:"Cheetah",
    11188:"Anathema",
    11192:"Buzzard",
    33397:"Chremoas",
    11176:"Crow",
    11178:"Raptor",
    11184:"Crusader",
    11186:"Malediction",
    11196:"Claw",
    11198:"Stiletto",
    11200:"Taranis",
    11202:"Ares",
    33673:"Whiptail",
    11978:"Scimitar",
    11985:"Basilisk",
    11987:"Guardian",
    11989:"Oneiros",
    32790:"Etana",
    11957:"Falcon",
    11963:"Rapier",
    11965:"Pilgrim",
    11969:"Arazu",
    33395:"Moracha",
    33675:"Chameleon",
    11377:"Nemesis",
    12032:"Manticore",
    12034:"Hound",
    12038:"Purifier",
    28352:"Rorqual",
    33687:"Rorqual ORE Development Edition",
    11174:"Keres",
    11190:"Sentinel",
    11194:"Kitsune",
    11387:"Hyena",
    11995:"Onyx",
    12013:"Broadsword",
    12017:"Devoter",
    12021:"Phobos",
    22428:"Redeemer",
    22430:"Sin",
    22436:"Widow",
    22440:"Panther",
    28659:"Paladin",
    28661:"Kronos",
    28665:"Vargur",
    28710:"Golem",
    28844:"Rhea",
    28846:"Nomad",
    28848:"Anshar",
    28850:"Ark",
    11959:"Rook",
    11961:"Huginn",
    11971:"Lachesis",
    20125:"Curse",
    28606:"Orca",
    33685:"Orca ORE Development Edition",
    2077:"Amarr Frigate Container",
    2163:"CONCORD Collection Vessel",
    2187:"Orca Container",
    2189:"Drone Infested Dominix",
    2214:"Guard Post",
    2903:"Manager's Station",
    3054:"Sansha Territorial Reclamation Outpost",
    3495:"Shield Transfer Control Tower",
    3502:"Nation Ore Refinery",
    3503:"Emergency Evacuation Freighter",
    3508:"Sansha Control Relay",
    30654:"Luxury Spaceliner",
    30762:"Dead Drop",
    30777:"Mizara Family Hovel",
    30783:"Colonial Supply Depot",
    30793:"Storage Warehouse Container",
    30805:"Wolf Burgan's Hideout",
    30820:"Generic Cargo Container",
    30899:"Cargo Wreathe",
    30949:"Josameto Verification Center",
    30953:"Cargo Facility 7A-21",
    30965:"Communications Array",
    32127:"Linked Broadcast Array Hub",
    32206:"Defiants Storage Facility",
    32224:"Conference Center ",
    32271:"Business Associate",
    32273:"Safe House Ruins",
    32291:"Chapel Container",
    32299:"Senator Pillius Ardanne",
    32394:"Serpentis Transport Hub",
    32404:"Cilis Leglise's Headquarters",
    29984:"Tengu",
    29986:"Legion",
    29988:"Proteus",
    29990:"Loki",
    2078:"Zephyr" }