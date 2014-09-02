__author__ = 'ghoti'
from errbot import BotPlugin, botcmd
import arrow
import logging
import configparser
import datetime
import os
import sqlite3
import time
import evelink.eve
import evelink.api
import evelink.map

EVESTATICDATADUMP = os.getcwd() + '/static.db'

class NotificationBot(BotPlugin):

    class Character(object):
        def __init__(self, name, keyid, vcode, dirkeyid, dirvcode, cachetimer):
            self.name = name
            self.keyid = keyid
            self.vcode = vcode
            self.dirkeyid = dirkeyid
            self.dirvcode = dirvcode
            self.cachetimer = cachetimer

    def loadapis(self):
        #this is a bad data structure to hold api info for each corp/character - but im lazy
        self.characters = []
        config = configparser.ConfigParser()
        for file in os.listdir('api/'):
            if file.endswith('.cfg'):
                #config.readfp(open('config/characters/'+file))
                config.read_file(open('api/'+file))
                name = config.get('api', 'CharacterName')
                keyid = config.get('api', 'keyid')
                vcode = config.get('api', 'vcode')
                dirkeyid = config.get('api', 'dirkeyid')
                dirvcode = config.get('api', 'dirvcode')
                cachetimer = 0

                self.characters.append(self.Character(name, keyid, vcode, dirkeyid, dirvcode, cachetimer))

    def noteid(self):
            return{
                #16:self.application,
                #17:self.denial,
                #18:self.acceptance,
                #5:self.war,    againstID: 99002172 cost: 0 declaredByID: 1690959089 delayHours: 24 hostileState: 0
                45:self.anchoralert,
                46:self.vulnstruct,
                47:self.invulnstruct,
                48:self.sbualert,
                75:self.toweralert,
                76:self.posfuel,
                77:self.stationservicealert,
                86:self.tcualert,
                87:self.sbushot,
                88:self.ihubalert,
                93:self.pocoalert,
                94:self.pocorf,
                96:self.fwwarn,
                97:self.fwkick,
                111:self.bounty,
                #128:self.joinfweddit #join note is same as app note with different id hue
            }

    def bounty(self, id, toon):
        logging.info("Bounty Message Called")
        bounty = self.gettext(id, toon)
        name = self.getname(bounty[id]['victimID'])
        message = 'A bounty on {0} was claimed!'.format(name[0])
        self.send('logistics@conference.j4lp.com', message, message_type='groupchat')

    def application(self, id, toon):
        logging.info("Application Message Called")
        app = self.gettext(id, toon)
        name = self.getname(app[id]['charID'])
        text = app[id]['applicationText'].strip()
        #corp = app[id]['corporationName']
        corp = self.getcorp(toon, app[id]['corpID'])
        if text:
            message = '{0} has apped to {1}: {2}'.format(name[0],corp, text)
        else:
            message = '{0} has apped to {1}'.format(name[0], corp)

    def denial(self, id, toon):
        app = self.gettext(id, toon)
        name = self.getname(app[id]['charID'])
        message = '{0} was denied into fweddit!'.format(name[0])

    def acceptance(self, id, toon):
        message = 'Someone was accepted into fweddit!'

    def anchoralert(self, id, toon):
        logging.info("Anchor alert")
        anchor = self.gettext(id, toon)
        conn = sqlite3.connect(EVESTATICDATADUMP)
        c = conn.cursor()
        moon = c.execute('select itemName from mapDenormalize where itemID={0}'.format(anchor[id]['moonID']))
        moon = moon.fetchone()[0]
        thing = c.execute('select typeName from invTypes where typeID={0}'.format(anchor[id]['typeID']))
        thing = thing.fetchone()[0]
        #who = self.getcorp(toon, anchor[id]['corpID'])
        who = self.getalliancefromid(toon, anchor[id]['allianceID'])
        message = '{0} was anchored on {1} by {2}!'.format(thing, moon, who)
        self.send('leadership@conference.j4lp.com', message, message_type="groupchat")

    def vulnstruct(self, id, toon):
        logging.info("Structure Vulnerable Warning")
        #allianceID: 99002172 corpID: 98114328 solarSystemID: 30004774
        # system vuln from sbu?
        vuln = self.gettext(id, toon)
        system = c.execute('select itemName from mapDenormalize where itemID={0}'.format(sbu[id]['solarSystemID']))
        system = system.fetchone()[0]
        #return 'Something went vulnerable in our sov!'
        message = '{0} has become vulnerable to attack!'.format(system)
        self.send('leadership@conference.j4lp.com', message, message_type="groupchat")

    def invulnstruct(self, id, toon):
        logging.info("Structure Invulnerable Warning")
        message = 'Something went invulnerable in our sov!'
        self.send('leadership@conference.j4lp.com', message, message_type="groupchat")

    def sbualert(self, id, toon):
        logging.info("SBU Alert")
        #allianceID: 99002172 corpID: 98114328 solarSystemID: 30004775
        sbu = self.gettext(id, toon)
        conn = sqlite3.connect(EVESTATICDATADUMP)
        c = conn.cursor()
        system = c.execute('select itemName from mapDenormalize where itemID={0}'.format(sbu[id]['solarSystemID']))
        system = system.fetchone()[0]
        corp = self.getcorp(toon, corpid=sbu[id]['corpID'])
        alliance = 'No Alliance'
        if sbu[id]['allianceID']:
            all = evelink.eve.EVE()
            #all.character_names_from_ids(id_list=(99002172))[0][99002172]
            alliance = all.character_names_from_ids(id_list=(sbu[id]['allianceID']))[0][sbu[id]['allianceID']]
            #alliance = self.getname(sbu[id]['allianceID'])[0][sbu[id]['allianceID']]
        message = 'An SBU has been anchored in {0} by a member of {1}/{2}!!!'.format(system, corp, alliance)
        self.send('leadership@conference.j4lp.com', message, message_type="groupchat")

    def posfuel(self, id, toon):
        #allianceID: 99002172 corpID: 98114328 moonID: 40302497 solarSystemID: 30004776 typeID: 20063 wants: - quantity: 189 typeID: 4312
        logging.info("Fuel Alert")
        #I HAS NO IDEA WHAT INFO IS USEFUL HERE
        pos = self.gettext(id, toon)
        conn = sqlite3.connect(EVESTATICDATADUMP)
        c = conn.cursor()
        moon = c.execute('select itemName from mapDenormalize where itemID={0}'.format(pos[id]['moonID']))
        moon = moon.fetchone()[0]
        corp = self.getcorp(toon, pos[id]['corpID'])
        fuel = c.execute('select typeName from invTypes where typeID={}'.format(pos[id]['typeID']))
        fuel = fuel.fetchone()[0]
        #message = 'THE TOWER AT %s NEEDS FUELS PLS - %d remaining' % (moon, pos[id]['- quantity'])
        message = 'FUEL ALERT: {}: {} has {} {} FUEL REMAINING'.format(corp, moon, pos[id]['- quantity'], fuel)
        self.send('logistics@conference.j4lp.com', message, message_type='groupchat')

    def stationservicealert(self, id, toon):
        logging.info("Station Service Alert")
        #<![CDATA[aggressorCorpID: null aggressorID: null shieldValue: 0.9989018188158935 solarSystemID: 30004776 stationID: 61000414 typeID: 28166]]>
        message = 'A Station Service is Under Attack!'
        self.send('leadership@conference.j4lp.com', message, message_type="groupchat")

    def toweralert(self, id, toon):
        logging.info("Tower Attack Alert")
        #aggressorAllianceID: 99001635 aggressorCorpID: 805828589 aggressorID: 90103336 armorValue: 1.0 hullValue: 1.0 moonID: 40171366 shieldValue: 0.9999959798917017 solarSystemID: 30002693 typeID: 20065
        pos = self.gettext(id, toon)
        conn = sqlite3.connect(EVESTATICDATADUMP)
        c = conn.cursor()
        moon = c.execute('select itemName from mapDenormalize where itemID={0}'.format(pos[id]['moonID']))
        moon = moon.fetchone()[0]
        what = c.execute('select typeName from invTypes where typeID={0}'.format(pos[id]['typeID'])).fetchone()[0]
        who = self.getname(pos[id]['aggressorID'])
        corp = self.getcorp(toon, pos[id]['aggressorCorpID'])
        try:
            alliance = self.getalliance(toon, pos[id]['aggressorID'])
        except:
            alliance = None
        message = 'The POS ({0}) at {1} was shot by {2}/{3}/{4}!'.format(what, moon, who[0], corp, alliance)
        message2 = 'Current HP status (S/A/H): {0:.0f}%/{0:.0f}%/{0:.0f}%'.format(float(pos[id]['shieldValue'])*100,
                                                                                  float(pos[id]['armorValue'])*100,
                                                                                  float(pos[id]['hullValue'])*100)
        self.send('leadership@conference.j4lp.com', message, message_type='groupchat')
        self.send('leadership@conference.j4lp.com', message2, message_type='groupchat')

    def tcualert(self, id, toon):
        logging.info("TCU Alert")
        sbu = self.gettext(id, toon)
        conn = sqlite3.connect(EVESTATICDATADUMP)
        c = conn.cursor()
        system = c.execute('select itemName from mapDenormalize where itemID={0}'.format(sbu[id]['solarSystemID']))
        system = system.fetchone()[0]

        who = self.getname(sbu[id]['aggressorID'])
        corp = self.getcorp(toon, sbu[id]['aggressorCorpID'])
        try:
            alliance = self.getalliance(toon, sbu[id]['aggressorID'])
        except:
            alliance = None
        message = 'The TCU at {0} was shot by {1}/{2}/{3}!'.format(system, who[0], corp, alliance)
        self.send('leadership@conference.j4lp.com', message, message_type="groupchat")

    def sbushot(self, id, toon):
        logging.info("SBU Shot Alert")
        #aggressorAllianceID: 99002172 aggressorCorpID: 98114328 aggressorID: 92014786 armorValue: 1.0 hullValue: 1.0 shieldValue: 0.9999877498283185 solarSystemID: 30004774
        sbu = self.gettext(id, toon)
        conn = sqlite3.connect(EVESTATICDATADUMP)
        c = conn.cursor()
        system = c.execute('select itemName from mapDenormalize where itemID={0}'.format(sbu[id]['solarSystemID']))
        system = system.fetchone()[0]

        who = self.getname(sbu[id]['aggressorID'])
        corp = self.getcorp(toon, sbu[id]['aggressorCorpID'])
        try:
            alliance = self.getalliance(toon, sbu[id]['aggressorID'])
        except:
            alliance = None
        message = 'An SBU at {0} was shot by {1}/{2}/{3}!'.format(system, who[0], corp, alliance)
        self.send('leadership@conference.j4lp.com', message, message_type="groupchat")

    def ihubalert(self, id, toon):
        logging.info("IHUB alert")
        #aggressorAllianceID: 99003550 aggressorCorpID: 98285822 aggressorID: 94377267 armorValue: 1.0 hullValue: 1.0 shieldValue: 0.999993179392 solarSystemID: 30004777
        #aggressorAllianceID: 99002172 aggressorCorpID: 98114328 aggressorID: 92014786 armorValue: 1.0 hullValue: 1.0 shieldValue: 0.9999877498283185 solarSystemID: 30004774
        sbu = self.gettext(id, toon)
        conn = sqlite3.connect(EVESTATICDATADUMP)
        c = conn.cursor()
        system = c.execute('select itemName from mapDenormalize where itemID={0}'.format(sbu[id]['solarSystemID']))
        system = system.fetchone()[0]

        who = self.getname(sbu[id]['aggressorID'])
        corp = self.getcorp(toon, sbu[id]['aggressorCorpID'])
        try:
            alliance = self.getalliance(toon, sbu[id]['aggressorID'])
        except:
            alliance = None
        message = 'The iHub at {0} was shot by {1}/{2}/{3}!'.format(system, who[0], corp, alliance)
        self.send("leadership@conference.j4lp.com", message, message_type="groupchat")

    def pocoalert(self, id, toon):
        logging.info("POCO Alert")
        #aggressorAllianceID: 99002172 aggressorCorpID: 98114328 aggressorID: 420385569 planetID: 40171284 planetTypeID: 2016 shieldLevel: 0.18022909510808988 solarSystemID: 30002693 typeID: 2233
        poco = self.gettext(id, toon)
        aggressor = self.getname(poco[id]['aggressorID'])
        conn = sqlite3.connect(EVESTATICDATADUMP)
        c = conn.cursor()
        planet = c.execute('select itemName from mapDenormalize where itemID={0}'.format(poco[id]['planetID']))
        planet = planet.fetchone()[0]
        message = '{0} has shot the POCO we own sitting on {1}!'.format(aggressor[0], planet)
        self.send('leadership@conference.j4lp.com', message, message_type="groupchat")

    def pocorf(self, id, toon):
        logging.info("POCO RF Alert")
        message = 'Someone reinforced a POCO we own!'
        self.send('leadership@conference.j4lp.com', message, message_type="groupchat")

    def fwwarn(self, id, toon):
        logging.info("FW Warning")
        message = 'We are in danger of being kicked from FW!'
        self.send('leadership@conference.j4lp.com', message, message_type="groupchat")

    def fwkick(self, id, toon):
        logging.info("FW Kicked")
        message = 'We have been kicked from FW! RIP!'
        self.send('leadership@conference.j4lp.com', message, message_type="groupchat")

    def joinfweddit(self, id, toon):
        logging.info("Join Corp")
        app = self.gettext(id, toon)
        name = self.getname(app[id]['charID'])
        corp = self.getcorp(toon, app[id]['corpID'])
        message = '{0} has joined {1}!'.format(name[0], corp)

    def gettext(self,notificationid, toon):
        api = evelink.api.API(api_key=(toon.keyid, toon.vcode))
        eve = evelink.eve.EVE()
        id = eve.character_id_from_name(toon.name)
        char = evelink.char.Char(char_id=id, api=api)

        notes = char.notification_texts(notification_ids=(notificationid))
        return notes[0]

    def getname(self, eveid):
        eve = evelink.eve.EVE()
        return eve.character_name_from_id(eveid)

    def getcorp(self, toon, corpid):
        api = evelink.api.API(api_key=(toon.keyid, toon.vcode))
        corp = evelink.corp.Corp(api=api)
        return corp.corporation_sheet(corpid)[0]['name']

    def getalliance(self, toon, char):
        #api = evelink.api.API(api_key=(toon.keyid, toon.vcode))
        alliance = evelink.eve.EVE()
        return alliance.affiliations_for_character(char_id=char)[0]['alliance']['name']

    def getalliancefromid(self, toon, id):
        alliance = evelink.eve.EVE()
        return alliance.alliances

    def runner(self):
        eve = evelink.eve.EVE()

        for toon in self.characters:

            if toon.cachetimer > arrow.utcnow().timestamp:
                #print('{} not ready yet: {} left'.format(toon.name, toon.cachetimer - arrow.utcnow().timestamp))
                continue

            api = evelink.api.API(api_key=(toon.keyid, toon.vcode))
            id = eve.character_id_from_name(toon.name)
            char = evelink.char.Char(char_id=id, api=api)

            notes = char.notifications()

            toon.cachetimer = notes.expires

            for notificationID in notes[0]:
                timesent = notes[0][notificationID]['timestamp']
                timesent = datetime.datetime.fromtimestamp(timesent)
                now = datetime.datetime.now()
                if timesent > now-datetime.timedelta(minutes=30):
                    sendme = self.noteid().get(int(notes[0][notificationID]['type_id']), '')
                    if sendme:
                        sendme(notificationID, toon)

    def activate(self):
        #activate ourself as a polling object
        super(NotificationBot, self).activate()
        #load the apis into a list
        self.loadapis()
        #start the poller, run every 5 minutes
        self.start_poller(59, self.runner)


