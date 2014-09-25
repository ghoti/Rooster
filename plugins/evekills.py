from datetime import datetime
#from lxml import etree
from xml import etree
import evelink.api
import evelink.eve

import ago
import arrow
import datetime
import json
import humanize
import csv
import traceback
import os
import sys
import time
import stomp
import logging

logging.basicConfig() 
logging.getLogger("stomp.py").setLevel(logging.WARNING)

from errbot import botcmd, BotPlugin, PY2
from errbot.templating import tenv

invtypes = {}
with open(os.path.dirname(os.path.abspath(sys.argv[0])) + '/invTypes.csv', 'r') as f:
    invreader = csv.reader(f, delimiter=',', quotechar='"')
    for i in invreader:
        invtypes[i[0]] = i[1]

class EveKills(BotPlugin):
    #min_err_version = '1.6.0' # Optional, but recommended
    #max_err_version = '2.0.0' # Optional, but recommended

    def activate(self):
        super(EveKills, self).activate()

        self.resetStomp()
        self.seen = []
        if not "value" in self:
            self["value"] = 10000000
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

        #stomp decided today to go apeshit and show kills from 2 weeks ago, this should fix that
        now = arrow.utcnow()
        killtime = arrow.get(kill['killTime'])
        length = now - killtime
        if length > datetime.timedelta(hours=2):
            return

        #no need to check, we are subscribed to alliance events
        #guy = self._our_guys(kill)
        #if guy is None:
        #    self["stats"] = stats
        #    return  # Killmail didn't have anyone we care about on it

        #kill isn't high enough value to be posted, ignore it
        if round(float(kill['zkb']['totalValue'])) < self['value']:
            self['stats'] = stats
            return

        victimId = int(kill["victim"]["allianceID"])
        loss = victimId in self["users"].keys()
        if loss:  # For the !kill stats command...
            stats["lost"] += 1
        else:
            stats["killed"] += 1

        formattedKill = self._format_kill(kill, loss)

        self.send(self['channel'], formattedKill, message_type='groupchat')
        self["stats"] = stats  # Save our new stats to the shelf


    def _get_characer_id(self, name):
        api = evelink.eve.EVE()
        try:
            id = api.character_id_from_name(name=name)[0]
        except Exception:
            raise Exception("Alliance not found")
        return id

    @staticmethod
    def _ship_name(itemId):
        try:
            ship = invtypes[str(itemId)]
        except KeyError:
            #this should never happen?
            ship = '???'
        return ship

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

        return {'members': members, 'value':humanize.intword(self['value'])}

    @botcmd(split_args_with=None)
    def kill_value(self, mess, args):
        """Limit kills to be announced over a given value in isk"""
        if not args:
            self['value'] = 10000000
            return 'Limiting kills announced to 10million ISK or higher'
        try:
            value = int(args[0])
        except Exception as e:
            return e
        else:
            self['value'] = value
        return "Now Limiting kills announced to values of {} ISK or higher".format(humanize.intword(value))


    @botcmd(split_args_with=' ')
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

