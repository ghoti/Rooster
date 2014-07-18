from __future__ import print_function

from errbot import BotPlugin, botcmd
import re
import requests
#import eveapi
import evelink.eve
import arrow
from collections import defaultdict


#Relic of outdated irc version of this same module, maybe used someday for xhtml formatting in err so it stays.
colours = defaultdict(str)
colours.update({
    "NORMAL": u"\u000f",
    "RED": u"\u000304",
    "GREEN": u"\u000309",
    "YELLOW": u"\u000308",
    "ORANGE": u"\u00037"
})

ZKBAPI = "https://zkillboard.com/api/stats/characterID/%s/"


class Who(BotPlugin):
    """Basic information on eve characters using killboard and evewho"""

    @staticmethod
    def formatsecstatus(data):
        data = "%.2f" % data
        value = float(data)
        if value < -5:
            return (colours["RED"], data)
        if value < 0:
            return (colours["ORANGE"], data)
        if value <= 4:
            return (colours["NORMAL"], data)
        if value > 4:
            return (colours["GREEN"], data)

    @staticmethod
    def getdetailshash(name):
        api = evelink.eve.EVE()

        r = api.character_id_from_name(name=name)
        if r[0] is None:
            r = api.character_id_from_name(name=name.title())
        #assert(len(r) > 0)
        id = r[0]
        r = api.character_info_from_id(char_id=id)
        return id, r

    @staticmethod
    def getkbstats(id):

        r = requests.get(ZKBAPI % id)
        data = r.json()
        kills = data["totals"]["countDestroyed"]
        lost = data["totals"]["countLost"]
        return "["+colours["GREEN"]+str(kills)+colours["NORMAL"]+", "+colours["RED"]+str(lost)+colours["NORMAL"]+"]"

    @botcmd(split_args_with=' ')
    def who(self, mess, args):
        """Usage: !who <player name>
        Is case sensitive, though does try to capitilize first and last name, but not always successful.

        Returns KB stats, corp, alliance, and length of service"""

        if not args or not mess:
            return 'Should I read your mind on who to look for?'
        colours.clear()
        target = ''
        for i in args:
            target += i + ' '
        target = target.strip()
        try:
            id, r = self.getdetailshash(target.strip())
        #PANIC ON ALL ERRORS
        except:
            return "There's no pilot by the name {0} or {1}, dumdum".format(target, target.capitalize())
        if r.result['sec_status']:
            sec = self.formatsecstatus(r.result['sec_status'])
        else:
            sec = ("", "")
        kbstats = self.getkbstats(id)
        created = arrow.get(r.result['corp']['timestamp']).humanize()
        startDate = arrow.get(r.result['history'][0]['start_ts']).humanize()

        if not r.result['alliance']['name']:
            return "{}{} {}{}{} [{}] - {} [{}]".format(sec[0], r.result['name'], "["+sec[1]+"]", colours["NORMAL"],
                                                       kbstats, created, r.result['corp']['name'], startDate)
        else:
            return "{}{} {}{}{} [{}] - {} [{}] - {}".format(
                sec[0], r.result['name'], "["+sec[1]+"]", colours["NORMAL"], kbstats, created, r.result['corp']['name'],
                startDate, r.result['alliance']['name'])